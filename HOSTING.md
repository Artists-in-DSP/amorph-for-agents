# External-context hosting contract

The reviewed `public-context/` tree is the complete deployable artifact. Its
canonical candidate origin is the Artists in DSP GitHub Pages project at
`https://artists-in-dsp.github.io/amorph-for-agents` using the Pages workflow
in this repository.

## Release properties

- Every model-facing URL addresses exactly one target/variant static HTML page:
  `/v1/<release>/<target>/<variant>.html` for immutable candidates and
  `/v1/stable/<target>/<variant>.html` for the promoted compatible channel.
- Once a release path has been used in an Amorph build or public evaluation,
  its bytes never change. Corrections require a new release path.
- Stable changes must originate from `scripts/promote_external_context.py`,
  which copies the exact audited visible text into both an immutable archive
  and the stable channel. Re-running a promotion is deterministic; rollback is
  promotion of an earlier compatible v1 release.
- The launcher URL and public manifest never contain `CONTEXT_ID` or
  `END_TOKEN` values. Those receipts occur only inside the complete document.
- Each model-facing response must be anonymous HTTP 200 UTF-8 `text/html`. The
  complete canonical document must be present in the initial response inside
  the single `<pre id="amorph-context">`; its parsed text must equal the paired
  audit artifact and manifest hash. No authentication, cookie, JavaScript,
  secondary fetch, redirect, or partial-content step is required.
- The index is crawlable and links every HTML page; `sitemap.xml` lists the
  same pages, and `llms.txt` provides optional discovery metadata. `robots.txt`
  explicitly allows real-time retrieval. The production hostname
  must not inherit a proxy rule that returns 403 to chat-retrieval user agents.
- Unknown and truncated paths return HTTP 404; they must never fall back to a
  valid context document.

## Review and publication

The validation workflow runs on pull requests. A dedicated preview branch may
deploy a new immutable preview path without changing `/v1/stable`. Stable is
updated only by a separate reviewed promotion after the provider gate report.

GitHub Pages must use GitHub Actions with public access and HTTPS enforcement.
The candidate deliberately uses the project-domain origin: it requires no DNS
or Cloudflare configuration, and the versioned document path is the exact URL
tested by Amorph. A future custom domain is a separate migration that requires
fresh HTTP and unsigned-consumer evaluation before Amorph may use it.

Run `scripts/verify_http_endpoint.py` against the deployed candidate and save
its JSON output with the release evidence. Require exact receipt retrieval in
fresh ChatGPT, Gemini, Claude, Perplexity, Copilot, and Scira chats before
promotion. Do not merge the Amorph launcher until anonymous HTTP verification,
the named provider gate, real Copy Prompt parity, and compile/UI evaluation all
pass.
