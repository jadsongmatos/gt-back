import os
import logging
from flask import Flask, request, jsonify
from waitress import serve
from function import handler

from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve
from function import handler

# Configurar LOG_LEVEL
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level_str, logging.INFO)

# Setup do logger
logging.basicConfig(level=numeric_level,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Ajustar loggers específicos
logging.getLogger("waitress").setLevel(numeric_level)
logging.getLogger("werkzeug").setLevel(numeric_level)

# App Flask
app = Flask(__name__)

# permitir CORS
CORS(app)
#CORS(app, resources={r"/*": {"origins": ["http://localhost:5000", "http://127.0.0.1:5000"]}})

app.logger.setLevel(numeric_level)

# Classes Event e Context
class Event:
    def __init__(self):
        self.body = request.get_data()
        self.headers = request.headers
        self.method = request.method
        self.query = request.args
        self.path = request.path

class Context:
    def __init__(self):
        self.hostname = os.getenv('HOSTNAME', 'localhost')

# Helpers de formatação
def format_status_code(res):
    if 'statusCode' in res:
        return res['statusCode']
    return 200

def get_content_type(res):
    if 'headers' in res:
        return res['headers'].get('Content-type', '') if isinstance(res['headers'], dict) else ''

def format_body(res, content_type):
    if content_type == 'application/octet-stream':
        return res['body']
    if 'body' not in res:
        return ""
    if isinstance(res['body'], dict):
        return jsonify(res['body'])
    return str(res['body'])

def format_headers(res):
    if 'headers' not in res:
        return []
    if isinstance(res['headers'], dict):
        return [(key, value) for key, value in res['headers'].items()]
    return res['headers']

def format_response(res):
    if res is None:
        return ('', 200)
    if isinstance(res, dict):
        status_code = format_status_code(res)
        content_type = get_content_type(res)
        body = format_body(res, content_type)
        headers = format_headers(res)
        return (body, status_code, headers)
    return res

# Rotas
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def call_handler(path):
    event = Event()
    context = Context()
    response_data = handler.handle(event, context)
    return format_response(response_data)

# Main
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)
