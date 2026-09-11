import os

os.environ["CASHFLOW_ENV"] = "production"
os.environ["CASHFLOW_SECRET_KEY"] = "test-secret-key-that-is-not-committed"
os.environ["CASHFLOW_DATABASE_URI"] = "sqlite:///:memory:"
os.environ.pop("CASHFLOW_ADMIN_USERNAME", None)
os.environ.pop("CASHFLOW_ADMIN_PASSWORD", None)

from app import create_app

app = create_app()
assert app.config["SECRET_KEY"] == "test-secret-key-that-is-not-committed"
assert app.config["SESSION_COOKIE_HTTPONLY"] is True
assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
assert app.config["SESSION_COOKIE_SECURE"] is False
assert app.url_map is not None
print("security configuration: ok")
