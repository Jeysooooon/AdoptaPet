import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# Recuerda instalar: pip install flask flask-sqlalchemy pymysql python-dotenv
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        db.engine.connect()
        print("¡Conexión a Railway exitosa!")
    except Exception as e:
        print(f"Error de conexión: {e}")