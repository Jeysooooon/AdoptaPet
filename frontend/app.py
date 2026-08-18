from flask import Flask, render_template, send_from_directory
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')

# Ruta principal: SPA
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# (opcional) servir favicon u otros assets fuera de /static si lo deseas
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
