from functools import wraps

from flask import g

from .validation import error_response


def require_roles(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            current_user = g.current_user
            if current_user["role"] not in allowed_roles:
                return error_response(
                    f"Role '{current_user['role']}' is not allowed to perform this action.",
                    403,
                )
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
