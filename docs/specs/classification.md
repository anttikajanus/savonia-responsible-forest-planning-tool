# Classification specification

These are functional planning rules for the personal prototype. [Geometry/classification contracts](../architecture/calculations.md) own exact geometry operations and numeric tolerances; [source contracts](../architecture/source-layer-requirements.md#accepted-classification-values) own accepted input codes; [output schema](../architecture/output-schema.md) owns stored fields; [source evidence](../architecture/data-sources.md) owns their supporting provider references.

## CL-01 Reporting domain and geometry

- Clip forest stands to the chosen AOI, then split them at relevant sensitivity boundaries. Keep polygon results; grid boundaries supply indicators without subdividing the result or changing classification.
- Every result piece carries classifications for all six tiers. Each tier describes the same analyzed forest; adding areas across tiers would count that forest repeatedly.
- The reporting area is forest represented by the classified stand pieces. It does not automatically include the whole AOI or open mires outside those stands.
- Use direct polygon overlap, without implicit buffers or proximity rules. A criterion hit must exceed 1 m² in EPSG:3067. Exactly 1 m², smaller intersections and shared edges/points do not trigger sensitivity.
- For a qualifying Section 10 habitat hit, promote every piece derived from the AOI-clipped parent stand in tiers containing that criterion. Other criteria affect the matching pieces. Preserve the stand-promotion reason and matched source identifiers.
- Accept pairwise overlaps between clipped input stands up to and including 1 m² without trimming; these can contribute to both stands' areas and indicators. Larger overlaps stop publication. Grid duplicates/overlaps use the separate technical geometry policy and must not double count indicators.

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

Acceptance examples: a 1 ha stand with a qualifying protected strip of 0.25 ha and no other trigger has 0.25 sensitive/0.75 economic ha in All out through Protection, and 1 sensitive ha in Superprotection. A qualifying Section 10 strip instead promotes the whole clipped parent stand in every tier containing Section 10. Verify threshold behavior below, at and above 1 m² and cumulative membership across all tiers.

## CL-04 Exclusions and interpretation

SYKE forest-sensitive-water criteria, peat/mire sensitivity criteria, water-protection buffers, recreation areas, potential protected sites and MY plan areas are out of scope. Do not retrieve/process their geometries as classification evidence or make their absence an unknown-source failure. Ranta10 shoreline context is deferred; it is disabled and not requested or processed.

Grid peatland and natural-mire **indicators** are included within analyzed forest and do not add sensitivity criteria. Programme membership does not establish current legal protection, and Section 10 stand promotion is a conservative prototype assumption. No mapped habitat does not prove habitat absence.

The plugin prepares spatial evidence and descriptive inputs. It does not determine legal harvesting rights, approve a forestry prescription, model scenario harvest/economic/carbon/biodiversity/water/recreation effects, or replace field assessment and owner/public decision making. Deferred sources and policy questions remain in [architecture](../architecture/deferred-sources.md).
