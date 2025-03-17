from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_user

from app.models import User


def init_routes(app):
    @app.route('/')
    def index():
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('admin.index'))

        if request.method == 'POST':
            phone = request.form.get('phone')
            user = User.query.filter_by(phone_number=phone).first()

            if user and user.role == 'admin':
                login_user(user)
                return redirect(url_for('admin.index'))
            else:
                flash('Неверный номер телефона или недостаточно прав', 'danger')

        return render_template('login.html')
