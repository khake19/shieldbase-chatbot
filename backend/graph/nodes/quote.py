import json
import re
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from graph.state import ChatState
from utils.llm import get_llm

_llm = None

REQUIRED_FIELDS = {
    "auto": ["age", "vehicle_year", "driving_history", "coverage_level"],
    "home": ["property_value", "property_type", "coverage_level"],
    "life": ["age", "coverage_amount", "health_status", "term_length"],
}

FIELD_DESCRIPTIONS = {
    "age": "your age (in years)",
    "vehicle_year": "the model year of your vehicle",
    "driving_history": "your driving history (clean, minor, or major)",
    "coverage_level": "your preferred coverage level (basic, standard, or comprehensive)",
    "property_value": "the estimated value of your property (in dollars)",
    "property_type": "the type of property (house, condo, or apartment)",
    "coverage_amount": "the desired coverage amount (in dollars, minimum $10,000)",
    "health_status": "your current health status (excellent, good, fair, or poor)",
    "term_length": "the policy term length (10, 20, or 30 years)",
}


FIELD_VALIDATORS = {
    "age": lambda v: (int(v), "Age must be between 16 and 120." if not (16 <= int(v) <= 120) else None),
    "vehicle_year": lambda v: (int(v), f"Vehicle year must be between 1900 and {datetime.now().year}." if not (1900 <= int(v) <= datetime.now().year) else None),
    "property_value": lambda v: (float(str(v).replace(",", "").replace("$", "")), "Property value must be a positive number." if float(str(v).replace(",", "").replace("$", "")) <= 0 else None),
    "coverage_amount": lambda v: (float(str(v).replace(",", "").replace("$", "")), "Coverage amount must be at least $10,000." if float(str(v).replace(",", "").replace("$", "")) < 10000 else None),
    "term_length": lambda v: (int(v), "Term length must be 10, 20, or 30 years." if int(v) not in (10, 20, 30) else None),
    "coverage_level": lambda v: (str(v).lower(), "Coverage level must be basic, standard, or comprehensive." if str(v).lower() not in ("basic", "standard", "comprehensive") else None),
    "driving_history": lambda v: (str(v).lower(), "Driving history must be clean, minor, or major." if str(v).lower() not in ("clean", "minor", "major") else None),
    "property_type": lambda v: (str(v).lower(), "Property type must be house, condo, or apartment." if str(v).lower() not in ("house", "condo", "apartment") else None),
    "health_status": lambda v: (str(v).lower(), "Health status must be excellent, good, fair, or poor." if str(v).lower() not in ("excellent", "good", "fair", "poor") else None),
}


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(temperature=0)
    return _llm


def _append_message(state: ChatState, content: str) -> list:
    return list(state["messages"]) + [AIMessage(content=content)]


def quote_identify_product(state: ChatState) -> ChatState:
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    if state.get("insurance_type"):
        return {
            **state,
            "quote_step": "collect_details",
        }

    prompt = f"""Determine which insurance product the user wants. Reply with ONLY one of: "auto", "home", "life", or "unknown".

User message: {last_message}

Product:"""

    llm = _get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    product = response.content.strip().lower().strip('"\'')

    if product in ("auto", "home", "life"):
        return {
            **state,
            "insurance_type": product,
            "quote_step": "collect_details",
            "quote_data": {},
        }

    msg = "I'd be happy to help you get a quote! Which type of insurance are you interested in?\n\n- **Auto Insurance** — for your vehicle\n- **Home Insurance** — for your property\n- **Life Insurance** — for your family's financial security"

    return {
        **state,
        "messages": _append_message(state, msg),
    }


