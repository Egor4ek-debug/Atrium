from flask import render_template, request, redirect, url_for, abort
from flask_login import login_user, current_user, login_required
from app import db
from app.models import User, Task


def init_routes(app):
    @app.route('/admin/stats')
    @login_required
    def admin_stats():
        if current_user.role != 'admin':
            abort(403)

        # Статистика с outerjoin для сотрудников без задач
        workers_stats = db.session.query(
            User.full_name,
            db.func.count(Task.id).label('total'),
            db.func.sum(db.case((Task.status == 'done', 1), else_=0)).label('completed')
        ).outerjoin(Task, User.id == Task.worker_id).group_by(User.id).all()

        return render_template('admin/stats.html',
                               total_tasks=Task.query.count(),
                               completed_tasks=Task.query.filter_by(status='done').count(),
                               workers_stats=workers_stats)