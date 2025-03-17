import asyncio
import logging
import threading
from datetime import datetime

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from telegram.helpers import escape_markdown

from app import db
from app.models import User, Task

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def setup_telegram_bot(app, token):
    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        application = Application.builder().token(token).build()

        async def handle_message(update: Update, context: CallbackContext):
            with app.app_context():
                user_id = update.message.from_user.id
                text = update.message.text
                logger.info(f"Received message: {text} from user: {user_id}")
                # Если сообщение не содержит текста (например, это контакт)
                if text is None:
                    # Обработка контакта
                    if update.message.contact:
                        phone = update.message.contact.phone_number
                        print(phone)
                        user = User.query.filter_by(phone_number=phone).first()
                        if user:
                            user.telegram_id = user_id
                            db.session.commit()
                            await update.message.reply_text(
                                "✅ Аккаунт привязан!",
                                reply_markup=ReplyKeyboardMarkup([["/mytasks"]], resize_keyboard=True)
                            )
                        else:
                            await update.message.reply_text(
                                "Вас нет в базе",
                                reply_markup=ReplyKeyboardMarkup([["/mytasks"]], resize_keyboard=True)
                            )
                    return  # Выход, чтобы избежать ошибок
                # Обработка команды /start
                if text == '/start':
                    user = User.query.filter_by(telegram_id=user_id).first()
                    welcome_text = (
                        "👋 *Добро пожаловать в Task Manager Bot!*\n\n"
                        "⚙️ **Назначение:**\n"
                        "1. Получайте задачи\n"
                        "2. Обновляйте статусы через кнопки\n"
                        "3. Указывайте причины при проблемах\n\n"
                        "📌 **Команды:**\n"
                        "/mytasks - список активных задач"
                    )
                    escaped_text = escape_markdown(welcome_text, version=2)

                    if user and user.telegram_id:
                        await update.message.reply_text(
                            escaped_text,
                            parse_mode='MarkdownV2',
                            reply_markup=ReplyKeyboardMarkup([["/mytasks"]], resize_keyboard=True)
                        )
                    else:
                        contact_btn = KeyboardButton("📲 Привязать аккаунт", request_contact=True)
                        await update.message.reply_text(
                            escaped_text,
                            parse_mode='MarkdownV2',
                            reply_markup=ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True)
                        )

                # Обработка команды /mytasks
                elif text == '/mytasks':
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        await update.message.reply_text("❌ Аккаунт не привязан!")
                        return

                    tasks = Task.query.filter(
                        Task.worker_id == user.id,
                        Task.status.in_(['new', 'in_progress'])
                    ).all()

                    # Обновление статуса new -> in_progress
                    for task in tasks:
                        if task.status == 'new':
                            task.status = 'in_progress'
                            db.session.commit()
                            logger.info(f"Task {task.id} updated to 'in_progress'")

                    # Формирование клавиатуры
                    keyboard = []
                    task_map = {}  # Хранит соответствие короткого ID и полного UUID
                    for task in tasks:
                        task_id_short = task.id.hex[:8]  # Используем 8 символов для уникальности
                        task_map[task_id_short] = task.id
                        keyboard.append([
                            f"✅ Готово {task_id_short}",
                            f"🚫 Проблемы {task_id_short}",
                            f"⛔ Отказаться {task_id_short}"
                        ])
                    context.user_data['task_map'] = task_map  # Сохраняем в контексте
                    #keyboard.append(['🔄 Обновить'])

                    # Формирование сообщения
                    response = ["📋 *Активные задачи:*"]
                    for task in tasks:
                        desc = escape_markdown(task.description, version=2)
                        due_time = escape_markdown(
                            task.due_time.strftime('%d.%m.%Y %H:%M'),
                            version=2
                        )
                        response.append(
                            f"*\\#{task.id.hex[:8]}*: {desc}\n"
                            f"Статус: `{escape_markdown(task.status, version=2)}`\n"
                            f"Срок: {due_time}"
                        )

                    await update.message.reply_text(
                        "\n\n".join(response),
                        parse_mode='MarkdownV2',
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )

                # Обработка кнопок статусов
                elif any(text.startswith(prefix) for prefix in ['✅', '🚫', '⛔']):
                    user = User.query.filter_by(telegram_id=user_id).first()
                    if not user:
                        await update.message.reply_text("❌ Аккаунт не привязан!")
                        return

                    # Извлечение короткого ID из текста кнопки
                    task_id_short = text.split()[-1]
                    task_map = context.user_data.get('task_map', {})
                    task_id = task_map.get(task_id_short)

                    if not task_id:
                        await update.message.reply_text("❌ Задача не найдена!")
                        return

                    # Поиск задачи по полному UUID
                    task = Task.query.filter(
                        Task.id == task_id,
                        Task.worker_id == user.id
                    ).first()

                    if not task:
                        await update.message.reply_text("❌ Задача не найдена!")
                        return

                    # Обновление статуса
                    try:
                        if text.startswith('✅'):
                            task.status = 'done'
                            task.completed_at = datetime.utcnow()
                            reply = "✅ Статус обновлен: Завершено"
                        elif text.startswith('🚫'):
                            task.status = 'canceled'
                            reply = "📝 Укажите причину проблемы:"
                            context.user_data['pending_task'] = task.id
                        elif text.startswith('⛔'):
                            task.status = 'rejected'
                            reply = "📝 Укажите причину отказа:"
                            context.user_data['pending_task'] = task.id

                        db.session.commit()
                        logger.info(f"Task {task.id} status updated to {task.status}")
                        await update.message.reply_text(reply, reply_markup=ReplyKeyboardRemove())

                        await update.message.reply_text(
                            "Можете посмотреть новые задачи",
                            reply_markup=ReplyKeyboardMarkup([["/mytasks"]], resize_keyboard=True)
                        )

                    except Exception as e:
                        logger.error(f"Ошибка обновления задачи: {str(e)}", exc_info=True)
                        await update.message.reply_text("⚠️ Ошибка сервера")

                # Обработка причин
                elif 'pending_task' in context.user_data:
                    task_id = context.user_data.pop('pending_task')
                    task = Task.query.get(task_id)
                    if task:
                        task.reason = text
                        db.session.commit()
                        logger.info(f"Причина добавлена к задаче {task.id}")
                        await update.message.reply_text("📝 Причина сохранена")

                # Обработка контакта
                elif update.message.contact:
                    phone = update.message.contact.phone_number
                    user = User.query.filter_by(phone_number=phone).first()
                    if user:
                        user.telegram_id = user_id
                        db.session.commit()
                        await update.message.reply_text(
                            "✅ Аккаунт привязан!",
                            reply_markup=ReplyKeyboardMarkup([["/mytasks"]], resize_keyboard=True)
                        )

        application.add_handler(MessageHandler(filters.ALL, handle_message))
        application.run_polling()

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
