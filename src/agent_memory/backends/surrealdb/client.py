from typing import Any

from surrealdb import AsyncSurreal


class SurrealMemoryClient:
    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        username: str,
        password: str,
    ):
        self.client = AsyncSurreal(url)
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password

    async def connect(self):
        await self.client.connect()

        await self.client.signin(
            {
                "username": self.username,
                "password": self.password,
            }
        )

        await self.client.use(self.namespace, self.database)

    async def close(self):
        await self.client.close()

    async def create_memory(self, memory_type: str, payload: dict[str, Any]):
        return await self.client.create(memory_type, payload)

    async def get_memory(self, record_id: str):
        return await self.client.select(record_id)

    async def query(self, sql: str, variables: dict[str, Any] | None = None):
        return await self.client.query(sql, variables or {})
