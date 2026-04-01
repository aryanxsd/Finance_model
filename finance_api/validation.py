from datetime import date

from flask import jsonify

from .config import VALID_ROLES, VALID_STATUSES


def error_response(message: str, status_code: int, details: dict | None = None):
    payload = {"error": {"message": message, "status": status_code}}
    if details:
        payload["error"]["details"] = details
    response = jsonify(payload)
    response.status_code = status_code
    return response


def require_json(payload):
    if payload is None:
        raise ValueError("Request body must be valid JSON.")
    return payload


def validate_email(email: str) -> str:
    value = str(email).strip().lower()
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("Email must be a valid email address.")
    return value


def validate_user_payload(payload: dict, partial: bool = False) -> dict:
    cleaned = {}

    if not partial or "name" in payload:
        name = str(payload.get("name", "")).strip()
        if len(name) < 2:
            raise ValueError("Name must be at least 2 characters long.")
        cleaned["name"] = name

    if not partial or "email" in payload:
        cleaned["email"] = validate_email(payload.get("email", ""))

    if not partial or "role" in payload:
        role = str(payload.get("role", "")).strip().lower()
        if role not in VALID_ROLES:
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}.")
        cleaned["role"] = role

    if not partial or "status" in payload:
        status = str(payload.get("status", "")).strip().lower()
        if status not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}.")
        cleaned["status"] = status

    return cleaned


def validate_record_payload(payload: dict, partial: bool = False) -> dict:
    cleaned = {}

    if not partial or "amount" in payload:
        try:
            amount = float(payload.get("amount"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Amount must be a number.") from exc
        if amount < 0:
            raise ValueError("Amount must be greater than or equal to 0.")
        cleaned["amount"] = round(amount, 2)

    if not partial or "type" in payload:
        record_type = str(payload.get("type", "")).strip().lower()
        if record_type not in {"income", "expense"}:
            raise ValueError("Type must be either 'income' or 'expense'.")
        cleaned["record_type"] = record_type

    if not partial or "category" in payload:
        category = str(payload.get("category", "")).strip()
        if len(category) < 2:
            raise ValueError("Category must be at least 2 characters long.")
        cleaned["category"] = category

    if not partial or "date" in payload:
        value = str(payload.get("date", "")).strip()
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Date must use ISO format YYYY-MM-DD.") from exc
        cleaned["record_date"] = value

    if not partial or "notes" in payload:
        notes = payload.get("notes")
        if notes is not None:
            notes = str(notes).strip()
            if len(notes) > 500:
                raise ValueError("Notes must be 500 characters or fewer.")
        cleaned["notes"] = notes

    return cleaned
