import requests
import time
from datetime import datetime
from app import db
from app.models import MonitoredEndpoint, CheckResult, AlertLog


def check_endpoint(endpoint: MonitoredEndpoint) -> CheckResult:
    """Perform a single HTTP health check against an endpoint."""
    start = time.time()
    result = CheckResult(endpoint_id=endpoint.id, checked_at=datetime.utcnow())

    try:
        response = requests.request(
            method=endpoint.method,
            url=endpoint.url,
            timeout=endpoint.timeout,
            allow_redirects=True,
        )
        elapsed_ms = (time.time() - start) * 1000
        result.status_code = response.status_code
        result.response_time_ms = round(elapsed_ms, 2)
        result.success = response.status_code == endpoint.expected_status

        if not result.success:
            result.error_message = (
                f"Expected status {endpoint.expected_status}, got {response.status_code}"
            )
    except requests.exceptions.Timeout:
        result.success = False
        result.error_message = f"Request timed out after {endpoint.timeout}s"
    except requests.exceptions.ConnectionError as e:
        result.success = False
        result.error_message = f"Connection error: {str(e)[:200]}"
    except Exception as e:
        result.success = False
        result.error_message = f"Unexpected error: {str(e)[:200]}"

    return result


def maybe_send_alert(app, endpoint: MonitoredEndpoint, result: CheckResult):
    """Simulate sending an email alert when an endpoint goes down."""
    if result.success or not endpoint.alert_email:
        return

    # Only alert if the previous check was also a failure (avoid spam on first failure)
    recent = (
        endpoint.checks.order_by(CheckResult.checked_at.desc())
        .offset(1)
        .first()
    )
    if recent and not recent.success:
        return  # Already alerted

    subject = f"[ALERT] {endpoint.name} is DOWN"
    body = (
        f"Endpoint: {endpoint.name}\n"
        f"URL: {endpoint.url}\n"
        f"Time: {result.checked_at.isoformat()}\n"
        f"Error: {result.error_message or 'Unknown'}\n\n"
        f"This is a simulated alert (no real email was sent)."
    )

    alert = AlertLog(
        endpoint_id=endpoint.id,
        recipient=endpoint.alert_email,
        subject=subject,
        body=body,
        simulated=True,
    )
    db.session.add(alert)
    db.session.commit()
    app.logger.info(f"[SIMULATED ALERT] To: {endpoint.alert_email} | {subject}")


def run_all_checks(app):
    """Job function: check all active endpoints and persist results."""
    with app.app_context():
        endpoints = MonitoredEndpoint.query.filter_by(is_active=True).all()
        app.logger.info(f"Running checks on {len(endpoints)} endpoints...")
        for endpoint in endpoints:
            result = check_endpoint(endpoint)
            db.session.add(result)
            db.session.flush()
            maybe_send_alert(app, endpoint, result)
        db.session.commit()
        app.logger.info("Health checks complete.")
