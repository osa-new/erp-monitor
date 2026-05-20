import os
import jwt
import functools
from datetime import datetime, timedelta
from flask import request, jsonify, current_app

API_KEY = os.getenv("API_KEY", "dev-api-key-change-me")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 8))


def generate_token(user_id: str = "admin") -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator: accept either Bearer JWT or X-API-Key header."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # Check API key first
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)

        # Fall back to JWT bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_token(token)
            if payload:
                return f(*args, **kwargs)

        return jsonify({"error": "Unauthorized. Provide a valid X-API-Key or Bearer token."}), 401

    return wrapper
