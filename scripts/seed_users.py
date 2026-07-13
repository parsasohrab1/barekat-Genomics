#!/usr/bin/env python3
"""ایجاد کاربران پیش‌فرض برای هر نقش RBAC."""

import sys
import uuid

from barekat_genomics.core.database import SessionLocal
from barekat_genomics.core.security import hash_password
from barekat_genomics.models.user import User

DEFAULT_USERS = [
    {
        "email": "clinician@barekat.local",
        "password": "clinician123",
        "full_name": "دکتر احمدی",
        "role": "clinician",
    },
    {
        "email": "geneticist@barekat.local",
        "password": "geneticist123",
        "full_name": "دکتر رضایی",
        "role": "geneticist",
    },
    {
        "email": "lab@barekat.local",
        "password": "labtech123",
        "full_name": "تکنسین کریمی",
        "role": "lab_tech",
    },
    {
        "email": "admin@barekat.local",
        "password": "admin123",
        "full_name": "مدیر سیستم",
        "role": "admin",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        created = 0
        for spec in DEFAULT_USERS:
            existing = db.query(User).filter(User.email == spec["email"]).first()
            if existing:
                print(f"skip: {spec['email']} (exists)")
                continue
            user = User(
                id=uuid.uuid4(),
                email=spec["email"],
                hashed_password=hash_password(spec["password"]),
                full_name=spec["full_name"],
                role=spec["role"],
                is_active=True,
            )
            db.add(user)
            created += 1
            print(f"created: {spec['email']} / {spec['password']} ({spec['role']})")
        db.commit()
        print(f"\nDone. {created} user(s) created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    sys.exit(0)
