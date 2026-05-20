from flask import Blueprint, request, jsonify
from app.services.auth import generate_token, API_KEY

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/token")
def get_token():
    """
    Exchange credentials or API key for a JWT.
    Body: {"username": "admin", "password": "..."} OR header X-API-Key.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key == API_KEY:
        return jsonify({"access_token": generate_token(), "token_type": "Bearer"})

    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    admin_user = "admin"
    import os
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin")

    if username == admin_user and password == admin_pass:
        return jsonify({"access_token": generate_token(username), "token_type": "Bearer"})

    return jsonify({"error": "Invalid credentials"}), 401
