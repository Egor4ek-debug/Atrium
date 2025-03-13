import asyncio
import threading
from datetime import datetime

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackContext,
    filters
)

from app import db
from app.models import User, Task


def setup_telegram_bot(app, token):
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(token).build()

        async def handle_message(update: Update, context: CallbackContext):
            with app.app_context():
                user_id = update.message.from_user.id

                # Обработка контакта
                if update.message.contact:
                    phone = update.message.contact.phone_number
                    if not phone.startswith('+'):
                        phone = f'+{phone}'

                    user = User.query.filter_by(phone_number=phone).first()
                    if user:
                        user.telegram_id = user_id
                        db.session.commit()
                        await update.message.reply_text("✅ Аккаунт успешно привязан!")
                    else:
                        await update.message.reply_text(f"❌ Пользователь с номером {phone} не найден")

                # Команда /start
                elif update.message.text == '/start':
                    welcome_text = (
                        "👋 Добро пожаловать в Task Manager Bot!\n\n"
                        "📌 Для работы с системой:\n"
                        "1. Привяжите телефон через кнопку ниже\n"
                        "2. Ожидайте назначения задач\n"
                        "3. Обновляйте статусы через кнопки\n\n"
                        "⚙️ Доступные команды:\n"
                        "/мои_задачи - список ваших задач"
                    )

                    contact_btn = KeyboardButton("📲 Привязать аккаунт", request_contact=True)
                    markup = ReplyKeyboardMarkup(
                        [[contact_btn], ["/мои_задачи"]],
                        resize_keyboard=True
                    )
                    await update.message.reply_text(welcome_text, reply_markup=markup)

                # Показать задачи
                elif update.message.text == '/мои_задачи':
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        return

                    tasks = Task.query.filter_by(worker_id=user.id).all()
                    markup = ReplyKeyboardMarkup(
                        [
                            ['✅ Готово', '🚫 Не выполнено'],
                            ['⛔ Не смогу'],
                            ['🔄 Обновить']
                        ],
                        resize_keyboard=True
                    )

                    if not tasks:
                        await update.message.reply_text("📭 Нет активных задач", reply_markup=markup)
                        return

                    response = ["📌 Ваши задачи:"]
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
                            f"📍 Адрес: {task.address}\n"
                            f"⏰ Срок: {task.due_time.strftime('%d.%m.%Y %H:%M')}\n"
                            f"📌 Статус: {status}"
                        )

                    await update.message.reply_text("\n\n".join(response), reply_markup=markup)

                # Обработка статусов
                elif update.message.text in ['✅ Готово', '🚫 Не выполнено', '⛔ Не смогу']:
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        return

                    task = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['new', 'in_progress'])
                    ).first()

                    if not task:
                        await update.message.reply_text("❌ Нет задач для обновления")
                        return

                    if update.message.text == '✅ Готово':
                        task.status = 'done'
                        task.completed_at = datetime.utcnow()
                        reply = "✅ Задача отмечена выполненной"
                    elif update.message.text == '🚫 Не выполнено':
                        task.status = 'canceled'
                        reply = "🚫 Укажите причину через пробел"
                    elif update.message.text == '⛔ Не смогу':
                        task.status = 'rejected'
                        reply = "⛔ Укажите причину через пробел"

                    db.session.commit()
                    await update.message.reply_text(reply, reply_markup=ReplyKeyboardRemove())

                # Сохранение причины
                elif update.message.text.startswith(('🚫', '⛔')):
                    user = User.query.filter_by(telegram_id=user_id).first()
                    task = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['canceled', 'rejected'])
                    ).first()

                    if task:
                        task.reason = update.message.text.split(' ', 1)[-1]
                        db.session.commit()
                        await update.message.reply_text("📝 Причина сохранена")

        application.add_handler(MessageHandler(filters.ALL, handle_message))
        application.run_polling()

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
