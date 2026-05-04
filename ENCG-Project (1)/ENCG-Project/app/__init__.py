from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading')

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # Blueprints existants
    from app.auth         import auth_bp
    from app.main         import main_bp
    from app.rooms        import rooms_bp
    from app.resources    import resources_bp
    from app.opportunities import opportunities_bp

    # Nouveaux blueprints
    from app.profile      import profile_bp
    from app.leaderboard  import leaderboard_bp
    from app.premium      import premium_bp
    from app.admin        import admin_bp
    from app.avis         import avis_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(premium_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(avis_bp)

    # Filtre Jinja2 pour enumerate (nécessaire dans les templates)
    app.jinja_env.globals['enumerate'] = enumerate

    with app.app_context():
        db.create_all()

    return app