"""Shared execution and error handling for Supabase RPC repositories."""

import asyncio
from collections.abc import Mapping

import httpx
from postgrest.exceptions import APIError
from supabase import Client


class DatabaseRepositoryError(RuntimeError):
    """Raised when a database repository cannot complete an operation."""


class SupabaseRpcRepository:
    """Base adapter for synchronous Supabase RPC calls used by async workflows."""

    def __init__(self, client: Client) -> None:
        self._client = client

    async def call_rpc(self, function_name: str, parameters: Mapping[str, object]) -> object:
        """Execute one RPC without blocking the application event loop."""
        try:
            response = await asyncio.to_thread(lambda: self._client.rpc(function_name, dict(parameters)).execute())
        except (APIError, httpx.HTTPError) as error:
            raise DatabaseRepositoryError(f"Supabase RPC '{function_name}' failed") from error
        return response.data
