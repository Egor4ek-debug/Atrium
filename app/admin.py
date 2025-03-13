from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import SelectField
from app import db
from .models import User, Task
from .config import Config
import requests

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        from flask import redirect, url_for
        return redirect(url_for('login'))


class UserAdminView(SecureModelView):
    column_list = ['full_name', 'phone_number', 'role']
    form_columns = ['full_name', 'phone_number', 'role']
    form_overrides = {'role': SelectField}
    form_args = {
        'role': {
            'choices': [('admin', 'Admin'), ('worker', 'Worker')],
            'coerce': str
        }
    }


class TaskAdminView(SecureModelView):

    column_list = ['description', 'address', 'due_time', 'worker', 'status']
    form_columns = ['description', 'address', 'due_time', 'worker', 'status']
    form_ajax_refs = {
        'worker': {
            'fields': ['full_name'],
            'page_size': 10
        }
    }

    def on_model_change(self, form, model, is_created):
        if is_created:
            self.send_task_notification(model)
        return super().on_model_change(form, model, is_created)

    def send_task_notification(self, task):
        try:
            from .config import Config  # Локальный импорт
            if task.worker and task.worker.telegram_id:
                message = (
                    "🎯 *Новая задача!*\n"
                    f"📝 Описание: {task.description}\n"
                    f"📍 Адрес: {task.address}\n"
                    f"⏰ Срок: {task.due_time.strftime('%d.%m.%Y %H:%M')}"
                )

                url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
                response = requests.post(url, json={
                    'chat_id': task.worker.telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                })
                response.raise_for_status()  # Проверка ошибок HTTP
        except Exception as e:
            print(f"Ошибка отправки уведомления: {str(e)}")


def init_admin(app):
    admin = Admin(app, name='Task Manager', template_mode='bootstrap3')
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(TaskAdminView(Task, db.session))