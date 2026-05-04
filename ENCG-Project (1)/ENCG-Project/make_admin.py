from app import create_app, db
from app.models import User

ADMINS = [
    "nissrinezahiri31@gmail.com",
    "tarafifatimazahra642@gmail.com",
    "douaat149@gmail.com",
    "saralahmami04@gmail.com",
]

app = create_app()

with app.app_context():
    print("=== Configuration des administrateurs ===\n")
    for email in ADMINS:
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"✅ {user.name} ({email}) → Administrateur")
        else:
            print(f"⚠️  Pas encore inscrit : {email}")
    print("\nTerminé ! Les admins verront le bouton 🛡️ Admin après reconnexion.")