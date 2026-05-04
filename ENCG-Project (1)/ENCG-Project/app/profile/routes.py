from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from app.profile import profile_bp
from app.models import StudySession, Resource, Application


@profile_bp.route('/')
@login_required
def index():
    # Sessions des 7 derniers jours
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = StudySession.query.filter(
        StudySession.user_id == current_user.id,
        StudySession.started_at >= week_ago
    ).all()

    weekly_minutes = sum(s.duration_minutes for s in recent_sessions)

    # Données par jour pour le graphique
    daily_data = {}
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        key = day.strftime('%a')
        daily_data[key] = 0
    for s in recent_sessions:
        key = s.started_at.strftime('%a')
        if key in daily_data:
            daily_data[key] += s.duration_minutes

    my_resources    = Resource.query.filter_by(uploader_id=current_user.id).all()
    total_downloads = sum(r.download_count for r in my_resources)
    total_votes     = sum(r.vote_score for r in my_resources)
    my_applications = Application.query.filter_by(user_id=current_user.id)\
                        .order_by(Application.created_at.desc()).limit(5).all()

    return render_template('profile/index.html',
        weekly_minutes=weekly_minutes,
        daily_data=daily_data,
        my_resources=my_resources,
        total_downloads=total_downloads,
        total_votes=total_votes,
        my_applications=my_applications,
    )


@profile_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    current_user.bio     = request.form.get('bio', '').strip()[:300]
    current_user.filiere = request.form.get('filiere', '').strip()
    db.session.commit()
    flash('Profil mis à jour !', 'success')
    return redirect(url_for('profile.index'))


@profile_bp.route('/session/start', methods=['POST'])
@login_required
def start_session():
    """Appelé en JavaScript quand l'étudiant entre dans une salle."""
    room_id = request.form.get('room_id', type=int)
    # Fermer toute session ouverte
    open_sess = StudySession.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if open_sess:
        _close_session(open_sess)
    sess = StudySession(user_id=current_user.id, room_id=room_id)
    db.session.add(sess)
    db.session.commit()
    return jsonify({'session_id': sess.id, 'status': 'started'})


@profile_bp.route('/session/end', methods=['POST'])
@login_required
def end_session():
    """Appelé en JavaScript quand l'étudiant quitte une salle."""
    sess = StudySession.query.filter_by(user_id=current_user.id, ended_at=None).first()
    if sess:
        _close_session(sess)
    return jsonify({'status': 'ended'})


def _close_session(sess):
    now = datetime.utcnow()
    sess.ended_at = now
    duration = int((now - sess.started_at).total_seconds() / 60)
    sess.duration_minutes = duration
    sess.student.total_study_minutes += duration
    sess.student.score += duration // 30   # +1 point par 30 minutes
    db.session.commit()