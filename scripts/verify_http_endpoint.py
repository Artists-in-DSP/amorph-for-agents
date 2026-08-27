#!/usr/bin/env python3
"""Verify a deployed static-HTML Amorph context endpoint anonymously."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = "preview-20260827-n"
DEFAULT_AGENTS = (
    "Mozilla/5.0 AmorphContextQA/1.0",
    "ChatGPT-User",
    "OAI-SearchBot",
    "GoogleOther",
    "DuckDuckBot",
)


class ContextPreParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_context = False
        self.parts: List[str] = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and dict(attrs).get("id") == "amorph-context":
            self.in_context = True
        if tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag):
        if tag == "pre" and self.in_context:
            self.in_context = False

    def handle_data(self, data):
        if self.in_context:
            self.parts.append(data)

    @property
    def context(self) -> str:
        return "".join(self.parts)


def fetch(url: str, user_agent: str, accept: str = "text/html,*/*;q=0.1") -> Tuple[int, str, Dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return (
                response.status,
                response.geturl(),
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.geturl(),
            {key.lower(): value for key, value in error.headers.items()},
            error.read(),
        )


def verify(base_url: str, release: str, agents: Tuple[str, ...]) -> Dict[str, object]:
    release_root = ROOT / "public-context" / "v1" / release
    manifest = json.loads((release_root / "manifest.json").read_text(encoding="utf-8"))
    failures: List[str] = []
    receipts: List[Dict[str, object]] = []
    base_url = base_url.rstrip("/")

    robots_status, robots_url, _, robots_raw = fetch(
        f"{base_url}/robots.txt", agents[0], "text/plain,*/*;q=0.1"
    )
    robots_text = robots_raw.decode("utf-8", errors="replace")
    if robots_status != 200 or "Allow: /" not in robots_text or "Disallow: /" in robots_text:
        failures.append("robots.txt does not explicitly allow complete retrieval")

    sitemap_status, sitemap_url, _, sitemap_raw = fetch(
        f"{base_url}/sitemap.xml", agents[0], "application/xml,text/xml,*/*;q=0.1"
    )
    if sitemap_status != 200:
        failures.append("sitemap.xml is unavailable")

    for agent in agents:
        for record in manifest["documents"]:
            url = f"{base_url}/v1/{release}/{record['html_path']}"
            status, final_url, headers, raw = fetch(url, agent)
            parser = ContextPreParser()
            decoded = raw.decode("utf-8", errors="replace")
            parser.feed(decoded)
            visible_raw = parser.context.encode("utf-8")
            content_type = headers.get("content-type", "")
            checks = {
                "status_200": status == 200,
                "no_redirect": final_url == url,
                "text_html": content_type.lower().startswith("text/html"),
                "html_hash_match": hashlib.sha256(raw).hexdigest() == record["html_sha256"],
                "visible_text_hash_match": (
                    hashlib.sha256(visible_raw).hexdigest() == record["canonical_text_sha256"]
                ),
                "visible_text_size_match": len(visible_raw) == record["visible_text_bytes"],
                "no_set_cookie": "set-cookie" not in headers,
                "no_script": parser.scripts == 0,
                "complete_markers": (
                    visible_raw.startswith(b"AMORPH_EXTERNAL_CONTEXT v1\n")
                    and b"\nEND_AMORPH_CONTEXT\nEND_TOKEN: " in visible_raw
                ),
            }
            failed_checks = [name for name, passed in checks.items() if not passed]
            if failed_checks:
                failures.append(f"{agent} {record['html_path']}: {', '.join(failed_checks)}")
            receipts.append(
                {
                    "user_agent": agent,
                    "path": record["html_path"],
                    "status": status,
                    "final_url": final_url,
                    "content_type": content_type,
                    "cache_control": headers.get("cache-control", ""),
                    "etag": headers.get("etag", ""),
                    "html_bytes": len(raw),
                    "visible_text_bytes": len(visible_raw),
                    "html_sha256": hashlib.sha256(raw).hexdigest(),
                    "visible_text_sha256": hashlib.sha256(visible_raw).hexdigest(),
                    "checks": checks,
                }
            )

    missing_url = f"{base_url}/v1/{release}/dsp/__missing__.html"
    missing_status, _, _, _ = fetch(missing_url, agents[0])
    if missing_status != 404:
        failures.append(f"missing path returned {missing_status}, expected 404")

    return {
        "schema_version": 2,
        "base_url": base_url,
        "release": release,
        "anonymous": True,
        "robots": {"url": robots_url, "status": robots_status},
        "sitemap": {"url": sitemap_url, "status": sitemap_status, "bytes": len(sitemap_raw)},
        "missing_path_status": missing_status,
        "passed": not failures,
        "failures": failures,
        "receipts": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--release", default=DEFAULT_RELEASE)
    parser.add_argument("--user-agent", action="append", dest="agents")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = verify(args.base_url, args.release, tuple(args.agents or DEFAULT_AGENTS))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
