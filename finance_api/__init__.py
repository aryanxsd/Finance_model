from collections import defaultdict, deque
from time import time

from flask import Flask, request

from .db import close_db, init_db
from .routes.dashboard import dashboard_bp
from .routes.records import records_bp
from .routes.users import users_bp
from .validation import error_response


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_PATH="finance_dashboard.db",
        JSON_SORT_KEYS=False,
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_MAX_REQUESTS=60,
        RATE_LIMIT_WINDOW_SECONDS=60,
    )

    if test_config:
        app.config.update(test_config)

    rate_limit_store: dict[str, deque] = defaultdict(deque)

    app.teardown_appcontext(close_db)
    app.register_blueprint(users_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(dashboard_bp)

    @app.before_request
    def apply_rate_limit():
        if not app.config.get("RATE_LIMIT_ENABLED", True):
            return None

        if request.endpoint == "health_check" or request.path.startswith("/static/"):
            return None

        identifier = (
            request.headers.get("Authorization", "").strip()
            or request.headers.get("X-API-Token", "").strip()
            or request.remote_addr
            or "anonymous"
        )
        window_seconds = int(app.config["RATE_LIMIT_WINDOW_SECONDS"])
        max_requests = int(app.config["RATE_LIMIT_MAX_REQUESTS"])
        now = time()
        bucket = rate_limit_store[identifier]

        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()

        if len(bucket) >= max_requests:
            return error_response(
                "Rate limit exceeded. Please retry after the current window resets.",
                429,
                details={
                    "limit": max_requests,
                    "window_seconds": window_seconds,
                },
            )

        bucket.append(now)
        return None

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(_error):
        return error_response("Endpoint not found.", 404)

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return error_response("Method not allowed for this endpoint.", 405)

    @app.errorhandler(500)
    def internal_error(_error):
        return error_response("An unexpected server error occurred.", 500)

    with app.app_context():
        init_db()

    return app
