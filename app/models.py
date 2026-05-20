from app import db
from datetime import datetime


class MonitoredEndpoint(db.Model):
    __tablename__ = "monitored_endpoints"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    method = db.Column(db.String(10), default="GET")
    expected_status = db.Column(db.Integer, default=200)
    timeout = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    alert_email = db.Column(db.String(256), nullable=True)

    checks = db.relationship("CheckResult", backref="endpoint", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def uptime_percentage(self):
        total = self.checks.count()
        if total == 0:
            return None
        successes = self.checks.filter_by(success=True).count()
        return round((successes / total) * 100, 2)

    @property
    def avg_response_time(self):
        results = self.checks.filter(CheckResult.response_time_ms.isnot(None)).all()
        if not results:
            return None
        return round(sum(r.response_time_ms for r in results) / len(results), 1)

    @property
    def last_check(self):
        return self.checks.order_by(CheckResult.checked_at.desc()).first()

    @property
    def status(self):
        last = self.last_check
        if last is None:
            return "unknown"
        return "up" if last.success else "down"

    def to_dict(self):
        last = self.last_check
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "method": self.method,
            "expected_status": self.expected_status,
            "timeout": self.timeout,
            "is_active": self.is_active,
            "status": self.status,
            "uptime_percentage": self.uptime_percentage,
            "avg_response_time_ms": self.avg_response_time,
            "last_checked": last.checked_at.isoformat() if last else None,
            "alert_email": self.alert_email,
        }


class CheckResult(db.Model):
    __tablename__ = "check_results"

    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(db.Integer, db.ForeignKey("monitored_endpoints.id"), nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, nullable=False)
    status_code = db.Column(db.Integer, nullable=True)
    response_time_ms = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "endpoint_name": self.endpoint.name if self.endpoint else None,
            "checked_at": self.checked_at.isoformat(),
            "success": self.success,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
        }


class AlertLog(db.Model):
    __tablename__ = "alert_logs"

    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(db.Integer, db.ForeignKey("monitored_endpoints.id"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    recipient = db.Column(db.String(256))
    subject = db.Column(db.String(512))
    body = db.Column(db.Text)
    simulated = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "endpoint_id": self.endpoint_id,
            "sent_at": self.sent_at.isoformat(),
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "simulated": self.simulated,
        }
