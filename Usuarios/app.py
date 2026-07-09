import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuración de la base de datos (apuntando a db_usuarios ahora)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route('/')
def home():
    return {"status": "Microservicio de Usuarios Corriendo Exitosamente"}, 200

if __name__ == "__main__":
    # IMPORTANTE: Railway necesita leer el puerto dinámico del sistema
    port = int(os.environ.get("PORT", 48910))
    app.run(host="0.0.0.0", port=port, debug=True)