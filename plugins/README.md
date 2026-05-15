# SurrealDB Plugins

Extensible plugins for SurrealDB based on docs and solutions.

## Available Plugins

| Plugin | File | Description |
|--------|------|-------------|
| **Airbyte** | `plugins/airbyte.py` | ETL data pipelines |
| **n8n** | `plugins/n8n.py` | Workflow automation |
| **Embeddings** | `plugins/embeddings.py` | Vector embeddings |
| **Real-Time** | `plugins/realtime.py` | Live queries |
| **Data Quality** | `plugins/data_quality.py` | Quality assurance |
| **Reactive** | `plugins/reactive.py` | Events & triggers |

## Install All Plugins

```python
# Import individual plugin
from plugins.airbyte import AirbytePlugin
from plugins.n8n import N8nPlugin
from plugins.embeddings import EmbeddingsPlugin
from plugins.realtime import RealTimePlugin
from plugins.data_quality import DataQualityPlugin
from plugins.reactive import ReactivePlugin
```

## Usage

### Airbyte ETL
```python
plugin = AirbytePlugin()
await plugin.install()
await plugin.register_stream("users", "updated_at")
await plugin.sync_stream("users", "SELECT * FROM users")
```

### n8n Workflow
```python
plugin = N8nPlugin()
await plugin.install()
workflow = await plugin.create_workflow("name", nodes=[], connections=[])
await plugin.execute(workflow["id"], {})
```

### Embeddings
```python
plugin = EmbeddingsPlugin(provider="openai")
await plugin.install()
emb = await plugin.get_embedding("Hello world")
result = await plugin.vector_search("query", "document")
```

### Real-Time Live Queries
```python
plugin = RealTimePlugin()
await plugin.install()
await plugin.subscribe_table("chat", callback=handle_change)
await plugin.create_audit_log("user")
```

### Data Quality
```python
plugin = DataQualityPlugin()
await plugin.install()
await plugin.create_rule("email_not_null", "not_null", {"field": "email"})
result = await plugin.check_uniqueness("user", "email")
```

### Reactive Events
```python
plugin = ReactivePlugin()
await plugin.install()
await plugin.create_audit_trail("order")
await plugin.on_field_change("user", "status", "...")
await plugin.compute_field("order", "total_with_tax", "this.total * 1.1")
```

## Combine Plugins

```python
# Full stack with multiple plugins
from plugins.embeddings import EmbeddingsPlugin
from plugins.realtime import RealTimePlugin
from plugins.reactive import ReactivePlugin

# Setup
embed = EmbeddingsPlugin()
await embed.install()

realtime = RealTimePlugin()
await realtime.install()

reactive = ReactivePlugin()
await reactive.install()
```

## Resources

- [SurrealDB Integrations](https://surrealdb.com/docs/build/integrations/overview)
- [Data Management](https://surrealdb.com/docs/build/integrations/data-management/overview)
- [Real-Time](https://surrealdb.com/use-cases/real-time)