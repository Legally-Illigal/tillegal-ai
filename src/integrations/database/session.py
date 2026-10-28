"""Supabase client construction."""

from supabase import Client, create_client

from src.core.config import SupabaseSettings


def create_supabase_client(settings: SupabaseSettings) -> Client:
    """Create a Supabase client from validated application settings."""
    api_key = settings.api_key
    if settings.url is None or api_key is None:
        raise ValueError("Supabase URL and an API key are required to create a client")

    return create_client(str(settings.url), api_key.get_secret_value())
