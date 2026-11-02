# Savonia - Responsible Forest Planning

Shared language for this unfinished personal prototype's interpretation of forest-planning evidence and management scenarios. These definitions do not establish Savonia's approval or accepted requirements. [Project context](docs/project-context.md) explains the external use case and prototype scope; [architecture](docs/architecture/README.md) records technical decisions and evidence.

## Project identity

**Savonia - Responsible Forest Planning (Savonia - Vastuullinen metsäsuunnittelu)**:
The English and Finnish names of Antti Kajanus's personal forest-planning prototype. The names identify the same project and do not imply Savonia's endorsement or approval.

## Planning and model boundaries

**Forest-management scenario (management pathway; metsänkäsittelypolku)**:
A proposed approach to managing a forest whose consequences can be compared with other approaches. A scenario includes management assumptions beyond the plugin's spatial sensitivity classification.
_Avoid_: sensitivity class as a synonym for scenario

**Value table (arvotaulukko)**:
A decision-support comparison of a forest owner's assets and alternative management pathways across economic, carbon, biodiversity, water, and recreation effects. The plugin prepares forest evidence for this comparison; it does not produce the completed value table.

**Value-table model**:
The separate model that uses forest evidence and management assumptions to compare forest-management scenarios.
_Avoid_: plugin impact calculator

**Scenario impact**:
A consequence of a forest-management scenario assessed by the value-table model. A sensitivity classification or forest indicator is evidence for that assessment, not an impact estimate.

**Sensitivity tier**:
One of the project's ordered planning levels—All out, BAU, Light, Balance, Protection, or Superprotection—used to classify the same forest under progressively broader sensitivity assumptions. A tier is neither a management prescription nor a legal protection status.
_Avoid_: protection status, management prescription

## Analysis area and forest units

**Analysis area (AOI)**:
The geographic area selected for an analysis. It may include land that is not represented in the forest results.
_Avoid_: analyzed forest as a synonym for AOI

**Forest stand (kuvio)**:
A forest-management unit described by stand-level information. It is distinct from an inventory grid cell and from a classified forest polygon.
_Avoid_: grid cell, result polygon as synonyms for stand

**Inventory grid cell (hila)**:
A mapped unit carrying estimates of forest conditions. Grid cells provide a different view of the forest from stand-level information.

**Classified forest polygon**:
A mapped piece of forest with a sensitivity classification for each tier. It is the basic spatial unit used to present results.
_Avoid_: result grid cell, whole stand when referring to a split piece

**Analyzed forest**:
The forest represented by the classified forest polygons. It is distinct from the entire analysis area.
_Avoid_: whole-AOI forest coverage

**Reporting area**:
The area that an indicator or summary describes, such as a classified polygon or a group of results. It can differ from the area with usable evidence for a particular indicator.

**Land area (maapinta-ala)**:
The physical area of land, distinct from the cross-sectional area of tree trunks.
_Avoid_: basal area as a synonym for land area

## Sensitivity evidence

**Sensitivity criterion**:
A mapped condition or forest attribute used as evidence in a planning classification. Including a criterion does not by itself establish legal protection.
_Avoid_: legal prohibition as a synonym for criterion

**Criterion match**:
A finding that available evidence meets a sensitivity criterion. A match is a planning classification input, not a legal determination.
_Avoid_: proximity as an unqualified criterion, legal setback

**Forest Act Section 10 habitat (metsälain 10 §:n elinympäristö)**:
A habitat identified in the context of Finland's Forest Act Section 10. Its use as planning evidence does not determine the legal status of an entire forest stand.

**Section 10 stand-wide promotion**:
A planning assumption under which Section 10 habitat evidence can affect the classification of the associated stand beyond the mapped habitat itself. It does not mean that the whole stand is legally protected.
_Avoid_: whole-stand legal protection

**Active protected area**:
An area with an established, currently active conservation or wilderness protection status. It is distinct from a conservation programme area or a potential protected site.

**Nature conservation programme area (luonnonsuojeluohjelma-alue)**:
An area designated as part of a nature conservation programme. Programme designation is distinct from established legal protection.
_Avoid_: established protected area

