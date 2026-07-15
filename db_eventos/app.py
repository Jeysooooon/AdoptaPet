import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'key-segura-eventos')

database_url = os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Evento(db.Model):
    __tablename__ = 'eventos'
    id_evento = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.String(500), nullable=False)
    fecha_evento = db.Column(db.String(100), nullable=False) # Fecha en texto para simplificar
    ubicacion = db.Column(db.String(150), nullable=False)

    def to_dict(self):
        return {
            'id_evento': self.id_evento,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'fecha_evento': self.fecha_evento,
            'ubicacion': self.ubicacion
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Eventos Corriendo Exitosamente"}), 200

# POST - Publicar Evento
@app.route('/eventos', methods=['POST'])
def crear_evento():
    data = request.get_json() or {}
    titulo = data.get('titulo')
    descripcion = data.get('descripcion')
    fecha_evento = data.get('fecha_evento')
    ubicacion = data.get('ubicacion')
    
    if not all([titulo, descripcion, fecha_evento, ubicacion]):
        return jsonify(error="Faltan campos obligatorios."), 400
        
    try:
        nuevo_evento = Evento(
            titulo=titulo,
            descripcion=descripcion,
            fecha_evento=fecha_evento,
            ubicacion=ubicacion
        )
        db.session.add(nuevo_evento)
        db.session.commit()
        return jsonify(message="Evento publicado exitosamente.", evento=nuevo_evento.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al publicar: {str(e)}"), 500

# GET - Ver todos los eventos programados
@app.route('/eventos', methods=['GET'])
def listar_eventos():
    try:
        eventos = Evento.query.all()
        return jsonify(eventos=[e.to_dict() for e in eventos]), 200
    except Exception as e:
        return jsonify(error=f"Error al listar: {str(e)}"), 500

# PUT - Editar un Evento
@app.route('/eventos/<int:id>', methods=['PUT'])
def actualizar_evento(id):
    evento = Evento.query.get(id)
    if not evento:
        return jsonify(error="Evento no encontrado."), 404
        
    data = request.get_json() or {}
    try:
        evento.titulo = data.get('titulo', evento.titulo)
        evento.descripcion = data.get('descripcion', evento.descripcion)
        evento.fecha_evento = data.get('fecha_evento', evento.fecha_evento)
        evento.ubicacion = data.get('ubicacion', evento.ubicacion)
        
        db.session.commit()
        return jsonify(message="Evento modificado correctamente.", evento=evento.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al editar: {str(e)}"), 500

# DELETE - Cancelar Evento
@app.route('/eventos/<int:id>', methods=['DELETE'])
def eliminar_evento(id):
    evento = Evento.query.get(id)
    if not evento:
        return jsonify(error="Evento no encontrado."), 404
    try:
        db.session.delete(evento)
        db.session.commit()
        return jsonify(message="Evento cancelado y eliminado correctamente."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al eliminar: {str(e)}"), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 48913))
    app.run(host="0.0.0.0", port=port, debug=True)