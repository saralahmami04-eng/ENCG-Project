from functools import wraps
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from app.admin import admin_bp
from app.models import User, Resource, StudyRoom, Opportunity, Application, Avis


def admin_required(f):
    """Décorateur : seuls les admins peuvent accéder."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès réservé aux administrateurs.", 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Tableau de bord principal de l'admin."""
    total_users     = User.query.count()
    total_resources = Resource.query.count()
    total_rooms     = StudyRoom.query.count()
    total_opps      = Opportunity.query.count()
    total_avis      = Avis.query.count()

    # Derniers inscrits
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()

    # Top contributeurs
    top_users = User.query.order_by(desc(User.score)).limit(5).all()

    return render_template('admin/index.html',
        total_users=total_users,
        total_resources=total_resources,
        total_rooms=total_rooms,
        total_opps=total_opps,
        total_avis=total_avis,
        recent_users=recent_users,
        top_users=top_users,
    )


@admin_bp.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    """Liste complète de tous les utilisateurs."""
    school_filter = request.args.get('school', '')
    search        = request.args.get('search', '')

    query = User.query
    if school_filter:
        query = query.filter_by(school=school_filter)
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )

    users = query.order_by(desc(User.created_at)).all()

    from app.models import ENCG_SCHOOLS
    return render_template('admin/utilisateurs.html',
        users=users,
        schools=ENCG_SCHOOLS,
        school_filter=school_filter,
        search=search,
    )


@admin_bp.route('/utilisateur/<int:user_id>')
@login_required
@admin_required
def detail_utilisateur(user_id):
    """Détail d'un utilisateur."""
    user = User.query.get_or_404(user_id)
    return render_template('admin/detail_utilisateur.html', user=user)


@admin_bp.route('/utilisateur/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Promouvoir ou rétrograder un admin."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas modifier votre propre statut.", 'warning')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        statut = "admin" if user.is_admin else "utilisateur normal"
        flash(f"{user.name} est maintenant {statut}.", 'success')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/utilisateur/<int:user_id>/supprimer', methods=['POST'])
@login_required
@admin_required
def supprimer_utilisateur(user_id):
    """Supprimer un utilisateur."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Vous ne pouvez pas vous supprimer vous-même.", 'danger')
        return redirect(url_for('admin.utilisateurs'))
    db.session.delete(user)
    db.session.commit()
    flash(f"L'utilisateur {user.name} a été supprimé.", 'success')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/avis')
@login_required
@admin_required
def voir_avis():
    """Voir tous les avis des étudiants."""
    avis = Avis.query.order_by(desc(Avis.created_at)).all()
    return render_template('admin/avis.html', avis=avis)


@admin_bp.route('/candidatures')
@login_required
@admin_required
def candidatures():
    """Voir toutes les candidatures premium."""
    apps = Application.query.order_by(desc(Application.created_at)).all()
    return render_template('admin/candidatures.html', apps=apps)