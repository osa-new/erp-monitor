from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
scheduler = APScheduler()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///monitor.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SCHEDULER_API_ENABLED"] = False
    app.config["CHECK_INTERVAL_SECONDS"] = int(os.getenv("CHECK_INTERVAL_SECONDS", 60))

    db.init_app(app)

    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
        db.create_all()
        _seed_default_endpoints()

    scheduler.init_app(app)
    from app.services.checker import run_all_checks
    scheduler.add_job(
        id="health_check",
        func=run_all_checks,
        args=[app],
        trigger="interval",
        seconds=app.config["CHECK_INTERVAL_SECONDS"],
    )
    scheduler.start()

    return app


def _seed_default_endpoints():
    from app.models import MonitoredEndpoint
    if MonitoredEndpoint.query.count() == 0:
        defaults = [
            MonitoredEndpoint(name="JSONPlaceholder API", url="https://jsonplaceholder.typicode.com/posts/1", method="GET", expected_status=200, timeout=10),
            MonitoredEndpoint(name="HTTPBin Status 200", url="https://httpbin.org/status/200", method="GET", expected_status=200, timeout=10),
            MonitoredEndpoint(name="HTTPBin Delay", url="https://httpbin.org/delay/1", method="GET", expected_status=200, timeout=15),
            MonitoredEndpoint(name="HTTPBin 500 (Failure)", url="https://httpbin.org/status/500", method="GET", expected_status=200, timeout=10),
        ]
        for ep in defaults:
            db.session.add(ep)
        db.session.commit()
