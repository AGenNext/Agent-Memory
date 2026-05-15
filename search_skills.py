#!/usr/bin/env python3
"""
GitHub Skills Search & Import Tool

Search GitHub for skill files and import them into your project.

Usage:
    python search_skills.py search surrealdb
    python search_skills.py clone surrealdb/agent-skills
    python search_skills.py import https://raw.githubusercontent.com/.../skill.md
    python search_skills.py list
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


SKILLS_DIR = Path("skills")
DEFAULT_QUERY = "surrealql skill OR agent-skill OR surrealdb"


def search_github(query: str, max_results: int = 10):
    """Search GitHub for skill files."""
    url = f"https://api.github.com/search/code?q={query}+in:file,path&per_page={max_results}"
    
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            
        if not data.get("items"):
            print("No results found.")
            return
        
        print(f"\n{'='*60}")
        print(f"Found {data.get('total_count', 0)} results")
        print(f"{'='*60}\n")
        
        for i, item in enumerate(data["items"], 1):
            print(f"{i}. {item['name']}")
            print(f"   📁 {item['path']}")
            print(f"   🔗 {item['html_url']}")
            print(f"   📊 {item.get('size', 0)} bytes")
            print()
        
        return data["items"]
    
    except Exception as e:
        print(f"Error: {e}")
        return []


def clone_repo(repo: str, skills_path: str = None):
    """Clone a GitHub repository to get skills."""
    repo = repo.strip()
    if not repo.endswith(".git"):
        repo = f"https://github.com/{repo}.git"
    
    print(f"Cloning {repo}...")
    
    try:
        # Clone to temp directory
        temp_dir = Path("/tmp/skills_import")
        temp_dir.mkdir(exist_ok=True)
        
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo, str(temp_dir)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return
        
        # Find skill files
        skill_files = list(temp_dir.rglob("*.md")) + list(temp_dir.rglob("*.mdc"))
        
        print(f"\nFound {len(skill_files)} skill files:")
        
        for f in skill_files:
            print(f"  - {f.relative_to(temp_dir)}")
        
        # Copy to skills directory
        SKILLS_DIR.mkdir(exist_ok=True)
        
        count = 0
        for f in skill_files:
            dest = SKILLS_DIR / f.name
            import shutil
            shutil.copy(f, dest)
            count += 1
            print(f"✅ Copied: {f.name}")
        
        print(f"\n✅ Imported {count} skill files to {SKILLS_DIR}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"Error: {e}")


def import_url(url: str):
    """Import a skill from raw URL."""
    try:
        print(f"Fetching {url}...")
        
        with urllib.request.urlopen(url) as response:
            content = response.read().decode("utf-8")
        
        # Get filename from URL
        filename = Path(url).name
        if not filename.endswith((".md", ".mdc")):
            filename = filename.split("?")[0] + ".md"
        
        # Save to skills directory
        SKILLS_DIR.mkdir(exist_ok=True)
        filepath = SKILLS_DIR / filename
        
        with open(filepath, "w") as f:
            f.write(content)
        
        print(f"✅ Imported: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def import_file(filepath: str):
    """Import a local skill file."""
    src = Path(filepath)
    
    if not src.exists():
        print(f"File not found: {filepath}")
        return
    
    SKILLS_DIR.mkdir(exist_ok=True)
    dest = SKILLS_DIR / src.name
    
    import shutil
    shutil.copy(src, dest)
    
    print(f"✅ Imported: {dest}")


def list_skills():
    """List all local skills."""
    if not SKILLS_DIR.exists():
        print("No skills directory found.")
        return
    
    skill_files = list(SKILLS_DIR.glob("*.md")) + list(SKILLS_DIR.glob("*.mdc"))
    
    print(f"\n{'='*60}")
    print(f"Local Skills ({len(skill_files)} files)")
    print(f"{'='*60}\n")
    
    for f in sorted(skill_files):
        size = f.stat().st_size
        print(f"  📄 {f.name} ({size} bytes)")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="GitHub Skills Import Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # Search command
    subparsers.add_parser("search", help="Search GitHub for skills")
    subparsers.add_parser("clone", help="Clone repo to get skills")  
    subparsers.add_parser("import", help="Import from URL")
    subparsers.add_parser("list", help="List local skills")
    
    parser.add_argument("query", nargs="?", help="Search query or repo URL")
    parser.add_argument("extra", nargs="?", help="Extra argument")
    
    args = parser.parse_args()
    
    if args.command == "search":
        query = args.query or DEFAULT_QUERY
        search_github(query)
    
    elif args.command == "clone":
        if not args.query:
            print("Usage: clone <repo>")
            return
        clone_repo(args.query)
    
    elif args.command == "import":
        if not args.query:
            print("Usage: import <url>")
            return
        import_url(args.query)
    
    elif args.command == "list":
        list_skills()
    
    else:
        # Default: show help
        print("""
GitHub Skills Search & Import Tool

Usage:
    python search_skills.py search surrealdb agent
    python search_skills.py clone surrealdb/agent-skills
    python search_skills.py import https://raw.githubusercontent.com/...skill.md
    python search_skills.py list
    python search_skills.py clone owner/repo --path skills/
        """)
        
        # Also search for default skills
        print("\nSearching for SurrealDB skills...\n")
        search_github(DEFAULT_QUERY)


if __name__ == "__main__":
    main()