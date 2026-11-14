from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import bp as auth_bp
    from .pages import bp as pages_bp
    from .backup import bp as backup_bp
    from .health import bp as health_bp
    from .api.summary import bp as api_summary_bp
    from .api.transactions import bp as api_tx_bp
    from .api.fixed_records import bp as api_fixed_bp
    from .api.products import bp as api_products_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(api_summary_bp)
    app.register_blueprint(api_tx_bp)
    app.register_blueprint(api_fixed_bp)
    app.register_blueprint(api_products_bp)
