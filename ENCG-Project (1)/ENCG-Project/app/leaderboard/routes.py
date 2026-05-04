from flask import render_template, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from app.leaderboard import leaderboard_bp
from app.models import User, ENCG_SCHOOLS


@leaderboard_bp.route('/')
@login_required
def index():
    school_filter = request.args.get('school', '')

    query = User.query
    if school_filter:
        query = query.filter_by(school=school_filter)

    top_users = query.order_by(desc(User.score)).limit(100).all()

    # Calculer le rang de l'utilisateur actuel
    all_users = User.query.order_by(desc(User.score)).all()
    mon_rang = next((i + 1 for i, u in enumerate(all_users) if u.id == current_user.id), None)

    return render_template('leaderboard/index.html',
        top_users=top_users,
        schools=ENCG_SCHOOLS,
        school_filter=school_filter,
        mon_rang=mon_rang,
    )