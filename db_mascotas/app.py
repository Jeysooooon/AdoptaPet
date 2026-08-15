import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from auth_utils import auth_required

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)  # Evita bloqueos de conexión con el Frontend
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'key-segura-mascotas')

database_url = os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== MODELOS DE BASE DE DATOS ====================

class Mascota(db.Model):
    __tablename__ = 'mascotas'
    id_mascota = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    especie = db.Column(db.String(100), nullable=False)
    raza = db.Column(db.String(100), nullable=False)
    edad_meses = db.Column(db.Integer, nullable=False)
    tamaño = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    estado = db.Column(db.String(50), nullable=False, default='Disponible')
    foto_url = db.Column(db.String(500), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    caracteristicas = db.relationship(
        'Caracteristica',
        secondary='mascota_caracteristica',
        backref=db.backref('mascotas', lazy=True),
        lazy=True
    )

    def to_dict(self):
        return {
            'id_mascota': self.id_mascota,
            'nombre': self.nombre,
            'especie': self.especie,
            'raza': self.raza,
            'edad_meses': self.edad_meses,
            'tamaño': self.tamaño,
            'descripcion': self.descripcion,
            'estado': self.estado,
            'foto_url': self.foto_url,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }

class Foto(db.Model):
    __tablename__ = 'fotos'
    id_foto = db.Column(db.Integer, primary_key=True)
    id_mascota = db.Column(db.Integer, db.ForeignKey('mascotas.id_mascota', ondelete='CASCADE'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    es_principal = db.Column(db.Boolean, default=False, nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    mascota = db.relationship('Mascota', backref=db.backref('fotos', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id_foto': self.id_foto,
            'id_mascota': self.id_mascota,
            'url': self.url,
            'es_principal': self.es_principal,
            'fecha_subida': self.fecha_subida.isoformat() if self.fecha_subida else None
        }

class Caracteristica(db.Model):
    __tablename__ = 'caracteristicas'
    id_caracteristica = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)

    def to_dict(self):
        return {
            'id_caracteristica': self.id_caracteristica,
            'nombre': self.nombre
        }

mascota_caracteristica = db.Table(
    'mascota_caracteristica',
    db.Column('id_mascota', db.Integer, db.ForeignKey('mascotas.id_mascota', ondelete='CASCADE'), primary_key=True),
    db.Column('id_caracteristica', db.Integer, db.ForeignKey('caracteristicas.id_caracteristica', ondelete='CASCADE'), primary_key=True)
)

# ==================== RUTAS PRINCIPALES DE MASCOTAS ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Mascotas Corriendo Exitosamente"}), 200

@app.route('/mascotas', methods=['POST'])
@auth_required('admin')
def crear_mascota():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    especie = data.get('especie')
    raza = data.get('raza')
    edad_meses = data.get('edad_meses')
    tamaño = data.get('tamaño')
    descripcion = data.get('descripcion')
    
    if not all([nombre, especie, raza, edad_meses, tamaño, descripcion]):
        return jsonify(error="Faltan campos obligatorios."), 400
        
    try:
        nueva_mascota = Mascota(
            nombre=nombre,
            especie=especie,
            raza=raza,
            edad_meses=int(edad_meses),
            tamaño=tamaño,
            descripcion=descripcion,
            foto_url=data.get('foto_url'),
            estado=data.get('estado', 'Disponible')
        )
        db.session.add(nueva_mascota)
        db.session.commit()
        return jsonify(message="Mascota registrada exitosamente.", mascota=nueva_mascota.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al registrar mascota: {str(e)}"), 500

@app.route('/mascotas', methods=['GET'])
def listar_mascotas():
    try:
        especie_filtro = request.args.get('especie')
        estado_filtro = request.args.get('estado')
        
        query = Mascota.query
        if especie_filtro:
            query = query.filter_by(especie=especie_filtro)
        if estado_filtro:
            query = query.filter_by(estado=estado_filtro)
            
        mascotas = query.all()
        return jsonify(mascotas=[m.to_dict() for m in mascotas]), 200
    except Exception as e:
        return jsonify(error=f"Error al obtener mascotas: {str(e)}"), 500

@app.route('/mascotas/<int:id>', methods=['GET'])
def obtener_mascota(id):
    mascota = Mascota.query.get(id)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
    return jsonify(mascota.to_dict()), 200

@app.route('/mascotas/<int:id>', methods=['PUT'])
@auth_required('admin')
def actualizar_mascota(id):
    mascota = Mascota.query.get(id)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
        
    data = request.get_json() or {}
    try:
        mascota.nombre = data.get('nombre', mascota.nombre)
        mascota.especie = data.get('especie', mascota.especie)
        mascota.raza = data.get('raza', mascota.raza)
        if 'edad_meses' in data:
            mascota.edad_meses = int(data['edad_meses'])
        mascota.tamaño = data.get('tamaño', mascota.tamaño)
        mascota.descripcion = data.get('descripcion', mascota.descripcion)
        mascota.estado = data.get('estado', mascota.estado)
        mascota.foto_url = data.get('foto_url', mascota.foto_url)
        
        db.session.commit()
        return jsonify(message="Mascota actualizada exitosamente.", mascota=mascota.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al actualizar mascota: {str(e)}"), 500

@app.route('/mascotas/<int:id>', methods=['DELETE'])
@auth_required('admin')
def eliminar_mascota(id):
    mascota = Mascota.query.get(id)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
    try:
        db.session.delete(mascota)
        db.session.commit()
        return jsonify(message="Mascota eliminada exitosamente."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al eliminar mascota: {str(e)}"), 500

# ==================== ENDPOINTS DE FOTOS ====================

@app.route('/mascotas/<int:id_mascota>/fotos', methods=['POST'])
@auth_required('admin')
def agregar_foto(id_mascota):
    mascota = Mascota.query.get(id_mascota)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404

    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify(error="La URL de la foto es obligatoria."), 400

    try:
        nueva_foto = Foto(
            id_mascota=id_mascota,
            url=url,
            es_principal=data.get('es_principal', False)
        )
        db.session.add(nueva_foto)
        db.session.commit()
        return jsonify(message="Foto agregada exitosamente.", foto=nueva_foto.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al agregar foto: {str(e)}"), 500

@app.route('/mascotas/<int:id_mascota>/fotos', methods=['GET'])
def listar_fotos(id_mascota):
    mascota = Mascota.query.get(id_mascota)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
    fotos = Foto.query.filter_by(id_mascota=id_mascota).all()
    return jsonify(fotos=[f.to_dict() for f in fotos]), 200

@app.route('/fotos/<int:id_foto>', methods=['DELETE'])
@auth_required('admin')
def eliminar_foto(id_foto):
    foto = Foto.query.get(id_foto)
    if not foto:
        return jsonify(error="Foto no encontrada."), 404
    try:
        db.session.delete(foto)
        db.session.commit()
        return jsonify(message="Foto eliminada exitosamente."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al eliminar foto: {str(e)}"), 500

# ==================== ENDPOINTS DE CARACTERÍSTICAS ====================

@app.route('/caracteristicas', methods=['POST'])
@auth_required('admin')
def crear_caracteristica():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre:
        return jsonify(error="El nombre de la característica es obligatorio."), 400
    try:
        if Caracteristica.query.filter_by(nombre=nombre).first():
            return jsonify(error="Esa característica ya existe."), 409
        nueva_caracteristica = Caracteristica(nombre=nombre)
        db.session.add(nueva_caracteristica)
        db.session.commit()
        return jsonify(message="Característica creada exitosamente.", caracteristica=nueva_caracteristica.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al crear característica: {str(e)}"), 500

@app.route('/caracteristicas', methods=['GET'])
def listar_caracteristicas():
    try:
        caracteristicas = Caracteristica.query.all()
        return jsonify(caracteristicas=[c.to_dict() for c in caracteristicas]), 200
    except Exception as e:
        return jsonify(error=f"Error al listar características: {str(e)}"), 500

@app.route('/mascotas/<int:id_mascota>/caracteristicas', methods=['POST'])
@auth_required('admin')
def asignar_caracteristica(id_mascota):
    mascota = Mascota.query.get(id_mascota)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404

    data = request.get_json() or {}
    id_caracteristica = data.get('id_caracteristica')
    if not id_caracteristica:
        return jsonify(error="id_caracteristica es obligatorio."), 400

    caracteristica = Caracteristica.query.get(id_caracteristica)
    if not caracteristica:
        return jsonify(error="Característica no encontrada."), 404

    try:
        if caracteristica in mascota.caracteristicas:
            return jsonify(error="La mascota ya tiene asignada esa característica."), 409
        mascota.caracteristicas.append(caracteristica)
        db.session.commit()
        return jsonify(
            message="Característica asignada a la mascota.",
            caracteristicas=[c.to_dict() for c in mascota.caracteristicas]
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al asignar característica: {str(e)}"), 500

@app.route('/mascotas/<int:id_mascota>/caracteristicas', methods=['GET'])
def listar_caracteristicas_mascota(id_mascota):
    mascota = Mascota.query.get(id_mascota)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
    return jsonify(caracteristicas=[c.to_dict() for c in mascota.caracteristicas]), 200

@app.route('/mascotas/<int:id_mascota>/caracteristicas/<int:id_caracteristica>', methods=['DELETE'])
@auth_required('admin')
def quitar_caracteristica(id_mascota, id_caracteristica):
    mascota = Mascota.query.get(id_mascota)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404

    caracteristica = Caracteristica.query.get(id_caracteristica)
    if not caracteristica or caracteristica not in mascota.caracteristicas:
        return jsonify(error="Esa mascota no tiene asignada esa característica."), 404

    try:
        mascota.caracteristicas.remove(caracteristica)
        db.session.commit()
        return jsonify(message="Característica removida de la mascota."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al remover característica: {str(e)}"), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 48914))
    app.run(host="0.0.0.0", port=port, debug=True)