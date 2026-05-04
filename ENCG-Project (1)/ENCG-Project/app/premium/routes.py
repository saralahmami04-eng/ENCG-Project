from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.premium import premium_bp
from app.models import Opportunity, Application

OPP_TYPES = ['Stage', 'Emploi', 'Concours', 'Bourse', 'Événement']

PSYCHO_QUESTIONS = [
    {'q': "Face à un problème complexe, vous préférez :", 'choices': [
        ("Analyser méthodiquement toutes les données avant d'agir", 4),
        ("Tester rapidement plusieurs solutions", 3),
        ("Consulter des collègues", 3),
        ("Attendre que la situation évolue", 1),
    ]},
    {'q': "En équipe, votre rôle naturel est :", 'choices': [
        ("Coordinateur / leader", 4),
        ("Expert technique", 4),
        ("Médiateur / facilitateur", 3),
        ("Suiveur", 2),
    ]},
    {'q': "Votre rapport aux délais professionnels :", 'choices': [
        ("Je livre toujours en avance", 5),
        ("Je respecte systématiquement les délais", 4),
        ("Je respecte dans la majorité des cas", 2),
        ("J'ai souvent du retard", 1),
    ]},
    {'q': "Comment gérez-vous l'échec ?", 'choices': [
        ("Je l'analyse pour en tirer des leçons", 5),
        ("Je m'en remets avec le temps", 3),
        ("Je cherche des responsables externes", 1),
        ("Je me remets rarement d'un échec", 1),
    ]},
    {'q': "Votre motivation pour ce poste est :", 'choices': [
        ("Très élevée — c'est mon premier choix", 5),
        ("Élevée — correspond bien à mes objectifs", 4),
        ("Moyenne", 2),
        ("Faible — je postule pour explorer", 1),
    ]},
]

SKILLS_QUESTIONS = [
    {'q': "Votre maîtrise d'Excel / Google Sheets :", 'choices': [
        ("Expert (TCD, macros, formules avancées)", 5),
        ("Avancé (formules complexes, graphiques)", 4),
        ("Intermédiaire (fonctions de base)", 2),
        ("Débutant", 1),
    ]},
    {'q': "Expérience en comptabilité / finance :", 'choices': [
        ("Oui, professionnelle (stage ou emploi)", 5),
        ("Oui, académique solide (projets, cas pratiques)", 4),
        ("Notions théoriques uniquement", 2),
        ("Non", 1),
    ]},
    {'q': "Votre niveau en anglais professionnel :", 'choices': [
        ("Courant / bilingue", 5),
        ("Intermédiaire avancé (B2)", 4),
        ("Intermédiaire (B1)", 2),
        ("Débutant", 1),
    ]},
    {'q': "Maîtrise d'un outil de gestion (ERP, CRM…) :", 'choices': [
        ("Oui, plusieurs outils professionnels", 5),
        ("Oui, un outil (Sage, Odoo…)", 4),
        ("Formation en cours", 2),
        ("Non", 1),
    ]},
    {'q': "Études de cas ou mémoires réalisés :", 'choices': [
        ("Oui, plusieurs, primés ou reconnus", 5),
        ("Oui, un ou deux de qualité", 4),
        ("En cours de rédaction", 2),
        ("Non", 1),
    ]},
]


