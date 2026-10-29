# Publish a calculated sawlog euro amount beside its unit price

Status: accepted  
Recorded: 2026-10-29  
Supersedes: only the exclusion of sawlog monetary amounts in [ADR-0014](0014-user-supplied-sawlog-price.md)

The planner expects multiplying represented sawlog volume by the supplied price
to produce a useful euro amount. Publish a separate calculated sawlog value
while retaining the €/m³ field as a unit price. Reinterpreting that existing
field as euros would mislabel its units and silently change a durable contract.
Use original piece hectares and stand sawlog density, summing exact amounts
before rounding published values to cents. Known zero stock gives zero euros;
missing evidence stays unknown. An incomplete group total remains null while
coverage retains its known subtotal, avoiding an understated apparent total.

This extends the former price-only scope without adding another input, pulpwood
valuation, whole-forest value or scenario income modelling. Retained stand
overlaps can duplicate both stock and monetary contributions. See
[IO-01–IO-03](../../specs/indicators-and-outputs.md) and the
[calculation contract](../indicator-calculations.md#calculated-sawlog-value).
