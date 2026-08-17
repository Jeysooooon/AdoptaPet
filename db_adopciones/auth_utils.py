import os
import jwt
from functools import wraps
from flask import request, jsonify

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'clave-compartida-adoptapet-2026')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')


def auth_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify(error='Token de autenticación requerido.'), 401
            token = auth_header.split(' ', 1)[1].strip()
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            except jwt.ExpiredSignatureError:
                return jsonify(error='El token ha expirado. Inicia sesión de nuevo.'), 401
            except jwt.InvalidTokenError:
                return jsonify(error='Token inválido.'), 401
            if role and payload.get('rol') != role:
                return jsonify(error=f'Acceso denegado. Requiere rol {role}.'), 403
            return f(payload, *args, **kwargs)
        return wrapper
    return decorator
