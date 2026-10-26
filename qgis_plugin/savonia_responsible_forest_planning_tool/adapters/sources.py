"""WFS discovery and schema inspection for online V1 sources."""

import datetime
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re

from qgis.core import QgsDataSourceUri, QgsSettings


SYKE_USER_ID_KEY = "savonia-forest-planning/sykeuserid"


def syke_user_id():
    return str(QgsSettings().value(SYKE_USER_ID_KEY, "") or "").strip()


def safe_source_error(error):
    message = str(error)
    identifier = syke_user_id()
    if identifier:
        message = message.replace(identifier, "[redacted]")
        message = message.replace(urllib.parse.quote(identifier, safe=""), "[redacted]")
    return re.sub(r"(?i)(sykeuserid=)[^&\s'\"]+", r"\1[redacted]", message)


def _endpoint_with_syke_id(endpoint):
    if "paikkatiedot.ymparisto.fi" not in endpoint:
        return endpoint
    identifier = syke_user_id()
    if not identifier:
        return endpoint
    delimiter = "&" if "?" in endpoint else "?"
    return endpoint + delimiter + urllib.parse.urlencode({"sykeuserid": identifier})

SERVICE_DEFINITIONS = {
    "forest_centre_stand": {
        "endpoint": "https://avoin.metsakeskus.fi/rajapinnat/v2/stand/ows",
        "required": True,
        "name_key": "stand_layer",
        "kind": "stand",
    },
    "forest_centre_habitat": {
        "endpoint": "https://avoin.metsakeskus.fi/rajapinnat/v2/habitat/ows",
        "required": True,
        "name_key": "habitat_layer",
        "kind": "habitat",
    },
    "syke_protected_areas_state_owned": {
        "endpoint": "https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs",
        "required": True,
        "name_key": "protected_state_layer",
        "kind": "protected",
        "feature_type": "inspire_ps:PS.ProtectedSitesValtionOmistamaLuonnonsuojelualue",
    },
    "syke_protected_areas_private_land": {
        "endpoint": "https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs",
        "required": True,
        "name_key": "protected_private_layer",
        "kind": "protected",
        "feature_type": "inspire_ps:PS.ProtectedSitesYksityistenMaillaOlevaLuonnonsuojelualue",
    },
    "syke_protected_areas_wilderness": {
        "endpoint": "https://paikkatiedot.ymparisto.fi/geoserver/inspire_ps/wfs",
        "required": True,
        "name_key": "protected_wilderness_layer",
        "kind": "protected",
        "feature_type": "inspire_ps:PS.ProtectedSitesEramaaAlue",
    },
    "syke_nature_conservation_programme_areas": {
        "endpoint": "https://paikkatiedot.ymparisto.fi/geoserver/syke_luonnonsuojeluohjelma_alueet/wfs",
        "required": True,
        "name_key": "programme_layer",
        "kind": "programme",
    },
    "syke_groundwater_areas": {
        "endpoint": "https://paikkatiedot.ymparisto.fi/geoserver/syke_vhspohjavesi/wfs",
        "required": True,
        "name_key": "groundwater_layer",
        "kind": "groundwater",
        "feature_type": "syke_vhspohjavesi:VHS2022_Pohjavesi",
    },
    "forest_centre_gridcell": {
        "endpoint": "https://avoin.metsakeskus.fi/rajapinnat/v2/gridcell/ows",
        "required": True,
        "name_key": "gridcell_layer",
        "kind": "gridcell",
        "feature_type": "v2:gridcell",
    },
}

OUT_OF_SCOPE_COVERAGE = tuple(
    {"service_id": source_id, "status": "OUT_OF_SCOPE"}
    for source_id in (
        "syke_forest_sensitive_water", "peatlands", "water_protection_buffers",
        "recreation_areas", "potential_protected_sites", "my_areas",
    )
)


class SourceError(Exception):
    """A stable, user-reportable source discovery/validation failure."""

    def __init__(self, service_id, message, code="SOURCE_UNAVAILABLE"):
        super().__init__(message)
        self.service_id = service_id
        self.code = code
        self.message = message


def _local_name(tag):
    return tag.rsplit("}", 1)[-1].split(":")[-1]


