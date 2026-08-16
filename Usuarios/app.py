import os
import re
import logging
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración JWT
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'clave-compartida-adoptapet-2026')
JWT_ALGORITHM = 'HS256'
JWT_EXP_HORAS = 8

# Configuración de Base de Datos
database_url = os.getenv('DATABASE_URL', 'sqlite:///usuarios.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url.strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Regex para validación de correo
EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

# Modelo de Usuario
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='usuario')
    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def password(self):
        raise AttributeError('La contraseña no es accesible directamente.')

    @password.setter
    def password(self, raw_password):
        self._password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self._password, raw_password)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'correo': self.correo,
            'rol': self.rol
        }

# Helpers JWT
def generar_token(usuario):
    payload = {
        'id': usuario.id,
        'correo': usuario.correo,
        'rol': usuario.rol,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HORAS)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def requiere_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify(error='Token de autenticación requerido.'), 401

        token = auth_header.split(' ', 1)[1].strip()
        try:
            usuario_actual = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify(error='El token ha expirado. Inicia sesión de nuevo.'), 401
        except jwt.InvalidTokenError:
            return jsonify(error='Token inválido.'), 401

        return f(usuario_actual, *args, **kwargs)
    return wrapper

# Endpoints
@app.route('/')
def home():
    return jsonify(status="Microservicio de Usuarios Corriendo Exitosamente"), 200

@app.route('/registro', methods=['POST'])
def registro():
    data = request.get_json() or {}
    nombre = data.get('nombre', '').strip()
    correo = data.get('correo', '').strip().lower()
    password = data.get('password')

    if not nombre or not correo or not password:
        return jsonify(error='Nombre, correo y contraseña son obligatorios.'), 400

    if not re.match(EMAIL_REGEX, correo):
        return jsonify(error='Formato de correo electrónico inválido.'), 400

    try:
        if Usuario.query.filter_by(correo=correo).first():
            return jsonify(error='El correo ya está registrado.'), 409

        usuario = Usuario(nombre=nombre, correo=correo)
        usuario.password = password
        db.session.add(usuario)
        db.session.commit()

        token = generar_token(usuario)
        return jsonify(
            message='Usuario creado exitosamente.',
            usuario=usuario.to_dict(),
            token=token
        ), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error en registro: {str(e)}")
        return jsonify(error='Error interno al crear el usuario.'), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    correo = data.get('correo', '').strip().lower()
    password = data.get('password')

    if not correo or not password:
        return jsonify(error='Correo y contraseña son obligatorios.'), 400

    try:
        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario or not usuario.check_password(password):
            return jsonify(error='Credenciales inválidas.'), 401

        token = generar_token(usuario)
        return jsonify(message='Inicio de sesión exitoso.', usuario=usuario.to_dict(), token=token), 200
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        return jsonify(error='Error interno al iniciar sesión.'), 500

@app.route('/logout', methods=['POST'])
def logout():
    return jsonify(message='Cierre de sesión exitoso en cliente.'), 200

@app.route('/perfil/<int:id>', methods=['GET'])
@requiere_token
def obtener_perfil(usuario_actual, id):
    try:
        if usuario_actual['id'] != id and usuario_actual['rol'] != 'admin':
            return jsonify(error='Acceso no autorizado.'), 403

        usuario = db.session.get(Usuario, id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404

        return jsonify(usuario=usuario.to_dict()), 200
    except Exception as e:
        logger.error(f"Error al obtener perfil: {str(e)}")
        return jsonify(error='Error interno al obtener el perfil.'), 500

@app.route('/perfil/<int:id>', methods=['PUT'])
@requiere_token
def actualizar_perfil(usuario_actual, id):
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    password = data.get('password')

    try:
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404

        if usuario_actual['id'] != usuario.id and usuario_actual['rol'] != 'admin':
            return jsonify(error='Acceso no autorizado.'), 403

        if correo:
            correo = correo.strip().lower()
            if not re.match(EMAIL_REGEX, correo):
                return jsonify(error='Formato de correo electrónico inválido.'), 400

            if correo != usuario.correo:
                if Usuario.query.filter_by(correo=correo).first():
                    return jsonify(error='El correo ya está registrado.'), 409
                usuario.correo = correo

        if nombre:
            usuario.nombre = nombre.strip()

        if password:
            usuario.password = password

        db.session.commit()
        return jsonify(message='Perfil actualizado.', usuario=usuario.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al actualizar perfil: {str(e)}")
        return jsonify(error='Error interno al actualizar el perfil.'), 500

@app.route('/usuarios/<int:id>', methods=['DELETE'])
@requiere_token
def eliminar_usuario(usuario_actual, id):
    try:
        usuario = db.session.get(Usuario, id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404

        if usuario_actual['id'] != usuario.id and usuario_actual['rol'] != 'admin':
            return jsonify(error='Acceso no autorizado.'), 403

        db.session.delete(usuario)
        db.session.commit()
        return jsonify(message='Usuario eliminado.'), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar usuario: {str(e)}")
        return jsonify(error='Error interno al eliminar el usuario.'), 500

@app.route('/usuarios', methods=['GET'])
@requiere_token
def listar_usuarios(usuario_actual):
    try:
        if usuario_actual['rol'] != 'admin':
            return jsonify(error='Acceso denegado. Requiere rol admin.'), 403

        usuarios = Usuario.query.all()
        return jsonify(usuarios=[u.to_dict() for u in usuarios]), 200
    except Exception as e:
        logger.error(f"Error al listar usuarios: {str(e)}")
        return jsonify(error='Error interno al obtener usuarios.'), 500

@app.route('/recuperar-password', methods=['POST'])
def recuperar_password():
    data = request.get_json() or {}
    correo = data.get('correo', '').strip().lower()
    if not correo:
        return jsonify(error='El correo es requerido.'), 400

    try:
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            pass # Integrar lógica de envío de correo
        return jsonify(message='Si el correo existe, se han enviado instrucciones para recuperar la contraseña.'), 200
    except Exception as e:
        logger.error(f"Error en recuperar-password: {str(e)}")
        return jsonify(error='Error interno al procesar la solicitud.'), 500

# Inicialización de tablas
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)