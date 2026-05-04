from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db, socketio
from app.rooms import rooms_bp
from app.models import StudyRoom, Message, User, ENCG_SCHOOLS
from flask_socketio import join_room, leave_room, emit
from datetime import datetime


@rooms_bp.route('/')
@login_required
def index():
    school_filter = request.args.get('school', '')
    mode_filter = request.args.get('mode', '')

    query = StudyRoom.query.filter_by(is_active=True)
    if school_filter:
        query = query.filter_by(school=school_filter)
    if mode_filter:
        query = query.filter_by(mode=mode_filter)

    rooms = query.order_by(StudyRoom.created_at.desc()).all()
    return render_template('rooms/index.html', rooms=rooms, schools=ENCG_SCHOOLS,
                           school_filter=school_filter, mode_filter=mode_filter)


@rooms_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        mode = request.form.get('mode', 'group')
        subject = request.form.get('subject', '').strip()
        school = request.form.get('school', current_user.school)

        if not name:
            flash('Le nom de la salle est obligatoire.', 'danger')
            return render_template('rooms/create.html', schools=ENCG_SCHOOLS)

        room = StudyRoom(name=name, description=description, mode=mode,
                         subject=subject, school=school, creator_id=current_user.id)
        db.session.add(room)
        db.session.commit()
        flash(f'Salle "{name}" créée avec succès !', 'success')
        return redirect(url_for('rooms.room', room_id=room.id))

    return render_template('rooms/create.html', schools=ENCG_SCHOOLS)


@rooms_bp.route('/<int:room_id>')
@login_required
def room(room_id):
    study_room = StudyRoom.query.get_or_404(room_id)
    messages = Message.query.filter_by(room_id=room_id).order_by(Message.created_at.asc()).limit(100).all()
    return render_template('rooms/room.html', room=study_room, messages=messages)


@rooms_bp.route('/<int:room_id>/delete', methods=['POST'])
@login_required
def delete_room(room_id):
    study_room = StudyRoom.query.get_or_404(room_id)
    if study_room.creator_id != current_user.id:
        flash("Vous n'êtes pas autorisé à supprimer cette salle.", 'danger')
        return redirect(url_for('rooms.index'))
    study_room.is_active = False
    db.session.commit()
    flash('Salle supprimée.', 'info')
    return redirect(url_for('rooms.index'))


# ── Socket.IO events ──────────────────────────────────────────────────────────

@socketio.on('join')
def on_join(data):
    room_id = str(data['room_id'])
    join_room(room_id)
    emit('user_joined', {
        'username': data['username'],
        'message': f"{data['username']} a rejoint la salle",
        'timestamp': datetime.utcnow().strftime('%H:%M'),
    }, to=room_id)


@socketio.on('leave')
def on_leave(data):
    room_id = str(data['room_id'])
    leave_room(room_id)
    emit('user_left', {
        'username': data['username'],
        'message': f"{data['username']} a quitté la salle",
        'timestamp': datetime.utcnow().strftime('%H:%M'),
    }, to=room_id)


@socketio.on('send_message')
def on_message(data):
    room_id = data['room_id']
    user_id = data['user_id']
    content = data.get('content', '').strip()
    if not content:
        return

    msg = Message(content=content, room_id=room_id, user_id=user_id)
    db.session.add(msg)
    db.session.commit()

    user = User.query.get(user_id)
    emit('new_message', {
        'username': user.name,
        'content': content,
        'timestamp': datetime.utcnow().strftime('%H:%M'),
        'user_id': user_id,
    }, to=str(room_id))


# WebRTC signaling — broadcast to room, clients filter by target field
@socketio.on('camera_on')
def on_camera_on(data):
    emit('camera_on', data, to=str(data['room_id']), include_self=False)


@socketio.on('camera_off')
def on_camera_off(data):
    emit('camera_off', data, to=str(data['room_id']), include_self=False)


@socketio.on('webrtc_offer')
def on_offer(data):
    emit('webrtc_offer', data, to=str(data['room_id']), include_self=False)


@socketio.on('webrtc_answer')
def on_answer(data):
    emit('webrtc_answer', data, to=str(data['room_id']), include_self=False)


@socketio.on('webrtc_ice')
def on_ice(data):
    emit('webrtc_ice', data, to=str(data['room_id']), include_self=False)
