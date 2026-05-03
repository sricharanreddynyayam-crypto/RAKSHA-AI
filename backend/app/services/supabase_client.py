import os

from typing import Any

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None
    Client = Any

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def get_supabase_client() -> Client | None:
    if not SUPABASE_URL or not SUPABASE_KEY or create_client is None:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_location_point(client: Client, payload: dict) -> Any:
    return client.table("location_points").insert(payload).execute()


def upsert_user_profile(client: Client, payload: dict) -> Any:
    return client.table("users").insert(payload, upsert=True).execute()


def upsert_tracking_session(client: Client, payload: dict) -> Any:
    return client.table("tracking_sessions").insert(payload, upsert=True).execute()
