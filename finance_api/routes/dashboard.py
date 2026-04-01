from flask import Blueprint, request

from ..auth import require_auth
from ..config import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER
from ..db import query_all, query_one
from ..permissions import require_roles


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def build_filter_clause() -> tuple[str, list]:
    clauses = ["is_deleted = 0"]
    params: list = []

    start_date = request.args.get("start_date", "").strip()
    if start_date:
        clauses.append("record_date >= ?")
        params.append(start_date)

    end_date = request.args.get("end_date", "").strip()
    if end_date:
        clauses.append("record_date <= ?")
        params.append(end_date)

    record_type = request.args.get("type", "").strip().lower()
    if record_type in {"income", "expense"}:
        clauses.append("record_type = ?")
        params.append(record_type)

    category = request.args.get("category", "").strip()
    if category:
        clauses.append("LOWER(category) = LOWER(?)")
        params.append(category)

    return " AND ".join(clauses), params


@dashboard_bp.get("/summary")
@require_auth
@require_roles(ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)
def get_summary():
    where_clause, params = build_filter_clause()

    totals = query_one(
        f"""
        SELECT
            COALESCE(SUM(CASE WHEN record_type = 'income' THEN amount END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN record_type = 'expense' THEN amount END), 0) AS total_expenses,
            COUNT(*) AS total_records
        FROM financial_records
        WHERE {where_clause}
        """,
        tuple(params),
    )

    category_rows = query_all(
        f"""
        SELECT category, record_type, ROUND(SUM(amount), 2) AS total
        FROM financial_records
        WHERE {where_clause}
        GROUP BY category, record_type
        ORDER BY total DESC, category ASC
        """,
        tuple(params),
    )

    total_income = round(float(totals["total_income"]), 2)
    total_expenses = round(float(totals["total_expenses"]), 2)
    return {
        "data": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": round(total_income - total_expenses, 2),
            "total_records": totals["total_records"],
            "category_totals": category_rows,
        }
    }


@dashboard_bp.get("/recent-activity")
@require_auth
@require_roles(ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)
def recent_activity():
    limit = request.args.get("limit", "5")
    try:
        limit_value = max(1, min(int(limit), 20))
    except ValueError:
        limit_value = 5

    records = query_all(
        """
        SELECT id, amount, record_type, category, record_date, notes, updated_at
        FROM financial_records
        WHERE is_deleted = 0
        ORDER BY record_date DESC, updated_at DESC
        LIMIT ?
        """,
        (limit_value,),
    )
    return {"data": records, "count": len(records)}


@dashboard_bp.get("/trends")
@require_auth
@require_roles(ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN)
def trends():
    records = query_all(
        """
        SELECT
            SUBSTR(record_date, 1, 7) AS month,
            ROUND(SUM(CASE WHEN record_type = 'income' THEN amount ELSE 0 END), 2) AS income,
            ROUND(SUM(CASE WHEN record_type = 'expense' THEN amount ELSE 0 END), 2) AS expenses
        FROM financial_records
        WHERE is_deleted = 0
        GROUP BY SUBSTR(record_date, 1, 7)
        ORDER BY month ASC
        """
    )

    for row in records:
        row["net_balance"] = round(float(row["income"]) - float(row["expenses"]), 2)

    return {"data": records, "count": len(records)}
