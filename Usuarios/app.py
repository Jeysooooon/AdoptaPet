import os
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

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='usuario')

    @property
    def password(self):
        raise AttributeError('La contraseña no es accesible.')

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
            'rol': self.rol,
        }

@app.route('/registro', methods=['POST'])
def registro():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    password = data.get('password')

    if not nombre or not correo or not password:
        return jsonify(error='Nombre, correo y contraseña son obligatorios.'), 400

    try:
        if Usuario.query.filter_by(correo=correo).first():
            return jsonify(error='El correo ya está registrado.'), 409

        usuario = Usuario(nombre=nombre, correo=correo)
        usuario.password = password
        db.session.add(usuario)
        db.session.commit()

        return jsonify(message='Usuario creado exitosamente.', usuario=usuario.to_dict()), 201
    except Exception:
        db.session.rollback()
        return jsonify(error='Error al crear el usuario.'), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify(error='Correo y contraseña son obligatorios.'), 400

    try:
        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario or not usuario.check_password(password):
            return jsonify(error='Credenciales inválidas.'), 401

        session['user_id'] = usuario.id
        session['user_email'] = usuario.correo
        session['user_role'] = usuario.rol
        return jsonify(message='Inicio de sesión exitoso.', usuario=usuario.to_dict()), 200
    except Exception:
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
    # 3. Restauramos la creación automática de tablas en Railway al iniciar el script
    with app.app_context():
        db.create_all()
        
    port = int(os.environ.get("PORT", 48910))
    app.run(host="0.0.0.0", port=port, debug=True)