def quote_collect_details(state: ChatState) -> ChatState:
    insurance_type = state["insurance_type"]
    quote_data = dict(state.get("quote_data", {}))
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    required = REQUIRED_FIELDS[insurance_type]

    missing_before = [f for f in required if f not in quote_data]

    if missing_before and last_message:
        fields_to_extract = missing_before[:3]
        fields_json = json.dumps({f: FIELD_DESCRIPTIONS[f] for f in fields_to_extract})

        prompt = f"""Extract insurance quote details from the user's message. Return a JSON object with only the fields you can confidently extract. Return empty object {{}} if no fields are found.

Fields to look for: {fields_json}

Valid values:
- driving_history: "clean", "minor", or "major"
- coverage_level: "basic", "standard", or "comprehensive"
- property_type: "house", "condo", or "apartment"
- health_status: "excellent", "good", "fair", or "poor"
- term_length: 10, 20, or 30 (number)
- age, vehicle_year: integer numbers
- property_value, coverage_amount: numeric values (remove $ and commas)

User message: {last_message}

JSON:"""

        llm = _get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        json_match = re.search(r'\{[^{}]*\}', raw)
        if json_match:
            try:
                extracted = json.loads(json_match.group())
                for key, value in extracted.items():
                    if key in required and value is not None and value != "":
                        quote_data[key] = value
            except json.JSONDecodeError:
                pass

    # Fallback: if LLM didn't extract the expected field, try direct parsing
    still_missing = [f for f in required if f not in quote_data]
    if missing_before and still_missing and missing_before[0] == still_missing[0] and last_message:
        expected_field = missing_before[0]
        raw = last_message.strip().lower().replace("$", "").replace(",", "")

        parsed_value = None
        if expected_field in ("age", "vehicle_year", "term_length"):
            num_match = re.search(r'\d+', raw)
            if num_match:
                parsed_value = int(num_match.group())
        elif expected_field in ("property_value", "coverage_amount"):
            num_match = re.search(r'[\d.]+', raw)
            if num_match:
                parsed_value = float(num_match.group())
        elif expected_field == "driving_history":
            for val in ("clean", "minor", "major"):
                if val in raw:
                    parsed_value = val
                    break
        elif expected_field == "coverage_level":
            for val in ("basic", "standard", "comprehensive"):
                if val in raw:
                    parsed_value = val
                    break
        elif expected_field == "property_type":
            for val in ("house", "condo", "apartment"):
                if val in raw:
                    parsed_value = val
                    break
        elif expected_field == "health_status":
            for val in ("excellent", "good", "fair", "poor"):
                if val in raw:
                    parsed_value = val
                    break

        if parsed_value is not None:
            quote_data[expected_field] = parsed_value

    # Inline validation: check newly extracted fields immediately
    inline_errors = []
    for field in list(quote_data.keys()):
        if field not in missing_before:
            continue  # Skip fields that were already collected before this turn
        validator = FIELD_VALIDATORS.get(field)
        if validator:
            try:
                converted, error = validator(quote_data[field])
                if error:
                    inline_errors.append(error)
                    quote_data.pop(field)
                else:
                    quote_data[field] = converted
            except (ValueError, TypeError):
                quote_data.pop(field)
                inline_errors.append(f"Please provide a valid value for {FIELD_DESCRIPTIONS[field]}.")

    if inline_errors:
        error_msg = "\n".join(f"- {e}" for e in inline_errors)
        # Re-ask for the same field(s)
        still_needed = [f for f in required if f not in quote_data]
        next_field = still_needed[0] if still_needed else required[0]
        question = f"What is {FIELD_DESCRIPTIONS[next_field]}?"

        collected_summary = ""
        if quote_data:
            items = [f"  - **{k.replace('_', ' ').title()}**: {v}" for k, v in quote_data.items()]
            collected_summary = "Here's what I have so far:\n" + "\n".join(items) + "\n\n"

        msg = f"{error_msg}\n\n{collected_summary}{question}"
        return {
            **state,
            "quote_data": quote_data,
            "messages": _append_message(state, msg),
        }

    missing_after = [f for f in required if f not in quote_data]

    if not missing_after:
        return {
            **state,
            "quote_data": quote_data,
            "quote_step": "validate",
        }

    # Check if no new fields were extracted (user didn't provide useful data)
    no_new_data = missing_before == missing_after and last_message
    nudge = ""
    if no_new_data and quote_data:
        nudge = f"I didn't catch any new details from that. We're currently working on your **{insurance_type} insurance** quote.\n\n"

    next_field = missing_after[0]
    question = f"What is {FIELD_DESCRIPTIONS[next_field]}?"

    greeting = ""
    if not quote_data:
        type_label = {"auto": "auto", "home": "home", "life": "life"}[insurance_type]
        greeting = f"Great! Let's get you a {type_label} insurance quote. I'll need a few details from you.\n\n"

    collected_summary = ""
    if quote_data:
        items = [f"  - **{k.replace('_', ' ').title()}**: {v}" for k, v in quote_data.items()]
        collected_summary = "Here's what I have so far:\n" + "\n".join(items) + "\n\n"

    msg = f"{nudge}{greeting}{collected_summary}{question}"

    return {
        **state,
        "quote_data": quote_data,
        "messages": _append_message(state, msg),
    }