**Other valuable habitat (muu arvokas elinympäristö)**:
A mapped forest habitat category distinct from Forest Act Section 10 habitats.

**Groundwater area (pohjavesialue)**:
An area associated with groundwater resources and relevant to forest-planning decisions. Its presence alone does not establish a site-specific legal restriction.
_Avoid_: inferred legal restrictions

**Riparian buffer zone (vesistöjen suojavyöhyke)**:
An area near rivers or lakes considered in planning to reduce potential effects on water. It is not a universal legal setback or a site-specific water-protection assessment.
_Avoid_: legal shoreline setback, verified water-protection zone

**Potential protected site (potentiaalinen suojelukohde)**:
An area considered potentially suitable for protection. It is distinct from an established protected area and a conservation programme area.

**Potential protection due to forest age (mahdollinen suojelualue metsän iän perusteella)**:
Planning evidence that an older forest may merit consideration for protection. It does not establish legal protection or ecological suitability.

**Context layer**:
Geographic information that helps interpret a map but is not itself sensitivity evidence. Examples include property boundaries, identifiers, and basemaps.

## Tiers and classifications

**All out (Kaikki pois)**:
A named planning tier paired with the All out management scenario. It is a distinct comparison label even where it shares sensitivity assumptions with other tiers.

**BAU (business as usual)**:
The business-as-usual management scenario and its corresponding planning tier. It is a distinct scenario from All out and Light.

**Light (Kevyt)**:
A lighter forest-management scenario and its corresponding planning tier, distinct from the business-as-usual scenario.

**Balance (Tasapaino)**:
A planning tier representing a balance among forest-management objectives.

**Protection (Suojelu)**:
A planning tier emphasizing forest protection. Its name does not mean that the classified forest has legal protection.

**Superprotection (Tehostettu suojelu)**:
The project's most protective planning tier. It represents a stronger sensitivity assumption, not a legal designation.

**Sensitive classification (Herkkä)**:
A tier-specific classification that indicates forest treated as sensitive under the planning assumptions. It does not mean harvesting is legally prohibited.
_Avoid_: legally unharvestable, protected forest as synonyms for sensitive

**Economic classification (Taloudellinen)**:
A tier-specific classification for forest not identified as sensitive under the available evidence. It does not establish profitability, legal harvesting permission, or the absence of unmapped constraints.
_Avoid_: unrestricted forest, profitable forest, economic by default

**Unknown classification (Tuntematon)**:
A classification state used when available evidence cannot establish whether forest is sensitive or economic. It is not a third forest type or an assumption of zero sensitivity.
_Avoid_: zero sensitivity, out of scope

**Tier/class group**:
Results sharing one sensitivity tier and one classification, grouped for reporting. Different tiers describe the same forest under different planning assumptions.

## Evidence and coverage

**Source schema readiness**:
Whether a source has the information needed for its intended interpretation. It does not establish that individual records are usable or that the source covers the whole reporting area.
_Avoid_: schema availability

**Source availability**:
Whether a source could provide the requested evidence for an analysis. Availability does not establish complete geographic coverage.
_Avoid_: complete coverage as a synonym for availability

**Source coverage**:
Information about a source's availability, returned evidence, and known retrieval limits for an analysis. It does not certify the provider's complete geographic coverage.

**Metric coverage**:
How much of a reporting area has usable evidence for a particular indicator, and how much remains unknown. Coverage is specific to each indicator, even when indicators share a source.
_Avoid_: source availability as proof of complete metric coverage

**Valid area / unknown area**:
The portions of a reporting area with usable evidence / without usable evidence for a particular indicator. Unknown area is not known zero.

**Partial indicator**:
An indicator with usable evidence for only part of its reporting area. Its value must be understood in light of the area that remains unknown.

**Known zero**:
A valid observation of zero or a complete classification with no matching area. It is distinct from missing evidence.
_Avoid_: blank means zero

**Out of scope**:
A criterion or indicator intentionally excluded from the agreed analysis. Exclusion is a scope decision, not evidence failure or proof that the condition is absent.
_Avoid_: unavailable, unknown as synonyms for out of scope

