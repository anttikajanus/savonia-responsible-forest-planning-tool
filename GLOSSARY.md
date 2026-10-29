# Savonia - Responsible Forest Planning

Shared language for this unfinished personal learning prototype's interpretation of forest-planning evidence and management scenarios; these definitions do not establish Savonia's approval or accepted requirements. [Project context](docs/project-context.md) explains the external use case and prototype scope; [architecture](docs/architecture/README.md) records technical decisions and evidence.

## Project identity

**Savonia - Responsible Forest Planning (Savonia - Vastuullinen metsäsuunnittelu)**:
The English and Finnish names of Antti Kajanus's personal forest-planning prototype.
The names identify the same project and do not imply Savonia's endorsement or approval.

## Planning and model boundaries

**Forest-management scenario (management pathway; metsänkäsittelypolku)**:
A proposed approach to managing a forest whose consequences can be compared with other approaches. A scenario includes management assumptions beyond the plugin's spatial sensitivity classification.
_Avoid_: sensitivity class as a synonym for scenario

**Value table (arvotaulukko)**:
A decision-support comparison of a forest owner's assets and alternative management pathways across economic, carbon, biodiversity, water, and recreation effects. The plugin's forest-input summaries contribute evidence to this comparison rather than constituting the completed value table.

**Value-table model**:
The separately developed calculation model that uses forest inputs and management assumptions to evaluate management pathways. The procurement describes its calculation component as a simultaneous-equation model, separate from the tool that prepares and classifies forest evidence.
_Avoid_: plugin impact calculator

**Scenario impact**:
A consequence of a forest-management scenario evaluated by the value-table model. A sensitivity class or forest indicator is an input to that evaluation, rather than an impact estimate.

**Sensitivity tier**:
One of six cumulative sets of criteria used to classify the same analyzed forest: All out, BAU, Light, Balance, Protection, and Superprotection. A tier defines spatial sensitivity assumptions for scenario comparison, without prescribing management or determining legal harvesting rights.
_Avoid_: protection status, management prescription

## Analysis area and forest units

**Analysis area (AOI)**:
The geographic boundary selected for an analysis, whether drawn, taken from existing polygons, or captured from the map extent. It can include land outside the forest stands represented in the results.
_Avoid_: analyzed forest as a synonym for AOI

**Forest stand (kuvio)**:
A source forest-management polygon with stand-level forest attributes. It remains the parent unit of result polygons even when clipping and sensitivity boundaries divide it into several pieces.
_Avoid_: grid cell, result polygon as synonyms for stand

**Inventory grid cell (hila)**:
A source forest-inventory polygon carrying local estimates of tree volume, mean age, soil type, and drainage state. Only its intersected area contributes to a result polygon's grid indicators; it does not define a new sensitivity boundary.

**Classified forest polygon**:
A piece of a source stand within the analysis area, divided at relevant sensitivity-criterion boundaries and carrying a classification for every tier. Its indicators describe that piece, with their own evidence coverage.
_Avoid_: result grid cell, whole stand when referring to a split piece

**Analyzed forest**:
The forest area represented by the classified forest polygons. Land outside those polygons, including open mires outside the source stands, is outside this reporting domain.
_Avoid_: whole-AOI forest coverage

**Reporting area**:
The land area to which an indicator or summary refers: a classified polygon or a tier/class group within analyzed forest. It is distinct from the smaller area that may have valid evidence for a particular metric.

**Land area (maapinta-ala)**:
The ground area of the actual classified polygon, expressed in hectares. It is independent of tree basal area and indicator availability.
_Avoid_: basal area as a synonym for land area

## Sensitivity evidence

**Sensitivity criterion**:
A mapped condition used by one or more tiers to identify sensitive forest. Its inclusion is a planning rule, not by itself a finding of legal protection.
_Avoid_: legal prohibition as a synonym for criterion

**Criterion match**:
A qualifying overlap between forest and mapped sensitivity evidence. In the agreed classification, an overlap must exceed one square metre; smaller overlaps and boundary-only contact do not qualify.
_Avoid_: proximity match, buffer match

**Forest Act Section 10 habitat (metsälain 10 §:n elinympäristö)**:
A mapped habitat interpreted from Metsäkeskus's Section 10 categories, including the category requiring corrective measures. This is the habitat evidence used for stand-wide promotion, rather than a determination that the entire stand is legally a Section 10 habitat.

**Section 10 stand-wide promotion**:
The conservative planning assumption that a qualifying Section 10 habitat overlap with an AOI-clipped source stand makes every result polygon from that stand sensitive in tiers containing the criterion. The promoted area can therefore extend beyond the mapped habitat footprint.
_Avoid_: whole-stand legal protection

**Active protected area**:
A mapped SYKE conservation or wilderness area with a recognized category and an active status. It is distinct from a conservation programme area or a potentially suitable protection site.

