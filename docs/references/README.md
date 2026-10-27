# External reference material

This directory holds original external sources. Maintained prototype behavior
belongs in [specifications](../specs/README.md), and adopted interpretations and
technical contracts belong in [architecture](../architecture/README.md).

## Procurement and project context

The original materials for procurement 629864 are versioned in
`procurement/629864/`:

- [Tender report](procurement/629864/TarjouspyyntoRaportti629864.pdf)
- [Project description, Annex 1](procurement/629864/liite1_hankkeenkuvaus.pdf)
- [Procurement scope, Annex 2](procurement/629864/liite2_hankinnankohteenkuvaus.pdf)

[Project context](../project-context.md#procurement-reference-and-authority)
explains their authority, portal access limits and relationship to this personal
prototype. These source requirements remain distinct from adopted requirements
and buyer acceptance.

## Provider services and layers

[Service metadata](service-metadata/README.md) contains cached WFS capabilities,
layer schemas, provider dictionaries and model documents, grouped by provider
and service. Its README and manifest are versioned; downloaded artifacts and
retrieval metadata are ignored by Git. Follow its instructions to populate or
explicitly refresh the cache with `scripts/download_references.py`.

Cached evidence describes provider material at capture time. Retrieval dates
do not establish live service state, valid feature values or complete coverage.
