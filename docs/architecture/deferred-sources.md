# Deferred sources and unadopted alternatives

These candidate sources are outside the implemented scope except where the current specs explicitly adopt a limited product. The adopted Ranta10 30 m riparian buffer is described in [CL-02](../specs/classification.md#cl-02-six-cumulative-tiers); other SYKE water-protection sources and rules remain deferred. The remaining exclusions are recorded in [ADR-0004](adr/0004-stand-based-sensitivity-classification.md). Verify access, licensing, schema, dates and coverage before adopting a candidate, and define its purpose, denominator and rule.
[ADR-0004](adr/0004-stand-based-sensitivity-classification.md). Verify access,
licensing, schema, dates and coverage before adopting a candidate, and define
its purpose, denominator and rule.

## Potential protected sites

External candidate-site datasets remain deferred. The included
[stand-age screen](../specs/classification.md#cl-02-six-cumulative-tiers)
uses the existing stand source; it does not activate any external dataset or
establish legal protection.

Candidate screening, established protected sites, programme membership and mapped Section 10 habitats are distinct. Existing protected/programme/habitat records must not be counted again as a new potential-site layer. Screening scores do not establish legal protection or exact habitat boundaries.

| Candidate | Source evidence | Decision still needed |
| --- | --- | --- |
| SYKE high biodiversity value forests 2018, Zonation | [Dataset](https://luontotieto.syke.fi/en/aineisto/monimuotoisuudelle-tarkeat-metsaalueet-high-biodiversity-value-forests-2018-zonation-fin-eng-swe-2/) describes 12 national/regional prioritization rasters, 96 × 96 m cells and forest coverage excluding Åland. Higher values indicate higher priority. [Services](https://www.syke.fi/fi/ymparistotieto/avoimet-rajapinnat/paikkatietorajapinnat), [Zonation overview](https://www.syke.fi/fi/ymparistotieto/laskurit-ja-tyokalut/zonation). | Choose analysis/version, score semantics, threshold, no-data policy and whether it is a review flag or a Protection-tier trigger. Verify access to newer products; an open nationwide 2024 replacement remains unverified. |
| Potential flood forests / wooded flood meadows 2023 | [SYKE product/resources](https://luontotieto.syke.fi/aineisto/potentiaalisen-tulvametsan-tai-metsaluhdan-esiintymistodennakoisyys-2023/) describes a habitat-specific predictive product, with a 0.25 ha mapping unit. | Verify operational schema, access, prediction threshold and resolution. This is not a general protected-site mask. |
| Natural and old forest inventory-support data | [SYKE project](https://www.syke.fi/fi/projektit/luonnontilaiset-ja-vanhat-metsat-eun-bd-strategian-maaritelman-paikkatietoaineistojen-ja) describes support data from the 2021–2023 project. | An operational open layer/schema remains unverified; check permitted use, date, coverage and delivery. |

A policy discussion could inspect score distributions in representative AOIs, retain score/version provenance and compare candidate flags with existing evidence. No threshold or sensitivity rule has been selected for these external candidates.

## Taajamametsät, planning boundaries and MY

Urban structure, plan extent, recreation use and an actual MY plan designation have different meanings. A plan's outer boundary cannot establish its internal zoning; a YKR boundary does not establish recreational use, access or forest quality. No national urban-forest threshold or MY integration has been adopted.

| Candidate | Source evidence | Open choice / limitation |
| --- | --- | --- |
| YKR-taajamat | [Metadata](https://ckan.ymparisto.fi/dataset/ykr-taajama) defines built-up settlement structure using 250 m cells and a 200-resident minimum; large internal forest/open areas may be excluded. [Downloads](https://www.syke.fi/fi/ymparistotieto/ladattavat-paikkatietoaineistot). | Define whether “urban forest” means within built-up structure or includes nearby forests. Pin year and overlap-share threshold rather than silently forcing boundary stands to yes/no. |
| Harva ja tiheä taajama-alue | [Metadata](https://ckan.ymparisto.fi/dataset/harva-ja-tihea-taajama-alue) separates dense/sparse settlement structure. | Could distinguish core/periphery; not a legally effective plan boundary or an adopted sensitivity criterion. |
| Asemakaavoitettu alue | [Metadata](https://ckan.ymparisto.fi/dataset/asemakaavoitettu-alue) describes municipal detailed-plan outer extents, not individual designations; excludes shore detailed plans and Åland. | Useful as a separate planning-context measure. It may contain unbuilt forests/water and cannot identify MY. Verify selected annual version and geometry. |
| SYKE general-plan service | [Service/terms](https://www.syke.fi/fi/ymparistotieto/kartta-ja-tietopalvelut/elinympariston-tietopalvelu-liiteri/yleiskaavapalvelu), [metadata](https://ckan.ymparisto.fi/dataset/yleiskaavapalvelun-aineistot) describe extent vectors/map images, contract/cost conditions, overlaps and temporal/legal-effect caveats. | Verify coverage, terms and charges. Obtain actual designation geometries and plan provisions if interpreting MY. |
| Ryhti / VOOKA and municipal services | [Ryhti consumer services](https://ryhti.syke.fi/palvelut/palvelut-tiedon-hyodyntajille/), [API guidance](https://ryhti.syke.fi/palvelut/ohjeet-ryhti-jarjestelman-avoimien-rajapintojen-kayttoon/), [VOOKA](https://www.syke.fi/fi/projektit/vooka), [existing plans](https://ryhti.syke.fi/alueidenkaytto/voimassa-olevat-kaavat-tietojarjestelmaan/). These references do not establish complete national coverage. | Verify actual current coverage; municipal data may be needed. Normalize designations, dates, legal effect and reuse terms per source. |

A future design can compare YKR and detailed-plan extents as separate contextual
shares. Their role in classification requires an explicit decision.

## Indicator alternatives

Birch-specific volume is excluded by [ADR-0011](adr/0011-deciduous-volume-instead-of-birch.md), which adopts deciduous volume instead. The retained birch-source evidence below is background for any future scope reconsideration, not pending work to fulfill the adopted indicator requirements.

| Candidate | Retained source evidence | Decisions required before use |
| --- | --- | --- |
| Current-state stand GeoPackage strata | [Metsäkeskus model](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-tietomallikaavio-mv_ey_2-1-3-metsakeskuksen-tietomallin-uudistus.xlsx), [content guide](https://www.metsakeskus.fi/sites/default/files/document/tiedosto-geopackage-sisaltoohjeet-tietomalli-2-0.pdf), [species codes](https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/metsarek/codeschemes/paapuulaji-v_1_0/codes). Related stand → treestand → treestratum records include species, volume, sawlog/pulpwood and growth. | A local adapter and record selection are needed. Choose inventory/current/forecast class and date; avoid combining all-storey summaries with component strata. Birch requires explicit codes 3/4 and a decision about 27; unspecified deciduous 9/29 is not birch. |
| Luke 2023 multi-source forest inventory rasters | [Readme](https://kartta.luke.fi/LUETAMA-2023.txt), [publisher](https://kartta.luke.fi/). The checked product has 16 m birch and assortment themes; a required annual-growth layer remains unverified. | Inspect actual band masks: source descriptions disagree on no-data `32757` versus `32767`, with `32766` also missing. Choose a coherent product or disclose mixed-source dates/reconciliation. Do not silently fill Metsäkeskus birch from a different model. |
| SYKE peat/drainage raster | [Dataset](https://ckan.ymparisto.fi/dataset/soiden-ja-kivennaismaiden-ojitustilanne), [technical caveats](https://geoportal.ymparisto.fi/meta/julkinen/dokumentit/Soiden_ja_kivenn%C3%A4ismaiden_ojitustilanne.pdf). The checked 2025 product has 10 m undrained/drained peat classes 20/21 and extraction class 23. | Define whether extraction land and open mires count, domain/denominator, date and classification uncertainty. Source corrections mean version changes are not necessarily real drainage change. |
| GTK site types and naturalness | [Site-type metadata](https://ckan.ymparisto.fi/dataset/suotyypit-ja-turvekankaat), [production explanation](https://www.gtk.fi/ajankohtaista/ensimmainen-suotyyppien-paikkatietoaineisto-kattaa-koko-suomen-suot-ja-turvemaat/), [naturalness methodology](https://gtkdata.gtk.fi/turvevarojen_tilinpito/luonnontilaisuusluokat.html), [survey metadata](https://tupa.gtk.fi/paikkatieto/meta/turvevarojen_tilinpitotiedot.html). | Regional modeled site types and mire-complex naturalness are not interchangeable with grid soil/drainage or site certification. Agree assessment scale, coverage and ecological meaning; an undrained pixel is not necessarily a natural mire. |
| Luke stumpage prices | [Monthly table](https://statdb.luke.fi/PxWeb/pxweb/fi/LUKE/LUKE__met__teokau__kk/0100_teokau.px/), [statistical documentation](https://www.luke.fi/fi/tilastot/teollisuuspuun-kauppa/teollisuuspuun-kauppa-tilaston-dokumentaatio). | External price retrieval remains excluded; the adopted [user-supplied sawlog assumption](adr/0014-user-supplied-sawlog-price.md) is separate. A future proxy needs a pinned period/region, harvest method, species/assortment quantities and priced-volume coverage. Use relevant `sum(quantity × price) / sum(quantity)` weights; purchase-weighted stumpage is not roadside price, a stand's contract price or an income forecast. |

The implemented [indicator design](indicators.md) defines current behavior. A different growth aggregation, whole-AOI mire domain, raster mode or local-source workflow requires a new explicit decision and specification.
