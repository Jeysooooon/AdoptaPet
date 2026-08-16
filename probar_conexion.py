import os
import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

pymysql.install_as_MySQLdb()

# 1. Cargar las variables ANTES de crear el objeto app
load_dotenv()

app = Flask(__name__)

def normalize_database_url(database_url):
    if not database_url:
        return database_url
    database_url = database_url.strip()
    if database_url.startswith('mysql://'):
        return database_url.replace('mysql://', 'mysql+pymysql://', 1)
    return database_url

# 2. Asignar la variable leída del sistema
app.config['SQLALCHEMY_DATABASE_URI'] = normalize_database_url(os.getenv('DATABASE_URL'))
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