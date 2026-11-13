import json
from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.auth import User, UserRole
from app.schemas.auth import UserRegister
from app.services.role_assignments import get_role_id, grant_role


def _create_supabase_user(admin_input: UserRegister) -> UUID:
    if not settings.supabase_url:
        raise SystemExit("Set SUPABASE_URL before creating the admin.")
    secret_key = settings.supabase_secret_key or settings.supabase_service_role_key
    if secret_key is None:
        raise SystemExit("Set SUPABASE_SECRET_KEY in the backend environment.")

    api_key = secret_key.get_secret_value()
    request = Request(
        f"{settings.supabase_url}/auth/v1/admin/users",
        data=json.dumps(
            {
                "email": str(admin_input.email),
                "password": admin_input.password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": admin_input.full_name,
                    "phone_number": admin_input.phone_number,
                },
            }
        ).encode("utf-8"),
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except HTTPError as exc:
        raise SystemExit(
            f"Supabase Auth could not create the admin user (HTTP {exc.code}). "
            "Check whether this email already exists in Supabase Auth."
        ) from exc
    except URLError as exc:
        raise SystemExit("Could not reach Supabase Auth to create the admin user.") from exc

    if not isinstance(payload, dict):
        raise SystemExit("Supabase Auth returned an unexpected response while creating the admin.")
    auth_user_id = payload.get("id")
    if not isinstance(auth_user_id, str):
        raise SystemExit("Supabase Auth created no usable user ID; inspect the Auth dashboard.")
    try:
        return UUID(auth_user_id)
    except ValueError as exc:
        raise SystemExit("Supabase Auth returned an invalid user ID.") from exc


def main() -> None:
    full_name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    phone_number = input("Admin phone number (10 digits): ").strip()
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
        existing_admin = next((user.id for user in db.scalars(select(User)).all()
                               if UserRole.ADMIN.value in user.roles), None)
        if existing_admin is not None:
            raise SystemExit("An admin already exists; bootstrap creation is disabled.")
        if db.scalar(select(User.id).where(User.email == str(admin_input.email))) is not None:
            raise SystemExit("An app account already uses that email address.")

        auth_user_id = _create_supabase_user(admin_input)
        admin = User(
            auth_user_id=auth_user_id,
            full_name=admin_input.full_name,
            email=str(admin_input.email),
            phone_number=admin_input.phone_number,
            role_id=get_role_id(db, UserRole.ADMIN),
            is_active=True,
            is_email_verified=True,
        )
        db.add(admin)
        try:
            db.flush()
            grant_role(db, admin, UserRole.BUYER)
            grant_role(db, admin, UserRole.ADMIN)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise SystemExit(
                "Supabase Auth created the admin identity, but the app profile could not be saved. "
                "Keep that Auth user and resolve the database conflict before retrying."
            ) from exc
    print(f"Admin account created for {admin_input.email}.")


if __name__ == "__main__":
    main()
