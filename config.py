import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "instance", "tasks.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')