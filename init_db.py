from app import app, db
from models import Record, File

with app.app_context():
    db.create_all()
