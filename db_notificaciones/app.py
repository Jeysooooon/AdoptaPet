import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'key-segura-notificaciones')

database_url = os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id_notificacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, nullable=False)
    mensaje = db.Column(db.String(255), nullable=False)
    leida = db.Column(db.Boolean, default=False, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_notificacion': self.id_notificacion,
            'id_usuario': self.id_usuario,
            'mensaje': self.mensaje,
            'leida': self.leida,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Notificaciones Corriendo Exitosamente"}), 200

# POST - Crear Notificación
@app.route('/notificaciones', methods=['POST'])
def crear_notificacion():
    data = request.get_json() or {}
    id_usuario = data.get('id_usuario')
    mensaje = data.get('mensaje')
    
    if not id_usuario or not mensaje:
        return jsonify(error="id_usuario y mensaje son obligatorios."), 400
        
    try:
        nueva_notificacion = Notificacion(
            id_usuario=int(id_usuario),
            mensaje=mensaje,
            leida=False
        )
        db.session.add(nueva_notificacion)
        db.session.commit()
        return jsonify(message="Notificación guardada.", notificacion=nueva_notificacion.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al guardar: {str(e)}"), 500

# GET - Obtener notificaciones de un usuario
@app.route('/notificaciones', methods=['GET'])
def listar_notificaciones():
    try:
        id_usuario = request.args.get('id_usuario')
        query = Notificacion.query
        if id_usuario:
            query = query.filter_by(id_usuario=int(id_usuario))
            
        notificaciones = query.all()
        return jsonify(notificaciones=[n.to_dict() for n in notificaciones]), 200
    except Exception as e:
        return jsonify(error=f"Error al listar: {str(e)}"), 500

# PUT - Marcar notificación como leída
@app.route('/notificaciones/<int:id>/leer', methods=['PUT'])
def marcar_como_leida(id):
    notificacion = Notificacion.query.get(id)
    if not notificacion:
        return jsonify(error="Notificación no encontrada."), 404
    try:
        notificacion.leida = True
        db.session.commit()
        return jsonify(message="Notificación leída.", notificacion=notificacion.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al actualizar: {str(e)}"), 500

# DELETE - Borrar Notificación
@app.route('/notificaciones/<int:id>', methods=['DELETE'])
def eliminar_notificacion(id):
    notificacion = Notificacion.query.get(id)
    if not notificacion:
        return jsonify(error="Notificación no encontrada."), 404
    try:
        db.session.delete(notificacion)
        db.session.commit()
        return jsonify(message="Notificación eliminada."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al borrar: {str(e)}"), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 48915))
    app.run(host="0.0.0.0", port=port, debug=True)