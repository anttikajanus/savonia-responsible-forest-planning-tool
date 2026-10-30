# Classification specification

These are functional planning rules for the personal prototype. [Geometry/classification contracts](../architecture/calculations.md) own exact geometry operations and numeric tolerances; [source contracts](../architecture/source-layer-requirements.md#accepted-classification-values) own accepted input codes; [output schema](../architecture/output-schema.md) owns stored fields; [source evidence](../architecture/data-sources.md) owns their supporting provider references.

## CL-01 Reporting domain and geometry

- Clip forest stands to the chosen AOI, then split them at relevant sensitivity boundaries. Keep polygon results; grid boundaries supply indicators without subdividing the result or changing classification.
- Exclude individual result polygons of 0.01 m² or less using unrounded EPSG:3067 area, including disconnected clipped components and split remainders. Report their count and total excluded area; preserve clipped source snapshots. Only retained polygons contribute to results and summaries. Larger polygons remain even when hectare rounding displays zero. If none remain, stop before publication with the no-forest-stands error.
- Every result piece carries classifications for all six tiers. Each tier describes the same analyzed forest; adding areas across tiers would count that forest repeatedly.
- The reporting area is forest represented by the classified stand pieces. It does not automatically include the whole AOI or open mires outside those stands.
- Use direct polygon overlap, without implicit buffers or proximity rules. A criterion hit must exceed 1 m² in EPSG:3067. Exactly 1 m², smaller intersections and shared edges/points do not trigger sensitivity.
- For a qualifying Section 10 habitat hit, promote every piece derived from the AOI-clipped parent stand in tiers containing that criterion. Other criteria affect the matching pieces. Preserve the stand-promotion reason and matched source identifiers.
- Accept overlaps of every size between AOI-clipped input stands without trimming or choosing a winning stand. Overlaps beyond numerical tolerance produce technical pair records and a successful-completion warning; shared boundaries and overlaps wholly outside the AOI do not. Summaries can count area and timber contributions more than once and do not represent unique ground coverage. Every result piece inherits its parent stand's overlap flag, including pieces outside the physical intersection. Grid duplicates/overlaps retain their separate fatal conflict policy.

## CL-02 Six cumulative tiers

| Tier | Sensitivity criteria |
| --- | --- |
| All out | Recognized active protected areas and mapped Section 10 habitats |
| BAU | Same criteria as All out, retained as a separate tier |
| Light | Same criteria as All out/BAU |
| Balance | Light criteria plus nature conservation programme areas and groundwater areas |
| Protection | Balance criteria plus other valuable habitats |
| Superprotection | Protection criteria plus all remaining analyzed forest when required evidence is available |

The [accepted input mapping](../architecture/source-layer-requirements.md#accepted-classification-values) distinguishes Section 10 from other valuable habitat. Programme areas and established protected areas remain distinct evidence, with programme identifiers/context and their observed protected-area overlap retained. All returned groundwater footprints count without class/subtype filtering. These are product rules, not statements about legal restrictions.

## CL-03 Classes and evidence policy

- Store stable `SENSITIVE`, `ECONOMIC` and `UNKNOWN` class codes for each tier. Translate display labels rather than stored codes.
- A recognized positive trigger makes a piece sensitive. With no trigger, a piece is economic only when required evidence for that tier is available. Unavailable dependencies leave an unmatched piece unknown; Superprotection's catch-all must not erase that uncertainty.
- `UNKNOWN` is a data-quality state, not a third forest type. The pure classification policy supports unknown dependencies, while the current application stops on required-source, request, geometry or interpretation failures as specified in [WF-07](workflow.md#wf-07-failure-cancellation-and-observability).
- In particular, returned protected-area statuses/categories, habitat codes and programme classes/identifiers must be recognized. The current workflow also rejects protected records with a status other than the accepted active status; it does not publish them as ignored inactive evidence.
- Preserve matched rule IDs and source IDs per tier, original stand identity, Section 10 promotion and available programme context. An economic result means no included trigger was found under the available evidence; it does not establish that no constraint exists on the ground.
- Provide ordinary attributes for protected-area, Section 10 promotion, programme, groundwater and other-habitat checks. Store stable `MATCH`, `NO_MATCH` and `UNKNOWN` codes with bilingual presentation; unavailable evidence is never a no-match. Section 10 reports parent promotion even outside the mapped habitat footprint. Superprotection's remaining-forest policy stays in its existing provenance rather than becoming another source check.

Acceptance examples: a 1 ha stand with a qualifying protected strip of 0.25 ha and no other trigger has 0.25 sensitive/0.75 economic ha in All out through Protection, and 1 sensitive ha in Superprotection. A qualifying Section 10 strip instead promotes the whole clipped parent stand in every tier containing Section 10. Verify threshold behavior below, at and above 1 m² and cumulative membership across all tiers.

Overlapping protected records retain only the identifiers that match each piece.
A piece touched by one record must not inherit another piece's identifiers when
later overlays split their common parent. Section 10 identifiers remain
stand-wide under its explicit promotion rule. Verify both source orders and
conservation of the parent geometry and full-precision area.

## CL-04 Exclusions and interpretation

SYKE forest-sensitive-water criteria, peat/mire sensitivity criteria, water-protection buffers, recreation areas, potential protected sites and MY plan areas are out of scope. Do not retrieve/process their geometries as classification evidence or make their absence an unknown-source failure.

Grid peatland and natural-mire **indicators** are included within analyzed forest and do not add sensitivity criteria. Programme membership does not establish current legal protection, and Section 10 stand promotion is a conservative prototype assumption. No mapped habitat does not prove habitat absence.

The plugin prepares spatial evidence and descriptive inputs. It does not determine legal harvesting rights, approve a forestry prescription, model scenario harvest/economic/carbon/biodiversity/water/recreation effects, or replace field assessment and owner/public decision making. Deferred sources and policy questions remain in [architecture](../architecture/deferred-sources.md).
