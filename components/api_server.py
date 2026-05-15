#!/usr/bin/env python3
"""
Component: REST API Server

Complete HTTP REST API for SurrealDB.
"""

import asyncio
from aiohttp import web
from surrealdb import Surreal


class SurrealDBServer:
    """REST API server component for SurrealDB."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc", 
                 user: str = "root", password: str = "root",
                 namespace: str = "memory", database: str = "agent"):
        self.url = url
        self.user = user
        self.password = password
        self.ns = namespace
        self.db = database
        self.surrealdb = None
    
    async def start(self):
        """Start and connect to SurrealDB."""
        self.surrealdb = Surreal(self.url)
        await self.surrealdb.connect()
        await self.surrealdb.use({"namespace": self.ns, "database": self.db})
        await self.surrealdb.signin({"username": self.user, "password": self.password})
        print(f"✅ Connected to {self.url}")
        return self
    
    async def stop(self):
        """Stop and disconnect."""
        if self.surrealdb:
            await self.surrealdb.close()
    
    # ----- HTTP Handlers -----
    
    async def health(self, request: web.Request) -> web.Response:
        """GET /health"""
        return web.json_response({"status": "healthy"})
    
    async def version(self, request: web.Request) -> web.Response:
        """GET /version"""
        return web.json_response({"version": "3.0.0", "db": "SurrealDB"})
    
    async def signin(self, request: web.Request) -> web.Response:
        """POST /signin"""
        data = await request.json()
        result = await self.surrealdb.signin({
            "username": data.get("username"),
            "password": data.get("password"),
            "namespace": data.get("namespace", self.ns),
            "database": data.get("database", self.db),
        })
        return web.json_response(result)
    
    async def select(self, request: web.Request) -> web.Response:
        """GET /key/{table}"""
        table = request.match_info["table"]
        result = await self.surrealdb.query(f"SELECT * FROM {table}")
        return web.json_response(result[0] if result else [])
    
    async def select_one(self, request: web.Request) -> web.Response:
        """GET /key/{table}/{id}"""
        table = request.match_info["table"]
        record_id = request.match_info["id"]
        result = await self.surrealdb.query(f"SELECT * FROM {table}:{record_id}")
        return web.json_response(result[0][0] if result and result[0] else {})
    
    async def create(self, request: web.Request) -> web.Response:
        """POST /key/{table}"""
        table = request.match_info["table"]
        data = await request.json()
        result = await self.surrealdb.query(f"CREATE {table} SET $data", {"data": data})
        return web.json_response(result[0][0] if result and result[0] else {})
    
    async def update(self, request: web.Request) -> web.Response:
        """PUT /key/{table}/{id}"""
        table = request.match_info["table"]
        record_id = request.match_info["id"]
        data = await request.json()
        result = await self.surrealdb.query(f"UPDATE {table}:{record_id} SET $data", {"data": data})
        return web.json_response(result[0][0] if result and result[0] else {})
    
    async def delete(self, request: web.Request) -> web.Response:
        """DELETE /key/{table}/{id}"""
        table = request.match_info["table"]
        record_id = request.match_info["id"]
        await self.surrealdb.query(f"DELETE FROM {table}:{record_id}")
        return web.json_response({"deleted": True})
    
    async def sql(self, request: web.Request) -> web.Response:
        """POST /sql"""
        data = await request.json()
        result = await self.surrealdb.query(data.get("query", ""), data.get("vars", {}))
        return web.json_response(result[0] if result else [])
    
    async def export(self, request: web.Request) -> web.Response:
        """GET /export"""
        tables = ["user", "note", "document", "entity"]
        data = {}
        for table in tables:
            result = await self.surrealdb.query(f"SELECT * FROM {table}")
            data[table] = result[0] if result else []
        return web.json_response(data)
    
    # ----- App Factory -----
    
    def app(self) -> web.Application:
        """Create aiohttp application."""
        app = web.Application()
        
        # Routes
        app.router.add_get("/health", self.health)
        app.router.add_get("/version", self.version)
        app.router.add_post("/signin", self.signin)
        app.router.add_get("/key/{table}", self.select)
        app.router.add_get("/key/{table}/{id}", self.select_one)
        app.router.add_post("/key/{table}", self.create)
        app.router.add_put("/key/{table}/{id}", self.update)
        app.router.add_delete("/key/{table}/{id}", self.delete)
        app.router.add_post("/sql", self.sql)
        app.router.add_get("/export", self.export)
        
        return app


async def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the REST API server."""
    server = SurrealDBServer()
    await server.start()
    
    app = server.app()
    print(f"\n🚀 Server running at http://{host}:{port}")
    print("Endpoints:")
    print("  GET    /health")
    print("  GET    /version")
    print("  POST   /signin")
    print("  GET    /key/{table}")
    print("  GET    /key/{table}/{id}")
    print("  POST   /key/{table}")
    print("  PUT    /key/{table}/{id}")
    print("  DELETE /key/{table}/{id}")
    print("  POST   /sql")
    print("  GET    /export")
    
    await web._run_app(app, host=host, port=port)


if __name__ == "__main__":
    asyncio.run(run_server())