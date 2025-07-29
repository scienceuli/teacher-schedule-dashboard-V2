from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env
load_dotenv()

# Get credentials from env
username = os.getenv("ADMIN_USERNAME")
password = os.getenv("ADMIN_PASSWORD")

with open('users.json') as f:
    users = json.load(f)



# Connect to Mongo (adjust host if running in Docker)
client = MongoClient("mongodb://localhost:27017/")
db = client.teacherapp

for user in users:
    existing = db.users.find_one({'username': user['username']})
    if existing:
        print(f"User '{user['username']}' already exists.")
    else:
        hashed_pw = generate_password_hash(user['password'])
        db.users.insert_one({
            'username': user['username'],
            'password': hashed_pw,
            'role': user.get('role', 'user')
        })
        print(f"User '{user['username']}' created.")




