from functools import wraps

from flask import g, request

from .config import STATUS_ACTIVE
from .db import query_one
from .validation import error_response


def get_authenticated_user():
    header = request.headers.get("Authorization", "").strip()
    token = ""

    if header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()

    if not token:
        token = request.headers.get("X-API-Token", "").strip()

    if not token:
        return None

    user = query_one(
        """
        SELECT id, name, email, role, status, api_token, created_at, updated_at
        FROM users
        WHERE api_token = ?
        """,
        (token,),
    )
    if not user or user["status"] != STATUS_ACTIVE:
        return None
    return user


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return error_response(
                "Authentication required. Provide a valid bearer token for an active user.",
                401,
            )
        g.current_user = user
        return view_func(*args, **kwargs)

    return wrapper
