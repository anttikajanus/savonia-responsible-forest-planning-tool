"""Provider-backed field resolution and normalization for V1 interpretation."""


PROTECTED_SOURCE_IDS = (
    "syke_protected_areas_state_owned",
    "syke_protected_areas_private_land",
    "syke_protected_areas_wilderness",
)
_PROTECTED_FIELD_GROUPS = (("olotila",), ("tyyppilyhenne", "kohdetyyppi"))


_REQUIRED_FIELD_GROUPS = {
    # Keep optional indicators out of the readiness gate; their absent values are
    # reported as unknown, while these fields support the core stand calculations.
    "forest_centre_stand": (
        ("volume",), ("sawlogvolume",), ("volumegrowth",), ("meanage",),
    ),
    "forest_centre_gridcell": (
        ("gridcellid",), ("volume",), ("volumepine",), ("volumespruce",),
        ("volumedeciduous",), ("age",), ("soiltype",), ("drainagestate",),
    ),
    **{service_id: _PROTECTED_FIELD_GROUPS for service_id in PROTECTED_SOURCE_IDS},
    "forest_centre_habitat": (("habitattype",),),
    "syke_nature_conservation_programme_areas": (("lsoaluetunnus",), ("luokka",)),
    # Groundwater areas are interpreted from their polygon footprints; no
    # attribute status or class filter is applied in this analysis.
    "syke_groundwater_areas": (),
}


def assess_source_schema(service_id, field_names):
    """Check required source attributes against names exposed by a provider.

    The check is independent of provider type and metadata format so WFS,
    local-file, and custom-source adapters can share the same requirements.
    Each inner tuple contains aliases in priority order; the first name is the
    normalized key. The returned field_map binds that key to the provider's
    actual field spelling, so retrieval uses exactly the fields checked here.
    Field types and unrelated extra fields are not checked.
    """
    requirements = _REQUIRED_FIELD_GROUPS.get(service_id)
    if requirements is None:
        return {
            "status": "NOT_AVAILABLE",
            "reason_code": "SOURCE_CONTRACT_MISSING",
            "missing_fields": [],
        }

    try:
        available = {
            str(name).strip().lower(): str(name)
            for name in field_names
            if name is not None and str(name).strip()
        }
    except TypeError:
        available = {}
    field_map = {
        alternatives[0]: next(
            (available[field] for field in alternatives if field in available), None
        )
        for alternatives in requirements
    }
    missing = [
        " or ".join(alternatives)
        for alternatives in requirements
        if field_map[alternatives[0]] is None
    ]
    if missing:
        return {
            "status": "NOT_AVAILABLE",
            "reason_code": "REQUIRED_FIELDS_MISSING",
            "missing_fields": missing,
        }
    return {
        "status": "AVAILABLE",
        "reason_code": "SCHEMA_READY",
        "missing_fields": [],
        "field_map": field_map,
    }


def normalize_source_attributes(attributes, field_map):
    """Read interpretation values using the already-validated provider mapping.

    Keep original attributes separate for snapshots and provenance. Missing/null
    values remain missing; alias selection never depends on a feature's values.
    """
    return {name: attributes.get(provider_name) for name, provider_name in field_map.items()}
