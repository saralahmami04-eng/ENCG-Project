from flask import render_template
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import StudyRoom, Resource, Opportunity


@main_bp.route('/')
@login_required
def home():
    rooms = StudyRoom.query.filter_by(is_active=True).order_by(StudyRoom.created_at.desc()).limit(6).all()
    resources = Resource.query.order_by(Resource.created_at.desc()).limit(6).all()
    opportunities = Opportunity.query.order_by(Opportunity.created_at.desc()).limit(6).all()
    return render_template('home.html', rooms=rooms, resources=resources, opportunities=opportunities)
