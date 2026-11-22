"""Supabase client construction."""

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from src.core.config import SupabaseSettings


def create_supabase_client(settings: SupabaseSettings, *, http_client: httpx.Client | None = None) -> Client:
    """Create a Supabase client from validated application settings."""
    api_key = settings.api_key
    if settings.url is None or api_key is None:
        raise ValueError("Supabase URL and an API key are required to create a client")

    if http_client is not None:
        return create_client(
            str(settings.url), api_key.get_secret_value(), options=SyncClientOptions(httpx_client=http_client),
        )
    return create_client(str(settings.url), api_key.get_secret_value())
