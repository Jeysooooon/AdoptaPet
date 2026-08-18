import os
import requests  # Para comunicarse con otros servicios
import jwt
import pymysql
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from auth_utils import auth_required

# SQLAlchemy intenta importar MySQLdb por compatibilidad; PyMySQL debe estar
# disponible como backend para cadenas mysql://
pymysql.install_as_MySQLdb()

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:8000", "http://127.0.0.1:8000"]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "Accept"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'key-segura-adopciones')

def normalize_database_url(database_url):
    if not database_url:
        return database_url
    database_url = database_url.strip()
    if database_url.startswith('mysql://'):
        return database_url.replace('mysql://', 'mysql+pymysql://', 1)
    return database_url

database_url = normalize_database_url(os.getenv('DATABASE_URL'))
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


def generate_service_token():
    """Genera un JWT usado por este servicio para autenticarse ante otros servicios.
    Firma con el JWT_SECRET_KEY y el rol 'service'."""
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'clave-compartida-adoptapet-2026')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    SERVICE_TOKEN_EXP_HORAS = int(os.getenv('SERVICE_TOKEN_EXP_HORAS', 24))
    payload = {
        'rol': 'service',
        'iss': 'adopciones',
        'exp': datetime.utcnow() + timedelta(hours=SERVICE_TOKEN_EXP_HORAS)
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # PyJWT < 2 devuelve bytes, asegurarse de retornar str
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token

# URLs internas para comunicarse con los otros microservicios
MASCOTAS_SERVICE_URL = "http://localhost:48914/mascotas"
NOTIFICACIONES_SERVICE_URL = "http://localhost:48915/notificaciones"

class SolicitudAdopcion(db.Model):
    __tablename__ = 'solicitudes_adopcion'
    id_solicitud = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, nullable=False)
    id_mascota = db.Column(db.Integer, nullable=False)
    motivo_adopcion = db.Column(db.String(500), nullable=False)
    estado = db.Column(db.String(50), nullable=False, default='Pendiente')
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id_solicitud': self.id_solicitud,
            'id_usuario': self.id_usuario,
            'id_mascota': self.id_mascota,
            'motivo_adopcion': self.motivo_adopcion,
            'estado': self.estado,
            'fecha_solicitud': self.fecha_solicitud.isoformat() if self.fecha_solicitud else None,
            'fecha_resolucion': self.fecha_resolucion.isoformat() if self.fecha_resolucion else None
        }

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Microservicio de Adopciones Corriendo Exitosamente"}), 200

# POST - Crear Solicitud de Adopción
@app.route('/adopciones', methods=['POST'])
@auth_required()
def crear_solicitud(usuario_actual):
    data = request.get_json() or {}
    # Preferir el id del usuario autenticado; si no existe, usar el enviado (no recomendado)
    id_usuario = usuario_actual.get('id') or data.get('id_usuario')
    id_mascota = data.get('id_mascota')
    motivo_adopcion = data.get('motivo_adopcion')
    
    if not all([id_usuario, id_mascota, motivo_adopcion]):
        return jsonify(error="Faltan campos obligatorios."), 400
        
    # Verificar si la mascota existe y está disponible comunicándose con el microservicio de Mascotas
    try:
        response = requests.get(f"{MASCOTAS_SERVICE_URL}/{id_mascota}", timeout=3)
        if response.status_code == 404:
            return jsonify(error="La mascota especificada no existe."), 404
        
        mascota_data = response.json()
        if mascota_data.get('estado') != 'Disponible':
            return jsonify(error="Esta mascota ya no se encuentra disponible."), 400
    except requests.exceptions.RequestException:
        pass # Permitir guardar en local si el otro servicio está temporalmente apagado

    try:
        nueva_solicitud = SolicitudAdopcion(
            id_usuario=int(id_usuario),
            id_mascota=int(id_mascota),
            motivo_adopcion=motivo_adopcion,
            estado='Pendiente'
        )
        db.session.add(nueva_solicitud)
        db.session.commit()
        return jsonify(message="Solicitud de adopción enviada con éxito.", solicitud=nueva_solicitud.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al guardar solicitud: {str(e)}"), 500

# GET - Listar todas las solicitudes
@app.route('/adopciones', methods=['GET'])
def listar_solicitudes():
    try:
        solicitudes = SolicitudAdopcion.query.all()
        return jsonify(solicitudes=[s.to_dict() for s in solicitudes]), 200
    except Exception as e:
        return jsonify(error=f"Error al listar: {str(e)}"), 500

# PUT - Cambiar estado de la solicitud (Aprobar / Rechazar)
@app.route('/adopciones/<int:id>', methods=['PUT'])
@auth_required('admin')
def actualizar_solicitud(usuario_actual, id):
    solicitud = SolicitudAdopcion.query.get(id)
    if not solicitud:
        return jsonify(error="Solicitud no encontrada."), 404
        
    data = request.get_json() or {}
    nuevo_estado = data.get('estado')
    
    if nuevo_estado not in ['Pendiente', 'Aprobado', 'Rechazado']:
        return jsonify(error="Estado inválido. Use 'Aprobado' o 'Rechazado'."), 400
        
    try:
        solicitud.estado = nuevo_estado
        solicitud.fecha_resolucion = datetime.utcnow()
        db.session.commit()

        # Si se aprueba, cambiamos automáticamente la mascota a "Adoptado"
        if nuevo_estado == 'Aprobado':
            try:
                service_token = generate_service_token()
                requests.put(
                    f"{MASCOTAS_SERVICE_URL}/{solicitud.id_mascota}",
                    json={"estado": "Adoptado"},
                    headers={'Authorization': f'Bearer {service_token}'},
                    timeout=3
                )
            except requests.exceptions.RequestException:
                pass

            try:
                mensaje_notif = f"Tu solicitud de adopción para la mascota #{solicitud.id_mascota} ha sido {nuevo_estado}."
                service_token = generate_service_token()
                requests.post(
                    NOTIFICACIONES_SERVICE_URL,
                    json={
                        "id_usuario": solicitud.id_usuario,
                        "mensaje": mensaje_notif
                    },
                    headers={'Authorization': f'Bearer {service_token}'},
                    timeout=3
                )
            except requests.exceptions.RequestException:
                pass

        return jsonify(message="Solicitud procesada correctamente.", solicitud=solicitud.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al actualizar: {str(e)}"), 500

# DELETE - Cancelar/Eliminar solicitud
@app.route('/adopciones/<int:id>', methods=['DELETE'])
@auth_required()
def eliminar_solicitud(usuario_actual, id):
    solicitud = SolicitudAdopcion.query.get(id)
    if not solicitud:
        return jsonify(error="Solicitud no encontrada."), 404
    # Solo el autor de la solicitud o un admin pueden eliminarla
    if usuario_actual.get('rol') != 'admin' and usuario_actual.get('id') != solicitud.id_usuario:
        return jsonify(error='No autorizado.'), 403
    try:
        db.session.delete(solicitud)
        db.session.commit()
        return jsonify(message="Solicitud eliminada correctamente."), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al eliminar: {str(e)}"), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 48911))
    app.run(host="0.0.0.0", port=port, debug=True)