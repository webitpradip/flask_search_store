import os

class Config:
    SECRET_KEY = os.urandom(24)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/flaskr.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