def _request_xml(url, params=None, timeout=30, service_id=None):
    query = dict(params or {})
    full_url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        full_url,
        headers={"User-Agent": "SavoniaResponsibleForestPlanning/1.0", "Accept": "application/xml,text/xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SourceError(service_id or url, "WFS request failed: {0}".format(safe_source_error(exc)))
    try:
        return ET.fromstring(payload), full_url
    except ET.ParseError as exc:
        raise SourceError(service_id or url, "WFS returned invalid XML: {0}".format(exc), "INVALID_WFS_RESPONSE")


def discover_feature_types(endpoint, service_id):
    """Return advertised WFS feature types, each with name, title and CRS."""
    endpoint = _endpoint_with_syke_id(endpoint)
    root, _url = _request_xml(endpoint, {"service": "WFS", "request": "GetCapabilities"}, service_id=service_id)
    feature_types = []
    for node in root.iter():
        if _local_name(node.tag) != "FeatureType":
            continue
        values = {_local_name(child.tag): (child.text or "").strip() for child in node}
        name = values.get("Name")
        if name:
            feature_types.append({
                "name": name,
                "title": values.get("Title", name),
                "default_crs": values.get("DefaultCRS") or values.get("DefaultSRS") or "",
                "other_crs": values.get("OtherCRS") or values.get("OtherSRS") or "",
            })
    if not feature_types:
        raise SourceError(service_id, "WFS capabilities did not advertise a feature type.", "NO_FEATURE_TYPES")
    return feature_types


def describe_feature_type(endpoint, service_id, typename):
    endpoint = _endpoint_with_syke_id(endpoint)
    root, _url = _request_xml(endpoint, {
        "service": "WFS", "request": "DescribeFeatureType", "typeNames": typename,
    }, service_id=service_id)
    properties = []
    for node in root.iter():
        if _local_name(node.tag) not in ("element", "PropertyType"):
            continue
        name = node.attrib.get("name") or node.attrib.get("Name")
        if not name:
            continue
        properties.append({
            "name": name,
            "type": node.attrib.get("type") or node.attrib.get("typeName") or "",
            "min_occurs": node.attrib.get("minOccurs", "1"),
            "nillable": node.attrib.get("nillable", "false").lower() == "true",
        })
    if not properties:
        raise SourceError(service_id, "DescribeFeatureType returned no readable properties.", "INVALID_SCHEMA")
    return properties


def select_feature_type(feature_types, kind):
    """Select a feature type only when its advertised title/name is unambiguous."""
    terms = {
        "stand": ("stand", "kuvio", "metsavara"),
        "habitat": ("habitat", "elinympar", "elinympär"),
        "protected": ("protected", "suojelu", "conservation"),
        "programme": ("programme", "ohjelma", "luonnonsuojeluohjelma"),
        "groundwater": ("pohjavesialue", "groundwater area", "groundwater"),
    }.get(kind, ())
    scored = []
    for item in feature_types:
        text = (item["name"] + " " + item["title"]).lower()
        if kind == "groundwater" and any(
            term in text for term in ("rajaviiva", "boundary", "havaintopaikka", "monitoring point")
        ):
            continue
        score = sum(1 for term in terms if term in text)
        if score:
            scored.append((score, item))
    if not scored:
        if len(feature_types) == 1:
            return feature_types[0]
        raise ValueError("No advertised feature type matched kind {0}".format(kind))
    max_score = max(score for score, _item in scored)
    best = [item for score, item in scored if score == max_score]
    if len(best) != 1:
        raise ValueError("Feature type discovery is ambiguous: {0}".format(", ".join(x["name"] for x in best)))
    return best[0]


def inspect_service(service_id):
    """Discover a configured source and return its validated raw schema."""
    definition = SERVICE_DEFINITIONS[service_id]
    endpoint = definition["endpoint"]
    feature_types = discover_feature_types(endpoint, service_id)
    configured_type = definition.get("feature_type")
    if configured_type:
        feature_type = next(
            (item for item in feature_types if item["name"].lower() == configured_type.lower()),
            None,
        )
        if feature_type is None:
            raise SourceError(
                service_id,
                "Configured WFS feature type is not advertised: {0}".format(configured_type),
                "FEATURE_TYPE_MISSING",
            )
    else:
        try:
            feature_type = select_feature_type(feature_types, definition["kind"])
        except ValueError as exc:
            raise SourceError(service_id, str(exc), "AMBIGUOUS_FEATURE_TYPE")
    properties = describe_feature_type(endpoint, service_id, feature_type["name"])
    return {
        "service_id": service_id,
        "provider": "WFS",
        "endpoint": endpoint,
        "feature_type": feature_type["name"],
        "feature_title": feature_type["title"],
        "query_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_crs": feature_type["default_crs"],
        "properties": properties,
        "feature_types": feature_types,
        "schema_status": "DISCOVERED",
    }


def qgis_wfs_uri(metadata):
    """Build an explicit WFS provider URI from discovered, not guessed, metadata."""
    endpoint = _endpoint_with_syke_id(metadata["endpoint"])
    return "url='{0}' typename='{1}' version='2.0.0' pagingEnabled='true' restrictToRequestBBOX='1'".format(
        endpoint, metadata["feature_type"]
    )


def restrict_wfs_uri_to_request_bbox(uri):
    """Keep remote reads AOI-bounded because an unrestricted WFS iterator may fetch the full service."""
    data_source = QgsDataSourceUri(uri)
    data_source.setParam("restrictToRequestBBOX", "1")
    return data_source.uri()


def validate_fields(metadata, required_fields):
    """Validate case-insensitive field presence without guessing alternatives."""
    available = {prop["name"].lower(): prop for prop in metadata["properties"]}
    missing = [name for name in required_fields if name.lower() not in available]
    if missing:
        raise SourceError(
            metadata["service_id"],
            "Required source fields are missing: {0}".format(", ".join(missing)),
            "REQUIRED_FIELDS_MISSING",
        )
    return {name: available[name.lower()] for name in required_fields}
