from flask import Blueprint
premium_bp = Blueprint('premium', __name__, url_prefix='/premium')
from app.premium import routes