**Nature conservation programme area (luonnonsuojeluohjelma-alue)**:
A mapped area belonging to a recognized nature conservation programme. Programme membership is sensitivity evidence for Balance and higher tiers, without proving that protection has been legally established.
_Avoid_: established protected area

**Other valuable habitat (muu arvokas elinympäristö)**:
A mapped Metsäkeskus habitat in the other-valuable-habitat category, distinct from its Section 10 categories. It adds sensitivity evidence in Protection and Superprotection.

**Groundwater area (pohjavesialue)**:
A mapped SYKE groundwater-area footprint used as sensitivity evidence in Balance and higher tiers. Its planning interpretation includes the returned footprints without filtering by groundwater class or subtype.

**Potential protected site (potentiaalinen suojelukohde)**:
An area identified as potentially suitable for protection, rather than evidence of an established protected area or a conservation programme designation. It is excluded from the agreed sensitivity criteria.

**Context layer**:
Geographic information provided for map interpretation without contributing sensitivity evidence. Shoreline context and basemaps do not create criterion matches.

## Tiers and classifications

**All out (Kaikki pois)**:
The tier whose sensitivity criteria are active protected areas and Section 10 stand-wide promotion. Its current spatial criteria are shared by BAU and Light.

**BAU (business as usual)**:
The baseline management scenario and its corresponding sensitivity tier. The tier shares All out's current spatial criteria; this does not make the management scenarios identical.

**Light (Kevyt)**:
The sensitivity tier between BAU and Balance. Its current criteria are the same as All out and BAU, with no additional mapped trigger.

**Balance (Tasapaino)**:
The tier that adds nature conservation programme areas and groundwater areas to the All out / BAU / Light criteria.

**Protection (Suojelu)**:
The tier that adds other valuable habitats to the Balance criteria. Its name denotes a planning tier, rather than legal protection status.

**Superprotection (Tehostettu suojelu)**:
The tier that includes the Protection criteria and treats all remaining analyzed forest as sensitive when the required evidence is available.

**Sensitive classification (Herkkä)**:
A tier-specific classification supported by a qualifying criterion match, or by Superprotection's remaining-forest rule. It expresses a planning sensitivity assumption rather than a harvesting prohibition.
_Avoid_: legally unharvestable, protected forest as synonyms for sensitive

**Economic classification (Taloudellinen)**:
A tier-specific classification for forest with no qualifying sensitivity match when the evidence required by that tier is available. It does not establish profitability, legal harvesting permission, or the absence of unmapped constraints.
_Avoid_: unrestricted forest, profitable forest, economic by default

**Unknown classification (Tuntematon)**:
A data-quality state in which the available evidence cannot establish a tier classification. It is neither a third forest type nor an economic assumption.
_Avoid_: zero sensitivity, out of scope

**Tier/class group**:
The classified forest polygons sharing one sensitivity tier and one class, used together for reporting. Each tier describes the same analyzed forest, so areas from different tiers are alternative classifications rather than additional land.

## Evidence readiness and coverage

**Source schema readiness**:
Whether a source contains the attributes required for its agreed interpretation. Readiness does not establish that individual values are usable or that the source covers the entire reporting area.
_Avoid_: schema availability

**Source availability**:
Whether an in-scope source was usable and its requested evidence was successfully retrieved. A successful response containing no mapped features can be available without establishing complete geographic coverage.
_Avoid_: complete coverage as a synonym for availability

**Source coverage**:
The account of source availability, returned evidence, and retrieval limitations for an analysis. Returned feature counts and overlaps describe observed evidence rather than authoritative boundaries of the provider's data coverage.

**Metric coverage**:
The portion of the reporting area with valid evidence for a particular indicator, together with the portion whose value is unknown. Coverage belongs to each metric independently, even when metrics share a source.
_Avoid_: source availability as proof of complete metric coverage

**Valid area / unknown area**:
The reporting hectares with usable evidence / without usable evidence for a particular metric. Missing spatial coverage and missing or invalid values contribute unknown area rather than known zero.

**Partial indicator**:
An indicator with some usable evidence and some unknown reporting area. A partial density or age share describes its valid area; a partial peatland or natural-mire observation is a lower bound rather than a complete area total.

**Known zero**:
A valid observation of zero, or a complete known classification with no matching area. It is distinct from missing evidence and from a small positive quantity rounded to zero for reporting.
_Avoid_: blank means zero

**Out of scope**:
A criterion or metric intentionally excluded from the agreed analysis. Its exclusion is a scope decision rather than evidence failure or proof of absence.
_Avoid_: unavailable, unknown as synonyms for out of scope

## Forest indicators

