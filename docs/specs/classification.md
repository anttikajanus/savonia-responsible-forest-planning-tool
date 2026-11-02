# Classification specification

These are functional planning rules for the personal prototype. [Geometry/classification contracts](../architecture/calculations.md) own exact geometry operations and numeric tolerances; [source contracts](../architecture/source-layer-requirements.md#accepted-classification-values) own accepted input codes; [output schema](../architecture/output-schema.md) owns stored fields; [source evidence](../architecture/data-sources.md) owns their supporting provider references.

## CL-01 Reporting domain and geometry

- Clip forest stands to the chosen AOI, then split them at relevant sensitivity boundaries. Keep polygon results; grid boundaries supply indicators without subdividing the result or changing classification.
- Exclude each final result polygon of 0.01 m² or less before sampling and publication, using unrounded EPSG:3067 area. Count disconnected components and split remainders individually. Report the excluded count and total area while preserving clipped source snapshots. The [geometry contract](../architecture/calculations.md#area-and-geometry) owns the precise measurement procedure and tolerance. Only retained polygons contribute to results and summaries; if none remain, stop before publication with the no-forest-stands error.
- Every result piece carries classifications for all six tiers. Each tier describes the same analyzed forest; adding areas across tiers would count that forest repeatedly.
- The reporting area is forest represented by the classified stand pieces. It does not automatically include the whole AOI or open mires outside those stands.
- Use direct source-polygon overlap for mapped area criteria, except for the adopted Ranta10 riparian-buffer criterion. A mapped criterion, including the derived riparian footprint, matches only when overlap exceeds 1 m²; exactly 1 m² or less and shared edges/points do not match. The riparian footprint is the union of 30 m buffers around the three Ranta10 water products, buffered before AOI clipping. Line rivers extend 30 m on both sides; polygon rivers and lakes retain the water surface within their positive buffer. The [geometry contract](../architecture/calculations.md#area-and-geometry) owns the precise geometry operations and numerical tolerances. Stand age and peatland criteria in CL-02 use parent-stand attributes without an overlap test.
- For a qualifying Section 10 habitat hit, promote every piece derived from the AOI-clipped parent stand in tiers containing that criterion. Other mapped area criteria affect the matching pieces. Preserve the stand-promotion reason and matched source identifiers.
- Accept overlaps of every size between AOI-clipped input stands without trimming or choosing a winning stand. Overlaps beyond numerical tolerance produce technical pair records and a successful-completion warning; shared boundaries and overlaps wholly outside the AOI do not. Summaries can count area and timber contributions more than once and do not represent unique ground coverage. Every result piece inherits its parent stand's overlap flag, including pieces outside the physical intersection. Grid duplicates/overlaps retain their separate fatal conflict policy.

## CL-02 Six cumulative tiers

| Tier | Sensitivity criteria |
| --- | --- |
| All out | Recognized active protected areas and mapped Section 10 habitats |
| BAU | Same criteria as All out, plus parent-stand natural-state mire when `DRAINAGESTATE == 6`; retained as a separate tier |
| Light | All out/BAU criteria plus potential protection when parent-stand `MEANAGE >= 100` years and parent-stand natural-state mire when `DRAINAGESTATE == 6` |
| Balance | Light criteria plus nature conservation programme areas, groundwater areas, Ranta10 riparian buffers, parent-stand peatland screen (`SOILTYPE` 60–69), potential protection when `MEANAGE >= 90` years, and parent-stand natural-state mire when `DRAINAGESTATE == 6` |
| Protection | Balance criteria plus other valuable habitats, potential protection when `MEANAGE >= 80` years, and parent-stand natural-state mire when `DRAINAGESTATE == 6` |
| Superprotection | Protection criteria plus all remaining analyzed forest when required evidence is available |

The [accepted input mapping](../architecture/source-layer-requirements.md#accepted-classification-values) distinguishes Section 10 from other valuable habitat. Programme areas and established protected areas remain distinct evidence, with programme identifiers/context and their observed protected-area overlap retained. All returned groundwater footprints count without class/subtype filtering. The riparian criterion uses the three required Ranta10 water products; buffer construction and union behavior are defined in the [geometry contract](../architecture/calculations.md#area-and-geometry). These are planning rules, not statements about legal restrictions.

Mean age of at least 100 years triggers potential protection throughout every
result piece from that stand in Light. Mean age of at least 90 years triggers
it in Balance; at least 80 years triggers it in Protection and Superprotection.
These inclusive checks are reported separately at 80, 90 and 100 years, each
with its own result attribute. The stand soil-code analysis remains a separate
criterion: codes 60–69 inclusive trigger potential protection throughout every
piece in Balance, Protection and Superprotection. Recognized stand
`DRAINAGESTATE` code 6 triggers natural-state mire sensitivity in BAU through
Superprotection; recognized codes 1, 2, 3, 7, 8 and 9 do not match. The stand
drainage check is distinct from the grid natural-mire area indicator. The three
age checks, soil-code check and drainage check are independent of each other,
grid age/soil/drainage indicators and active protected-area status. They add
no geometric boundary or external potential-site source. Accepted value
formats and invalid-value handling are defined by the [source contract](../architecture/source-layer-requirements.md#accepted-classification-values).

## CL-03 Classes and evidence policy

- Classify each tier as sensitive, economic or unknown. Keep stored class codes language-neutral and translate their display labels. The exact codes and output fields are defined in the [output schema](../architecture/output-schema.md#class-codes).
- A recognized positive trigger makes a piece sensitive. With no trigger, a piece is economic only when required evidence for that tier is available. Unavailable dependencies leave an unmatched piece unknown; Superprotection's catch-all must not erase that uncertainty.
- `UNKNOWN` is a data-quality state, not a third forest type. The pure classification policy supports unknown dependencies, while the current application stops on required-source, request, geometry or interpretation failures as specified in [WF-07](workflow.md#wf-07-failure-cancellation-and-observability).
- Missing or invalid individual stand ages, soil codes or drainage codes make their respective checks unknown. With no other positive trigger, BAU through Superprotection are unknown when the natural-state mire check is unknown; Light is also unknown if its age check is unknown; Balance is unknown if its age or soil check is unknown; Protection and Superprotection are unknown if their age or soil check is unknown. The Superprotection catch-all cannot override missing applicable stand evidence. The [source contract](../architecture/source-layer-requirements.md#accepted-classification-values) owns accepted stand values; a missing required field stops the run at schema validation, while an invalid individual value can produce an unknown result.

For an unmatched result to be classified as economic, the pure policy requires:

| Tiers | Required evidence groups |
| --- | --- |
| All out | Protected + Habitat |
| BAU | Protected + Habitat + valid stand drainage value |
| Light | Protected + Habitat + valid stand age and drainage values |
| Balance | Protected + Habitat + Programme + Groundwater + Ranta10 water + valid stand age, soil and drainage values |
| Protection, Superprotection | Protected + Habitat + Programme + Groundwater + Ranta10 water + valid stand age, soil and drainage values |

The current workflow checks every configured source before classification; see
[WF-03](workflow.md#wf-03-source-readiness-and-retrieval) and
[WF-07](workflow.md#wf-07-failure-cancellation-and-observability).
- Preserve matched rule IDs and source IDs per tier, original stand identity, Section 10 promotion and available programme context. An economic result means no included trigger was found under the available evidence; it does not establish that no constraint exists on the ground.
- Expose independent checks for applicable source criteria, including protected areas, Section 10, programme areas, groundwater, riparian buffer, other valuable habitat, the three stand-age screens (80, 90 and 100 years), the stand soil screen, and the stand natural-state mire check. Each check is MATCH, NO_MATCH or UNKNOWN; unavailable evidence is not a no-match. Riparian matches retain only contributing water-source references for the result piece. Stored field names/codes and reason provenance are defined in the [output schema](../architecture/output-schema.md#classification-fields-and-values). Superprotection's remaining-forest policy stays in tier provenance rather than becoming another source check.

Check display labels for the three age criteria include their threshold in
years. Preserve the exact age rules and their interpretation in run metadata
and workbook calculation notes, following the [output schema](../architecture/output-schema.md).

Acceptance: a 1 ha stand aged 79 has no age-triggered sensitivity; age 80 triggers Protection and Superprotection; age 90 also triggers Balance; and age 100 also triggers Light. Each threshold result is MATCH at its inclusive boundary and above, NO_MATCH below it, and UNKNOWN for invalid age. These checks apply across all pieces of the parent stand. A soil code from 60 through 69 makes the full stand sensitive in Balance through Superprotection. A qualifying Section 10 hit promotes the whole clipped parent stand in every tier containing Section 10. Verify mapped overlap behavior below, at and above 1 m², age behavior at 79/80/89/90/99/100, soil boundaries 59/60/69/70, unknown stand values, positive-trigger precedence and cumulative tier membership. Detailed geometry tolerances remain in the [geometry contract](../architecture/calculations.md#area-and-geometry).

For the stand natural-state mire check, code 6 is MATCH, recognized codes 1, 2,
3, 7, 8 and 9 are NO_MATCH, and null or invalid values are UNKNOWN. The match
affects BAU, Light, Balance, Protection and Superprotection, never All out, and
inherits to every output piece from its parent stand. Missing the required
stand `DRAINAGESTATE` provider field fails schema readiness before publication.
The grid natural-mire area indicator and its coverage are unchanged.

Overlapping protected records retain only the identifiers that match each piece.
A piece touched by one record must not inherit another piece's identifiers when
later overlays split their common parent. Section 10 identifiers remain
stand-wide under its explicit promotion rule. Verify both source orders and
conservation of the parent geometry and full-precision area.

## CL-04 Exclusions and interpretation

Analysis thresholds, buffer distances and sensitivity rules are fixed in the
prototype; users cannot configure alternatives. Configurable planning
parameters for scenario comparison are deferred to the full product. The
user-supplied sawlog stumpage price is the deliberate exception, avoiding Luke
price integration.
[ADR-0018](../architecture/adr/0018-fixed-prototype-analysis-parameters.md)
records this scope decision.

Other SYKE forest-sensitive-water criteria, peat/mire sensitivity criteria beyond the adopted stand screen, recreation areas, external potential-protected-site datasets and MY plan areas are out of scope. The adopted Ranta10 buffer criterion is a planning assumption, not a legal setback or site-specific assessment; see [CL-02](#cl-02-six-cumulative-tiers) for its current scope. Do not treat it as adoption of other water-protection sources or rules.

Grid peatland and natural-mire **indicators** are included within analyzed forest and do not themselves add sensitivity criteria; the adopted stand soil-code screen is separate. Programme membership does not establish current legal protection, and Section 10 stand promotion is a conservative prototype assumption. No mapped habitat does not prove habitat absence.

The plugin prepares spatial evidence and descriptive inputs. It does not determine legal harvesting rights, approve a forestry prescription, model scenario harvest/economic/carbon/biodiversity/water/recreation effects, or replace field assessment and owner/public decision making. Deferred sources and policy questions remain in [architecture](../architecture/deferred-sources.md).
