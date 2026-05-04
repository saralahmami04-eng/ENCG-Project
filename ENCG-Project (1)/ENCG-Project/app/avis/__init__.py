from flask import Blueprint
avis_bp = Blueprint('avis', __name__, url_prefix='/avis')
from app.avis import routes