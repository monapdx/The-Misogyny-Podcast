#!/usr/bin/env python3
"""Regenerate the episode table in README.md from episodes/episode-N.md."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODES_DIR = ROOT / "episodes"
README_PATH = ROOT / "README.md"

START_MARKER = "<!-- EPISODES_TABLE_START -->"
END_MARKER = "<!-- EPISODES_TABLE_END -->"

EPISODE_FILENAME = re.compile(r"episode-(\d+)\.md$", re.IGNORECASE)
TITLE_LINE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)


def read_title(path: Path) -> str:
    """Read the title value from an episode's YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = TITLE_LINE.search(text)

    if not match:
        raise ValueError(f"Missing frontmatter title in {path.relative_to(ROOT)}")

    raw_title = match.group(1).strip()

    if raw_title.startswith('"') and raw_title.endswith('"'):
        title = json.loads(raw_title)
    elif raw_title.startswith("'") and raw_title.endswith("'"):
        title = raw_title[1:-1].replace("''", "'")
    else:
        title = raw_title

    return title.replace("|", "\\|")


def collect_episodes() -> list[tuple[int, str, str]]:
    """Return episode number, title, and repository-relative link."""
    episodes: list[tuple[int, str, str]] = []

    for path in EPISODES_DIR.glob("episode-*.md"):
        match = EPISODE_FILENAME.fullmatch(path.name)
        if not match:
            continue

        number = int(match.group(1))
        title = read_title(path)
        link = f"./episodes/{path.name}"
        episodes.append((number, title, link))

    episodes.sort(key=lambda episode: episode[0])
    return episodes


def build_table(episodes: list[tuple[int, str, str]]) -> str:
    lines = [
        START_MARKER,
        "",
        "| Episode No. | Title |",
        "|---:|---|",
    ]

    for number, title, link in episodes:
        lines.append(f"| {number} | [{title}]({link}) |")

    lines.extend(["", END_MARKER])
    return "\n".join(lines)


def update_readme() -> bool:
    readme = README_PATH.read_text(encoding="utf-8")

    if START_MARKER not in readme or END_MARKER not in readme:
        raise ValueError(
            "README.md must contain the episode table start and end markers."
        )

    before, remainder = readme.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    updated = before + build_table(collect_episodes()) + after

    if updated == readme:
        print("Episode table is already current.")
        return False

    README_PATH.write_text(updated, encoding="utf-8")
    print("Updated the episode table in README.md.")
    return True


if __name__ == "__main__":
    update_readme()

