import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'key-segura-donaciones')

database_url = os.getenv('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Donacion(db.Model):
    __tablename__ = 'donaciones'
    id_donacion = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, nullable=True) # Puede ser anónima (None)
    monto = db.Column(db.Float, nullable=False)
    comentario = db.Column(db.String(255), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_donacion': self.id_donacion,
            'id_usuario': self.id_usuario,
            'monto': self.monto,
            'comentario': self.comentario,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Donaciones Corriendo Exitosamente"}), 200

# POST - Registrar Donación
@app.route('/donaciones', methods=['POST'])
def registrar_donacion():
    data = request.get_json() or {}
    monto = data.get('monto')
    
    if not monto:
        return jsonify(error="El monto es obligatorio."), 400
        
    try:
        nueva_donacion = Donacion(
            id_usuario=data.get('id_usuario'),
            monto=float(monto),
            comentario=data.get('comentario')
        )
        db.session.add(nueva_donacion)
        db.session.commit()
        return jsonify(message="¡Muchas gracias por apoyar a las mascotas!", donacion=nueva_donacion.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al registrar donación: {str(e)}"), 500

# GET - Ver todas las donaciones recibidas
@app.route('/donaciones', methods=['GET'])
def listar_donaciones():
    try:
        donaciones = Donacion.query.all()
        return jsonify(donaciones=[d.to_dict() for d in donaciones]), 200
    except Exception as e:
        return jsonify(error=f"Error al obtener: {str(e)}"), 500

# DELETE - Eliminar registro de donación (Logs de auditoría)
@app.route('/donaciones/<int:id>', methods=['DELETE'])
def eliminar_donacion(id):
    donacion = Donacion.query.get(id)
    if not donacion:
        return jsonify(error="Donación no encontrada."), 404
    try:
        db.session.delete(donacion)
        db.session.commit()
        return jsonify(message="Registro borrado."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al borrar: {str(e)}"), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 48912))
    app.run(host="0.0.0.0", port=port, debug=True)