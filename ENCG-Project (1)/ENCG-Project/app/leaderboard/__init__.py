from flask import Blueprint
leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/classement')
from app.leaderboard import routes