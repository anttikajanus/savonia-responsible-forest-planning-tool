# Download provider references into an ignored local cache

Status: accepted

Recorded: 2026-10-26

Layout updated: 2026-10-27. Provider evidence lives under
`docs/references/service-metadata/`; the existing procurement PDFs remain
versioned under `docs/references/procurement/629864/`. The
[reference index](../../references/README.md) separates these source categories.

Provider schemas, service descriptions and model documents are needed for
development and interpretation. Use
[`scripts/download_references.py`](../../../scripts/download_references.py) to
populate `docs/references/service-metadata/` from the versioned
[manifest](../../references/service-metadata/manifest.json). Keep the downloader, manifest and
[reference instructions](../../references/service-metadata/README.md) in Git; do not check in
downloaded XML, XSD, PDF or XLSX files, or the generated `retrievals.json`.
The repository's [ignore rules](../../../.gitignore) enforce this boundary.

This keeps provider material out of repository history while giving maintainers
one shared acquisition process and source list. Compared with committing
reference snapshots, it avoids accumulating external documents and changing
service responses in Git. Service-generated XML may also contain request URLs
with provider identifiers; keeping the cache local avoids publishing those
responses through routine commits.

Read existing cached files before making new requests. Populate missing or
invalid files with the downloader and use `--refresh` when an explicit refresh
is needed. The reference instructions own the commands, validation, failure
handling and provenance details. Download records retain retrieval timestamps,
byte counts and SHA-256 hashes locally; maintained documentation must preserve
the evidence dates and interpretation limits needed without that cache.

The trade-off is that a fresh checkout needs provider access to populate its
references. Upstream URLs and contents can change, so the manifest alone cannot
reproduce the exact bytes of an earlier retrieval, and local hashes do not
archive those bytes. The cache supports development evidence; it is separate
from the plugin's feature-data retrieval and does not establish provider-field
semantics, representative values or geographic completeness. This decision
records the existing reference workflow without changing plugin behavior.
