import os
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, send_from_directory, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.resources import resources_bp
from app.models import Resource, ResourceVote, ENCG_SCHOOLS

RESOURCE_TYPES = ['Cours', 'Résumé', 'Exercice', 'Examen', 'Autre']

# Points gagnés selon le type de ressource partagée
SCORE_POINTS = {
    'Résumé'   : 15,
    'Cours'    : 10,
    'Exercice' : 8,
    'Examen'   : 10,
    'Autre'    : 5,
}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@resources_bp.route('/')
@login_required
def index():
    school_filter = request.args.get('school', '')
    type_filter   = request.args.get('type', '')
    search        = request.args.get('search', '')
    sort          = request.args.get('sort', 'recent')

    query = Resource.query
    if school_filter: query = query.filter_by(school=school_filter)
    if type_filter:   query = query.filter_by(resource_type=type_filter)
    if search:        query = query.filter(Resource.title.ilike(f'%{search}%'))

    resources = query.all()

    # Tri
    if sort == 'votes':
        resources.sort(key=lambda r: r.vote_score, reverse=True)
    elif sort == 'downloads':
        resources.sort(key=lambda r: r.download_count, reverse=True)
    else:
        resources.sort(key=lambda r: r.created_at, reverse=True)

    # Votes de l'utilisateur courant
    my_votes = {v.resource_id: v.value for v in current_user.votes_given}

    return render_template('resources/index.html',
        resources=resources, schools=ENCG_SCHOOLS, resource_types=RESOURCE_TYPES,
        school_filter=school_filter, type_filter=type_filter,
        search=search, sort=sort, my_votes=my_votes)


@resources_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        title         = request.form.get('title', '').strip()
        description   = request.form.get('description', '').strip()
        resource_type = request.form.get('resource_type', '')
        subject       = request.form.get('subject', '').strip()
        school        = request.form.get('school', current_user.school)
        file          = request.files.get('file')

        if not title or not file or file.filename == '':
            flash('Le titre et le fichier sont obligatoires.', 'danger')
            return render_template('resources/upload.html', schools=ENCG_SCHOOLS, resource_types=RESOURCE_TYPES)

        if not allowed_file(file.filename):
            flash('Type de fichier non autorisé.', 'danger')
            return render_template('resources/upload.html', schools=ENCG_SCHOOLS, resource_types=RESOURCE_TYPES)

        original_name = file.filename
        filename = datetime.utcnow().strftime('%Y%m%d_%H%M%S_') + secure_filename(original_name)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        resource = Resource(
            title=title, description=description, file_path=filename,
            file_name=original_name, resource_type=resource_type,
            subject=subject, school=school, uploader_id=current_user.id,
        )
        db.session.add(resource)

        # Ajouter les points au score
        points = SCORE_POINTS.get(resource_type, 5)
        current_user.score += points

        db.session.commit()
        flash(f'Ressource partagée ! +{points} points ajoutés à votre score 🎉', 'success')
        return redirect(url_for('resources.index'))

    return render_template('resources/upload.html', schools=ENCG_SCHOOLS, resource_types=RESOURCE_TYPES)


@resources_bp.route('/download/<int:resource_id>')
@login_required
def download(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    resource.download_count += 1
    db.session.commit()
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        resource.file_path,
        as_attachment=True,
        download_name=resource.file_name,
    )


@resources_bp.route('/vote/<int:resource_id>', methods=['POST'])
@login_required
def vote(resource_id):
    """Vote +1 ou -1 sur une ressource. Appelé en AJAX."""
    resource = Resource.query.get_or_404(resource_id)
    value = request.form.get('value', type=int)

    if value not in (1, -1):
        return jsonify({'error': 'Valeur invalide'}), 400
    if resource.uploader_id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas voter pour votre propre ressource'}), 403

    existing = ResourceVote.query.filter_by(
        user_id=current_user.id, resource_id=resource_id
    ).first()

    if existing:
        if existing.value == value:
            # Même vote → annuler
            resource.uploader.score -= (5 if value == 1 else -3)
            db.session.delete(existing)
        else:
            # Vote inverse → changer
            existing.value = value
            resource.uploader.score += (8 if value == 1 else -8)
    else:
        db.session.add(ResourceVote(user_id=current_user.id, resource_id=resource_id, value=value))
        resource.uploader.score += (5 if value == 1 else -3)

    db.session.commit()
    return jsonify({
        'vote_score': resource.vote_score,
        'upvotes':    resource.upvotes,
        'downvotes':  resource.downvotes,
    })