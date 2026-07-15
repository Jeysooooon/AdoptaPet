import os
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-me')

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
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False, default='user')

    @property
    def password(self):
        raise AttributeError('La contraseña no es accesible.')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
        return jsonify(message='Inicio de sesión exitoso.', usuario=usuario.to_dict()), 200
    except Exception:
        return jsonify(error='Error al iniciar sesión.'), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        session.pop('user_id', None)
        session.pop('user_email', None)
        return jsonify(message='Cierre de sesión exitoso.'), 200
    except Exception:
        return jsonify(error='Error al cerrar sesión.'), 500

@app.route('/')
def home():
    return {"status": "Microservicio de Usuarios Corriendo Exitosamente"}, 200

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 48910))
    app.run(host="0.0.0.0", port=port, debug=True)