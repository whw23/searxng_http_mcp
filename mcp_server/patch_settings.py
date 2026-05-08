"""Patch SearXNG settings.yml to enable JSON format output."""

import sys
from pathlib import Path

import yaml


def patch_settings(settings_path: str = "/etc/searxng/settings.yml"):
    path = Path(settings_path)
    if not path.exists():
        return

    with open(path) as f:
        settings = yaml.safe_load(f) or {}

    search = settings.setdefault("search", {})
    formats = search.setdefault("formats", [])
    if "json" not in formats:
        formats.append("json")
        with open(path, "w") as f:
            yaml.dump(settings, f, default_flow_style=False)


if __name__ == "__main__":
    settings_path = sys.argv[1] if len(sys.argv) > 1 else "/etc/searxng/settings.yml"
    patch_settings(settings_path)
