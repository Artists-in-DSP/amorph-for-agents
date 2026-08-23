# Amorph external Copy/Paste context v1

These six editable source documents are the knowledge source for Amorph's
external Copy Prompt flow. They are the canonical full Cmajor/UI rules corpus.
Amorph may still add relevant local evidence (preset and community examples,
session history, manifest, current DSP/UI code, diagnostics, and parameter
facts) plus compact paste-format and host-wiring reminders.

`scripts/build_external_context.py` wraps each source with the retrieval and
response contract, derives document-only receipt values, and writes the public
plain-text artifacts under `public-context/`.

Contract invariants:

- one self-contained document for each `dsp|ui` × `instrument|fx|midi` pair;
- no required secondary URL, authentication, cookie, script, or asset;
- a visible first-line marker, `CONTEXT_ID`, and tail `END_TOKEN`;
- receipt values are absent from the launcher URL and launcher text;
- exactly one `BEGIN_AMORPH_CONTEXT` and one `END_AMORPH_CONTEXT` marker;
- the linked document owns the complete language, wiring, safety, and response
  rules; compact high-value reminders in Amorph must remain consistent with it;
- Amorph retains Leo's layered local-context design and does not embed a second
  copy of the full static rules corpus.

Edit these sources directly. Do not edit generated files in `public-context/`.
