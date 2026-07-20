#!/usr/bin/env python3
"""Regenerate the README episode table and GitHub Pages episode grid."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EPISODES_DIR = ROOT / "episodes"
README_PATH = ROOT / "README.md"
INDEX_PATH = ROOT / "index.html"

README_START = "<!-- EPISODES_TABLE_START -->"
README_END = "<!-- EPISODES_TABLE_END -->"
GRID_START = "<!-- EPISODES_GRID_START -->"
GRID_END = "<!-- EPISODES_GRID_END -->"
COUNT_START = "<!-- EPISODE_COUNT_START -->"
COUNT_END = "<!-- EPISODE_COUNT_END -->"

EPISODE_FILENAME = re.compile(r"episode-(\d+)\.md$", re.IGNORECASE)
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", re.DOTALL)
FIELD_LINE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*$", re.MULTILINE)

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
    "is", "nor", "of", "on", "or", "the", "to", "up", "via", "vs",
}


@dataclass(frozen=True)
class Episode:
    number: int
    title: str
    category: str
    link: str


def unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"Missing YAML frontmatter in {path.relative_to(ROOT)}")
    return {
        key.lower(): unquote(value)
        for key, value in FIELD_LINE.findall(match.group(1))
    }


def display_title(title: str) -> str:
    """Convert all-caps frontmatter titles into restrained title case."""
    if not title.isupper():
        return title
    words = title.lower().split()
    result: list[str] = []
    for index, word in enumerate(words):
        if 0 < index < len(words) - 1 and word in SMALL_WORDS:
            result.append(word)
        else:
            result.append(word.capitalize())
    return " ".join(result)


def collect_episodes() -> list[Episode]:
    episodes: list[Episode] = []
    for path in EPISODES_DIR.glob("episode-*.md"):
        match = EPISODE_FILENAME.fullmatch(path.name)
        if not match:
            continue
        fields = read_frontmatter(path)
        if not fields.get("title"):
            raise ValueError(f"Missing frontmatter title in {path.relative_to(ROOT)}")
        episodes.append(Episode(
            number=int(match.group(1)),
            title=fields["title"],
            category=fields.get("category", "broadcast"),
            link=f"./episodes/{path.name}",
        ))
    return sorted(episodes, key=lambda episode: episode.number)


def replace_between(text: str, start: str, end: str, generated: str) -> str:
    if start not in text or end not in text:
        raise ValueError(f"Missing required markers: {start} and {end}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{generated}\n{end}{after}"


def build_readme_table(episodes: list[Episode]) -> str:
    lines = ["", "| Episode No. | Title |", "|---:|---|"]
    for episode in episodes:
        title = episode.title.replace("|", "\\|")
        lines.append(f"| {episode.number} | [{title}]({episode.link}) |")
    return "\n".join(lines) + "\n"


def card_accent(number: int) -> str:
    accents = ("", " accent-cyan", " accent-lime", "", " accent-lime", " accent-cyan")
    return accents[(number - 1) % len(accents)]


def build_episode_grid(episodes: list[Episode]) -> str:
    cards: list[str] = ["      <div class=\"episode-grid\">"]
    for episode in episodes:
        title = html.escape(display_title(episode.title))
        category = html.escape(display_title(episode.category))
        cards.extend([
            f'        <a class="episode-card{card_accent(episode.number)}" href="{html.escape(episode.link)}">',
            f'          <span class="episode-number">{episode.number:02d}</span>',
            f'          <span class="episode-type">{category}</span>',
            f'          <h3>{title}</h3>',
            '          <span class="episode-link">Read transcript →</span>',
            "        </a>",
            "",
        ])
    if cards[-1] == "":
        cards.pop()
    cards.append("      </div>")
    return "\n".join(cards)


def episode_count_text(count: int) -> str:
    words = {
        0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
        6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
        11: "Eleven", 12: "Twelve",
    }
    label = words.get(count, str(count))
    noun = "broadcast" if count == 1 else "broadcasts"
    return f"        <p>{label} {noun}. No corrections.<br>Several claims under review.</p>"


def write_if_changed(path: Path, updated: str) -> bool:
    original = path.read_text(encoding="utf-8")
    if original == updated:
        return False
    path.write_text(updated, encoding="utf-8")
    print(f"Updated {path.relative_to(ROOT)}")
    return True


def update_archives() -> None:
    episodes = collect_episodes()

    readme = README_PATH.read_text(encoding="utf-8")
    readme = replace_between(readme, README_START, README_END, build_readme_table(episodes))
    write_if_changed(README_PATH, readme)

    index = INDEX_PATH.read_text(encoding="utf-8")
    index = replace_between(index, GRID_START, GRID_END, build_episode_grid(episodes))
    index = replace_between(index, COUNT_START, COUNT_END, episode_count_text(len(episodes)))
    write_if_changed(INDEX_PATH, index)


if __name__ == "__main__":
    update_archives()
