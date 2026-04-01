from flask import Blueprint, g, request

from ..auth import require_auth
from ..config import ROLE_ADMIN, ROLE_ANALYST
from ..db import execute, query_all, query_one, utc_now
from ..permissions import require_roles
from ..validation import error_response, require_json, validate_record_payload


records_bp = Blueprint("records", __name__, url_prefix="/api/records")


def serialize_record(row: dict) -> dict:
    return {
        "id": row["id"],
        "amount": row["amount"],
        "type": row["record_type"],
        "category": row["category"],
        "date": row["record_date"],
        "notes": row["notes"],
        "created_by": row["created_by"],
        "updated_by": row["updated_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_record_or_404(record_id: int) -> dict | None:
    return query_one(
        """
        SELECT id, amount, record_type, category, record_date, notes,
               created_by, updated_by, created_at, updated_at
        FROM financial_records
        WHERE id = ? AND is_deleted = 0
        """,
        (record_id,),
    )


@records_bp.get("")
@require_auth
@require_roles(ROLE_ANALYST, ROLE_ADMIN)
def list_records():
    query = """
        SELECT id, amount, record_type, category, record_date, notes,
               created_by, updated_by, created_at, updated_at
        FROM financial_records
        WHERE is_deleted = 0
    """
    params: list = []

    record_type = request.args.get("type", "").strip().lower()
    if record_type:
        if record_type not in {"income", "expense"}:
            return error_response("Query parameter 'type' must be income or expense.", 400)
        query += " AND record_type = ?"
        params.append(record_type)

    category = request.args.get("category", "").strip()
    if category:
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)

    search_term = request.args.get("search", "").strip()
    if search_term:
        query += " AND (LOWER(category) LIKE LOWER(?) OR LOWER(COALESCE(notes, '')) LIKE LOWER(?))"
        wildcard_term = f"%{search_term}%"
        params.extend([wildcard_term, wildcard_term])

    start_date = request.args.get("start_date", "").strip()
    if start_date:
        query += " AND record_date >= ?"
        params.append(start_date)

    end_date = request.args.get("end_date", "").strip()
    if end_date:
        query += " AND record_date <= ?"
        params.append(end_date)

    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "10"))
    except ValueError:
        return error_response("Query parameters 'page' and 'page_size' must be integers.", 400)

    if page < 1:
        return error_response("Query parameter 'page' must be greater than 0.", 400)
    if page_size < 1 or page_size > 100:
        return error_response("Query parameter 'page_size' must be between 1 and 100.", 400)

    count_row = query_one(f"SELECT COUNT(*) AS total FROM ({query}) AS filtered_records", tuple(params))
    total_count = count_row["total"] if count_row else 0
    offset = (page - 1) * page_size

    paginated_query = query + " ORDER BY record_date DESC, id DESC LIMIT ? OFFSET ?"
    records = query_all(paginated_query, tuple([*params, page_size, offset]))
    return {
        "data": [serialize_record(record) for record in records],
        "count": len(records),
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": (total_count + page_size - 1) // page_size if total_count else 0,
        },
        "filters": {
            "type": record_type or None,
            "category": category or None,
            "search": search_term or None,
            "start_date": start_date or None,
            "end_date": end_date or None,
        },
    }


@records_bp.post("")
@require_auth
@require_roles(ROLE_ADMIN)
def create_record():
    try:
        payload = validate_record_payload(require_json(request.get_json(silent=True)))
    except ValueError as exc:
        return error_response(str(exc), 400)

    timestamp = utc_now()
    record_id = execute(
        """
        INSERT INTO financial_records (
            amount, record_type, category, record_date, notes,
            created_by, updated_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["amount"],
            payload["record_type"],
            payload["category"],
            payload["record_date"],
            payload["notes"],
            g.current_user["id"],
            g.current_user["id"],
            timestamp,
            timestamp,
        ),
    )
    created = get_record_or_404(record_id)
    return {"message": "Financial record created successfully.", "data": serialize_record(created)}, 201


@records_bp.get("/<int:record_id>")
@require_auth
@require_roles(ROLE_ANALYST, ROLE_ADMIN)
def get_record(record_id: int):
    record = get_record_or_404(record_id)
    if not record:
        return error_response("Financial record not found.", 404)
    return {"data": serialize_record(record)}


@records_bp.patch("/<int:record_id>")
@require_auth
@require_roles(ROLE_ADMIN)
def update_record(record_id: int):
    existing = get_record_or_404(record_id)
    if not existing:
        return error_response("Financial record not found.", 404)

    try:
        payload = validate_record_payload(require_json(request.get_json(silent=True)), partial=True)
    except ValueError as exc:
        return error_response(str(exc), 400)

    if not payload:
        return error_response("At least one field must be provided for update.", 400)

    updated = {
        "amount": payload.get("amount", existing["amount"]),
        "record_type": payload.get("record_type", existing["record_type"]),
        "category": payload.get("category", existing["category"]),
        "record_date": payload.get("record_date", existing["record_date"]),
        "notes": payload.get("notes", existing["notes"]),
        "updated_at": utc_now(),
    }

    execute(
        """
        UPDATE financial_records
        SET amount = ?, record_type = ?, category = ?, record_date = ?, notes = ?,
            updated_by = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            updated["amount"],
            updated["record_type"],
            updated["category"],
            updated["record_date"],
            updated["notes"],
            g.current_user["id"],
            updated["updated_at"],
            record_id,
        ),
    )
    record = get_record_or_404(record_id)
    return {"message": "Financial record updated successfully.", "data": serialize_record(record)}


@records_bp.delete("/<int:record_id>")
@require_auth
@require_roles(ROLE_ADMIN)
def delete_record(record_id: int):
    existing = get_record_or_404(record_id)
    if not existing:
        return error_response("Financial record not found.", 404)

    execute(
        """
        UPDATE financial_records
        SET is_deleted = 1, updated_by = ?, updated_at = ?
        WHERE id = ?
        """,
        (g.current_user["id"], utc_now(), record_id),
    )
    return {"message": "Financial record deleted successfully."}
