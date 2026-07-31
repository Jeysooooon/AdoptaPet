import os
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # <-- 1. Importamos CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app)  # <-- 2. Activamos CORS para evitar bloqueos con el Frontend
app.secret_key = os.getenv('SECRET_KEY', 'change-me')

database_url = os.getenv('DATABASE_URL')
if database_url:
    database_url = database_url.strip()

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Configuración de bloqueo por intentos fallidos ---
MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 15


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='usuario')

    # Control de intentos fallidos y bloqueo temporal
    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0)
    bloqueado_hasta = db.Column(db.DateTime, nullable=True)

    @property
    def password(self):
        raise AttributeError('La contraseña no es accesible.')

    @password.setter
    def password(self, raw_password):
        self._password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self._password, raw_password)

    def esta_bloqueado(self):
        """Devuelve True si la cuenta sigue bloqueada en este momento."""
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > datetime.utcnow()

    def registrar_intento_fallido(self):
        """Suma un intento fallido y bloquea la cuenta si llega al máximo."""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
            self.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=MINUTOS_BLOQUEO)
            self.intentos_fallidos = 0

    def reiniciar_intentos(self):
        """Limpia el contador y el bloqueo tras un login exitoso."""
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'username': self.username,
            'correo': self.correo,
            'rol': self.rol,
        }


PASSWORD_MIN_LENGTH = 8
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30


def validar_formato_correo(correo):
    """Valida que el correo tenga una forma básica válida (algo@algo.algo)."""
    patron = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(patron, correo) is not None


def validar_username(username):
    """
    Valida formato del username: solo letras, números y guion bajo,
    entre 3 y 30 caracteres, sin espacios.
    """
    if not (USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH):
        return False, f'El nombre de usuario debe tener entre {USERNAME_MIN_LENGTH} y {USERNAME_MAX_LENGTH} caracteres.'
    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return False, 'El nombre de usuario solo puede contener letras, números y guion bajo (_).'
    return True, ''


