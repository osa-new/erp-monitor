from flask import Blueprint, render_template
from app.models import MonitoredEndpoint, CheckResult, AlertLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    endpoints = MonitoredEndpoint.query.all()
    recent_logs = CheckResult.query.order_by(CheckResult.checked_at.desc()).limit(200).all()
    recent_alerts = AlertLog.query.order_by(AlertLog.sent_at.desc()).limit(20).all()

    total = len(endpoints)
    up = sum(1 for e in endpoints if e.status == "up")
    down = sum(1 for e in endpoints if e.status == "down")
    unknown = sum(1 for e in endpoints if e.status == "unknown")

    total_checks = CheckResult.query.count()
    failed_checks = CheckResult.query.filter_by(success=False).count()
    overall_uptime = round((1 - failed_checks / total_checks) * 100, 2) if total_checks else None

    return render_template(
        "dashboard.html",
        endpoints=endpoints,
        recent_logs=recent_logs,
        recent_alerts=recent_alerts,
        stats={
            "total": total,
            "up": up,
            "down": down,
            "unknown": unknown,
            "overall_uptime": overall_uptime,
            "total_checks": total_checks,
            "failed_checks": failed_checks,
        },
    )
