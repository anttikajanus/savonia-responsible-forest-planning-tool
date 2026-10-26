# Support only WFS 2.0 sources

Status: accepted  
Recorded: 2026-10-26

The managed sources already use WFS 2.0.0, and their request-failure handling is
tested against that protocol. Support only WFS 2.0, using the current 2.0.0
configuration, for source retrieval through both the wizard and Processing.
WFS 1.x endpoints, including legacy WFS 1.0 services, are unsupported and outside
the planned scope; do not add protocol downgrade fallback or legacy exception
response handling.

Supporting WFS 1.0 would require separate response inspection and tests because
the documented QGIS 4.2 parser behavior can treat a legacy
`ServiceExceptionReport` as an empty collection. Keeping one supported protocol
avoids that compatibility work and keeps the tested distinction between a
successful empty response and a failed request. The trade-off is that a source
available only through WFS 1.x cannot be used under the supported source contract.
This is an intentional scope boundary, rather than deferred compatibility work.

The [source contract](../source-layer-requirements.md) and
[retrieval evidence](../data-sources.md#wfs-retrieval-success) retain the detailed
failure semantics and their verification limits. This decision records the
existing managed-source boundary; it does not add runtime version rejection or
establish new provider or desktop acceptance evidence.
