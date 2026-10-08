#!/usr/bin/env python3
"""Update every GCP setup release URL after validating release metadata."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any


REPOSITORY = "StanfordHPDS/gcp_setup_script"
TAG_PATTERN = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
URL_PATTERN = re.compile(
    r"(?P<prefix>https://github\.com/StanfordHPDS/gcp_setup_script/releases/download/)"
    r"(?P<tag>[^/\s)]+)"
    r"(?P<suffix>/(?P<asset>setup|update)\.sh)"
)
REQUIRED_ASSETS = {"setup.sh", "update.sh"}


class UpdateError(ValueError):
    """The release or README cannot be updated safely."""


def validate_release(payload: Any, requested_tag: str | None = None) -> str:
    if not isinstance(payload, dict):
        raise UpdateError("release metadata must be a JSON object")

    tag = payload.get("tag_name")
    if not isinstance(tag, str) or TAG_PATTERN.fullmatch(tag) is None:
        raise UpdateError("release tag must have the form vX.Y.Z")
    if requested_tag is not None and tag != requested_tag:
        raise UpdateError(f"release metadata is for {tag}, not requested tag {requested_tag}")
    if payload.get("draft") is not False:
        raise UpdateError(f"release {tag} is a draft")
    if payload.get("prerelease") is not False:
        raise UpdateError(f"release {tag} is a prerelease")
    if not payload.get("published_at"):
        raise UpdateError(f"release {tag} is not published")

    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("release assets must be a JSON array")

    by_name: dict[str, dict[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
            raise UpdateError("release contains malformed asset metadata")
        name = asset["name"]
        if name in by_name:
            raise UpdateError(f"release contains duplicate asset {name}")
        by_name[name] = asset

    missing = sorted(REQUIRED_ASSETS - by_name.keys())
    if missing:
        raise UpdateError(f"release {tag} is missing assets: {', '.join(missing)}")

    for name in sorted(REQUIRED_ASSETS):
        asset = by_name[name]
        if asset.get("state") != "uploaded":
            raise UpdateError(f"release asset {name} is not uploaded")
        expected_url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
        if asset.get("browser_download_url") != expected_url:
            raise UpdateError(f"release asset {name} has an unexpected download URL")

    return tag


def update_readme(text: str, tag: str) -> tuple[str, bool]:
    matches = list(URL_PATTERN.finditer(text))
    if not matches:
        raise UpdateError("README contains no GCP setup release URLs")

    assets = {f"{match.group('asset')}.sh" for match in matches}
    missing = sorted(REQUIRED_ASSETS - assets)
    if missing:
        raise UpdateError(f"README is missing release URLs for: {', '.join(missing)}")

    updated = URL_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{tag}{match.group('suffix')}", text
    )
    return updated, updated != text


def write_atomic(path: Path, text: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    staged_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as staged:
            staged_path = Path(staged.name)
            staged.write(text)
            staged.flush()
            os.fsync(staged.fileno())
        os.chmod(staged_path, mode)
        os.replace(staged_path, path)
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


def append_outputs(path: Path, tag: str, changed: bool) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(f"tag={tag}\nchanged={'true' if changed else 'false'}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--requested-tag")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.release_json.read_text(encoding="utf-8"))
    tag = validate_release(payload, args.requested_tag)
    original = args.readme.read_text(encoding="utf-8")
    updated, changed = update_readme(original, tag)
    if changed:
        write_atomic(args.readme, updated)
    if args.output is not None:
        append_outputs(args.output, tag, changed)
    print(f"{'updated' if changed else 'already using'} {tag}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, UpdateError) as error:
        raise SystemExit(f"error: {error}") from error
