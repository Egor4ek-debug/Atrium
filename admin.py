from app import db
from models import User, Task
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import SelectField
import requests
from config import Config


class UserAdminView(ModelView):
    column_list = ['full_name', 'phone_number', 'role']
    form_columns = ['full_name', 'phone_number', 'role']
    form_overrides = {'role': SelectField}
    form_args = {
        'role': {
            'choices': [('admin', 'Admin'), ('worker', 'Worker')],
            'coerce': str
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'


class TaskAdminView(ModelView):
    column_list = ['description', 'address', 'due_time', 'worker', 'status']
    form_columns = ['description', 'address', 'due_time', 'worker', 'status']
    form_overrides = {'status': SelectField}
    form_args = {
        'status': {
            'choices': [
                ('new', 'Новая'),
                ('in_progress', 'В работе'),
                ('done', 'Выполнена'),
                ('canceled', 'Отменена'),
                ('rejected', 'Отклонена')
            ],
            'coerce': str
        }
    }

    def on_model_change(self, form, model, is_created):
        if is_created:
            self.send_task_notification(model)

    def send_task_notification(self, task):
        if task.worker and task.worker.telegram_id:
            keyboard = [[
                {"text": "✅ Готово"},
                {"text": "🚫 Не выполнено"},
                {"text": "⛔ Не смогу"}
            ]]

            message = (
                f"🎯 Новая задача!\n"
                f"Описание: {task.description}\n"
                f"Адрес: {task.address}\n"
                f"Срок: {task.due_time.strftime('%d.%m.%Y %H:%M')}"
            )

            url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={
                'chat_id': task.worker.telegram_id,
                'text': message,
                'reply_markup': {
                    'keyboard': keyboard,
                    'resize_keyboard': True
                }
            })


def init_admin(app):
    admin = Admin(app, name='Task Manager', template_mode='bootstrap3')
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(TaskAdminView(Task, db.session))