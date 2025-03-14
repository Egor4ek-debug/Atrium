import asyncio
import threading

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from telegram.helpers import escape_markdown

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

                # Приветственное сообщение
                if update.message.text == '/start':
                    # Формируем текст приветствия
                    welcome_text = (
                        "👋 *Добро пожаловать в Task Manager Bot!*\n\n"
                        "⚙️ **Назначение:**\n"
                        "1. Получайте задачи от администратора\n"
                        "2. Обновляйте статусы через кнопки\n"
                        "3. Указывайте причины при проблемах\n\n"
                        "📌 **Команды:**\n"
                        "/мои\_задачи - список активных задач"  # Экранируем нижнее подчеркивание
                    )

                    # Экранируем специальные символы для MarkdownV2
                    escaped_text = escape_markdown(welcome_text, version=2)

                    user = User.query.filter_by(telegram_id=user_id).first()

                    if user and user.telegram_id:
                        await update.message.reply_text(
                            escaped_text,
                            parse_mode='MarkdownV2',
                            reply_markup=ReplyKeyboardMarkup([["/мои_задачи"]], resize_keyboard=True)
                        )
                    else:
                        contact_btn = KeyboardButton("📲 Привязать аккаунт", request_contact=True)
                        await update.message.reply_text(
                            escaped_text,
                            parse_mode='MarkdownV2',
                            reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
                        )

                # Обработка задач
                elif update.message.text == '/мои_задачи':
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        await update.message.reply_text("❌ Аккаунт не привязан!")
                        return

                    tasks = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['new', 'in_progress'])
                    ).all()

                    for task in tasks:
                        if task.status == 'new':
                            task.status = 'in_progress'
                            db.session.commit()

                    markup = ReplyKeyboardMarkup(
                        [
                            ['✅ Готово', '🚫 Проблемы'],
                            ['⛔ Отказаться'],
                            ['🔄 Обновить']
                        ],
                        resize_keyboard=True
                    )

                    response = ["📌 *Ваши задачи:*"]
                    for task in tasks:
                        status_emoji = {
                            'new': '🆕',
                            'in_progress': '🏗',
                            'done': '✅',
                            'canceled': '🚫',
                            'rejected': '⛔'
                        }.get(task.status, '')

                        # Экранирование Markdown-символов
                        description = escape_markdown(task.description, version=2)
                        address = escape_markdown(task.address, version=2)
                        due_time = escape_markdown(task.due_time.strftime('%d.%m.%Y %H:%M'), version=2)

                        task_info = (
                            f"{status_emoji} *{description}*\n"
                            f"📍 Адрес: {address}\n"
                            f"⏰ Срок: {due_time}"
                        )
                        response.append(task_info)

                    await update.message.reply_text(
                        "\n\n".join(response),
                        parse_mode='MarkdownV2',  # Указание версии Markdown
                        reply_markup=markup
                    )
                # Обработка статусов
                elif update.message.text in ['✅ Готово', '🚫 Проблемы', '⛔ Отказаться']:
                    user = User.query.filter_by(telegram_id=user_id).first()
                    task = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['new', 'in_progress'])
                    ).first()

                    if not task:
                        await update.message.reply_text("❌ Нет активных задач")
                        return

                    if update.message.text == '✅ Готово':
                        task.status = 'done'
                        reply = "✅ Задача выполнена!"
                    elif update.message.text == '🚫 Проблемы':
                        task.status = 'canceled'
                        reply = "🚫 Укажите причину (напишите текст после команды)"
                    elif update.message.text == '⛔ Отказаться':
                        task.status = 'rejected'
                        reply = "⛔ Укажите причину отказа (напишите текст после команды)"

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
