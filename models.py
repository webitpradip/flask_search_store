from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    group_name = db.Column(db.String(120), nullable=True)
    files = db.relationship('File', backref='record', lazy=True)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'), nullable=False)
