from flask import current_app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import SelectField, validators
from sqlalchemy.orm import lazyload
from app import db
from app.models import User, Task
import requests


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'


class TaskAdminView(SecureModelView):
    column_list = ['description', 'address', 'due_time', 'worker', 'status', 'reason']
    form_columns = ['description', 'address', 'due_time', 'worker', 'status']

    # Фильтрация только работников
    def get_query(self):
        return super().get_query().join(User).filter(User.role == 'worker')

    # Выбор сотрудника по имени
    form_args = {
        'worker': {
            'query_factory': lambda: User.query.filter_by(role='worker'),
            'get_label': 'full_name'
        },
        'description': {'validators': [validators.InputRequired()]},
        'address': {'validators': [validators.InputRequired()]},
        'due_time': {'validators': [validators.InputRequired()]}
    }

    def on_model_change(self, form, model, is_created):
        if is_created and model.worker.telegram_id:
            self.send_telegram_notification(model)
        return super().on_model_change(form, model, is_created)

    def send_telegram_notification(self, task):
        try:
            message = (
                "🎯 *Новая задача!*\n"
                f"📝 {task.description}\n"
                f"📍 {task.address}\n"
                f"⏰ {task.due_time.strftime('%d.%m.%Y %H:%M')}"
            )
            requests.post(
                f"https://api.telegram.org/bot{current_app.config['TELEGRAM_TOKEN']}/sendMessage",
                json={
                    'chat_id': task.worker.telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
            )
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки уведомления: {e}")


def init_admin(app):
    admin = Admin(app, name='Task Manager', template_mode='bootstrap3', url='/admin')
    admin.add_view(ModelView(User, db.session, name='Сотрудники'))
    admin.add_view(TaskAdminView(Task, db.session, name='Задачи'))