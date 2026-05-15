# Official SurrealDB Agent Skills

Reference: https://github.com/surrealdb/agent-skills

## Install All

```bash
npx skills add surrealdb/agent-skills
```

## Install Specific Skill

```bash
# SurrealQL query language
npx skills add surrealdb/agent-skills --skill surrealql

# Vector search
npx skills add surrealdb/agent-skills --skill surrealdb-vector

# Python SDK
npx skills add surrealdb/agent-skills --skill surrealdb-python
```

## Local Install

```bash
# Clone
git clone https://github.com/surrealdb/agent-skills.git

# Copy skills to your agent
cp -r agent-skills/skills ~/.claude/skills/
# or
cp -r agent-skills/skills .cursor/rules/
```

## Skills Structure

```
skills/
├── SKILL.md           # Manifest
├── references/         # Docs
└── prompts/           # Prompts
```

## Available Skills

| Skill | Description |
|-------|-------------|
| **surrealql** | Query language, schema, graph relationships |
| **surrealdb-vector** | HNSW indexes, KNN queries, similarity |
| **surrealdb-python** | Python SDK client/server & embedded |

## Usage Examples

```
Write a SurrealQL query to find all users who follow each other
Create an HNSW vector index for semantic search on my documents table
Connect to SurrealDB from my Python application
```

## Agent Compatibility

| Agent | Path |
|-------|------|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/rules/` |
| Cline | `.cline/rules/` |
| Windsurf | `.windsurf/rules/` |

## Add to This Project

These skills are also locally available in this repository:

- `skills/surrealql.md`
- `skills/python.md`  
- `skills/javascript.md`
- `skills/vector-search.md`

## Resources

- [GitHub](https://github.com/surrealdb/agent-skills)
- [Skills.sh](https://skills.sh)
- [Docs](https://surrealdb.com/docs/build/ai-agents/agent-skills)