from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.opportunities import opportunities_bp
from app.models import Opportunity

OPP_TYPES = ['Stage', 'Emploi', 'Concours', 'Bourse', 'Événement']


@opportunities_bp.route('/')
@login_required
def index():
    type_filter = request.args.get('type', '')
    search = request.args.get('search', '')

    query = Opportunity.query
    if type_filter:
        query = query.filter_by(opp_type=type_filter)
    if search:
        query = query.filter(Opportunity.title.ilike(f'%{search}%'))

    opportunities = query.order_by(Opportunity.created_at.desc()).all()
    return render_template('opportunities/index.html', opportunities=opportunities,
                           opp_types=OPP_TYPES, type_filter=type_filter, search=search)


@opportunities_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        opp_type = request.form.get('opp_type', '')
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        deadline = request.form.get('deadline', '').strip()
        contact = request.form.get('contact', '').strip()

        if not title or not description:
            flash('Le titre et la description sont obligatoires.', 'danger')
            return render_template('opportunities/create.html', opp_types=OPP_TYPES)

        opp = Opportunity(
            title=title, description=description, opp_type=opp_type,
            company=company, location=location, deadline=deadline,
            contact=contact, poster_id=current_user.id,
        )
        db.session.add(opp)
        db.session.commit()
        flash('Opportunité publiée avec succès !', 'success')
        return redirect(url_for('opportunities.index'))

    return render_template('opportunities/create.html', opp_types=OPP_TYPES)


@opportunities_bp.route('/<int:opp_id>')
@login_required
def detail(opp_id):
    opp = Opportunity.query.get_or_404(opp_id)
    return render_template('opportunities/detail.html', opp=opp)
