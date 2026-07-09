import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

database_url = os.getenv('DATABASE_URL')
if database_url:
    database_url = database_url.strip()

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.route('/')
def home():
    return {"status": "Microservicio de Usuarios Corriendo Exitosamente"}, 200

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 48910))
    app.run(host="0.0.0.0", port=port, debug=True)