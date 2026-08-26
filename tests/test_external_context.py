#!/usr/bin/env python3

import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "preview-20260826-a"
RELEASE_ROOT = ROOT / "public-context" / "v1" / RELEASE
PUBLIC_BASE_URL = "https://artists-in-dsp.github.io/amorph-for-agents"


class ContextPreParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_context = False
        self.context_parts = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "pre" and attributes.get("id") == "amorph-context":
            self.in_context = True
        if tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag):
        if tag == "pre" and self.in_context:
            self.in_context = False

    def handle_data(self, data):
        if self.in_context:
            self.context_parts.append(data)

    @property
    def context(self):
        return "".join(self.context_parts)


class ExternalContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    def test_six_target_variant_documents_exist(self):
        records = self.manifest["documents"]
        self.assertEqual(2, self.manifest["schema_version"])
        self.assertEqual("static-html-v1", self.manifest["delivery_format"])
        self.assertEqual(6, len(records))
        self.assertEqual(
            {
                (target, variant)
                for target in ("dsp", "ui")
                for variant in ("instrument", "fx", "midi")
            },
            {(record["target"], record["variant"]) for record in records},
        )

    def test_static_html_visible_text_matches_audit_document(self):
        manifest_text = (RELEASE_ROOT / "manifest.json").read_text(encoding="utf-8")
        self.assertNotIn("context_id", manifest_text)
        self.assertNotIn("end_token", manifest_text)

        for record in self.manifest["documents"]:
            with self.subTest(path=record["html_path"]):
                audit_raw = (RELEASE_ROOT / record["audit_path"]).read_bytes()
                html_raw = (RELEASE_ROOT / record["html_path"]).read_bytes()
                audit_text = audit_raw.decode("utf-8")
                page = html_raw.decode("utf-8")
                parser = ContextPreParser()
                parser.feed(page)

                self.assertEqual(0, parser.scripts)
                self.assertEqual(audit_text, parser.context)
                self.assertTrue(parser.context.startswith("AMORPH_EXTERNAL_CONTEXT v1\n"))
                self.assertNotIn("<script", page.lower())
                self.assertNotIn("src=", page.lower())
                self.assertNotIn("javascript:", page.lower())
                self.assertIn('<meta name="robots" content="index,follow">', page)
                self.assertEqual(record["visible_text_bytes"], len(audit_raw))
                self.assertEqual(record["html_bytes"], len(html_raw))
                self.assertEqual(record["canonical_text_sha256"], hashlib.sha256(audit_raw).hexdigest())
                self.assertEqual(record["html_sha256"], hashlib.sha256(html_raw).hexdigest())

    def test_documents_are_self_contained_and_receipts_are_release_specific(self):
        for record in self.manifest["documents"]:
            with self.subTest(path=record["audit_path"]):
                path = RELEASE_ROOT / record["audit_path"]
                raw = path.read_bytes()
                text = raw.decode("utf-8")
                context_match = re.search(r"^CONTEXT_ID: (\S+)$", text, re.MULTILINE)
                end_match = re.search(r"^END_TOKEN: (\S+)$", text, re.MULTILINE)

                self.assertLess(len(raw), 30_000)
                self.assertNotIn(b"\x00", raw)
                self.assertNotIn("\r", text)
                self.assertNotIn("http://", text)
                self.assertNotIn("https://", text)
                self.assertEqual(1, text.count("BEGIN_AMORPH_CONTEXT"))
                self.assertEqual(1, text.count("END_AMORPH_CONTEXT"))
                self.assertIsNotNone(context_match)
                self.assertIsNotNone(end_match)
                body = text.split("BEGIN_AMORPH_CONTEXT\n", 1)[1].split(
                    "END_AMORPH_CONTEXT\n", 1
                )[0]
                body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
                receipt_sha = hashlib.sha256(
                    f"AMORPH_EXTERNAL_CONTEXT v1\nRELEASE: {RELEASE}\n{body}".encode("utf-8")
                ).hexdigest()
                self.assertEqual(record["body_sha256"], body_sha)
                self.assertEqual(
                    f"amorph-{record['target']}-{record['variant']}-{receipt_sha[:16]}",
                    context_match.group(1),
                )
                self.assertEqual(f"amorph-end-{receipt_sha[-16:]}", end_match.group(1))
                self.assertTrue(text.endswith(f"END_TOKEN: {end_match.group(1)}\n"))
                self.assertIn("return exactly CONTEXT_UNAVAILABLE", text)
                self.assertIn("// AMORPH_CONTEXT_ID: <exact CONTEXT_ID>", text)
                self.assertIn("// AMORPH_END_TOKEN: <exact END_TOKEN>", text)

    def test_landing_page_and_sitemap_link_all_html_documents(self):
        index = (ROOT / "public-context" / "index.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "public-context" / "sitemap.xml").read_text(encoding="utf-8")
        llms = (ROOT / "public-context" / "llms.txt").read_text(encoding="utf-8")
        self.assertNotIn("noindex", index)
        for record in self.manifest["documents"]:
            relative = f"v1/{RELEASE}/{record['html_path']}"
            self.assertIn(f'href="/{relative}"', index)
            self.assertIn(f"{PUBLIC_BASE_URL}/{relative}", sitemap)
            self.assertIn(f"{PUBLIC_BASE_URL}/{relative}", llms)

    def test_editable_sources_are_not_generated_amorph_exports(self):
        for path in sorted((ROOT / "context-src" / "v1").glob("*/*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("GENERATED by export_paste_context.py", text)
                self.assertNotIn("Source: InfinityLab commit", text)

    def test_dsp_sources_cover_observed_generalised_failures(self):
        for path in sorted((ROOT / "context-src" / "v1" / "dsp").glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("never declare a value with `let` inside a `for` or `while` body", text)
                self.assertIn("preserve every existing endpoint, parameter", text)
                self.assertIn("next sequential `paramN` ID", text)
                self.assertIn("a Cmajor state initializer is not a substitute", text)
                self.assertIn("preserves the existing intended/audible default", text)
                self.assertIn("After the two required receipt comments", text)
                self.assertNotIn("`select(cond, a, b)`", text)
                self.assertIn("Vector-only masked selection", text)
                self.assertIn("For scalar values use `cond ? a : b`", text)
                self.assertIn('display label `[[ name: "Output" ]]`', text)
                self.assertIn("never `output`", text)
                self.assertIn("never `init: Z, ]]`", text)
                self.assertIn("every occurrence of `processor.period`", text)
                self.assertIn("Never use bare `processor.period`", text)
                self.assertIn("`float64(processor.period)`", text)
                self.assertIn("`float dt = float(processor.period);`", text)

        instrument = (ROOT / "context-src" / "v1" / "dsp" / "instrument.md").read_text(encoding="utf-8")
        self.assertNotIn("float64 (voices[i].noteFreq) * processor.period", instrument)
        self.assertIn(
            "float64 (voices[i].noteFreq) * float (processor.period)",
            instrument,
        )

    def test_ui_sources_require_one_parameter_marker_per_endpoint(self):
        for path in sorted((ROOT / "context-src" / "v1" / "ui").glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("exactly ONE DOM element with `data-param`", text)
                self.assertIn('querySelectorAll("[data-param]").length', text)
                self.assertIn("line 3", text)
                self.assertIn("After the two required receipt comments", text)


if __name__ == "__main__":
    unittest.main()
