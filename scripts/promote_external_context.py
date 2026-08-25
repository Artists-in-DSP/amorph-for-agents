#!/usr/bin/env python3
"""Promote an existing immutable HTML context release to v1/stable."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from .build_external_context import ROOT, render_site_files
except ImportError:  # Direct script execution.
    from build_external_context import ROOT, render_site_files


def promote(output_root: Path, release: str) -> None:
    source_root = output_root / "v1" / release
    manifest_path = source_root / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"release does not exist: {release}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2 or manifest.get("delivery_format") != "static-html-v1":
        raise ValueError("only generated static-html-v1 releases can be promoted")

    revision = release.removeprefix("preview-")
    archive_root = output_root / "v1" / "releases" / revision
    if archive_root.exists():
        source_files = sorted(p.relative_to(source_root) for p in source_root.rglob("*") if p.is_file())
        archive_files = sorted(p.relative_to(archive_root) for p in archive_root.rglob("*") if p.is_file())
        if source_files != archive_files or any(
            (source_root / p).read_bytes() != (archive_root / p).read_bytes() for p in source_files
        ):
            raise ValueError(f"refusing to overwrite differing immutable archive: {archive_root}")
    else:
        shutil.copytree(source_root, archive_root)

    stable_root = output_root / "v1" / "stable"
    if stable_root.exists():
        shutil.rmtree(stable_root)
    stable_root.mkdir(parents=True)
    for record in manifest["documents"]:
        for key in ("audit_path", "html_path"):
            relative = Path(record[key])
            destination = stable_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((source_root / relative).read_bytes())

    stable_manifest = {
        "schema_version": 2,
        "channel": "stable",
        "active_release": release,
        "immutable_archive": f"v1/releases/{revision}",
        "delivery_format": "static-html-v1",
        "documents": manifest["documents"],
    }
    (stable_root / "manifest.json").write_text(
        json.dumps(stable_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    for path, content in render_site_files(output_root).items():
        path.write_text(content, encoding="utf-8")

    print(f"PASS: promoted {release} to v1/stable and archived as releases/{revision}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("release")
    parser.add_argument("--output-root", type=Path, default=ROOT / "public-context")
    args = parser.parse_args()
    promote(args.output_root.resolve(), args.release)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
