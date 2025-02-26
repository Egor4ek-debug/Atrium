from datetime import datetime
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    telegram_id = db.Column(db.String(50))
    role = db.Column(db.String(20), default='worker')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('Task', back_populates='worker', lazy=True)

    def __repr__(self):
        return self.full_name

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    due_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    worker = db.relationship('User', back_populates='tasks')