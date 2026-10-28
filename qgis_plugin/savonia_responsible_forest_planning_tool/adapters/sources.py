"""Provider discovery, schema inspection and connection settings for online sources."""

import base64
import datetime
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import re

from qgis.core import QgsDataSourceUri, QgsSettings


HTTP_USER_AGENT = "SavoniaResponsibleForestPlanning/1.0"
SYKE_USER_ID_SETTING_KEY = "savonia-forest-planning/sykeuserid"
MML_API_KEY_SETTING_KEY = "savonia-forest-planning/mml-api-key"
MML_PARCEL_SERVICE_ID = "mml_parcels"
MML_PARCEL_ENDPOINT = "https://avoin-paikkatieto.maanmittauslaitos.fi/kiinteisto-avoin/simple-features/v3/"
MML_PARCEL_COLLECTION = "PalstanSijaintitiedot"
MML_IDENTIFIER_SERVICE_ID = "mml_property_identifiers"
MML_IDENTIFIER_COLLECTION = "KiinteistotunnuksenSijaintitiedot"
MML_PARCEL_LABEL_FIELD = "kiinteistotunnuksenEsitysmuoto"
MML_WMTS_CAPABILITIES = "https://avoin-karttakuva.maanmittauslaitos.fi/avoin/wmts/1.0.0/WMTSCapabilities.xml"


def qgis_mml_wmts_uri(layer_name, image_format):
    """Use the national tile matrix and saved key for capabilities and tiles."""
    uri = QgsDataSourceUri()
    for name, value in {
        "url": MML_WMTS_CAPABILITIES, "layers": layer_name, "styles": "default",
        "format": image_format, "tileMatrixSet": "ETRS-TM35FIN", "crs": "EPSG:3067",
        "username": mml_api_key(), "password": "",
    }.items():
        uri.setParam(name, value)
    return bytes(uri.encodedUri()).decode("utf-8")


def syke_user_id():
    return str(QgsSettings().value(SYKE_USER_ID_SETTING_KEY, "") or "").strip()


def mml_api_key():
    return str(QgsSettings().value(MML_API_KEY_SETTING_KEY, "") or "").strip()


def safe_source_error(error):
    message = str(error)
    for identifier in (syke_user_id(), mml_api_key()):
        if identifier:
            message = message.replace(identifier, "[redacted]")
            message = message.replace(urllib.parse.quote(identifier, safe=""), "[redacted]")
            message = message.replace(urllib.parse.quote_plus(identifier, safe=""), "[redacted]")
            message = message.replace(identifier.replace("\\", "\\\\").replace("'", "\\'"), "[redacted]")
            encoded_basic = base64.b64encode((identifier + ":").encode("utf-8")).decode("ascii")
            message = message.replace(encoded_basic, "[redacted]")
    message = re.sub(r"(?i)((?:sykeuserid|api-key)=)[^&\s'\"]+", r"\1[redacted]", message)
    message = re.sub(r"(?i)(\b(?:user|username|password)\s*=\s*)(?:'[^']*'|\"[^\"]*\"|[^\s&]+)", r"\1'[redacted]'", message)
    return re.sub(r"(?i)(\bBasic\s+)[A-Za-z0-9+/]+=*", r"\1[redacted]", message)


def qgis_mml_uri(collection):
    """Build a view-bounded OGC API Features connection with the saved MML key."""
    key = mml_api_key()
    if not key:
        raise SourceError(MML_PARCEL_SERVICE_ID, "MML API key is required.", "MML_API_KEY_REQUIRED")
    uri = QgsDataSourceUri()
    uri.setParam("url", MML_PARCEL_ENDPOINT)
    # QGIS does not forward URL query parameters to every OAPIF discovery link.
    # MML supports Basic authentication: API key as username, empty password.
    uri.setUsername(key)
    uri.setPassword("")
    uri.setParam("typename", collection)
    uri.setParam("restrictToRequestBBOX", "1")
    uri.setParam("pageSize", "1000")
    return uri.uri()


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
        headers={"User-Agent": HTTP_USER_AGENT, "Accept": "application/xml,text/xml"},
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
    root, _url = _request_xml(endpoint, {
        "service": "WFS", "version": "2.0.0", "request": "GetCapabilities",
    }, service_id=service_id)
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
        "service": "WFS", "version": "2.0.0", "request": "DescribeFeatureType", "typeNames": typename,
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


def qgis_wfs_uri(metadata, existing_uri=None):
    """Configure managed WFS startup without sample reads or a total feature cap.

    When upgrading a managed layer, retain its endpoint, filters, authentication
    and chosen CRS. Analysis reads remain bounded by their feature request.
    """
    uri = QgsDataSourceUri(existing_uri or "")
    if existing_uri is None:
        uri.setParam("url", _endpoint_with_syke_id(metadata["endpoint"]))
        uri.setParam("typename", metadata["feature_type"])
    for key, value in {
        "version": "2.0.0", "pagingEnabled": "true", "pageSize": "1000",
        "restrictToRequestBBOX": "1", "skipInitialGetFeature": "true",
        "forceInitialGetFeature": "false",
    }.items():
        uri.removeParam(key)
        uri.setParam(key, value)
    # A page size bounds each response; a total cap would truncate evidence.
    uri.removeParam("maxNumFeatures")
    if metadata.get("source_crs") and not uri.param("srsname"):
        uri.setParam("srsname", metadata["source_crs"])
    return uri.uri(False)


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
