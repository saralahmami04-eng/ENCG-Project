from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import desc
from app import db
from app.avis import avis_bp
from app.models import Avis

CATEGORIES = [
    ('general',    '💬 Avis général'),
    ('ressources', '📚 Ressources'),
    ('salles',     '🚪 Salles d\'étude'),
    ('premium',    '⭐ Section premium'),
]


@avis_bp.route('/')
@login_required
def index():
    """Page publique qui montre tous les avis."""
    cat_filter = request.args.get('categorie', '')
    query = Avis.query.filter_by(is_public=True)
    if cat_filter:
        query = query.filter_by(categorie=cat_filter)
    tous_avis = query.order_by(desc(Avis.created_at)).all()

    # Statistiques
    tous = Avis.query.filter_by(is_public=True).all()
    note_moyenne = round(sum(a.note for a in tous) / len(tous), 1) if tous else 0

    mon_avis = Avis.query.filter_by(auteur_id=current_user.id).first()

    return render_template('avis/index.html',
        tous_avis=tous_avis,
        categories=CATEGORIES,
        cat_filter=cat_filter,
        note_moyenne=note_moyenne,
        total_avis=len(tous),
        mon_avis=mon_avis,
    )


@avis_bp.route('/donner', methods=['GET', 'POST'])
@login_required
def donner():
    """Formulaire pour donner son avis."""
    # Un seul avis par utilisateur
    existant = Avis.query.filter_by(auteur_id=current_user.id).first()

    if request.method == 'POST':
        contenu   = request.form.get('contenu', '').strip()
        note      = request.form.get('note', type=int, default=5)
        categorie = request.form.get('categorie', 'general')
        is_public = request.form.get('is_public') == 'on'

        if not contenu:
            flash("Le contenu de l'avis est obligatoire.", 'danger')
            return render_template('avis/donner.html', categories=CATEGORIES, existant=existant)

        if note not in range(1, 6):
            note = 5

        if existant:
            # Modifier l'avis existant
            existant.contenu   = contenu
            existant.note      = note
            existant.categorie = categorie
            existant.is_public = is_public
            flash("Votre avis a été mis à jour !", 'success')
        else:
            # Créer un nouvel avis
            avis = Avis(
                auteur_id=current_user.id,
                contenu=contenu,
                note=note,
                categorie=categorie,
                is_public=is_public,
            )
            db.session.add(avis)
            flash("Merci pour votre avis ! 🙏", 'success')

        db.session.commit()
        return redirect(url_for('avis.index'))

    return render_template('avis/donner.html', categories=CATEGORIES, existant=existant)


@avis_bp.route('/supprimer/<int:avis_id>', methods=['POST'])
@login_required
def supprimer(avis_id):
    """Supprimer son propre avis."""
    avis = Avis.query.get_or_404(avis_id)
    if avis.auteur_id != current_user.id and not current_user.is_admin:
        flash("Vous ne pouvez pas supprimer cet avis.", 'danger')
        return redirect(url_for('avis.index'))
    db.session.delete(avis)
    db.session.commit()
    flash("Avis supprimé.", 'info')
    return redirect(url_for('avis.index'))