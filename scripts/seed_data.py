"""Creates 3 autónomo test profiles with invoices, per docs/development_guide.md.
Reuses tests/fixtures/facturas.py as the single source of truth for the actual
invoice data — this script only supplies real Supabase Auth user ids (required
by the FK to auth.users) and performs the insert with the service role key.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

import tests.fixtures.facturas as fixtures

TEST_PASSWORD = "seed-data-password-123!"


def get_or_create_user(admin_client, email: str) -> str:
    existing = admin_client.auth.admin.list_users()
    for user in existing:
        if user.email == email:
            return user.id
    created = admin_client.auth.admin.create_user(
        {"email": email, "password": TEST_PASSWORD, "email_confirm": True}
    )
    return created.user.id


def main():
    url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    admin_client = create_client(url, service_key)

    fixtures.PROFILE_1_USER_ID = get_or_create_user(admin_client, "perfil1-solo-servicios@test.autonomos.local")
    fixtures.PROFILE_2_USER_ID = get_or_create_user(admin_client, "perfil2-mixto@test.autonomos.local")
    fixtures.PROFILE_3_USER_ID = get_or_create_user(admin_client, "perfil3-isp@test.autonomos.local")

    emitidas = fixtures.todas_las_facturas_emitidas()
    recibidas = fixtures.todas_las_facturas_recibidas()

    for factura in emitidas:
        row = factura.model_dump(mode="json")
        admin_client.table("factura_emitida").upsert(row).execute()

    for factura in recibidas:
        row = factura.model_dump(mode="json")
        admin_client.table("factura_recibida").upsert(row).execute()

    print(f"Seeded {len(emitidas)} facturas_emitidas, {len(recibidas)} facturas_recibidas")
    print(f"Perfil 1 (solo servicios): user_id={fixtures.PROFILE_1_USER_ID}")
    print(f"Perfil 2 (mixto con gastos): user_id={fixtures.PROFILE_2_USER_ID}")
    print(f"Perfil 3 (con ISP): user_id={fixtures.PROFILE_3_USER_ID}")


if __name__ == "__main__":
    main()