def _calculer_score_ia(user, psycho_rep, skills_rep):
    max_p = sum(max(c[1] for c in q['choices']) for q in PSYCHO_QUESTIONS)
    max_s = sum(max(c[1] for c in q['choices']) for q in SKILLS_QUESTIONS)

    score_psycho   = round(sum(psycho_rep) / max_p * 100)
    score_skills   = round(sum(skills_rep) / max_s * 100)

    # Score profil basé sur l'activité sur la plateforme
    f_study   = min(user.study_hours / 50, 1.0)
    f_score   = min(user.score / 200, 1.0)
    f_res     = min(user.resources_count / 10, 1.0)
    score_profil = round(f_study * 40 + f_score * 40 + f_res * 20)

    total = round(score_psycho * 0.35 + score_skills * 0.40 + score_profil * 0.25)

    # Feedback IA
    feedback = []
    if score_psycho >= 75:
        feedback.append("Profil psychologique très adapté aux exigences du poste.")
    elif score_psycho >= 50:
        feedback.append("Profil psychologique satisfaisant avec des axes d'amélioration.")
    else:
        feedback.append("Profil psychologique à renforcer sur la gestion du stress et la proactivité.")

    if score_skills >= 75:
        feedback.append("Compétences techniques solides et alignées avec le poste.")
    elif score_skills >= 50:
        feedback.append("Compétences techniques adéquates — approfondissement recommandé.")
    else:
        feedback.append("Des lacunes techniques ont été identifiées — formation conseillée.")

    if score_profil >= 60:
        feedback.append("Engagement académique remarquable sur la plateforme ENCG Study.")
    else:
        feedback.append("Activité sur la plateforme à développer pour renforcer votre dossier.")

    return score_psycho, score_skills, score_profil, total, " ".join(feedback)


@premium_bp.route('/')
@login_required
def index():
    type_filter = request.args.get('type', '')
    query = Opportunity.query.filter_by(is_premium=True)
    if type_filter:
        query = query.filter_by(opp_type=type_filter)
    opps = query.order_by(Opportunity.created_at.desc()).all()
    applied_ids = {a.opportunity_id for a in current_user.applications}
    return render_template('premium/index.html',
        opportunities=opps, opp_types=OPP_TYPES,
        type_filter=type_filter, applied_ids=applied_ids)


@premium_bp.route('/<int:opp_id>/postuler', methods=['GET', 'POST'])
@login_required
def postuler(opp_id):
    opp = Opportunity.query.get_or_404(opp_id)
    existing = Application.query.filter_by(user_id=current_user.id, opportunity_id=opp_id).first()
    if existing:
        flash("Vous avez déjà postulé.", 'warning')
        return redirect(url_for('premium.resultat', app_id=existing.id))

    if request.method == 'POST':
        psycho_rep = [request.form.get(f'psycho_{i}', type=int, default=1) for i in range(len(PSYCHO_QUESTIONS))]
        skills_rep = [request.form.get(f'skills_{i}', type=int, default=1) for i in range(len(SKILLS_QUESTIONS))]

        sp, ss, spr, total, feedback = _calculer_score_ia(current_user, psycho_rep, skills_rep)

        app_obj = Application(
            user_id=current_user.id, opportunity_id=opp_id,
            psycho_score=sp, skills_score=ss, profile_score=spr,
            total_score=total, ai_feedback=feedback,
            status='selectionne' if total >= 60 else 'en_attente'
        )
        db.session.add(app_obj)
        db.session.commit()
        return redirect(url_for('premium.resultat', app_id=app_obj.id))

    return render_template('premium/postuler.html', opp=opp,
        psycho_questions=PSYCHO_QUESTIONS,
        skills_questions=SKILLS_QUESTIONS)


@premium_bp.route('/resultat/<int:app_id>')
@login_required
def resultat(app_id):
    app_obj = Application.query.get_or_404(app_id)
    if app_obj.user_id != current_user.id:
        flash("Accès non autorisé.", 'danger')
        return redirect(url_for('premium.index'))
    return render_template('premium/resultat.html', application=app_obj)


@premium_bp.route('/creer', methods=['GET', 'POST'])
@login_required
def creer():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        desc  = request.form.get('description', '').strip()
        if not title or not desc:
            flash('Le titre et la description sont obligatoires.', 'danger')
            return render_template('premium/creer.html', opp_types=OPP_TYPES)
        opp = Opportunity(
            title=title, description=desc,
            opp_type=request.form.get('opp_type', ''),
            company=request.form.get('company', '').strip(),
            location=request.form.get('location', '').strip(),
            deadline=request.form.get('deadline', '').strip(),
            contact=request.form.get('contact', '').strip(),
            poster_id=current_user.id, is_premium=True
        )
        db.session.add(opp)
        db.session.commit()
        flash('Offre premium publiée !', 'success')
        return redirect(url_for('premium.index'))
    return render_template('premium/creer.html', opp_types=OPP_TYPES)