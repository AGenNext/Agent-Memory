#!/usr/bin/env python3
"""
Plugin: Data Quality (Qyrus-style)

Data quality assurance plugin.
Based on: https://surrealdb.com/docs/build/integrations/data-management/qyrus
"""

import asyncio
from surrealdb import Surreal


class DataQualityPlugin:
    """Data quality assurance plugin."""
    
    PLUGIN_NAME = "data_quality"
    PLUGIN_VERSION = "1.0.0"
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def install(self):
        """Install plugin."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "quality", "database": "assurance"})
        await self.db.signin({"username": "root", "password": "root"})
        
        print(f"✅ Data quality plugin installed")
        return self
    
    # ----- Rules -----
    
    async def create_rule(self, name: str, rule_type: str, config: dict):
        """Create data quality rule."""
        result = await self.db.query(
            "CREATE quality_rule SET name=$name, type=$type, config=$config",
            {"name": name, "type": rule_type, "config": config}
        )
        return result[0][0]
    
    async def validate(self, table: str, rule_id: str) -> dict:
        """Validate data against rule."""
        rule = await self.db.query(
            "SELECT * FROM quality_rule WHERE id = $id",
            {"id": rule_id}
        )
        
        if not rule or not rule[0]:
            return {"error": "Rule not found"}
        
        config = rule[0][0].get("config", {})
        rule_type = rule[0][0].get("type")
        
        # Execute validation
        if rule_type == "not_null":
            result = await self.db.query(
                f"SELECT count() AS count FROM {table} WHERE {config['field']} IS NONE"
            )
        elif rule_type == "unique":
            result = await self.db.query(
                f"SELECT {config['field']}, count() AS c FROM {table} GROUP BY {config['field']} HAVING c > 1"
            )
        elif rule_type == "range":
            result = await self.db.query(
                f"""SELECT * FROM {table} WHERE {config['field']} < $min 
                OR {config['field']} > $max""",
                {"min": config.get("min"), "max": config.get("max")}
            )
        else:
            result = [[]]
        
        issues = result[0] if result else []
        
        return {
            "rule": name,
            "table": table,
            "issues": issues,
            "passed": len(issues) == 0
        }
    
    # ----- Checks -----
    
    async def check_uniqueness(self, table: str, field: str) -> dict:
        """Check field uniqueness."""
        result = await self.db.query(
            f"SELECT {field}, count() AS c FROM {table} GROUP BY {field} HAVING c > 1"
        )
        duplicates = result[0] if result else []
        
        return {
            "check": "uniqueness",
            "field": field,
            "unique": len(duplicates) == 0,
            "duplicates": len(duplicates)
        }
    
    async def check_completeness(self, table: str, fields: list) -> dict:
        """Check field completeness."""
        results = {}
        
        for field in fields:
            result = await self.db.query(
                f"SELECT count() AS total, count({field}) AS filled FROM {table}"
            )
            
            if result and result[0]:
                results[field] = {
                    "total": result[0][0].get("total", 0),
                    "filled": result[0][0].get("filled", 0),
                    "complete": result[0][0].get("filled", 0) == result[0][0].get("total", 0)
                }
        
        return results


async def demo():
    """Demo."""
    plugin = DataQualityPlugin()
    await plugin.install()
    
    # Create rule
    rule = await plugin.create_rule("email_not_null", "not_null", {"field": "email"})
    print(f"Rule: {rule['name']}")
    
    # Check uniqueness
    result = await plugin.check_uniqueness("user", "email")
    print(f"Uniqueness: {result}")


if __name__ == "__main__":
    asyncio.run(demo())