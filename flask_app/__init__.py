import os
from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO(async_mode='threading')

def create_app(debug=False):
    app = Flask(__name__)

    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.debug = debug
    app.secret_key = 'AKWNF1231082fksejfOSEHFOISEHF24142124124124124iesfhsoijsopdjf'

    from .utils.database.database import database
    try:
        db = database()
        db.createTables(purge=False)
    except Exception as e:
        print(f"Warning: Could not connect to database on startup: {e}")

    socketio.init_app(app)

    with app.app_context():
        from . import routes
        return app
