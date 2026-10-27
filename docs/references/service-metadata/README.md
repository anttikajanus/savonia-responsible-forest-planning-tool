# Cached service metadata

Saved source descriptions and provider model documents support the
[source contracts](../../architecture/data-sources.md).
The decision to download these references locally and keep them out of Git is
recorded in [ADR-0012](../../architecture/adr/0012-local-reference-downloads.md).

Download the reference set once from the repository root with Python 3.10+:

```powershell
python scripts/download_references.py
```

With the installed QGIS Python on Windows, use its configured launcher instead:

```powershell
& 'C:\Program Files\QGIS 4.2.3\bin\python-qgis.bat' scripts/download_references.py
```

Only Python's standard library is required. Downloads go to
`docs/references/service-metadata/`. The script resolves this directory relative
to its own location, so its working directory does not change the destination.
The [manifest](manifest.json) owns the exact source URLs and local filenames.
Downloaded XML, XSD, PDFs, XLSX workbooks and `retrievals.json` are ignored by Git;
only this README and the manifest are versioned in this directory.

Useful options (use the same Python launcher as above):

```powershell
python scripts/download_references.py --list
python scripts/download_references.py --refresh
python scripts/download_references.py --only syke/groundwater/
python scripts/download_references.py --refresh --only metsakeskus/grid/
```

`--list` is offline. Normal runs reuse files whose formats validate and make no
requests for them. Missing or invalid files are downloaded; `--refresh` explicitly
replaces valid files too. `--only` selects a local path prefix from the manifest.
Requests use a 45-second socket timeout and up to two retries for transient
network/HTTP errors; `--timeout` and `--retries` override those defaults.

For sustained SYKE application use, supply the provider-issued identifier in
`$env:SYKE_USER_ID` before running. The script adds it only to SYKE WFS requests
and omits it from progress output and recorded URLs. See the
[provider guidance](https://www.syke.fi/fi/ymparistotieto/avoimet-rajapinnat/paikkatietorajapinnat).
Service-generated XML can itself include request URLs; the entire cache stays
local and should be reviewed before sharing.

## Reading and provenance

Agents and maintainers should inspect these local artifacts before fetching the
same provider material again. If the cache is missing, run the downloader; if it
is present, read it directly. These are development references, separate from
the plugin's online feature-data retrieval.

Each completed download records its public URL, UTC retrieval timestamp, byte
count and SHA-256 in `retrievals.json`. Reused files without retrieval metadata
keep their capture dates unspecified.
Provider document dates, forest observation dates and retrieval dates are distinct.
Cached evidence describes the services at capture time; it does not guarantee their current state.

Validation checks XML root/namespace, PDF header/end marker and XLSX archive
integrity. It rejects HTTP-200 WFS exception reports and HTML error pages.
Files are replaced atomically after validation. A failed download preserves an
existing copy, reports the failed path and allows other downloads to continue;
the final exit status is nonzero if anything failed. Retry the reported prefix
when access is restored. An interrupted run retains completed downloads.

The script saves the requested schemas, without recursively mirroring imported
OGC schemas. It downloads no feature records. File-format validation does not
verify field meanings, representative values, coverage or the age of a provider
document. Keep those limits in mind when reading the dictionaries below.

Saved WFS service descriptions are grouped by provider and service. Filenames
use lowercase kebab case. Each service uses `get-capabilities.xml`; its schema
response uses `describe-feature-type.xsd`, with a feature-type qualifier when
the service has multiple schemas in this reference set.

## Metsäkeskus

- [Version 2.1.3 model workbook](metsakeskus/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx).
  Its required **MV GeoServer** and **EY GeoServer** sheets describe layer
  fields, units, and Suomi.fi code-set references. The separate GeoServer
  sheets are the relevant model definitions for the WFS properties below.
- Forest stands, feature type `v2:stand`: [GetCapabilities](metsakeskus/stands/get-capabilities.xml) · [DescribeFeatureType](metsakeskus/stands/describe-feature-type.xsd)
- Habitats, feature type `v2:habitat`: [GetCapabilities](metsakeskus/habitats/get-capabilities.xml) · [DescribeFeatureType](metsakeskus/habitats/describe-feature-type.xsd)
- Inventory grid, feature type `v2:gridcell`: [GetCapabilities](metsakeskus/grid/get-capabilities.xml) · [DescribeFeatureType](metsakeskus/grid/describe-feature-type.xsd)
- [Forest stand product description](metsakeskus/stands/tietotuotekuvaus-metsavarakuviot.pdf).
- [Grid product description](metsakeskus/grid/tietotuotekuvaus-hila-aineisto.pdf) and [grid dictionary](metsakeskus/grid/hila-koodisto-ja-tietokantakuvaus.xlsx).
- [GeoPackage content guide](metsakeskus/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf); broader than the WFS schema.

## SYKE

- Protected sites: [GetCapabilities](syke/protected-sites/get-capabilities.xml)
  · state-owned [DescribeFeatureType](syke/protected-sites/state-owned-conservation-area.xsd)
  · private-land [DescribeFeatureType](syke/protected-sites/private-land-conservation-area.xsd)
  · wilderness [DescribeFeatureType](syke/protected-sites/wilderness-area.xsd)
  · [protected/wilderness dictionary](syke/protected-sites/luonnonsuojelu-ja-eramaa-alueet.pdf).
- Conservation programme areas, feature type
  `syke_luonnonsuojeluohjelma_alueet:Luonnonsuojeluohjelmaalueet`:
  [GetCapabilities](syke/conservation-programme-areas/get-capabilities.xml)
  · [DescribeFeatureType](syke/conservation-programme-areas/describe-feature-type.xsd)
  · [dictionary](syke/conservation-programme-areas/luonnonsuojeluohjelma-alueet.pdf).
- Groundwater, feature type `syke_vhspohjavesi:VHS2022_Pohjavesi`:
  [GetCapabilities](syke/groundwater/get-capabilities.xml)
  · [DescribeFeatureType](syke/groundwater/describe-feature-type.xsd)
  · [general groundwater dictionary](syke/groundwater/pohjavesialueet.pdf).

The files are retained as source evidence. The XSDs describe field names and
types; they do not contain representative feature values.

The manifest covers six services, eight layer schemas and eight provider
documents (22 files). The provider documents complement the service schemas.
See [provider evidence gaps](../../architecture/open-questions.md#provider-evidence)
for the value, interpretation and completeness checks still needed.

The maintained interpretation and verification limits are in
[architecture/data-sources.md](../../architecture/data-sources.md).
Regenerate this local evidence with the script when preparing a fresh checkout.
