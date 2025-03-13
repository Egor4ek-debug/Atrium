import uuid

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from .models import User, Task
        db.create_all()

        # Создание администратора по умолчанию
        try:
            admin_phone = '+79524603494'
            if not User.query.filter_by(phone_number=admin_phone).first():
                admin = User(
                    id=uuid.uuid4(),
                    full_name='Admin',
                    phone_number=admin_phone,
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
        except Exception as e:
            app.logger.error(f"Ошибка создания администратора: {e}")

        # Инициализация компонентов
        from .routes import init_routes
        from .admin import init_admin
        from .telegram_handlers import setup_telegram_bot

        init_routes(app)
        init_admin(app)

        # Запуск Telegram-бота
        if app.config.get('TELEGRAM_TOKEN'):
            setup_telegram_bot(app, app.config['TELEGRAM_TOKEN'])

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        try:
            return User.query.get(uuid.UUID(user_id))
        except (ValueError, TypeError):
            return None

    return app
