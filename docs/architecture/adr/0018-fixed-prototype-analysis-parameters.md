# Use constants for prototype analysis rules and parameters

Status: accepted  
Recorded: 2026-11-01

Define the prototype's analysis thresholds, buffer distances and sensitivity
rules as constants rather than exposing them as user-configurable scenario
parameters. For example, the riparian criterion uses a fixed 30 m buffer around
the adopted Ranta10 water features. This keeps the prototype scope manageable by
deferring parameter configuration and validation across alternative scenarios.
The current rules and their interpretation remain owned by
[classification requirements](../../specs/classification.md) and the
[geometry and classification contracts](../calculations.md).

The full product should let users run and compare analyses with different
planning parameters, such as a 15 m riparian buffer instead of 30 m. The fixed
prototype values are chosen planning assumptions, not universally appropriate
values for every scenario. Configurable analysis rules remain deferred; this
decision does not extend the prototype into the separate value-table model's
scenario-impact calculations or change the user's ability to select an analysis
area.

The price input (keskikantohinta) is the deliberate exception: users supply it
through the wizard, or explicitly through Processing, instead of the prototype
integrating with Luke for price data. This also keeps the prototype scope in
check. Under [ADR-0014](0014-user-supplied-sawlog-price.md), the input is a sawlog
stumpage unit price in euros per cubic metre, not an all-timber average.
[ADR-0016](0016-calculated-sawlog-value.md) retains that price assumption alongside
the calculated sawlog euro amount. This decision records the reason for manual
price entry without changing either pricing contract.

This is a prototype scope decision, not a claim that fixed parameters fulfill
all requirements of the intended product. See
[project context](../../project-context.md) and
[current classification rules](../../specs/classification.md#cl-02-six-cumulative-tiers).
