# External-context hosting contract

The reviewed `public-context/` tree is the complete deployable artifact. Its
canonical candidate origin is the Artists in DSP GitHub Pages project at
`https://artists-in-dsp.github.io/amorph-for-agents` using the Pages workflow
in this repository.

## Release properties

- Every launcher URL addresses exactly one target/variant document under a
  never-reused release path: `/v1/<release>/<target>/<variant>.txt`.
- Once a release path has been used in an Amorph build or public evaluation,
  its bytes never change. Corrections require a new release path.
- The launcher URL and public manifest never contain `CONTEXT_ID` or
  `END_TOKEN` values. Those receipts occur only inside the complete document.
- Each response must be anonymous HTTP 200, UTF-8 `text/plain`, and byte-for-byte
  equal to the audited document hash. No authentication, cookie, script,
  secondary fetch, redirect, or partial-content step is required.
- `robots.txt` explicitly allows real-time retrieval. The production hostname
  must not inherit a proxy rule that returns 403 to chat-retrieval user agents.
- Unknown and truncated paths return HTTP 404; they must never fall back to a
  valid context document.

## Review and publication

The validation workflow runs on the pull request. The deployment workflow runs
only after a reviewed change reaches `main`, or when a reviewer deliberately
dispatches the exact candidate ref for a public pre-release evaluation.

GitHub Pages must use GitHub Actions with public access and HTTPS enforcement.
The candidate deliberately uses the project-domain origin: it requires no DNS
or Cloudflare configuration, and the versioned document path is the exact URL
tested by Amorph. A future custom domain is a separate migration that requires
fresh HTTP and unsigned-consumer evaluation before Amorph may use it.

Run `scripts/verify_http_endpoint.py` against the deployed candidate and save
its JSON output with the release evaluation evidence. Do not merge the Amorph
launcher until anonymous HTTP verification and ordinary unsigned-chat tests
both pass.
