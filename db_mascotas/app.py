import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

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

# Modelo de base de datos para las Mascotas
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

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Mascotas Corriendo Exitosamente"}), 200

# POST - Crear Mascota
@app.route('/mascotas', methods=['POST'])
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

# GET - Listar todas las mascotas
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

# GET - Detalle de mascota por ID
@app.route('/mascotas/<int:id>', methods=['GET'])
def obtener_mascota(id):
    mascota = Mascota.query.get(id)
    if not mascota:
        return jsonify(error="Mascota no encontrada."), 404
    return jsonify(mascota.to_dict()), 200

# PUT - Actualizar Mascota
@app.route('/mascotas/<int:id>', methods=['PUT'])
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

# DELETE - Eliminar Mascota
@app.route('/mascotas/<int:id>', methods=['DELETE'])
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crea la tabla automáticamente en Railway
    port = int(os.getenv("PORT", 48914))
    app.run(host="0.0.0.0", port=port, debug=True)