import json
import os
import re
from openai import OpenAI
from schemas import LLMExtractedIntent


class NLUService:

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_AI", "true").lower() == "true"
        self.model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        api_key = os.getenv("OPENAI_API_KEY", "mock-key")
        self.client = OpenAI(api_key=api_key) if not self.use_mock else None

    def parse_intent_and_entities(self, transcript: str) -> LLMExtractedIntent:
        if self.use_mock:
            return self._mock_parse(transcript)

        prompt = f"""
        Extract intent and entities from this Kirana shop transcript: "{transcript}"
        Intents: ADD_STOCK, REMOVE_STOCK, CHECK_STOCK, LOW_STOCK, SALES_SUMMARY, UNKNOWN
        Languages: English, Hindi, Telugu, Hinglish, Code-mixed.

        Output ONLY strict JSON format matching:
        {{
            "language": "string",
            "intent": "ADD_STOCK" | "REMOVE_STOCK" | "CHECK_STOCK" | "LOW_STOCK" | "SALES_SUMMARY" | "UNKNOWN",
            "items": [
                {{"product_mention": "string", "quantity": float or null, "unit": "string or null"}}
            ],
            "time_range": "today" | "week" | "month" | null
        }}
        """

        for attempt in range(2):
            try:
                res = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt}],
                )
                data = json.loads(res.choices[0].message.content)
                return LLMExtractedIntent(**data)
            except Exception:
                if attempt == 1:
                    return LLMExtractedIntent(
                        intent="UNKNOWN", items=[], language="en"
                    )

    def _mock_parse(self, transcript: str) -> LLMExtractedIntent:
        """Mock NLU that properly parses product mentions from transcript
        rather than hardcoding arbitrary products."""
        t = transcript.lower().strip()

        # Detect language
        language = "en"
        if any(w in t for w in ("cheyyi", "kavali", "undi", "biyyam", "chakkera")):
            language = "te"
        elif any(w in t for w in ("karo", "chahiye", "kitna", "chawal")):
            language = "hi"

        # ── Intent detection ───────────────────────────────────────────
        # LOW_STOCK
        if "low" in t or "running low" in t:
            return LLMExtractedIntent(intent="LOW_STOCK", items=[], language=language)

        # SALES_SUMMARY
        if "sold most" in t or "sales" in t or "selling" in t:
            time_range = "today"
            if "week" in t:
                time_range = "week"
            elif "month" in t:
                time_range = "month"
            return LLMExtractedIntent(
                intent="SALES_SUMMARY", items=[], time_range=time_range, language=language
            )

        # CHECK_STOCK
        if "how much" in t or "left" in t or "check" in t or "kitna" in t or "undi" in t:
            mention = self._extract_product_mention(t)
            items = [{"product_mention": mention}] if mention else []
            return LLMExtractedIntent(
                intent="CHECK_STOCK", items=items, language=language
            )

        # REMOVE_STOCK
        if "sold" in t or "remove" in t or "hatao" in t or "nikalo" in t:
            mention = self._extract_product_mention(t)
            qty = self._extract_quantity(t)
            unit = self._extract_unit(t)
            items = [{"product_mention": mention or "unknown", "quantity": qty, "unit": unit}] if mention else []
            return LLMExtractedIntent(
                intent="REMOVE_STOCK", items=items, language=language
            )

        # ADD_STOCK (default for "add", "cheyyi", etc.)
        if "add" in t or "cheyyi" in t or "karo" in t or "dalo" in t or t.strip():
            # Check for multi-item: "X and Y"
            items = self._extract_multi_items(t)
            if items:
                return LLMExtractedIntent(
                    intent="ADD_STOCK", items=items, language=language
                )

            mention = self._extract_product_mention(t)
            qty = self._extract_quantity(t)
            unit = self._extract_unit(t)
            if mention:
                return LLMExtractedIntent(
                    intent="ADD_STOCK",
                    items=[{"product_mention": mention, "quantity": qty, "unit": unit}],
                    language=language,
                )

        return LLMExtractedIntent(intent="UNKNOWN", items=[], language=language)

    def _extract_product_mention(self, text: str) -> str:
        """Extract product mention from transcript by removing known non-product words."""
        # Known product words/aliases to look for (order matters: longer first)
        known_products = [
            "basmati rice", "green gram", "moong dal", "green dal", "green peas",
            "rice", "sugar", "biyyam", "chawal", "chakkera", "dal",
            "wheat", "flour", "oil", "salt", "tea", "coffee",
            "rise",  # common typo for rice
        ]

        for product in known_products:
            if product in text:
                return product

        # Fallback: try to extract noun-like words (remove common verbs/prepositions)
        stop_words = {
            "add", "remove", "sold", "check", "how", "much", "is", "left",
            "the", "a", "an", "of", "to", "in", "and", "or", "my", "me",
            "kg", "kilo", "kilos", "gram", "grams", "litre", "litres", "ml",
            "piece", "pieces", "packet", "packets", "box", "boxes", "dozen",
            "bag", "bags", "carton", "cartons",
            "anna", "cheyyi", "karo", "dalo", "hatao", "nikalo",
            "5", "10", "20", "50", "100", "500", "1", "2", "3",
        }

        words = text.split()
        import string
        remaining = []
        for w in words:
            clean_w = w.strip(string.punctuation)
            if clean_w and clean_w not in stop_words and not clean_w.replace(".", "").isdigit():
                remaining.append(clean_w)
        return " ".join(remaining).strip() if remaining else ""

    def _extract_quantity(self, text: str) -> float:
        """Extract numeric quantity from transcript."""
        # Look for numbers (including decimals)
        numbers = re.findall(r'\d+\.?\d*', text)
        if numbers:
            # Return the first number found
            return float(numbers[0])
        return 1.0

    def _extract_unit(self, text: str) -> str:
        """Extract unit from transcript."""
        unit_keywords = {
            "kg": "kg", "kilo": "kg", "kilos": "kg", "kilogram": "kg",
            "gram": "gram", "grams": "gram", "g ": "gram",
            "litre": "litre", "litres": "litre", "liter": "litre",
            "ml": "ml",
            "piece": "piece", "pieces": "piece",
            "packet": "packet", "packets": "packet",
            "box": "box", "boxes": "box",
            "bag": "bag", "bags": "bag",
            "dozen": "dozen",
            "carton": "carton", "cartons": "carton",
        }
        for keyword, unit in unit_keywords.items():
            if keyword in text:
                return unit
        return "kg"

    def _extract_multi_items(self, text: str) -> list:
        """Extract multiple items from 'X and Y' patterns."""
        if " and " not in text:
            return []

        parts = text.split(" and ")
        items = []
        for part in parts:
            part = part.strip()
            mention = self._extract_product_mention(part)
            qty = self._extract_quantity(part)
            unit = self._extract_unit(part)
            if mention:
                items.append({"product_mention": mention, "quantity": qty, "unit": unit})

        return items if len(items) >= 2 else []