def quote_validate(state: ChatState) -> ChatState:
    quote_data = state.get("quote_data", {})
    insurance_type = state["insurance_type"]
    errors = []
    current_year = datetime.now().year

    if "age" in quote_data:
        try:
            age = int(quote_data["age"])
            if age < 16 or age > 120:
                errors.append("Age must be between 16 and 120.")
            quote_data["age"] = age
        except (ValueError, TypeError):
            errors.append("Age must be a valid number.")

    if "vehicle_year" in quote_data:
        try:
            year = int(quote_data["vehicle_year"])
            if year < 1900 or year > current_year:
                errors.append(f"Vehicle year must be between 1900 and {current_year}.")
            quote_data["vehicle_year"] = year
        except (ValueError, TypeError):
            errors.append("Vehicle year must be a valid number.")

    if "property_value" in quote_data:
        try:
            val = float(str(quote_data["property_value"]).replace(",", "").replace("$", ""))
            if val <= 0:
                errors.append("Property value must be a positive number.")
            quote_data["property_value"] = val
        except (ValueError, TypeError):
            errors.append("Property value must be a valid number.")

    if "coverage_amount" in quote_data:
        try:
            val = float(str(quote_data["coverage_amount"]).replace(",", "").replace("$", ""))
            if val < 10000:
                errors.append("Coverage amount must be at least $10,000.")
            quote_data["coverage_amount"] = val
        except (ValueError, TypeError):
            errors.append("Coverage amount must be a valid number.")

    if "coverage_level" in quote_data:
        level = str(quote_data["coverage_level"]).lower()
        if level not in ("basic", "standard", "comprehensive"):
            errors.append("Coverage level must be basic, standard, or comprehensive.")
        quote_data["coverage_level"] = level

    if "driving_history" in quote_data:
        history = str(quote_data["driving_history"]).lower()
        if history not in ("clean", "minor", "major"):
            errors.append("Driving history must be clean, minor, or major.")
        quote_data["driving_history"] = history

    if "property_type" in quote_data:
        ptype = str(quote_data["property_type"]).lower()
        if ptype not in ("house", "condo", "apartment"):
            errors.append("Property type must be house, condo, or apartment.")
        quote_data["property_type"] = ptype

    if "health_status" in quote_data:
        status = str(quote_data["health_status"]).lower()
        if status not in ("excellent", "good", "fair", "poor"):
            errors.append("Health status must be excellent, good, fair, or poor.")
        quote_data["health_status"] = status

    if "term_length" in quote_data:
        try:
            term = int(quote_data["term_length"])
            if term not in (10, 20, 30):
                errors.append("Term length must be 10, 20, or 30 years.")
            quote_data["term_length"] = term
        except (ValueError, TypeError):
            errors.append("Term length must be 10, 20, or 30.")

    if errors:
        error_msg = "I found some issues with the information provided:\n\n"
        error_msg += "\n".join(f"- {e}" for e in errors)
        error_msg += "\n\nPlease correct these and we'll try again."

        invalid_fields = []
        for err in errors:
            for field in REQUIRED_FIELDS[insurance_type]:
                if field.replace("_", " ") in err.lower() or any(
                    keyword in err.lower()
                    for keyword in field.split("_")
                ):
                    invalid_fields.append(field)

        for field in invalid_fields:
            quote_data.pop(field, None)

        return {
            **state,
            "quote_data": quote_data,
            "validation_errors": errors,
            "quote_step": "collect_details",
            "messages": _append_message(state, error_msg),
        }

    return {
        **state,
        "quote_data": quote_data,
        "validation_errors": [],
        "quote_step": "generate_quote",
    }


