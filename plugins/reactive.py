#!/usr/bin/env python3
"""
Plugin: Reactive Events

Reactive workflows inside the database.
Based on: https://surrealdb.com/use-cases/real-time
"""

import asyncio
from surrealdb import Surreal


class ReactivePlugin:
    """Reactive event system plugin."""
    
    PLUGIN_NAME = "reactive"
    PLUGIN_VERSION = "1.0.0"
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def install(self):
        """Install plugin."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "reactive", "database": "events"})
        await self.db.signin({"username": "root", "password": "root"})
        
        # Event registry
        await self.db.query("""
            DEFINE TABLE _event_handler SCHEMAFULL;
            DEFINE FIELD name ON _event_handler TYPE string;
            DEFINE FIELD table ON _event_handler TYPE string;
            DEFINE FIELD event ON _event_handler TYPE string; -- create, update, delete
            DEFINE FIELD condition ON _event_handler TYPE string;
            DEFINE FIELD action ON _event_handler TYPE string;
            DEFINE FIELD enabled ON _event_handler TYPE bool DEFAULT true;
        """)
        
        print(f"✅ Reactive events plugin installed")
        return self
    
    # ----- Table Events -----
    
    async def on_create(self, table: str, action: str, name: str = None):
        """Fire on CREATE."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN CREATE THEN
                {action};
        """)
        print(f"✅ Created event: {name or 'on_create'} on {table}")
    
    async def on_update(self, table: str, action: str, name: str = None):
        """Fire on UPDATE."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN UPDATE THEN
                {action};
        """)
        print(f"✅ Updated event: {name or 'on_update'} on {table}")
    
    async def on_delete(self, table: str, action: str, name: str = None):
        """Fire on DELETE."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN DELETE THEN
                {action};
        """)
        print(f"✅ Deleted event: {name or 'on_delete'} on {table}")
    
    # ----- Field-Level Triggers -----
    
    async def on_field_change(self, table: str, field: str, action: str):
        """React to field changes."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN UPDATE THEN
                IF $before.{field} != $after.{field} THEN
                    {action};
                END;
        """)
        print(f"✅ Field trigger: {field} on {table}")
    
    async def compute_field(self, table: str, computed_field: str, compute_sql: str):
        """Compute derived field."""
        await self.db.query(f"""
            DEFINE FIELD {computed_field} ON {table} TYPE string
            VALUE {compute_sql};
        """)
        print(f"✅ Computed field: {computed_field}")
    
    # ----- Audit -----
    
    async def create_audit_trail(self, table: str):
        """Create audit trail."""
        audit_table = f"_{table}_audit"
        
        # Audit table
        await self.db.query(f"""
            DEFINE TABLE {audit_table} SCHEMAFULL;
            DEFINE FIELD record_id ON {audit_table} TYPE record({table});
            DEFINE FIELD operation ON {audit_table} TYPE string;
            DEFINE FIELD old_value ON {audit_table} TYPE object;
            DEFINE FIELD new_value ON {audit_table} TYPE object;
            DEFINE FIELD timestamp ON {audit_table} TYPE datetime DEFAULT time::now();
            DEFINE FIELD user ON {audit_table} TYPE string;
        """)
        
        # Audit triggers
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN CREATE THEN
                CREATE {audit_table} SET record_id = this.id, operation = 'create', 
                new_value = this, timestamp = time::now();
        """)
        
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN UPDATE THEN
                CREATE {audit_table} SET record_id = this.id, operation = 'update',
                old_value = $before, new_value = $after, timestamp = time::now();
        """)
        
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN DELETE THEN
                CREATE {audit_table} SET record_id = this.id, operation = 'delete',
                old_value = this, timestamp = time::now();
        """)
        
        print(f"✅ Audit trail: {table}")
    
    # ----- Notifications -----
    
    async def notify_on_change(self, table: str, channel: str, fields: list = None):
        """Create notification on change."""
        fields = fields or ["*"]
        
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN CREATE OR UPDATE THEN
                CREATE notification SET channel = '{channel}', data = this;
        """)
        
        await self.db.query("""
            DEFINE TABLE notification SCHEMAFULL;
            DEFINE FIELD channel ON notification TYPE string;
            DEFINE FIELD data ON notification TYPE object;
            DEFINE FIELD read ON notification TYPE bool DEFAULT false;
            DEFINE FIELD created ON notification TYPE datetime DEFAULT time::now();
        """)
        
        print(f"✅ Notification: {table} -> {channel}")
    
    # ----- Cascading -----
    
    async def cascade_on_create(self, source_table: str, target_table: str, mapping: dict):
        """Cascade create to related tables."""
        for target_field, source_field in mapping.items():
            await self.db.query(f"""
                DEFINE EVENT ON {source_table} WHEN CREATE THEN
                    CREATE {target_table} SET {target_field} = this.{source_field};
            """)
        
        print(f"✅ Cascade: {source_table} -> {target_table}")
    
    async def sync_on_update(self, table: str, field: str, sql: str):
        """Sync field on update."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN UPDATE THEN
                IF $before.{field} != $after.{field} THEN
                    {sql};
                END;
        """)
        print(f"✅ Sync: {table}.{field}")
    
    # ----- Collaborative -----
    
    async def conflict_resolution(self, table: str, field: str, strategy: str = "last_write"):
        """Set conflict resolution strategy."""
        if strategy == "last_write":
            await self.db.query(f"""
                DEFINE EVENT ON {table} WHEN UPDATE THEN
                    IF $before.{field} != $after.{field} THEN
                        -- Last write wins
                        SET this.{field} = $after.{field};
                    END;
            """)
        
        print(f"✅ Conflict resolution: {strategy} on {table}.{field}")


async def demo():
    """Demo."""
    plugin = ReactivePlugin()
    await plugin.install()
    
    # Audit trail
    await plugin.create_audit_trail("order")
    
    # Notification
    await plugin.notify_on_change("order", "new_orders", ["id", "total"])
    
    # Computed field
    await plugin.compute_field("order", "total_with_tax", "this.total * 1.1")


if __name__ == "__main__":
    asyncio.run(demo())