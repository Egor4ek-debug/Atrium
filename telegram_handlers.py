import threading
import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackContext,
    filters
)
from datetime import datetime
from app import db
from models import User, Task
from config import Config


def setup_telegram_bot(app, token):
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(token).build()

        async def handle_message(update: Update, context: CallbackContext):
            with app.app_context():
                if update.message.contact:
                    user = User.query.filter_by(
                        phone_number=update.message.contact.phone_number
                    ).first()
                    if user:
                        user.telegram_id = update.message.from_user.id
                        db.session.commit()
                        await update.message.reply_text("✅ Аккаунт привязан!")

                elif update.message.text == '/start':
                    contact_btn = KeyboardButton("📲 Привязать аккаунт", request_contact=True)
                    markup = ReplyKeyboardMarkup(
                        [[contact_btn], ["/tasks"]],
                        resize_keyboard=True,
                        one_time_keyboard=False
                    )
                    await update.message.reply_text(
                        "Доступные команды:",
                        reply_markup=markup
                    )

                elif update.message.text == '/tasks':
                    user = User.query.filter_by(telegram_id=update.message.from_user.id).first()
                    if user:
                        tasks = Task.query.filter_by(worker_id=user.id).all()

                        if not tasks:
                            await update.message.reply_text("У вас нет активных задач")
                            return

                        response = ["📌 Ваши текущие задачи:"]
                        for task in tasks:
                            status = {
                                'new': '🆕 Новая',
                                'in_progress': '🏗 В работе',
                                'done': '✅ Выполнена',
                                'canceled': '🚫 Отменена',
                                'rejected': '⛔ Отклонена'
                            }.get(task.status, task.status)

                            response.append(
                                f"• {task.description}\n"
                                f"Адрес: {task.address}\n"
                                f"Срок: {task.due_time.strftime('%d.%m.%Y %H:%M')}\n"
                                f"Статус: {status}"
                            )

                        await update.message.reply_text("\n\n".join(response))

                elif update.message.text in ['✅ Готово', '🚫 Не выполнено', '⛔ Не смогу']:
                    user = User.query.filter_by(telegram_id=update.message.from_user.id).first()
                    if not user:
                        return

                    task = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['new', 'in_progress'])
                    ).first()

                    if not task:
                        await update.message.reply_text("❌ Нет активных задач для обновления")
                        return

                    if update.message.text == '✅ Готово':
                        task.status = 'done'
                        task.completed_at = datetime.utcnow()
                        reply = "✅ Задача отмечена выполненной"
                    elif update.message.text == '🚫 Не выполнено':
                        task.status = 'canceled'
                        reply = "🚫 Задача отменена. Укажите причину через пробел"
                    elif update.message.text == '⛔ Не смогу':
                        task.status = 'rejected'
                        reply = "⛔ Задача отклонена. Укажите причину через пробел"

                    db.session.commit()
                    await update.message.reply_text(reply)

                elif update.message.text.startswith(('🚫 Не выполнено', '⛔ Не смогу')):
                    user = User.query.filter_by(telegram_id=update.message.from_user.id).first()
                    task = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['canceled', 'rejected'])
                    ).first()

                    if task:
                        task.reason = update.message.text.split(' ', 1)[1]
                        db.session.commit()
                        await update.message.reply_text("Причина сохранена")

        application.add_handler(MessageHandler(filters.ALL, handle_message))
        application.run_polling()

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()