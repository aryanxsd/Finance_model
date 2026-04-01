from flask import Blueprint, g, request

from ..auth import require_auth
from ..config import ROLE_ADMIN
from ..db import execute, query_all, query_one, utc_now
from ..permissions import require_roles
from ..validation import error_response, require_json, validate_user_payload


users_bp = Blueprint("users", __name__, url_prefix="/api/users")


def serialize_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "api_token": row["api_token"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@users_bp.get("")
@require_auth
@require_roles(ROLE_ADMIN)
def list_users():
    users = query_all(
        """
        SELECT id, name, email, role, status, api_token, created_at, updated_at
        FROM users
        ORDER BY id ASC
        """
    )
    return {"data": [serialize_user(user) for user in users], "count": len(users)}


@users_bp.post("")
@require_auth
@require_roles(ROLE_ADMIN)
def create_user():
    try:
        payload = validate_user_payload(require_json(request.get_json(silent=True)))
    except ValueError as exc:
        return error_response(str(exc), 400)

    existing = query_one("SELECT id FROM users WHERE email = ?", (payload["email"],))
    if existing:
        return error_response("A user with this email already exists.", 409)

    timestamp = utc_now()
    token = f"{payload['role']}-{payload['email'].replace('@', '-at-')}"
    user_id = execute(
        """
        INSERT INTO users (name, email, role, status, api_token, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["name"],
            payload["email"],
            payload["role"],
            payload["status"],
            token,
            timestamp,
            timestamp,
        ),
    )
    created = query_one(
        """
        SELECT id, name, email, role, status, api_token, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    return {"message": "User created successfully.", "data": serialize_user(created)}, 201


@users_bp.get("/<int:user_id>")
@require_auth
@require_roles(ROLE_ADMIN)
def get_user(user_id: int):
    user = query_one(
        """
        SELECT id, name, email, role, status, api_token, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    if not user:
        return error_response("User not found.", 404)
    return {"data": serialize_user(user)}


@users_bp.patch("/<int:user_id>")
@require_auth
@require_roles(ROLE_ADMIN)
def update_user(user_id: int):
    existing = query_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not existing:
        return error_response("User not found.", 404)

    try:
        payload = validate_user_payload(require_json(request.get_json(silent=True)), partial=True)
    except ValueError as exc:
        return error_response(str(exc), 400)

    if not payload:
        return error_response("At least one field must be provided for update.", 400)

    if "email" in payload:
        duplicate = query_one("SELECT id FROM users WHERE email = ? AND id != ?", (payload["email"], user_id))
        if duplicate:
            return error_response("A user with this email already exists.", 409)

    updated_values = {
        "name": payload.get("name", existing["name"]),
        "email": payload.get("email", existing["email"]),
        "role": payload.get("role", existing["role"]),
        "status": payload.get("status", existing["status"]),
        "updated_at": utc_now(),
    }

    api_token = existing["api_token"]
    if "role" in payload or "email" in payload:
        api_token = f"{updated_values['role']}-{updated_values['email'].replace('@', '-at-')}"

    execute(
        """
        UPDATE users
        SET name = ?, email = ?, role = ?, status = ?, api_token = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            updated_values["name"],
            updated_values["email"],
            updated_values["role"],
            updated_values["status"],
            api_token,
            updated_values["updated_at"],
            user_id,
        ),
    )

    user = query_one(
        """
        SELECT id, name, email, role, status, api_token, created_at, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    return {"message": "User updated successfully.", "data": serialize_user(user)}


@users_bp.get("/me")
@require_auth
def me():
    return {"data": serialize_user(g.current_user)}
