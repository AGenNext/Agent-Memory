#!/usr/bin/env python3
"""
Component: Frontend UI

React + Vite template for SurrealDB app.
"""

# This would be the frontend/package.json
PACKAGE_JSON = {
    "name": "surrealdb-app",
    "private": True,
    "version": "1.0.0",
    "type": "module",
    "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview"
    },
    "dependencies": {
        "@surrealdb/sdk": "^3.0.0",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "@tanstack/react-query": "^5.0.0"
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.2.0",
        "vite": "^5.0.0"
    }
}

# vite.config.js
VITE_CONFIG = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000
  }
})
"""

# main.jsx
MAIN_JSX = """import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
)
"""

# App.jsx
APP_JSX = """import { useState, useEffect } from 'react'
import { Surreal } from '@surrealdb/sdk'

const db = new Surreal()

async function connect() {
  await db.connect('ws://localhost:8000/rpc')
  await db.use('memory:agent')
  await db.signin({ username: 'root', password: 'root' })
}

function App() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    connect().then(async () => {
      const result = await db.query('SELECT * FROM user')
      setUsers(result[0] || [])
      setLoading(false)
    })
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <h1>SurrealDB App</h1>
      <ul>
        {users.map(user => (
          <li key={user.id}>{user.name}</li>
        ))}
      </ul>
    </div>
  )
}

export default App
"""

# index.html
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SurrealDB App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/main.jsx"></script>
  </body>
</html>
"""

# Files dict
FILES = {
    "package.json": PACKAGE_JSON,
    "vite.config.js": VITE_CONFIG,
    "src/main.jsx": MAIN_JSX,
    "src/App.jsx": APP_JSX,
    "index.html": INDEX_HTML,
}


def create_app(output_dir: str = "frontend"):
    """Create frontend app files."""
    import json
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/src", exist_ok=True)
    
    # Write package.json
    with open(f"{output_dir}/package.json", "w") as f:
        json.dump(PACKAGE_JSON, f, indent=2)
    
    # Write other files
    for filename, content in FILES.items():
        path = f"{output_dir}/{filename}"
        with open(path, "w") as f:
            f.write(content)
    
    print(f"✅ Created frontend in {output_dir}/")


if __name__ == "__main__":
    create_app()