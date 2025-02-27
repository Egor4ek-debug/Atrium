from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from models import User, Task
        db.create_all()

        # Создание администратора
        admin_phone = '+79524603494'
        if not User.query.filter_by(phone_number=admin_phone).first():
            admin = User(
                full_name='Admin',
                phone_number=admin_phone,
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

        from admin import init_admin
        from routes import init_routes
        from telegram_handlers import setup_telegram_bot

        init_admin(app)
        init_routes(app)

        if app.config['TELEGRAM_TOKEN']:
            setup_telegram_bot(app, app.config['TELEGRAM_TOKEN'])

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app