# seed.py
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from database import db
from accounts.models import User

def seed_users():
    load_dotenv(dotenv_path=".env.db")  # or ".env.dev.db" or ".env.prod.db"

    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")

    user1_email = os.getenv("DEFAULT_USER1_EMAIL")
    user1_password = os.getenv("DEFAULT_USER1_PASSWORD")
    
    user2_email = os.getenv("DEFAULT_USER2_EMAIL")
    user2_password = os.getenv("DEFAULT_USER2_PASSWORD")

    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name="admin",
            email=admin_email,
            role="admin",
            password_hash=generate_password_hash(admin_password)
        )
        db.session.add(admin)

    if not User.query.filter_by(email=user1_email).first():
        user1 = User(
            name="claudia",
            email=user1_email,
            role="teacher",
            password_hash=generate_password_hash(user1_password)
        )
        db.session.add(user1)

    if not User.query.filter_by(email=user2_email).first():
        user2 = User(
            name="christine",
            email=user2_email,
            role="teacher",
            password_hash=generate_password_hash(user2_password)
        )
        db.session.add(user2)

    db.session.commit()
    print("✅ Default users created or already existed.")
