from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.auth import User, UserRole
from app.schemas.auth import UserRegister


def main() -> None:
    full_name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    phone_number = input("Admin phone number (+ and digits only): ").strip()
    password = getpass("Admin password (8–128 characters, including a letter, a number, and a special character): ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    try:
        admin_input = UserRegister(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            password=password,
        )
    except ValueError as exc:
        raise SystemExit(f"Invalid admin details: {exc}") from exc

    with SessionLocal() as db:
        existing_admin = db.scalar(
            select(User.id).where(User.role == UserRole.ADMIN).limit(1)
        )
        if existing_admin is not None:
            raise SystemExit("An admin already exists; bootstrap creation is disabled.")
        if db.scalar(select(User.id).where(User.email == str(admin_input.email))) is not None:
            raise SystemExit("An account already uses that email address.")

        admin = User(
            full_name=admin_input.full_name,
            email=str(admin_input.email),
            phone_number=admin_input.phone_number,
            password_hash=hash_password(admin_input.password),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit("The account could not be created; verify the database and email.") from exc
    print(f"Admin account created for {admin_input.email}.")


if __name__ == "__main__":
    main()
