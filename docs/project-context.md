# Project context and prototype scope

**Savonia - Responsible Forest Planning is Antti Kajanus's unfinished personal
learning prototype.** It is based on a real use case, limited understanding and
personal assumptions. Neither the prototype nor its results are official,
finalized, backed, endorsed or approved by Savonia.

Accepted decisions in [architecture](architecture/README.md) record choices
adopted within this prototype. They do not establish buyer acceptance.

This page explains the external use case and how it relates to the prototype.
Source details were checked on 23–26 October 2026; consult the original project
and procurement materials for current schedules and contractual terms.

## External use case

Savonia's forest-planning approach helps forest owners and decision-makers
compare management choices across economic, carbon, biodiversity, water and
recreation objectives. The aim is to help them weigh these goals when deciding
how their forests should be managed.

### Original municipal project

*Vastuullista metsäsuunnittelua kuntametsänomistajille* developed this approach
for municipal forest planning, using Siilinjärvi as a case. Its published
project period was **1 May 2024–30 April 2026**.
[Savonia project record](https://www.savonia.fi/tki-ja-palvelut/tutkimus-ja-kehittaminen/paattyneet-projektit-ja-hankkeet/?id=1960).

### Follow-on roadshow

*Vastuullisen metsänhoidon roadshow* was listed for
**1 April 2026–31 August 2027**. It aimed to bring the value-table approach to
**4–6 municipalities or parishes** through knowledge events, evidence
compilation, information for councils, dialogue and recommendations.
[Roadshow project record](https://hankkeet.savonia.fi/tutustu/kaynnissa-olevat-hankkeet/?id=2438).

### Planning method

A **value table (arvotaulukko)** compares alternative management pathways and
their modeled effects. The [method guide, pp. 4–9](https://laari.info/wp-content/uploads/2026/05/vastuullisen-metsasuunnittelun-opas.pdf)
describes six pathways and a planning process that combines:

- Spatial evidence about the forest and its surroundings.
- A separate calculation model based on simultaneous equations.
- Field validation.
- Dialogue with forest owners and the public.

Savonia's [method page](https://vastuullinenmetsasuunnittelu.savonia.fi/metsasuunnitelma/)
cautions that geospatial evidence can contain errors and needs on-site checking.
The [dataset catalogue](https://vastuullinenmetsasuunnittelu.savonia.fi/paikkatietoaineisto/)
identifies spatial datasets and their original providers. It is a catalogue of
sources, not one analysis-ready service.

### This prototype's role

The plugin prepares repeatable, traceable spatial evidence and sensitivity
classifications. Its workbook supplies forest inputs for the separate
value-table model; it is not a completed value table.

The prototype does not prescribe forest management, calculate scenario impacts,
establish legal rights or replace field assessment.
[ADR-0001](architecture/adr/0001-spatial-input-preparation-boundary.md) records
this boundary.

## Procurement reference and authority

The external reference is
[procurement 629864, Paikkatietotyökalu](https://tarjouspalvelu.fi/UX/TP/SiirryTarjouspyyntoon/?tpId=629864).
The available local sources are:

- [Tender report](references/procurement/629864/TarjouspyyntoRaportti629864.pdf).
- [Project description, Annex 1](references/procurement/629864/liite1_hankkeenkuvaus.pdf).
- [Procurement scope, Annex 2](references/procurement/629864/liite2_hankinnankohteenkuvaus.pdf).

Complete portal materials and clarifications require login. Consult the
authenticated portal for other attachments, buyer answers and contract terms.

### Requested tool and outputs

Annex 2 requests a repeatable QGIS tool that:

- Accepts an area boundary.
- Applies criteria supplied at the start of the work.
- Displays classified geography.
- Exports usable tables.

The requested summaries distinguish sensitive and economic areas and include
total, pine, spruce, birch and sawlog volumes; growth percentage; three age-band
shares; area; peat/natural-mire area; and average stumpage price.
Developing the separate calculation model is explicitly excluded.
[Annex 2](references/procurement/629864/liite2_hankinnankohteenkuvaus.pdf).

## Documentation precedence and interpretation

Use each maintained document for the information it owns:

| Information | Owner |
| --- | --- |
| Domain meanings | [Glossary](../GLOSSARY.md) |
| Current user goals and functional requirements | [User stories and specifications](specs/README.md) |
| Technical contracts and adopted design decisions | [Architecture index](architecture/README.md) |

Implementation status remains separate from acceptance.

### Adopted prototype scope

These choices describe this prototype. They do not change the original tender's
meaning or establish buyer acceptance:

- **Deciduous volume:** the prototype uses deciduous volume instead of the
  procurement-requested birch-specific volume.
  [ADR-0011](architecture/adr/0011-deciduous-volume-instead-of-birch.md).
- **Sawlog stumpage price:** the user supplies one sawlog unit price. This is
  narrower than a composition-dependent average for all timber or a full
  valuation. [ADR-0014](architecture/adr/0014-user-supplied-sawlog-price.md).
- **Calculated sawlog value:** the prototype also reports a sawlog euro amount,
  extending the earlier price-only scope. It remains distinct from whole-forest
  valuation and the separate model's scenario-income calculations.
  [ADR-0016](architecture/adr/0016-calculated-sawlog-value.md).

### Interpretation limits

Sensitivity classes, programme membership, active protection, predictive
candidates and scenario impacts refer to different concepts. Also keep these
measurements distinct:

- Grid age-area share and stand-count share.
- Deciduous volume and birch volume.
- Tree basal area and land area.

The glossary, [indicator design](architecture/indicators.md),
[data sources](architecture/data-sources.md) and
[deferred-source register](architecture/deferred-sources.md) retain their meanings
and evidence limits.
