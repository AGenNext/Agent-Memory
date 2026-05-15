"""
Agent Memory - WASM/Browser Edition

Run Agent Memory directly in the browser using SurrealDB WASM engine.
Supports in-memory and IndexedDB persistence.
"""

import type { Surreal } from '@surrealdb/sdk'
import type { Engine, Connection } from '@surrealdb/sdk'


# -- Types --

interface BrowserConfig {
  /** Use IndexedDB for persistence */
  persistent?: boolean
  /** Database name */
  database?: string
  /** Namespace */
  namespace?: string
}


interface InMemoryConfig {
  /** In-memory mode (no persistence) */
  memory?: boolean
  /** Database name */
  database?: string
  /** Namespace */
  namespace?: string
}


# -- Browser Memory --

class BrowserMemory {
  """
  Agent Memory running in browser using WASM.
  
  Works in:
  - Browser (Chrome, Firefox, Safari, Edge)
  - Web Worker
  - Node.js (with WASM)
  
  Supports:
  - In-memory storage
  - IndexedDB persistence
  """
  
  db: Surreal | null = null
  connected = false
  
  async connect(config: BrowserConfig = {}): Promise<void> {
    // Dynamic import to avoid issues with SSR
    const { Surreal } = await import('@surrealdb/wasm')
    
    this.db = new Surreal()
    
    if (config.persistent) {
      // IndexedDB persistence
      await this.db.connect('indexeddb://' + (config.database || 'agent-memory'))
    } else {
      // In-memory only
      await this.db.connect('mem://' + (config.database || 'agent-memory'))
    }
    
    await this.db.use({
      namespace: config.namespace || 'memory',
      database: config.database || 'agent',
    })
    
    await this.db.signin({
      username: 'root',
      password: 'root',
    })
    
    this.connected = true
  }
  
  async disconnect(): Promise<void> {
    if (this.db && this.connected) {
      await this.db.close()
      this.connected = false
    }
  }
  
  // -- Core Operations --
  
  async createSession(userId?: string): Promise<string> {
    const result = await this.db!.create('session:' + crypto.randomUUID(), {
      user_id: userId,
      status: 'active',
      created: new Date().toISOString(),
    })
    return result.id as string
  }
  
  async addEntity(
    sessionId: string,
    entityType: string,
    name: string,
    properties?: Record<string, unknown>,
  ): Promise<string> {
    const id = 'entity:' + crypto.randomUUID()
    const result = await this.db!.create(id, {
      session: sessionId,
      type: entityType,
      name,
      properties: properties || {},
      created: new Date().toISOString(),
    })
    return result.id as string
  }
  
  async traceDecision(
    sessionId: string,
    action: string,
    tool?: string,
    result?: string,
  ): Promise<void> {
    await this.db!.create('decision:' + crypto.randomUUID(), {
      session: sessionId,
      action,
      tool,
      result_summary: result,
      created: new Date().toISOString(),
    })
  }
  
  // -- Query --
  
  async query<T>(sql: string, vars?: Record<string, unknown>): Promise<T[]> {
    const result = await this.db!.query(sql, vars || {})
    return result as T[]
  }
  
  // -- Sessions --
  
  async getSessions(userId?: string): Promise<unknown[]> {
    const where = userId ? 'WHERE user_id = $userId' : ''
    return this.query('SELECT * FROM session ' + where + ' ORDER BY created DESC', { userId })
  }
  
  async getEntities(sessionId: string): Promise<unknown[]> {
    return this.query(
      'SELECT * FROM entity WHERE session = $session',
      { session: sessionId }
    )
  }
  
  async getDecisions(sessionId: string): Promise<unknown[]> {
    return this.query(
      'SELECT * FROM decision WHERE session = $session ORDER BY created ASC',
      { session: sessionId }
    )
  }
}


# -- Example Usage --

/*
// index.html
<!DOCTYPE html>
<html>
<head>
  <title>Agent Memory - Browser</title>
  <script type="importmap">
  {
    "imports": {
      "@surrealdb/wasm": "https://esm.surreal.team/wasm@3.0.5",
      "@surrealdb/sdk": "https://esm.surreal.team/sdk@3.0.5"
    }
  }
  </script>
</head>
<body>
  <h1>Agent Memory - Browser Edition</h1>
  <div id="app">
    <button id="connect">Connect (IndexedDB)</button>
    <button id="connect-mem">Connect (In-Memory)</button>
    <button id="new-session">New Session</button>
    <button id="add-entity">Add Entity</button>
    <pre id="output"></pre>
  </div>
  <script type="module">
    import { BrowserMemory } from './browser-memory.mjs';
    
    const memory = new BrowserMemory();
    const output = document.getElementById('output');
    
    function log(msg) {
      output.textContent = JSON.stringify(msg, null, 2);
    }
    
    document.getElementById('connect').onclick = async () => {
      await memory.connect({ persistent: true });
      log('Connected with IndexedDB!');
    };
    
    document.getElementById('connect-mem').onclick = async () => {
      await memory.connect({ persistent: false });
      log('Connected in-memory!');
    };
    
    document.getElementById('new-session').onclick = async () => {
      const id = await memory.createSession('user:1');
      log({ session: id });
    };
    
    document.getElementById('add-entity').onclick = async () => {
      const sessions = await memory.getSessions();
      if (sessions.length === 0) {
        log({ error: 'No sessions. Create one first.' });
        return;
      }
      const session = sessions[0].id;
      await memory.addEntity(session, 'person', 'Alice', { email: 'alice@test.com' });
      log({ entity: 'added' });
    };
  </script>
</body>
</html>
*/


# -- Export --

export { BrowserMemory, type BrowserConfig, type InMemoryConfig }