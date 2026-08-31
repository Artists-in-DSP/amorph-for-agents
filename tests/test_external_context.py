#!/usr/bin/env python3

import hashlib
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.build_external_context import compose_source


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "preview-20260831-c"
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
        self.assertEqual("1.0.3175", self.manifest["cmajor_sdk_version"])
        self.assertEqual("core-dsp-v1", self.manifest["knowledge_profile"])
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

                # MIDI now carries the same complete host-transport and named
                # musical-division contract as audio variants. Keep it below
                # 20 KB while the richer Instrument/FX documents stay below 24 KB.
                budget = 20_000 if record["target"] == "dsp" and record["variant"] == "midi" else 24_000
                self.assertLessEqual(len(raw), budget)
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
                text = compose_source("dsp", path.stem)
                self.assertIn("do not use `let` anywhere in the returned source", text)
                self.assertIn("Every host parameter endpoint ID must be the exact sequential form", text)
                self.assertIn("invalid for Amorph even if Cmajor accepts them", text)
                self.assertNotIn("custom names like `paramSnap`", text)
                self.assertIn("preserve every existing endpoint, parameter", text)
                self.assertIn("next sequential `paramN` ID", text)
                self.assertIn("a Cmajor state initializer is not a substitute", text)
                self.assertIn("preserves the existing intended/audible default", text)
                self.assertIn("After the two required receipt comments", text)
                self.assertIn("requires an identifier", text)
                self.assertIn("`processor [[ main ]]`", text)
                self.assertIn("`processor {`", text)
                self.assertIn("follows the name; it never replaces it", text)
                self.assertIn("`auto`", text)
                self.assertIn("identifiers must be ASCII", text)
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
                self.assertIn("**Final loop audit:**", text)
                self.assertIn("No value declared inside a repeated loop body may use `let`", text)
                self.assertIn("Do this literal audit after generating the complete file", text)
                self.assertIn("**Immutable `let`:**", text)
                self.assertIn("a `let` binding can never be assigned again", text)
                self.assertIn("explicit typed mutable local", text)
                self.assertIn("do not use `let` anywhere in the returned source", text)
                self.assertIn("Never invent `.set(...)` or `.get(...)` array methods", text)
                self.assertIn("write with `array.at(i) = value;`", text)
                self.assertIn("**Modulo/division safety:**", text)
                self.assertIn("`% max(1, count)`", text)
                self.assertIn("every `/` and `%` divisor", text)
                self.assertIn("syntax-based and does not infer safety from an outer branch", text)
                self.assertIn("inspect every literal `/` and `%` occurrence", text)
                self.assertIn("manual phase field and every expression assigned back to it must have the same type", text)
                self.assertIn("Never declare `float phase;`", text)
                self.assertIn("declare `float64 phase;`", text)
                self.assertIn("input event float transportIn;", text)
                self.assertIn("Amorph does not populate `std::timeline::*` endpoints", text)
                self.assertIn("play, bpm, numerator, denominator, ppq, barStart", text)
                self.assertIn("currentPpq = value;", text)
                self.assertIn("if (value < currentPpq) lastStepIndex = -1;", text)
                self.assertIn("if (value != hostBarStartPpq) lastStepIndex = -1;", text)
                self.assertIn("same local step", text)
                self.assertIn("Apply a valid host BPM immediately", text)
                self.assertIn("periodSeconds = divisionQuarterNotes * 60.0f", text)
                self.assertIn("`delayTimeParam * 0.25f`", text)
                self.assertIn("**not BPM sync**", text)
                self.assertIn('text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar"', text)
                self.assertIn("never arbitrary values", text)
                self.assertIn("0.121413", text)
                self.assertIn("getDivisionQuarterNotes()", text)
                self.assertIn("not phase-locked", text)
                self.assertNotIn("search_components(\"transport ppq parser\")", text)
                self.assertNotIn("Patches/StartupMidiLive/dsp.cmajor", text)

        for record in self.manifest["documents"]:
            if record["target"] != "dsp":
                continue
            generated = (RELEASE_ROOT / record["audit_path"]).read_text(encoding="utf-8")
            self.assertIn("Every host parameter endpoint ID must be the exact sequential form", generated)
            self.assertIn("audit every `input event float` declaration", generated)
            self.assertIn("immediately followed by a top-level identifier", generated)
            self.assertIn("Never return `processor [[ main ]]`", generated)

        instrument = (ROOT / "context-src" / "v1" / "dsp" / "instrument.md").read_text(encoding="utf-8")
        self.assertIn("**Polyphonic sum safety:**", instrument)
        self.assertIn("never use a fixed multiplier such as `0.25`", instrument)
        self.assertIn("`float(max(1, activeVoiceCount))`", instrument)

        self.assertNotIn("float64 (voices[i].noteFreq) * processor.period", instrument)
        self.assertIn(
            "float64 (voices[i].noteFreq * float (processor.period))",
            instrument,
        )
        self.assertIn("Never poll `midiIn.available()`", instrument)
        self.assertIn("`midiIn.read()` in `main`", instrument)
        self.assertIn("Choose exactly one MIDI architecture", instrument)
        self.assertIn("Never connect `std::midi::MPEConverter` to a processor endpoint typed `std::midi::Message`", instrument)
        self.assertIn("`midiIn -> std::midi::MPEConverter -> synth.midiIn` is invalid", instrument)
        self.assertIn("count the existing `paramN` declarations", instrument)
        self.assertIn("a requested new control must appear as `param5` in all four places", instrument)

        midi = (ROOT / "context-src" / "v1" / "dsp" / "midi.md").read_text(encoding="utf-8")
        self.assertIn("`% heldCount` is forbidden", midi)

        fx = (ROOT / "context-src" / "v1" / "dsp" / "fx.md").read_text(encoding="utf-8")
        self.assertIn("do not collapse the wet path to identical left and right signals", fx)
        self.assertIn("wetL == wetR", fx)

    def test_ui_sources_require_one_parameter_marker_per_endpoint(self):
        for path in sorted((ROOT / "context-src" / "v1" / "ui").glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("exactly ONE DOM element with `data-param`", text)
                self.assertIn('querySelectorAll("[data-param]").length', text)
                self.assertIn("line 3", text)
                self.assertIn("After the two required receipt comments", text)
                self.assertIn("factory declaration comes before every class", text)
                self.assertIn("`view.patchConnection = patchConnection`", text)
                self.assertIn("unless the returned element received this assignment", text)
                self.assertIn(
                    "The next source declaration MUST be `export default function createPatchView (patchConnection)`",
                    text,
                )
                self.assertIn("Never use `ResizeObserver`", text)
                self.assertIn("ResizeObserver loop-delivery warnings as runtime errors", text)
                self.assertNotIn("or use a `ResizeObserver`", text)
                self.assertIn("literal bracket-balance check", text)
                self.assertIn("one for the method and one for the class", text)
                self.assertIn("Prefer a shorter complete UI", text)
                self.assertIn("under 10000 visible", text)
                self.assertIn("Generate repeated controls or pads from small data arrays", text)
                self.assertIn("Never spend the budget on", text)
                self.assertIn("must return an actual `HTMLElement` instance", text)
                self.assertIn("Never return a class or constructor", text)
                self.assertNotIn("## H) STRUCTURAL SCAFFOLD", text)
                self.assertNotIn("```javascript\n", text)
                self.assertIn("## H) FINAL CONSTRUCTION AND AUDIT", text)
                self.assertIn("declare exactly N data entries and render all N", text)
                self.assertIn("one-octave chromatic keyboard has at least 12", text)
                self.assertIn("N octaves have at least `12 * N` keys", text)
                self.assertIn('real `<button type="button">`', text)
                self.assertIn("Remove any unrequested generic dark-dashboard styling", text)

    def test_dsp_foundations_are_version_pinned_and_semantically_complete(self):
        shared = (ROOT / "context-src" / "v1" / "shared" / "core-dsp-foundations.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "Cmajor `1.0.3175`",
            "Never emit `skew`",
            "mid: 1000",
            "dBtoGain",
            "tpt::svf",
            "true Q",
            "PolyblepState",
            "proportional in pitch space",
            "sample-rate\nindependent",
            "equal-power",
        ):
            self.assertIn(required, shared)

        for variant in ("instrument", "fx"):
            composed = compose_source("dsp", variant)
            self.assertNotIn("{{CORE_DSP_FOUNDATIONS}}", composed)
            self.assertNotIn("{{HOST_TRANSPORT_CONTRACT}}", composed)
            self.assertIn("Cmajor `1.0.3175`", composed)
            self.assertIn("Never emit `skew`", composed)

        midi = compose_source("dsp", "midi")
        self.assertNotIn("{{HOST_TRANSPORT_CONTRACT}}", midi)
        self.assertIn("input event float transportIn;", midi)

        instrument = compose_source("dsp", "instrument")
        self.assertNotIn(
            "float cutoff = clamp (2000.0f + resonance * 4000.0f",
            instrument,
        )

    def test_ui_sources_define_the_same_mid_mapping_as_cmajor(self):
        for path in sorted((ROOT / "context-src" / "v1" / "ui").glob("*.md")):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("data-mid", text)
                self.assertIn("Math.log(0.5)", text)
                self.assertIn("Math.pow(norm, power)", text)
                self.assertIn("A dB parameter remains linear", text)

    def test_exact_sdk_semantic_fixture_set_is_complete(self):
        fixture_root = ROOT / "tests" / "fixtures" / "cmajor"
        fixtures = {path.name: path.read_text(encoding="utf-8") for path in fixture_root.glob("*.cmajor")}
        self.assertEqual(
            {"filter_gain.cmajor", "host_synced_drums.cmajor", "kick_drum.cmajor", "stereo_reverb_delay.cmajor", "subtractive_synth.cmajor", "tempo_synced_delay.cmajor"},
            set(fixtures),
        )
        self.assertTrue(all("[[ main ]]" in source for source in fixtures.values()))
        self.assertTrue(all("skew:" not in source for source in fixtures.values()))
        self.assertIn("mid: 1000.0", fixtures["filter_gain.cmajor"])
        self.assertIn("PolyblepState", fixtures["subtractive_synth.cmajor"])
        self.assertIn("pitchEnvelope", fixtures["kick_drum.cmajor"])
        self.assertIn("fraction", fixtures["stereo_reverb_delay.cmajor"])
        self.assertIn("input event float transportIn;", fixtures["host_synced_drums.cmajor"])
        self.assertIn("currentPpq = value;", fixtures["host_synced_drums.cmajor"])
        self.assertIn("value < currentPpq", fixtures["host_synced_drums.cmajor"])
        self.assertIn("value != hostBarStartPpq", fixtures["host_synced_drums.cmajor"])
        self.assertNotIn("std::timeline::", fixtures["host_synced_drums.cmajor"])
        self.assertIn('text: "1/16|1/8T|1/8|1/4T|1/4|1/2|1/1|1 bar"', fixtures["host_synced_drums.cmajor"])
        self.assertIn("currentPpq - hostBarStartPpq", fixtures["host_synced_drums.cmajor"])
        self.assertIn("lastStepIndex = -1", fixtures["host_synced_drums.cmajor"])
        self.assertIn("input event float transportIn;", fixtures["tempo_synced_delay.cmajor"])
        self.assertIn("text:", fixtures["tempo_synced_delay.cmajor"])
        self.assertIn("60.0f / max (20.0f, hostBpm)", fixtures["tempo_synced_delay.cmajor"])
        self.assertNotIn("delayTimeParam * 0.25f", fixtures["tempo_synced_delay.cmajor"])

    def test_transport_sync_runtime_gate_is_present(self):
        self.assertTrue((ROOT / "scripts" / "verify_cmajor_transport_sync.py").is_file())
        self.assertTrue((ROOT / "tests" / "cmajor_transport_sync_runner.cpp").is_file())


if __name__ == "__main__":
    unittest.main()
