# Price represented sawlogs using one explicit user assumption

Status: accepted  
Recorded: 2026-10-29

The planner needs a repeatable price assumption alongside forest indicators.
Require one finite positive sawlog stumpage unit price from both entry points,
and apply it only where the original stand sawlog volume is valid and positive.
This adopts sawlog pricing in place of the previous excluded price placeholder;
it does not change the independent stand/grid estimates in
[ADR-0005](0005-independent-stand-and-grid-indicators.md).

A single supplied price gives the same eligible polygon and nonempty group
price, regardless of timber composition. Weight group prices by unrounded
represented sawlog cubic metres, retain the assumption and source in durable
metadata, and leave ineligible prices null. This accepts a simple explicit
assumption instead of an assortment/species model or external price retrieval.
Pulpwood pricing and total monetary valuation remain outside scope. See
[calculations](../indicator-calculations.md#sawlog-stumpage-price) and
[IO-01](../../specs/indicators-and-outputs.md#io-01-indicator-catalogue).