def validar_password_segura(password):
    """
    Valida que la contraseña cumpla reglas mínimas de seguridad.
    Devuelve una tupla (es_valida, mensaje_error).
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f'La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres.'
    if not re.search(r'[A-Z]', password):
        return False, 'La contraseña debe incluir al menos una letra mayúscula.'
    if not re.search(r'[a-z]', password):
        return False, 'La contraseña debe incluir al menos una letra minúscula.'
    if not re.search(r'[0-9]', password):
        return False, 'La contraseña debe incluir al menos un número.'
    return True, ''


@app.route('/registro', methods=['POST'])
def registro():
    data = request.get_json() or {}
    nombre = (data.get('nombre') or '').strip()
    username = (data.get('username') or '').strip()
    correo = (data.get('correo') or '').strip().lower()
    password = data.get('password') or ''
    confirmar_password = data.get('confirmar_password') or ''

    # 1. Campos obligatorios
    if not nombre or not username or not correo or not password or not confirmar_password:
        return jsonify(error='Nombre, usuario, correo, contraseña y confirmación de contraseña son obligatorios.'), 400

    # 2. Formato de username válido
    username_valido, mensaje_username = validar_username(username)
    if not username_valido:
        return jsonify(error=mensaje_username), 400

    # 3. Formato de correo válido
    if not validar_formato_correo(correo):
        return jsonify(error='El formato del correo electrónico no es válido.'), 400

    # 4. Confirmación de contraseña
    if password != confirmar_password:
        return jsonify(error='La contraseña y su confirmación no coinciden.'), 400

    # 5. Contraseña segura
    password_valida, mensaje_password = validar_password_segura(password)
    if not password_valida:
        return jsonify(error=mensaje_password), 400

    try:
        if Usuario.query.filter_by(correo=correo).first():
            return jsonify(error='Ya existe una cuenta registrada con este correo electrónico.'), 409

        if Usuario.query.filter_by(username=username).first():
            return jsonify(error='Ese nombre de usuario ya está en uso.'), 409

        usuario = Usuario(nombre=nombre, username=username, correo=correo)
        usuario.password = password
        db.session.add(usuario)
        db.session.commit()

        return jsonify(message='Usuario creado exitosamente.', usuario=usuario.to_dict()), 201
    except Exception:
        db.session.rollback()
        return jsonify(error='Ocurrió un error inesperado al crear el usuario. Inténtalo nuevamente.'), 500


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identificador = (data.get('correo') or data.get('username') or '').strip()
    password = data.get('password')

    if not identificador or not password:
        return jsonify(error='Correo/usuario y contraseña son obligatorios.'), 400

    try:
        usuario = Usuario.query.filter(
            (Usuario.correo == identificador.lower()) | (Usuario.username == identificador)
        ).first()

        if not usuario:
            return jsonify(error='Credenciales inválidas.'), 401

        # Verificar si la cuenta está bloqueada por intentos fallidos
        if usuario.esta_bloqueado():
            minutos_restantes = int((usuario.bloqueado_hasta - datetime.utcnow()).total_seconds() // 60) + 1
            return jsonify(
                error=f'Cuenta bloqueada temporalmente. Intenta de nuevo en {minutos_restantes} minuto(s).'
            ), 423  # 423 Locked

        # Verificar contraseña
        if not usuario.check_password(password):
            usuario.registrar_intento_fallido()
            db.session.commit()

            if usuario.bloqueado_hasta:
                return jsonify(
                    error=f'Cuenta bloqueada por {MINUTOS_BLOQUEO} minutos debido a múltiples intentos fallidos.'
                ), 423

            return jsonify(error='Credenciales inválidas.'), 401

        # Login correcto: reiniciar contador de intentos
        usuario.reiniciar_intentos()
        db.session.commit()

        session['user_id'] = usuario.id
        session['user_email'] = usuario.correo
        session['user_role'] = usuario.rol
        return jsonify(message='Inicio de sesión exitoso.', usuario=usuario.to_dict()), 200
    except Exception:
        db.session.rollback()
        return jsonify(error='Error al iniciar sesión.'), 500


@app.route('/logout', methods=['POST'])
def logout():
    try:
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.pop('user_role', None)
        return jsonify(message='Cierre de sesión exitoso.'), 200
    except Exception:
        return jsonify(error='Error al cerrar sesión.'), 500


@app.route('/perfil/<int:id>', methods=['GET'])
def obtener_perfil(id):
    try:
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404
        return jsonify(usuario=usuario.to_dict()), 200
    except Exception:
        return jsonify(error='Error al obtener el perfil.'), 500


@app.route('/perfil/<int:id>', methods=['PUT'])
def actualizar_perfil(id):
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    password = data.get('password')  # <-- Añadido soporte para contraseña

    try:
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404

        current_user_id = session.get('user_id')
        current_user_role = session.get('user_role')
        if current_user_id != usuario.id and current_user_role != 'admin':
            return jsonify(error='No autorizado.'), 403

        if correo and correo != usuario.correo:
            if Usuario.query.filter_by(correo=correo).first():
                return jsonify(error='El correo ya está registrado.'), 409
            usuario.correo = correo

        if nombre:
            usuario.nombre = nombre

        if password:  # <-- Si se envía contraseña, se encripta automáticamente
            usuario.password = password

        db.session.commit()
        return jsonify(message='Perfil actualizado.', usuario=usuario.to_dict()), 200
    except Exception:
        db.session.rollback()
        return jsonify(error='Error al actualizar el perfil.'), 500


@app.route('/usuarios/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    try:
        usuario = Usuario.query.get(id)
        if not usuario:
            return jsonify(error='Usuario no encontrado.'), 404

        current_user_id = session.get('user_id')
        current_user_role = session.get('user_role')
        if current_user_id != usuario.id and current_user_role != 'admin':
            return jsonify(error='No autorizado.'), 403

        db.session.delete(usuario)
        db.session.commit()
        return jsonify(message='Usuario eliminado.'), 200
    except Exception:
        db.session.rollback()
        return jsonify(error='Error al eliminar el usuario.'), 500


@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    try:
        current_user_role = session.get('user_role')
        if current_user_role != 'admin':
            return jsonify(error='Acceso denegado. Requiere rol admin.'), 403

        usuarios = Usuario.query.all()
        usuarios_list = [u.to_dict() for u in usuarios]
        return jsonify(usuarios=usuarios_list), 200
    except Exception:
        return jsonify(error='Error al obtener usuarios.'), 500


@app.route('/recuperar-password', methods=['POST'])
def recuperar_password():
    data = request.get_json() or {}
    correo = data.get('correo')
    if not correo:
        return jsonify(error='El correo es requerido.'), 400
    try:
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario:
            # Simular envío de correo: integrar servicio real en producción
            pass
        return jsonify(message='Si el correo existe, se han enviado instrucciones para recuperar la contraseña.'), 200
    except Exception:
        return jsonify(error='Error al procesar la solicitud.'), 500


@app.route('/')
def home():
    return {"status": "Microservicio de Usuarios Corriendo Exitosamente"}, 200


if __name__ == "__main__":
    # Restauramos la creación automática de tablas en Railway al iniciar el script
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 48910))
    app.run(host="0.0.0.0", port=port, debug=True)