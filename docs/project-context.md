# Project context and prototype scope

**Savonia - Responsible Forest Planning is Antti Kajanus's unfinished personal learning prototype.** It is based on a real use case, limited understanding and personal assumptions. Neither the prototype nor its results are official, finalized, backed, endorsed or approved by Savonia. The accepted decisions in [architecture](architecture/README.md) mean choices adopted within this prototype, not buyer acceptance.

This page explains the external use case and how it relates to the prototype.
Source details were checked on 23–26 October 2026; consult the original project
and procurement materials for current schedules and contractual terms.

## External use case

Savonia's *Vastuullista metsäsuunnittelua kuntametsänomistajille* project developed municipal forest planning that compares economic, carbon, biodiversity, water and recreation objectives. The published project period was 1 May 2024–30 April 2026, with Siilinjärvi as a case. The follow-on *Vastuullisen metsänhoidon roadshow* project was listed for 1 April 2026–31 August 2027 and aimed to transfer the value-table approach to 4–6 municipalities/parishes through knowledge events, evidence compilation, council information, dialogue and recommendations. [Earlier project record](https://www.savonia.fi/tki-ja-palvelut/tutkimus-ja-kehittaminen/paattyneet-projektit-ja-hankkeet/?id=1960), [Roadshow record](https://hankkeet.savonia.fi/tutustu/kaynnissa-olevat-hankkeet/?id=2438).

A value table compares management pathways and their modeled effects; the plugin's workbook supplies forest inputs rather than constituting the completed value table. The [method guide, pp. 4–9](https://laari.info/wp-content/uploads/2026/05/vastuullisen-metsasuunnittelun-opas.pdf) describes six pathways, spatial evidence, a separate simultaneous-equation model, field validation and owner/public dialogue. Savonia's [method page](https://vastuullinenmetsasuunnittelu.savonia.fi/metsasuunnitelma/) cautions that geospatial evidence can contain errors and needs on-site checking. Its [dataset catalogue](https://vastuullinenmetsasuunnittelu.savonia.fi/paikkatietoaineisto/) identifies original providers; it is not one analysis-ready service.

The tool's architectural boundary therefore ends at repeatable, traceable evidence preparation and sensitivity classification. It does not prescribe management, calculate scenario impacts, establish legal rights or replace field assessment. [ADR-0001](architecture/adr/0001-spatial-input-preparation-boundary.md).

## Procurement reference and authority

The external reference is [procurement 629864, Paikkatietotyökalu](https://tarjouspalvelu.fi/UX/TP/SiirryTarjouspyyntoon/?tpId=629864). Complete portal materials and clarifications require login. Available local sources are the [tender report](bid/TarjouspyyntoRaportti629864.pdf), [procurement scope, Annex 2](bid/liite2_hankinnankohteenkuvaus.pdf), and [project description, Annex 1](bid/liite1_hankkeenkuvaus.pdf). Consult the authenticated portal for other attachments, buyer answers and contract terms.

Annex 2 requests a repeatable QGIS tool accepting an area boundary, applying criteria supplied at work commencement, displaying classified geography, and exporting usable tables. It requests total/pine/spruce/birch and sawlog volumes, growth percentage, three age-band shares, area, peat/natural-mire area and average stumpage price separately for sensitive/economic areas. It explicitly excludes developing the separate calculation model. The notice specified delivery by 28 February 2027. These are source requirements and context, not a statement that this prototype fulfills them. [Annex 2](bid/liite2_hankinnankohteenkuvaus.pdf), [tender report](bid/TarjouspyyntoRaportti629864.pdf).

## Documentation precedence and interpretation

Use [GLOSSARY.md](../GLOSSARY.md) for domain meanings, the maintained [user stories and functional specifications](specs/README.md) for current product behavior, and the [architecture index](architecture/README.md) for technical contracts and adopted design decisions.

The [maintained specifications](specs/README.md) record current requirements and
[open discrepancies and verification](architecture/open-questions.md), with
implementation status kept separate from acceptance.

Sensitivity classes, programme membership, active protection, predictive candidates and scenario impacts remain distinct. Grid age-area share is not stand-count share; deciduous volume is not birch volume; tree basal area is not land area. [ADR-0011](architecture/adr/0011-deciduous-volume-instead-of-birch.md) deliberately changes the adopted product requirement to use deciduous volume instead of supporting procurement-requested birch-specific volume. This resolves the prototype's scope choice without changing the original tender's meaning or establishing buyer acceptance. Procurement-requested stumpage price remains excluded. These meanings and their evidence limits survive in the glossary, [indicator design](architecture/indicators.md), [data sources](architecture/data-sources.md), and [deferred-source register](architecture/deferred-sources.md).
