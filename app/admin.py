import requests
from flask import current_app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from telegram.helpers import escape_markdown
from wtforms import SelectField, validators

from app import db
from app.models import User, Task


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'


class UserAdminView(SecureModelView):
    form_excluded_columns = ['tasks']
    column_list = ['full_name', 'phone_number', 'role']

    form_overrides = {'role': SelectField}
    form_args = {
        'role': {
            'choices': [('admin', 'Admin'), ('worker', 'Worker')],
            'coerce': str,
            'validators': [validators.InputRequired()]
        }
    }


class TaskAdminView(SecureModelView):
    column_list = ['description', 'address', 'due_time', 'worker', 'status']
    form_excluded_columns = ['reason', 'created_at', 'completed_at']

    def on_model_change(self, form, model, is_created):
        if is_created:
            self.send_telegram_notification(model)

    def send_telegram_notification(self, task):
        try:
            if task.worker and task.worker.telegram_id:
                message = (
                    "🎯 *Новая задача\!*\n"
                    f"📝 Описание: {escape_markdown(task.description, version=2)}\n"
                    f"📍 Адрес: {escape_markdown(task.address, version=2)}\n"
                    f"⏰ Срок: {escape_markdown(task.due_time.strftime('%d\.%m\.%Y %H:%M'), version=2)}"
                )

                url = f"https://api.telegram.org/bot{current_app.config['TELEGRAM_TOKEN']}/sendMessage"
                requests.post(
                    url,
                    json={
                        "chat_id": task.worker.telegram_id,
                        "text": message,
                        "parse_mode": "MarkdownV2"
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Ошибка уведомления: {str(e)}")

    column_formatters = {
        'worker': lambda v, c, m, p: m.worker.full_name if m.worker else ''
    }

    form_args = {
        'worker': {
            'query_factory': lambda: User.query.filter_by(role='worker'),
            'get_label': 'full_name'
        }
    }


def init_admin(app):
    admin = Admin(app, name='Task Manager', template_mode='bootstrap3', url='/admin')
    admin.add_view(UserAdminView(User, db.session, name='Сотрудники'))
    admin.add_view(TaskAdminView(Task, db.session, name='Задачи'))
