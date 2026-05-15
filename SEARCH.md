# GitHub Skills Search Tool

Search, clone, and import skills from GitHub.

## Installation

```bash
pip install -r requirements.txt  # Already in project
```

## Quick Start

```bash
# Search GitHub for skills
python search_skills.py search surrealdb agent

# Clone a skill repository
python search_skills.py clone surrealdb/agent-skills

# Import from URL
python search_skills.py import https://raw.githubusercontent.com/.../skill.md

# List local skills
python search_skills.py list
```

## Usage

### Search GitHub
```bash
python search_skills.py search "surrealdb tutorial skills"
python search_skills.py search "agent skill"
python search_skills.py search "llm database"
```

### Clone Repository
```bash
# Clone official skills
python search_skills.py clone surrealdb/agent-skills

# Clone community skills
python search_skills.py clone owner/repo
```

### Import from URL
```bash
# Single file
python search_skills.py import https://raw.githubusercontent.com/user/repo/main/skill.md

# Direct from GitHub
python search_skills.py import https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/skills/query.md
```

### List Local Skills
```bash
python search_skills.py list
```

## Examples

### Search & Import
```bash
# 1. Search for skills
python search_skills.py search "surrealql tutorial"

# 2. Copy the URL from results

# 3. Import
python search_skills.py import <URL>
```

### Bulk Import
```bash
# Clone all skills from a repo
python search_skills.py clone surrealdb/agent-skills

# This copies all .md/.mdc files to skills/
```

## Output

Skills are saved to:

```
skills/
├── query.md
├── surrealql.md
├── python.md
└── ... (imported skills)
```

## Python API

```python
from search_skills import search_github, clone_repo, import_url

# Search
results = search_github("surrealdb agent skill")

# Clone repo
clone_repo("owner/repo")

# Import URL
import_url("https://raw.githubusercontent.com/.../skill.md")
```

## GitHub Token (Optional)

For higher rate limits, set GITHUB_TOKEN:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

## More Info

- [GitHub API](https://docs.github.com/en/rest/search)
- [skills.sh](https://skills.sh)