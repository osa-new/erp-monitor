from flask import Blueprint, request, jsonify
from app import db
from app.models import MonitoredEndpoint, CheckResult, AlertLog
from app.services.auth import require_auth
from app.services.checker import check_endpoint, maybe_send_alert
from flask import current_app

api_bp = Blueprint("api", __name__)


# ── Endpoints CRUD ──────────────────────────────────────────────────────────

@api_bp.get("/endpoints")
@require_auth
def list_endpoints():
    eps = MonitoredEndpoint.query.all()
    return jsonify([e.to_dict() for e in eps])


@api_bp.post("/endpoints")
@require_auth
def create_endpoint():
    data = request.get_json(silent=True) or {}
    required = ("name", "url")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    ep = MonitoredEndpoint(
        name=data["name"],
        url=data["url"],
        method=data.get("method", "GET").upper(),
        expected_status=int(data.get("expected_status", 200)),
        timeout=int(data.get("timeout", 10)),
        alert_email=data.get("alert_email"),
    )
    db.session.add(ep)
    db.session.commit()
    return jsonify(ep.to_dict()), 201


@api_bp.get("/endpoints/<int:ep_id>")
@require_auth
def get_endpoint(ep_id):
    ep = MonitoredEndpoint.query.get_or_404(ep_id)
    return jsonify(ep.to_dict())


@api_bp.put("/endpoints/<int:ep_id>")
@require_auth
def update_endpoint(ep_id):
    ep = MonitoredEndpoint.query.get_or_404(ep_id)
    data = request.get_json(silent=True) or {}
    for field in ("name", "url", "method", "expected_status", "timeout", "is_active", "alert_email"):
        if field in data:
            setattr(ep, field, data[field])
    db.session.commit()
    return jsonify(ep.to_dict())


@api_bp.delete("/endpoints/<int:ep_id>")
@require_auth
def delete_endpoint(ep_id):
    ep = MonitoredEndpoint.query.get_or_404(ep_id)
    db.session.delete(ep)
    db.session.commit()
    return jsonify({"message": f"Endpoint {ep_id} deleted."})


# ── Manual trigger ──────────────────────────────────────────────────────────

@api_bp.post("/endpoints/<int:ep_id>/check")
@require_auth
def trigger_check(ep_id):
    ep = MonitoredEndpoint.query.get_or_404(ep_id)
    result = check_endpoint(ep)
    db.session.add(result)
    db.session.commit()
    maybe_send_alert(current_app._get_current_object(), ep, result)
    return jsonify(result.to_dict())


@api_bp.post("/checks/run-all")
@require_auth
def trigger_all_checks():
    from app.services.checker import run_all_checks
    run_all_checks(current_app._get_current_object())
    return jsonify({"message": "All checks triggered."})


# ── Logs ─────────────────────────────────────────────────────────────────────

@api_bp.get("/logs")
@require_auth
def get_logs():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    ep_id = request.args.get("endpoint_id", type=int)
    only_failures = request.args.get("failures_only", "false").lower() == "true"

    query = CheckResult.query.order_by(CheckResult.checked_at.desc())
    if ep_id:
        query = query.filter_by(endpoint_id=ep_id)
    if only_failures:
        query = query.filter_by(success=False)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "results": [r.to_dict() for r in pagination.items],
    })


@api_bp.get("/alerts")
@require_auth
def get_alerts():
    alerts = AlertLog.query.order_by(AlertLog.sent_at.desc()).limit(100).all()
    return jsonify([a.to_dict() for a in alerts])


# ── Summary stats ─────────────────────────────────────────────────────────

@api_bp.get("/stats")
@require_auth
def get_stats():
    endpoints = MonitoredEndpoint.query.filter_by(is_active=True).all()
    total = len(endpoints)
    up = sum(1 for e in endpoints if e.status == "up")
    down = sum(1 for e in endpoints if e.status == "down")
    unknown = sum(1 for e in endpoints if e.status == "unknown")
    total_checks = CheckResult.query.count()
    failed_checks = CheckResult.query.filter_by(success=False).count()

    return jsonify({
        "endpoints_total": total,
        "endpoints_up": up,
        "endpoints_down": down,
        "endpoints_unknown": unknown,
        "total_checks": total_checks,
        "failed_checks": failed_checks,
        "overall_uptime": round((1 - failed_checks / total_checks) * 100, 2) if total_checks else None,
    })
