from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

ENCG_SCHOOLS = [
    'ENCG Agadir', 'ENCG Casablanca', 'ENCG El Jadida',
    'ENCG Fès', 'ENCG Kénitra', 'ENCG Béni Mellal',
    'ENCG Marrakech', 'ENCG Meknès', 'ENCG Oujda',
    'ENCG Settat', 'ENCG Tanger', 'ENCG Dakhla',
]


class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    school        = db.Column(db.String(100), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin      = db.Column(db.Boolean, default=False)   # ← NOUVEAU

    # Champs pour le score et le profil
    score               = db.Column(db.Integer, default=0)
    total_study_minutes = db.Column(db.Integer, default=0)
    bio                 = db.Column(db.String(300), default='')
    filiere             = db.Column(db.String(100), default='')

    # Relations
    resources      = db.relationship('Resource',     backref='uploader',  lazy=True)
    opportunities  = db.relationship('Opportunity',  backref='poster',    lazy=True)
    messages       = db.relationship('Message',      backref='author',    lazy=True)
    study_sessions = db.relationship('StudySession', backref='student',   lazy=True)
    votes_given    = db.relationship('ResourceVote', backref='voter',     lazy=True)
    applications   = db.relationship('Application',  backref='applicant', lazy=True)
    avis_donnes    = db.relationship('Avis',         backref='auteur',    lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def study_hours(self):
        return round(self.total_study_minutes / 60, 1)

    @property
    def rank_badge(self):
        if self.score >= 500: return ('🏆', 'Diamant')
        if self.score >= 200: return ('🥇', 'Or')
        if self.score >= 100: return ('🥈', 'Argent')
        if self.score >= 50:  return ('🥉', 'Bronze')
        return ('📚', 'Débutant')

    @property
    def resources_count(self):
        return len(self.resources)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
#  SALLES D'ÉTUDE
# ─────────────────────────────────────────────
class StudyRoom(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    mode        = db.Column(db.String(20), default='group')
    subject     = db.Column(db.String(100))
    school      = db.Column(db.String(100))
    creator_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    is_active   = db.Column(db.Boolean, default=True)

    creator  = db.relationship('User', foreign_keys=[creator_id])
    messages = db.relationship('Message', backref='room', lazy=True, cascade='all, delete-orphan')
    sessions = db.relationship('StudySession', backref='room', lazy=True)


class Message(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    content    = db.Column(db.Text, nullable=False)
    room_id    = db.Column(db.Integer, db.ForeignKey('study_room.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
#  SESSIONS D'ÉTUDE (pour l'analyse IA)
# ─────────────────────────────────────────────
class StudySession(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id          = db.Column(db.Integer, db.ForeignKey('study_room.id'), nullable=False)
    started_at       = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at         = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, default=0)


# ─────────────────────────────────────────────
#  RESSOURCES + VOTES
# ─────────────────────────────────────────────
class Resource(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.String(500))
    file_path      = db.Column(db.String(300), nullable=False)
    file_name      = db.Column(db.String(200), nullable=False)
    resource_type  = db.Column(db.String(50))
    subject        = db.Column(db.String(100))
    school         = db.Column(db.String(100))
    uploader_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)

    votes = db.relationship('ResourceVote', backref='resource', lazy=True, cascade='all, delete-orphan')

    @property
    def vote_score(self):
        return sum(v.value for v in self.votes)

    @property
    def upvotes(self):
        return sum(1 for v in self.votes if v.value == 1)

    @property
    def downvotes(self):
        return sum(1 for v in self.votes if v.value == -1)


class ResourceVote(db.Model):
    """Un vote par utilisateur par ressource. value = +1 ou -1"""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    value       = db.Column(db.Integer, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'resource_id', name='unique_vote'),)


# ─────────────────────────────────────────────
#  OPPORTUNITÉS
# ─────────────────────────────────────────────
class Opportunity(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    opp_type    = db.Column(db.String(50))
    company     = db.Column(db.String(150))
    location    = db.Column(db.String(100))
    deadline    = db.Column(db.String(50))
    contact     = db.Column(db.String(200))
    is_premium  = db.Column(db.Boolean, default=False)
    poster_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('Application', backref='opportunity', lazy=True)


# ─────────────────────────────────────────────
#  CANDIDATURES PREMIUM (pré-sélection IA)
# ─────────────────────────────────────────────
class Application(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunity.id'), nullable=False)
    status         = db.Column(db.String(30), default='pending')
    psycho_score   = db.Column(db.Integer, default=0)
    skills_score   = db.Column(db.Integer, default=0)
    profile_score  = db.Column(db.Integer, default=0)
    total_score    = db.Column(db.Integer, default=0)
    ai_feedback    = db.Column(db.Text, default='')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'opportunity_id', name='unique_application'),)


# ─────────────────────────────────────────────
#  AVIS DES ÉTUDIANTS
# ─────────────────────────────────────────────
class Avis(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    auteur_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contenu    = db.Column(db.Text, nullable=False)
    note       = db.Column(db.Integer, default=5)   # note de 1 à 5
    categorie  = db.Column(db.String(50), default='general')  # general | ressources | salles | premium
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public  = db.Column(db.Boolean, default=True)  # visible sur la page publique