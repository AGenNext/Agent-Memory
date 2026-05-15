# Agent Skills for SurrealDB

Based on: https://surrealdb.com/docs/build/ai-agents/agent-skills

## Installation

### Using Skills CLI

```bash
# Install all skills
npx skills add surrealdb/agent-skills

# Install specific skill
npx skills add surrealdb/agent-skills --skill surrealql
npx skills add surrealdb/agent-skills --skill surrealdb-vector
npx skills add surrealdb/agent-skills --skill surrealdb-python
```

### Manual Setup

```bash
# Clone skills
git clone https://github.com/surrealdb/agent-skills.git

# Copy to your agent's context directory
# - Claude Code: ~/.claude/skills/
# - Cursor: .cursor/rules/
# - GitHub Copilot: Use agent rules
```

---

## Available Skills

| Skill | What it covers |
|-------|---------------|
| **surrealql** | SurrealQL query language, schema, graph traversals |
| **surrealdb-vector** | Vector search, HNSW indexes, KNN queries |
| **surrealdb-python** | Python SDK in client/server and embedded mode |

---

## Usage in AI Tools

### Cursor / Windsurf

```
@https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/skills/query.md

Write a query to find users who bought product X
```

### Claude Code

```
Use the SurrealQL skill to write a schema for a blog
```

### GitHub Copilot

```
# Using agent-rules from surrealdb/agent-rules
Write a vector search query
```

---

## Skill Files

- `skills/query.md` - SurrealQL queries
- `skills/data-models.md` - Multi-model data
- `skills/admin.md` - Administration
- `skills/vector-search.md` - Vector/RAG

---

## Learn More

- [SurrealDB Agent Skills](https://github.com/surrealdb/agent-skills)
- [Agent Rules](https://surrealdb.com/docs/build/ai-agents/agent-rules)
- [AI Frameworks](https://surrealdb.com/docs/build/ai-agents/ai-frameworks)