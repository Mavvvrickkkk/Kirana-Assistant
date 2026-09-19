UNIT_CONVERSIONS = {
    "kg": {"base": "kg", "factor": 1.0},
    "kilo": {"base": "kg", "factor": 1.0},
    "kilos": {"base": "kg", "factor": 1.0},
    "kilogram": {"base": "kg", "factor": 1.0},
    "kilograms": {"base": "kg", "factor": 1.0},
    "gram": {"base": "kg", "factor": 0.001},
    "grams": {"base": "kg", "factor": 0.001},
    "g": {"base": "kg", "factor": 0.001},
    "litre": {"base": "litre", "factor": 1.0},
    "litres": {"base": "litre", "factor": 1.0},
    "liter": {"base": "litre", "factor": 1.0},
    "liters": {"base": "litre", "factor": 1.0},
    "l": {"base": "litre", "factor": 1.0},
    "ml": {"base": "litre", "factor": 0.001},
    "piece": {"base": "piece", "factor": 1.0},
    "pieces": {"base": "piece", "factor": 1.0},
    "packet": {"base": "packet", "factor": 1.0},
    "packets": {"base": "packet", "factor": 1.0},
    "box": {"base": "box", "factor": 1.0},
    "boxes": {"base": "box", "factor": 1.0},
    "carton": {"base": "carton", "factor": 1.0},
    "cartons": {"base": "carton", "factor": 1.0},
    "bag": {"base": "bag", "factor": 1.0},
    "bags": {"base": "bag", "factor": 1.0},
    "dozen": {"base": "dozen", "factor": 1.0},
}

def normalize_unit(unit_raw: str) -> str:
    if not unit_raw:
        return "kg"
    cleaned = unit_raw.lower().strip()
    if cleaned in UNIT_CONVERSIONS:
        return UNIT_CONVERSIONS[cleaned]["base"]
    return cleaned

def validate_and_convert_unit(requested_unit: str, base_unit: str, quantity: float):
    req_clean = requested_unit.lower().strip()
    base_clean = base_unit.lower().strip()

    if req_clean not in UNIT_CONVERSIONS or base_clean not in UNIT_CONVERSIONS:
        return False, quantity, f"Unsupported unit '{requested_unit}'."

    conv_req = UNIT_CONVERSIONS[req_clean]
    conv_base = UNIT_CONVERSIONS[base_clean]

    if conv_req["base"] != conv_base["base"]:
        return False, quantity, f"Unit '{requested_unit}' is incompatible with product base unit '{base_unit}'."

    normalized_qty = quantity * conv_req["factor"] / conv_base["factor"]
    return True, normalized_qty, None

def validate_operation(
    intent: str, quantity: float, unit: str, current_stock: float, base_unit: str = "kg"
):
    if quantity <= 0:
        return False, "Quantity must be greater than zero."
    if quantity > 10000:
        return False, "Quantity exceeds safety limit (10,000 units)."

    valid_unit, converted_qty, err = validate_and_convert_unit(unit, base_unit, quantity)
    if not valid_unit:
        return False, err

    if intent == "REMOVE_STOCK" and current_stock < converted_qty:
        return (
            False,
            f"Insufficient stock. Available: {current_stock} {base_unit}, Requested removal: {converted_qty} {base_unit}.",
        )

    return True, "Valid"