# Blink - SurrealDB WASM Note-Taking App

Based on: https://github.com/kearfy/blink

## What is Blink?

A **browser-based note-taking app** using SurrealDB WASM:
- Runs entirely in the browser (no backend!)
- Uses IndexedDB for persistence
- Real-time syncing with TanStack Query

## Tech Stack

| Tech | Use |
|------|-----|
| **React** | UI framework |
| **Mantine** | UI components |
| **SurrealDB WASM** | In-browser database |
| **IndexedDB** | Persistent storage |

## Quick Start

```bash
# Clone and run
git clone https://github.com/kearfy/blink.git
cd blink
bun install
bun dev

# Open http://localhost:5173
```

## Core Implementation

```python
# Using SurrealDB WASM in browser
from .js:
import { Surreal } from '@surrealdb/wasm'

# Connect to in-memory DB
const db = new Surreal()
await db.connect('mem://')

# Create note
await db.query("CREATE note SET title = 'My Note', content = 'Hello world'")

# Query
notes = await db.query("SELECT * FROM note")
```

## Schema

```sql
-- Notes table
DEFINE TABLE note SCHEMAFULL;
DEFINE FIELD title ON note TYPE string;
DEFINE FIELD content ON note TYPE string;
DEFINE FIELD created ON note TYPE datetime DEFAULT time::now();
DEFINE FIELD updated ON note TYPE datetime;
```

## Features

- Create/edit/delete notes
- Search notes
- Real-time updates
- Offline support (IndexedDB)

## Files

```
src/
├── components/     # UI components
├── queries/        # TanStack Query
├── schema/         # SurrealDB schema
└── utils/         # Helpers
```

## Web App

Live at: https://blink-surrealdb.netlify.app/