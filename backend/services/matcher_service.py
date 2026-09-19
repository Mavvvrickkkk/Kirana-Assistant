from rapidfuzz import process, fuzz
from sqlalchemy.orm import Session
from models import Product, ProductAlias

def get_product_candidates(db: Session, transcript: str):
    """Hybrid approach: gets exact aliases, or uses RapidFuzz to find top 5 candidates."""
    products = db.query(Product).all()
    aliases = db.query(ProductAlias).all()
    
    candidate_dict = {}
    for p in products:
        candidate_dict[p.name.lower()] = {"id": p.id, "name": p.name}
    for a in aliases:
        candidate_dict[a.alias.lower()] = {"id": a.product_id, "name": next((p.name for p in products if p.id == a.product_id), a.alias)}

    # Fuzzy match the transcript against all known names/aliases
    # We extract words from the transcript to find matches
    words = transcript.lower().split()
    best_matches = []
    
    for word in words:
        matches = process.extract(word, candidate_dict.keys(), scorer=fuzz.WRatio, limit=3)
        for match, score, _ in matches:
            if score > 75: # Threshold
                best_matches.append(candidate_dict[match])
                
    # Deduplicate
    unique_candidates = {v['id']: v for v in best_matches}.values()
    
    # If fuzzy failed, just send top 10 products as fallback catalog context
    if not unique_candidates:
        return [{"id": p.id, "name": p.name} for p in products[:10]]
        
    return list(unique_candidates)