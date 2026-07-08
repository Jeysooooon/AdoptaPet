import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# 1. Cargar las variables ANTES de crear el objeto app
load_dotenv()

app = Flask(__name__)

# 2. Asignar la variable leída del sistema
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

if __name__ == "__main__":
    with app.app_context():
        try:
            # Intentar realizar una operación simple
            db.engine.connect()
            print("--- ¡CONEXIÓN EXITOSA! ---")
        except Exception as e:
            print(f"--- ERROR: {e}")