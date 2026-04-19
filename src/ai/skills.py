"""
AI Skills module - Dynamic skill management system.

Skills are markdown files with instructions that extend the AI's capabilities.
They can be loaded from files or URLs.
"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import httpx
import yaml

from core.constants import SKILLS_DIR
from core.logger import log_error, log_info, log_warning

MAX_SKILL_CONTENT_SIZE = 102400  # 100KB max skill content from URL
SAFE_NAME_PATTERN = re.compile(r"^[a-z0-9_-]+$")


def _sanitize_skill_name(name: str) -> str:
    """Sanitize skill name to safe filesystem characters only."""
    safe = re.sub(r"[^a-z0-9_-]", "", name.lower().strip())
    if not safe:
        raise ValueError(f"Invalid skill name after sanitization: '{name}'")
    return safe


def _validate_skill_url(url: str) -> None:
    """Validate URL for skill loading - HTTPS only, no private IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        raise ValueError(f"Only HTTPS URLs are allowed for skill loading, got: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    # Block private/reserved IPs (SSRF prevention)
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError(f"URL points to private/reserved IP: {parsed.hostname}")
    except ValueError as e:
        if "does not appear to be" not in str(e):
            raise
        # hostname is not an IP literal, that's fine (it's a domain name)


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
    """Load a skill from a URL. HTTPS only, no private IPs, size-limited."""
    try:
        _validate_skill_url(url)
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            if len(response.content) > MAX_SKILL_CONTENT_SIZE:
                log_error(
                    f"Skill from URL exceeds size limit ({len(response.content)} > {MAX_SKILL_CONTENT_SIZE})"
                )
                return None
            content = response.text

        skill = parse_skill_markdown(content)
        if skill:
            log_info(f"Loaded skill from URL: {skill['name']}")
        return skill
    except ValueError as e:
        log_error(f"Invalid skill URL {url}: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to load skill from URL {url}: {e}")
        return None


def save_skill_to_file(skill: SkillData) -> Path:
    """Save a skill to a file. Skill name is sanitized to prevent path traversal."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_skill_name(skill["name"])

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

    file_path = (SKILLS_DIR / f"{safe_name}.md").resolve()
    # Verify resolved path is within SKILLS_DIR
    if not str(file_path).startswith(str(SKILLS_DIR.resolve())):
        raise ValueError(f"Skill path escapes skills directory: {file_path}")

    file_path.write_text(content, encoding="utf-8")
    log_info(f"Saved skill to: {file_path}")
    return file_path


def delete_skill_file(name: str) -> bool:
    """Delete a skill file. Name is sanitized to prevent path traversal."""
    safe_name = _sanitize_skill_name(name)
    file_path = (SKILLS_DIR / f"{safe_name}.md").resolve()
    # Verify resolved path is within SKILLS_DIR
    if not str(file_path).startswith(str(SKILLS_DIR.resolve())):
        log_error(f"Attempted path traversal in delete_skill_file: {name}")
        return False
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