## Forest indicators

**Forest indicator**:
A descriptive measure of forest conditions, such as timber volume, growth, age distribution, or classified land area. An indicator is not automatically a sensitivity criterion or scenario impact.
_Avoid_: scenario impact, sensitivity trigger as synonyms for indicator

**Stand total volume (kuvion kokonaistilavuus)**:
An estimate of total tree volume associated with forest stands. It is distinct from the inventory-grid estimate.

**Grid total volume (hilan kokonaistilavuus)**:
An inventory-grid estimate of total tree volume. It is a separate measure from stand total volume.
_Avoid_: combined stand/grid volume, stand-volume fallback

**Species volume**:
Tree volume associated with a species or species group, such as pine, spruce, or deciduous trees. Different species measures need not describe identical portions of the forest.

**Deciduous volume (lehtipuun tilavuus)**:
Tree volume attributed to deciduous trees as a group, including birch where represented. It is broader than birch-specific volume.
_Avoid_: birch volume, koivun tilavuus as synonyms for deciduous volume

**Birch volume (koivun tilavuus)**:
Tree volume attributed specifically to birch. It is narrower than deciduous volume.

**Sawtimber volume (tukkipuun määrä)**:
The standing volume of timber classified as suitable for sawlogs. It describes a timber assortment, not harvested yield or monetary value.

**Annual growth percentage (puuston kasvuprosentti)**:
An estimate of annual forest-volume growth expressed as a percentage. It describes growth, not the amount of timber harvested.

**Tree basal area (puuston pohjapinta-ala)**:
The combined cross-sectional area of tree trunks at breast height, expressed relative to land area. It describes tree density, not the size of a land parcel.
_Avoid_: polygon area, land area

**Age-area share**:
The proportion of forest area associated with inventory age classes. It describes area by recorded forest age, not stand counts or the age distribution of individual trees.
_Avoid_: stand-count share, tree-age distribution

**Peatland area (turvemaiden pinta-ala)**:
Forest area classified as peat soil. It is a land-area indicator, distinct from whether an area is a natural mire.

**Stand-based peatland screen (kuvion turvemaaluokitus)**:
A planning screen based on a forest stand's peatland classification. It is distinct from the peatland-area indicator and does not establish legal protection.

**Source-classified natural mire area (lähteen luonnontilaisten soiden pinta-ala)**:
Forest area classified as natural mire in a source dataset. This classification does not certify the area's present ecological condition.
_Avoid_: verified pristine mire area, whole-AOI mire area

**Average stumpage price (keskimääräinen kantohinta)**:
A timber price per unit volume based on standing timber before harvest.

**Sawlog stumpage price (tukkipuun kantohinta)**:
A price per unit volume for standing timber classified as sawlogs. It is distinct from a price for all timber assortments.
_Avoid_: all-timber average price

**Calculated sawlog value (tukkipuun laskennallinen arvo)**:
A monetary estimate associated with standing sawlog stock under a price assumption. It is not the value of the whole forest or a forecast of harvested income.

**Parent stand overlap**:
An area shared by two or more forest stands. Overlap means records for different stands can refer to some of the same ground.

**Represented volume**:
The timber quantity associated with a reporting area. It is distinct from volume per unit area.

**Observed matching area**:
The known area that meets a category or criterion. When evidence is incomplete, it may be only a lower bound on the full area.

## Traceability and interpretation

**Source snapshot**:
A record of source evidence used for a particular analysis. It represents that analysis's evidence rather than a later view of a changing source.

**Provenance**:
Information that identifies the origin and context of evidence used in a result. Provenance supports traceability but does not guarantee completeness or accuracy.

**Observation date / update date**:
The date forest information describes or was measured / the date its record was updated. A later update does not necessarily mean a newer forest observation.

**Reporting precision**:
The detail shown in a reported value, distinct from the accuracy of the source measurement. Rounding can make a small positive value appear as zero.
_Avoid_: measurement accuracy as a synonym for reporting precision
