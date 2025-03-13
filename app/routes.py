from flask import render_template, request, redirect, url_for, abort
from flask_login import login_user, current_user, login_required
from app import db
from app.models import User, Task


def init_routes(app):
    @app.route('/admin')
    @login_required
    def admin_protected():
        return redirect(url_for('admin.index'))

    @app.route('/')
    def index():
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')

        phone = request.form['phone'].strip()
        user = User.query.filter_by(phone_number=phone).first()
        if user:
            login_user(user)
            return redirect(url_for('admin.index'))
        return "Доступ запрещен", 403

    @app.route('/stats')
    @login_required
    def stats():
        if current_user.role != 'admin':
            abort(403)

        total_tasks = Task.query.count()
        completed_tasks = Task.query.filter_by(status='done').count()

        workers_stats = db.session.query(
            User.full_name,
            db.func.count(Task.id).label('total'),
            db.func.sum(db.case((Task.status == 'done', 1), else_=0)).label('completed')
        ).join(Task).group_by(User.id).all()

        return render_template('admin/stats.html',
                               total_tasks=total_tasks,
                               completed_tasks=completed_tasks,
                               workers_stats=workers_stats)