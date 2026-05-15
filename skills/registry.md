# Skills.sh Registry

Find and install community skills using the skills CLI.

## Install Skills CLI

```bash
npm install -g @skills/cli
# or
npx skills
```

## Find Skills

```bash
# Search for SurrealDB skills
npx skills find surrealdb
npx skills find vector
npx skills find database

# Show all skills
npx skills list
```

## Install Community Skills

```bash
# Install from GitHub
npx skills add owner/repo
npx skills add owner/repo --skill skill-name

# Install from URL
npx skills add https://github.com/owner/repo
npx skills add https://raw.githubusercontent.com/owner/repo/main/skill.md
```

## SurrealDB Skills

### Official Skills
```bash
npx skills add surrealdb/agent-skills
npx skills add surrealdb/agent-skills --skill surrealql
npx skills add surrealdb/agent-skills --skill surrealdb-vector
npx skills add surrealdb/agent-skills --skill surrealdb-python
```

### Community Skills
```bash
# Search community
npx skills find "surrealdb"

# Add community skill
npx skills add community/skill-name
```

## Publish Your Skill

### 1. Create Skill File
```markdown
# My Skill
Description of what this skill does.

## When to use
- Use case 1
- Use case 2

## Commands
\`\`\`bash
command1
command2
\`\`\`
```

### 2. Publish
```bash
# GitHub repository
git init
git add .
git commit -m "Add skill"
git push origin main

# Publish to skills.sh
npx skills publish
```

## Use in Agent

### Cursor
```
@skills/my-skill.md

Help me do X
```

### Claude Code
```
Use the my-skill to accomplish Y
```

## More Resources

- [skills.sh](https://skills.sh)
- [Skills Directory](https://skills.sh/directory)
- [Publish Guide](https://skills.sh/docs/publish)