**Forest indicator**:
A descriptive quantity about the analyzed forest, such as volume density, growth, age-area share, or source-classified land area. An indicator does not become a sensitivity criterion merely because it is reported.
_Avoid_: scenario impact, sensitivity trigger as synonyms for indicator

**Stand total volume (kuvio kokonaistilavuus)**:
The stand-source estimate of tree volume per hectare, retained independently of grid-derived estimates. Its contribution to a summary is weighted by the actual result-piece area with a valid stand value.

**Grid total volume (hila kokonaistilavuus)**:
The grid-source estimate of tree volume per hectare, weighted by actual intersected hectares with valid total-volume values. It is a separate estimate from stand total volume, with its own coverage.
_Avoid_: combined stand/grid volume, stand-volume fallback

**Species volume**:
A grid-derived volume density for pine, spruce, or deciduous trees, each with its own valid-area denominator. Species means need not sum to the grid total when their coverage differs.

**Deciduous volume (lehtipuun tilavuus)**:
The grid estimate of volume per hectare for all source-classified deciduous trees, including birch where represented. It is broader than birch-specific volume.
_Avoid_: birch volume, koivun tilavuus as synonyms for deciduous volume

**Birch volume (koivun tilavuus)**:
Volume per hectare specifically attributable to birch, requiring birch-specific evidence. It is narrower than deciduous volume, which includes other source-classified deciduous trees.

**Sawtimber volume (tukkipuun määrä)**:
The stand-source estimate of standing sawlog volume per hectare. It describes current stock rather than future harvested yield or timber price.

**Annual growth percentage (puuston kasvuprosentti)**:
Annual stand volume growth as a percentage of positive standing stand volume. Summaries describe the area-weighted mean of valid stand growth rates, independently of grid total volume.

**Tree basal area (puuston pohjapinta-ala)**:
The summed cross-sectional area of tree trunks at breast height per hectare of land, expressed in m²/ha and obtained from stand evidence. It describes tree density rather than the ground area of a polygon.
_Avoid_: polygon area, land area

**Age-area share**:
The percentage of valid-age grid area in one of three mean-age bands: under 20 years, 20–80 years inclusive, or over 80 years. It describes grid-cell mean ages rather than stand counts or individual-tree age distributions.
_Avoid_: stand-count share, tree-age distribution

**Peatland area (turvemaiden pinta-ala)**:
The analyzed-forest hectares classified as peat soil by the grid source. It is an area indicator, independently classified from natural mire, and does not add a peatland sensitivity criterion.

**Source-classified natural mire area (lähteen luonnontilaisten soiden pinta-ala)**:
The analyzed-forest hectares in the grid source's natural-mire drainage category. It is a source-date classification rather than certification of present ecological condition, and does not mean every undrained area.
_Avoid_: verified pristine mire area, whole-AOI mire area

**Average stumpage price (keskimääräinen kantohinta)**:
A timber unit price averaged over represented timber volume. In this analysis, the priced assortment is sawlogs only.

**Sawlog stumpage price (tukkipuun kantohinta)**:
The planner's assumed standing sawlog unit price in euros per cubic metre, applicable where positive sawlog stock is represented. It is distinct from a price for all standing timber or a total monetary value.
_Avoid_: all-timber average price, total forest value

**Calculated sawlog value (tukkipuun laskennallinen arvo)**:
The represented standing sawlog volume multiplied by the planner's assumed sawlog unit price, expressed in euros. It is a sawlog-only amount rather than the value of the whole forest or a forecast of harvested income.

**Parent stand overlap**:
A positive-area intersection between two source stands inside the analysis area. All pieces of an affected parent share this context even if an individual piece contains none of the overlapping land.

**Represented volume**:
The cubic metres attributed to the valid intersection of a reporting polygon and source evidence, using volume per hectare and intersected hectares. It is the quantity underlying a volume-density summary, rather than another per-hectare estimate.

**Observed matching area**:
The hectares positively identified as belonging to an age band or land category. For peatland and natural-mire reporting with unknown area, it is a lower bound rather than a complete total.

## Traceability and interpretation

**Source snapshot**:
The analysis-area-clipped source features and their retained original attributes used by a particular analysis. It records the evidence used for that run rather than a later view of a changing service.

**Provenance**:
The source identity, feature identifiers, dates, and interpretation context needed to trace a result to its evidence. Provenance explains origin and reproducibility rather than guaranteeing evidence completeness or accuracy.

**Observation date / update date**:
The date the source forest information describes or was measured / the date its database record was updated. A later update does not by itself establish a newer forest observation.

**Reporting precision**:
The increments used to publish indicator values, distinct from source measurement accuracy. Rounded polygon values can differ from an aggregate calculated from unrounded evidence, and a small positive quantity can appear as zero.
_Avoid_: measurement accuracy as a synonym for reporting precision