def quote_generate(state: ChatState) -> ChatState:
    quote_data = state["quote_data"]
    insurance_type = state["insurance_type"]

    if insurance_type == "auto":
        base = 500
        age = quote_data["age"]
        if age < 25:
            age_factor = 1.5
        elif age <= 65:
            age_factor = 1.0
        else:
            age_factor = 1.3

        history = quote_data["driving_history"]
        history_factor = {"clean": 0.9, "minor": 1.2, "major": 1.5}[history]

        coverage = quote_data["coverage_level"]
        coverage_factor = {"basic": 0.8, "standard": 1.0, "comprehensive": 1.5}[coverage]

        monthly = base * age_factor * history_factor * coverage_factor / 12

    elif insurance_type == "home":
        property_value = quote_data["property_value"]
        base = property_value * 0.003

        ptype = quote_data["property_type"]
        type_factor = {"apartment": 0.8, "house": 1.0, "condo": 0.9}[ptype]

        coverage = quote_data["coverage_level"]
        coverage_factor = {"basic": 0.7, "standard": 1.0, "comprehensive": 1.4}[coverage]

        monthly = base * type_factor * coverage_factor / 12

    elif insurance_type == "life":
        coverage_amount = quote_data["coverage_amount"]
        base = coverage_amount * 0.002

        age = quote_data["age"]
        if age < 30:
            age_factor = 0.8
        elif age <= 50:
            age_factor = 1.0
        else:
            age_factor = 1.5 if age <= 65 else 2.5

        health = quote_data["health_status"]
        health_factor = {"excellent": 0.8, "good": 1.0, "fair": 1.3, "poor": 1.8}[health]

        term = quote_data["term_length"]
        term_factor = {10: 0.8, 20: 1.0, 30: 1.3}[term]

        monthly = base * age_factor * health_factor * term_factor / 12
    else:
        monthly = 0

    monthly = round(monthly, 2)
    quote_data["monthly_premium"] = monthly

    return {
        **state,
        "quote_data": quote_data,
        "quote_step": "confirm",
    }


def quote_confirm(state: ChatState) -> ChatState:
    quote_data = state["quote_data"]
    insurance_type = state["insurance_type"]
    monthly = quote_data["monthly_premium"]
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    last_lower = last_message.lower()
    if any(word in last_lower for word in ["restart", "start over", "new quote", "different"]):
        msg = "No problem! Let's start a new quote. What type of insurance are you interested in?\n\n- **Auto Insurance**\n- **Home Insurance**\n- **Life Insurance**"
        return {
            **state,
            "quote_data": {},
            "quote_step": "identify_product",
            "insurance_type": None,
            "messages": _append_message(state, msg),
        }

    if any(word in last_lower for word in ["accept", "proceed", "enroll", "yes", "sure", "go ahead", "sign up"]):
        type_label = {"auto": "Auto", "home": "Home", "life": "Life"}[insurance_type]
        annual = round(monthly * 12, 2)
        msg = (
            f"Your **{type_label} Insurance** quote of **${monthly:,.2f}/month** (${annual:,.2f}/year) has been submitted!\n\n"
            "A ShieldBase representative will contact you within 1-2 business days to finalize your enrollment.\n\n"
            "Is there anything else I can help you with?"
        )
        return {
            **state,
            "current_mode": "router",
            "quote_step": None,
            "quote_data": {},
            "insurance_type": None,
            "messages": _append_message(state, msg),
        }

    if any(word in last_lower for word in ["adjust", "change", "modify", "update"]):
        msg = "Sure! What would you like to change about your quote? You can update any of the details you provided earlier."
        return {
            **state,
            "quote_step": "collect_details",
            "messages": _append_message(state, msg),
        }

    type_label = {"auto": "Auto", "home": "Home", "life": "Life"}[insurance_type]
    annual = round(monthly * 12, 2)

    details_lines = []
    display_fields = {k: v for k, v in quote_data.items() if k != "monthly_premium"}
    for key, value in display_fields.items():
        label = key.replace("_", " ").title()
        if isinstance(value, float) and key in ("property_value", "coverage_amount"):
            details_lines.append(f"- **{label}**: ${value:,.2f}")
        else:
            details_lines.append(f"- **{label}**: {str(value).title()}")

    details_str = "\n".join(details_lines)

    msg = f"""Here's your {type_label} Insurance quote from ShieldBase!

[QUOTE]

{type_label} Insurance Quote

{details_str}

---

**Monthly Premium: ${monthly:,.2f}/month**
**Annual Premium: ${annual:,.2f}/year**

[/QUOTE]

This quote is valid for 30 days. Would you like to:
- **Accept** this quote and proceed with enrollment
- **Adjust** any details to see a different price
- **Start over** with a new quote

What would you like to do?"""

    return {
        **state,
        "messages": _append_message(state, msg),
    }
