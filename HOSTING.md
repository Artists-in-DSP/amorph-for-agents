# External-context hosting contract

The reviewed `public-context/` tree is the complete deployable artifact. It is
intended for GitHub Pages at `https://context.artistsindsp.com` using the Pages
workflow in this repository.

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

Before the first deployment, configure GitHub Pages to use GitHub Actions and
add `context.artistsindsp.com` as the repository custom domain. In the existing
Cloudflare-managed `artistsindsp.com` zone, create the GitHub Pages CNAME as
DNS-only so the zone's current AI-bot blocking policy cannot replace the
endpoint response. Enable HTTPS in GitHub Pages after DNS verification.

Run `scripts/verify_http_endpoint.py` against the deployed candidate and save
its JSON output with the release evaluation evidence. Do not merge the Amorph
launcher until anonymous HTTP verification and ordinary unsigned-chat tests
both pass.
