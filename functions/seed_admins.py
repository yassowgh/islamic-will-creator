"""Seed one Super Admin and one Reporting user.
Credentials come from env vars - NEVER commit them:
  SEED_SUPER_ADMIN_EMAIL / SEED_SUPER_ADMIN_PASSWORD
  SEED_REPORTING_EMAIL / SEED_REPORTING_PASSWORD
Run: GOOGLE_APPLICATION_CREDENTIALS=sa.json python seed_admins.py
"""
import os
import sys

import firebase_admin
from firebase_admin import auth, firestore

firebase_admin.initialize_app()
db = firestore.client()

ROLES = [("SUPER_ADMIN", "super_admin"), ("REPORTING", "reporting")]
for env_prefix, role in ROLES:
    email = os.environ.get(f"SEED_{env_prefix}_EMAIL")
    password = os.environ.get(f"SEED_{env_prefix}_PASSWORD")
    if not email or not password:
        sys.exit(f"Missing SEED_{env_prefix}_EMAIL / _PASSWORD env vars")
    try:
        user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        user = auth.create_user(email=email, password=password)
    auth.set_custom_user_claims(user.uid, {"role": role})
    db.collection("admins").document(user.uid).set(
        {"role": role, "active": True, "createdBy": "seed"})
    db.collection("auditLog").add(
        {"actorUid": "seed", "action": f"create_{role}",
         "targetRef": f"admins/{user.uid}",
         "at": firestore.SERVER_TIMESTAMP})
    print(f"Seeded {role}: {email}")
