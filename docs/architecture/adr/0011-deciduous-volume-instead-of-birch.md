# Use deciduous volume instead of birch-specific volume

Status: accepted  
Recorded: 2026-10-26

The original bid/project specification requests birch-specific volume
([procurement Annex 2](../../bid/liite2_hankinnankohteenkuvaus.pdf)). The selected
grid source provides all-deciduous volume rather than a separate birch estimate.
Amend the adopted product scope to use **deciduous volume (lehtipuun tilavuus)**
instead and explicitly exclude birch-specific volume. This keeps the existing
online-source workflow without adding a separate species-specific source or
inferring birch from broader deciduous evidence. [Indicator design](../indicators.md).

Deciduous volume includes all source-classified deciduous trees, including birch
where represented; it must retain that meaning and label in outputs and must not
be presented as birch-only volume. No separate birch field, summary, coverage
entry, metadata indicator or UI indicator is required. The existing deciduous
field and its weighting and missing-data rules remain in force.
[IO-01 and IO-03](../../specs/indicators-and-outputs.md),
[field and calculation contract](../indicator-calculations.md).

This decision resolves the birch-support scope gap recorded alongside
[ADR-0005](0005-independent-stand-and-grid-indicators.md); the independent
stand/grid design remains in force. It deliberately changes the adopted
requirement from the original procurement specification, rather than asserting
that deciduous and birch volumes are equivalent. It records the project owner's
decision for this prototype, not Savonia or buyer acceptance of a contractual
change. [Project context and authority](../../project-context.md).
