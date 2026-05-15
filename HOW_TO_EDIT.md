# How to Edit Blueprints in AI Tools

## In Cursor / Windsurf

### Method 1: @ Mention

1. Open Cursor or Windsurf
2. Type `@` then paste the URL:

```
@https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py
```

3. Then ask to modify:

```
Create a FAQ bot that answers questions about SurrealDB
```

### Method 2: Paste URL in Chat

```
Here's an agent template: https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py

Can you modify it to add session tracking?
```

---

## In Claude Code / Continue

### Method 1: Inline Import

```python
# In your code file, paste:
# from https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py

# Then ask AI:
# "Create a class that extends this template for a FAQ bot"
```

### Method 2: URL in Prompt

```
Using this template: https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/tool_agent.py

Add a new tool for sending emails
```

---

## In VS Code (Manual)

### 1. Download

```bash
# Clone repo
git clone https://github.com/AGenNext/Agent-Memory.git

# Or just download one file
curl -O https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py
```

### 2. Edit

```bash
# Open in VS Code
code agent_template.py
```

### 3. Modify

Override the methods:

```python
class FAQAgent(AgentTemplate):
    async def setup(self):
        # Add FAQ table
        await self.db.query("DEFINE TABLE faq ...")
    
    async def query(self, question):
        # Custom logic
        return {"answer": "..."}
```

---

## Example Prompts to Modify

| Goal | Prompt |
|------|--------|
| FAQ Bot | "Add a `query()` method that searches the FAQ table" |
| Add Auth | "Add user authentication in `setup()`" |
| Add Tools | "Add a `search_docs` tool in `TOOLS`" |
| Change DB | "Change the database connection to use SurrealKV" |
| Add Memory | "Add conversation history in `chat()`" |

---

## Quick Test

```bash
# 1. Download template
curl -O https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py

# 2. Run it (should work)
python agent_template.py

# 3. Edit with AI
# Open in Cursor/Windsurf and ask: "Make it a FAQ bot"
```

---

## Video Demo

```
Coming soon: Watch how to use these URLs in AI coding tools
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| URL not loading | Check internet connection |
| Import error | Use `curl -O` to download first |
| Auth fails | Set `DB_USER` and `DB_PASS` env vars |
| OpenAI error | Set `OPENAI_API_KEY` env var |