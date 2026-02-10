"""
AI Skills module - Dynamic skill management system.

Skills are markdown files with instructions that extend the AI's capabilities.
They can be loaded from files or URLs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

import yaml

from core.logger import log_error, log_info, log_warning

SKILLS_DIR = Path("data/ai_skills")


class SkillData(TypedDict):
    """Skill data structure."""

    name: str
    description: str
    trigger: str
    priority: int
    content: str


def parse_skill_markdown(content: str) -> SkillData | None:
    """
    Parse a skill from markdown content with YAML frontmatter.

    Format:
    ---
    name: skill_name
    description: Short description
    trigger: always  # always, on_mention, manual
    priority: 10
    ---

    # Skill Content
    Instructions for the AI...
    """
    parts = re.split(r"^---\s*$", content.strip(), maxsplit=2, flags=re.MULTILINE)

    if len(parts) < 3:
        log_warning("Skill markdown missing frontmatter (---)")
        return None

    try:
        frontmatter = yaml.safe_load(parts[1])
        if not frontmatter:
            log_warning("Empty frontmatter in skill")
            return None

        name = frontmatter.get("name")
        if not name:
            log_warning("Skill missing 'name' in frontmatter")
            return None

        return SkillData(
            name=name,
            description=frontmatter.get("description", ""),
            trigger=frontmatter.get("trigger", "always"),
            priority=frontmatter.get("priority", 10),
            content=parts[2].strip(),
        )
    except yaml.YAMLError as e:
        log_error(f"Failed to parse skill frontmatter: {e}")
        return None


def load_skill_from_file(path: Path | str) -> SkillData | None:
    """Load a skill from a file."""
    path = Path(path)
    if not path.exists():
        log_error(f"Skill file not found: {path}")
        return None

    try:
        content = path.read_text(encoding="utf-8")
        skill = parse_skill_markdown(content)
        if skill:
            log_info(f"Loaded skill from file: {skill['name']}")
        return skill
    except Exception as e:
        log_error(f"Failed to load skill from {path}: {e}")
        return None


async def load_skill_from_url(url: str) -> SkillData | None:
    """Load a skill from a URL."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            content = response.text

        skill = parse_skill_markdown(content)
        if skill:
            log_info(f"Loaded skill from URL: {skill['name']}")
        return skill
    except Exception as e:
        log_error(f"Failed to load skill from URL {url}: {e}")
        return None


def save_skill_to_file(skill: SkillData) -> Path:
    """Save a skill to a file."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "name": skill["name"],
        "description": skill["description"],
        "trigger": skill["trigger"],
        "priority": skill["priority"],
    }

    content = f"""---
{yaml.dump(frontmatter, default_flow_style=False).strip()}
---

{skill["content"]}
"""

    file_path = SKILLS_DIR / f"{skill['name']}.md"
    file_path.write_text(content, encoding="utf-8")
    log_info(f"Saved skill to: {file_path}")
    return file_path


def delete_skill_file(name: str) -> bool:
    """Delete a skill file."""
    file_path = SKILLS_DIR / f"{name}.md"
    if file_path.exists():
        file_path.unlink()
        log_info(f"Deleted skill file: {file_path}")
        return True
    return False


def list_skill_files() -> list[Path]:
    """List all skill files in the skills directory."""
    if not SKILLS_DIR.exists():
        return []
    return list(SKILLS_DIR.glob("*.md"))


def load_all_skills() -> list[SkillData]:
    """Load all skills from the skills directory."""
    skills = []
    for path in list_skill_files():
        skill = load_skill_from_file(path)
        if skill:
            skills.append(skill)

    skills.sort(key=lambda s: s["priority"], reverse=True)
    return skills
