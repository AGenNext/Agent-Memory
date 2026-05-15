#!/usr/bin/env python3
"""
SurrealDB HTTP REST Tools - Postman Collection

Based on: https://www.postman.com/surrealdb/surrealdb/collection

HTTP Endpoints for SurrealDB REST API.
"""

import asyncio
import httpx
from typing import Any, Optional


class SurrealDBRestAPI:
    """
    SurrealDB REST API client.
    
    Usage:
        db = SurrealDBRestAPI("http://localhost:8000")
        await db.signin("root", "root")
        users = await db.select("user")
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
    
    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    # Health & Info
    async def health(self) -> dict:
        """GET /health - Check database health."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/health", headers=self._headers())
            return r.json()
    
    async def version(self) -> dict:
        """GET /version - Get database version."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/version", headers=self._headers())
            return r.json()
    
    # Auth
    async def signin(self, username: str, password: str, namespace: str = None, database: str = None) -> dict:
        """POST /signin - Sign in to database."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/signin",
                headers=self._headers(),
                json={
                    "username": username,
                    "password": password,
                    "namespace": namespace or "memory",
                    "database": database or "agent",
                }
            )
            data = r.json()
            if "token" in data:
                self.token = data["token"]
            return data
    
    # Select
    async def select(self, table: str) -> list:
        """GET /key/:table - Select all records."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/key/{table}", headers=self._headers())
            return r.json()
    
    async def select_one(self, table: str, record_id: str) -> dict:
        """GET /key/:table/:id - Select single record."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/key/{table}/{record_id}", headers=self._headers())
            return r.json()
    
    # Create
    async def create(self, table: str, data: dict) -> dict:
        """POST /key/:table - Create new record."""
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/key/{table}", headers=self._headers(), json=data)
            return r.json()
    
    async def create_one(self, table: str, record_id: str, data: dict) -> dict:
        """POST /key/:table/:id - Create record with ID."""
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/key/{table}/{record_id}", headers=self._headers(), json=data)
            return r.json()
    
    # Update
    async def update(self, table: str, data: dict) -> list:
        """PUT /key/:table - Update all records."""
        async with httpx.AsyncClient() as client:
            r = await client.put(f"{self.base_url}/key/{table}", headers=self._headers(), json=data)
            return r.json()
    
    async def update_one(self, table: str, record_id: str, data: dict) -> dict:
        """PUT /key/:table/:id - Update single record."""
        async with httpx.AsyncClient() as client:
            r = await client.put(f"{self.base_url}/key/{table}/{record_id}", headers=self._headers(), json=data)
            return r.json()
    
    async def merge(self, table: str, record_id: str, data: dict) -> dict:
        """PATCH /key/:table/:id - Merge update."""
        async with httpx.AsyncClient() as client:
            r = await client.patch(f"{self.base_url}/key/{table}/{record_id}", headers=self._headers(), json=data)
            return r.json()
    
    # Delete
    async def delete_all(self, table: str) -> list:
        """DELETE /key/:table - Delete all records."""
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self.base_url}/key/{table}", headers=self._headers())
            return r.json()
    
    async def delete_one(self, table: str, record_id: str) -> dict:
        """DELETE /key/:table/:id - Delete single record."""
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self.base_url}/key/{table}/{record_id}", headers=self._headers())
            return r.json()
    
    # Query
    async def query(self, sql: str, vars: dict = None) -> list:
        """POST /sql - Run SurrealQL query."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/sql",
                headers=self._headers(),
                json={"query": sql, "vars": vars or {}}
            )
            return r.json()
    
    # Import/Export
    async def export(self) -> dict:
        """GET /export - Export database."""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/export", headers=self._headers())
            return r.json()
    
    async def import_data(self, data: dict) -> dict:
        """POST /import - Import data."""
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/import", headers=self._headers(), json=data)
            return r.json()


# Example
if __name__ == "__main__":
    async def demo():
        db = SurrealDBRestAPI("http://localhost:8000")
        await db.signin("root", "root")
        
        # CRUD
        await db.create("user", {"name": "Alice"})
        users = await db.select("user")
        print(users)
        
        # Query
        result = await db.query("SELECT * FROM user")
        print(result)
        
        # Health
        print(await db.health())
    
    asyncio.run(demo())