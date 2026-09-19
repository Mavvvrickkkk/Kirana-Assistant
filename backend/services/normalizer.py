import os
from models import Product, ProductAlias
from rapidfuzz import fuzz, process
from sqlalchemy import func
from sqlalchemy.orm import Session
from openai import OpenAI
import json


class ProductNormalizer:

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_AI", "true").lower() == "true"
        api_key = os.getenv("OPENAI_API_KEY", "mock-key")
        self.client = OpenAI(api_key=api_key) if not self.use_mock else None

    def normalize(self, mention: str, db: Session):
        if not mention:
            return None, 0.0, True, "No product mentioned."

        cleaned = mention.lower().strip()
        products = db.query(Product).filter(Product.is_active == True).all()

        # 1. Exact canonical match
        for p in products:
            if p.name.lower() == cleaned or (
                p.name_local and p.name_local.lower() == cleaned
            ):
                return p, 1.0, False, None

        # 2. Exact alias match
        alias_entry = (
            db.query(ProductAlias)
            .filter(func.lower(ProductAlias.alias) == cleaned)
            .first()
        )
        if alias_entry:
            p = (
                db.query(Product)
                .filter(Product.id == alias_entry.product_id)
                .first()
            )
            if p:
                return p, 0.98, False, None

        # 3. RapidFuzz candidate scoring
        candidates_map = {p.name.lower(): p for p in products}
        alias_rows = db.query(ProductAlias).all()
        for a in alias_rows:
            p = db.query(Product).filter(Product.id == a.product_id).first()
            if p:
                candidates_map[a.alias.lower()] = p

        matches = process.extract(
            cleaned, candidates_map.keys(), scorer=fuzz.WRatio, limit=3
        )
        valid_matches = [m for m in matches if m[1] >= 55]

        if not valid_matches:
            return (
                None,
                0.0,
                True,
                f"Product '{mention}' not found in catalog.",
            )

        # 4. Ambiguity / Middle-confidence check
        if (
            len(valid_matches) > 1
            and abs(valid_matches[0][1] - valid_matches[1][1]) <= 25
        ):
            p1 = candidates_map[valid_matches[0][0]]
            p2 = candidates_map[valid_matches[1][0]]
            if p1.id != p2.id:
                # If LLM is available, let LLM choose ONLY from candidates
                if not self.use_mock:
                    resolved_id = self._llm_resolve_ambiguity(
                        mention, [p1, p2]
                    )
                    if resolved_id:
                        matched_p = next(
                            (x for x in [p1, p2] if x.id == resolved_id), None
                        )
                        if matched_p:
                            return matched_p, 0.85, False, None
                return (
                    None,
                    0.5,
                    True,
                    f"Which product do you mean: {p1.name} or {p2.name}?",
                )

        best_match_key = valid_matches[0][0]
        score = valid_matches[0][1] / 100.0
        best_product = candidates_map[best_match_key]
        return best_product, score, False, None

    def _llm_resolve_ambiguity(self, mention: str, candidates: list):
        try:
            cand_list = [{"id": c.id, "name": c.name} for c in candidates]
            prompt = f"User mentioned '{mention}'. Choose the correct product ID from these candidates only: {json.dumps(cand_list)}. Return strict JSON: {{\"product_id\": int}}"
            res = self.client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4-turbo-preview"),
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            data = json.loads(res.choices[0].message.content)
            return data.get("product_id")
        except Exception:
            return None

    def learn_alias(
        self, product_id: int, alias: str, db: Session, language: str = "te"
    ):
        cleaned = alias.lower().strip()
        existing = (
            db.query(ProductAlias)
            .filter(
                ProductAlias.product_id == product_id,
                func.lower(ProductAlias.alias) == cleaned,
            )
            .first()
        )
        if existing:
            existing.usage_count += 1
        else:
            db.add(
                ProductAlias(
                    product_id=product_id,
                    alias=cleaned,
                    language=language,
                    source="user_confirmed",
                    usage_count=1,
                )
            )
        db.commit()