"""Tiny loopback WFS 1.0/2.0 fixture; no external network or source data.

By default the server returns configured polygons regardless of request filters.
An optional record predicate can model filtering before paging and record counts.
The real workflow still transforms/clips them. Only the operations used by these
tests are implemented; this is not a general WFS implementation.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET


def request_has_bbox(query):
    """QGIS embeds the rectangle inside FILTER when another predicate is present."""
    return "bbox" in query or (
        "filter" in query and ET.fromstring(query["filter"]).find(".//{*}BBOX") is not None
    )


class LocalWfs:
    def __init__(self, sources, records=None, version="1.0.0", page_size=0, record_filter=None):
        self.sources = sources
        self.records = records
        self.version = version
        self.page_size = page_size
        self.record_filter = record_filter
        self.returned_counts = []
        self.requests = []
        self.feature_failures = set()
        self.page_failures = set()
        self.service_exceptions = set()
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                query = {key.lower(): value[0] for key, value in parse_qs(urlsplit(self.path).query).items()}
                fixture.requests.append(query)
                request = query.get("request", "").lower()
                if request == "getcapabilities":
                    body = fixture.capabilities()
                else:
                    source = query.get("typename", query.get("typenames", "")).split(":")[-1]
                    if source not in fixture.sources:
                        self.send_error(400, "Unknown fixture source")
                        return
                    if request == "getfeature" and (source in fixture.feature_failures or (
                            source, int(query.get("startindex", 0))) in fixture.page_failures):
                        self.send_error(503, "Controlled fixture retrieval failure")
                        return
                    body = fixture.schema(source) if request == "describefeaturetype" else fixture.features(source, query)
                payload = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = "http://127.0.0.1:{0}/wfs".format(self.server.server_port)
        # shutdown() waits for this poll; avoid a half-second delay per scenario.
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def capabilities(self):
        if self.version == "2.0.0":
            operations = "".join(
                '<ows:Operation name="{0}"><ows:DCP><ows:HTTP><ows:Get xlink:href="{1}"/>'
                '</ows:HTTP></ows:DCP></ows:Operation>'.format(name, self.endpoint)
                for name in ("GetCapabilities", "DescribeFeatureType", "GetFeature"))
            types = "".join(
                '<wfs:FeatureType><wfs:Name>fixture:{0}</wfs:Name><wfs:Title>{0}</wfs:Title>'
                '<wfs:DefaultCRS>urn:ogc:def:crs:EPSG::3067</wfs:DefaultCRS>'
                '<ows:WGS84BoundingBox><ows:LowerCorner>20 60</ows:LowerCorner>'
                '<ows:UpperCorner>30 70</ows:UpperCorner></ows:WGS84BoundingBox></wfs:FeatureType>'.format(source)
                for source in self.sources)
            return (
                '<wfs:WFS_Capabilities version="2.0.0" xmlns:wfs="http://www.opengis.net/wfs/2.0" '
                'xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xlink="http://www.w3.org/1999/xlink" '
                'xmlns:fixture="urn:responsible-forest-planning:fixture"><ows:ServiceIdentification><ows:Title>Local WFS 2</ows:Title>'
                '<ows:ServiceType>WFS</ows:ServiceType><ows:ServiceTypeVersion>2.0.0</ows:ServiceTypeVersion>'
                '</ows:ServiceIdentification><ows:OperationsMetadata>{0}'
                '<ows:Constraint name="ImplementsResultPaging"><ows:NoValues/><ows:DefaultValue>TRUE</ows:DefaultValue></ows:Constraint>'
                '<ows:Constraint name="CountDefault"><ows:NoValues/><ows:DefaultValue>{1}</ows:DefaultValue></ows:Constraint>'
                '</ows:OperationsMetadata><wfs:FeatureTypeList>{2}</wfs:FeatureTypeList></wfs:WFS_Capabilities>'
            ).format(operations, self.page_size or 1000, types)
        operations = "".join(
            '<{0}>{1}<DCPType><HTTP><Get onlineResource="{2}"/></HTTP></DCPType></{0}>'.format(
                name, extra, self.endpoint
            ) for name, extra in (
                ("GetCapabilities", ""),
                ("DescribeFeatureType", "<SchemaDescriptionLanguage><XMLSCHEMA/></SchemaDescriptionLanguage>"),
                ("GetFeature", "<ResultFormat><GML2/></ResultFormat>"),
            )
        )
        types = "".join(
            '<FeatureType><Name>fixture:{0}</Name><Title>{0}</Title><SRS>EPSG:3067</SRS>'
            '<LatLongBoundingBox minx="20" miny="60" maxx="30" maxy="70"/></FeatureType>'.format(source)
            for source in self.sources
        )
        return (
            '<WFS_Capabilities version="1.0.0" xmlns="http://www.opengis.net/wfs" '
            'xmlns:fixture="urn:responsible-forest-planning:fixture"><Service><Name>WFS</Name><Title>Local fixture</Title>'
            '</Service><Capability><Request>{0}</Request></Capability><FeatureTypeList>'
            '<Operations><Query/></Operations>{1}</FeatureTypeList></WFS_Capabilities>'
        ).format(operations, types)

    def schema(self, source):
        fields = "".join(
            '<xsd:element name="{0}" type="xsd:{1}" minOccurs="0" nillable="true"/>'.format(
                name, "double" if isinstance(value, (float, int)) else "string"
            ) for name, value in self.sources[source].items()
        )
        schema = (
            '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:gml="http://www.opengis.net/gml" xmlns:fixture="urn:responsible-forest-planning:fixture" '
            'targetNamespace="urn:responsible-forest-planning:fixture" elementFormDefault="qualified">'
            '<xsd:complexType name="{0}Type"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType">'
            '<xsd:sequence><xsd:element name="geometry" type="gml:PolygonPropertyType"/>{1}'
            '</xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>'
            '<xsd:element name="{0}" type="fixture:{0}Type" substitutionGroup="gml:_Feature"/>'
            '</xsd:schema>'
        ).format(source, fields)
        if self.version == "2.0.0":
            schema = schema.replace('http://www.opengis.net/gml"', 'http://www.opengis.net/gml/3.2"')
            schema = schema.replace('gml:_Feature', 'gml:AbstractFeature')
        return schema

    def features(self, source, query=None):
        query = query or {}
        if source in self.service_exceptions:
            # Managed production sources use WFS 2.0.0 / OWS exceptions. The
            # fixture transport is WFS 1.0 for tiny GML2 geometries, but exercises
            # the managed sources' HTTP-200 failure response here.
            return ('<ows:ExceptionReport version="2.0.0" xmlns:ows="http://www.opengis.net/ows/1.1">'
                    '<ows:Exception exceptionCode="NoApplicableCode">'
                    '<ows:ExceptionText>Controlled fixture retrieval failure</ows:ExceptionText>'
                    '</ows:Exception></ows:ExceptionReport>')
        records = self.records.get(source, ()) if self.records is not None else [{
            "attributes": self.sources[source],
            "coordinates": "350000,6900000 350100,6900000 350100,6900100 350000,6900100 350000,6900000",
        }]
        if self.record_filter is not None:
            # A feature's WFS identity must survive different filters and pages.
            records = [{**record, "_fixture_id": index} for index, record in enumerate(records, 1)
                       if self.record_filter(record, query)]
        if self.version == "2.0.0":
            total = len(records)
            start = int(query.get("startindex", 0))
            count = min(int(query.get("count", self.page_size or 1000)), self.page_size or 1000)
            records = records[start:start + count] if query.get("resulttype", "").lower() != "hits" else []
            self.returned_counts.append((source, len(records)))
            members = []
            for index, record in enumerate(records, start + 1):
                fields = "".join('<fixture:{0}>{1}</fixture:{0}>'.format(name, escape(str(value)))
                                 for name, value in record["attributes"].items() if value is not None)
                members.append((
                    '<wfs:member><fixture:{0} gml:id="{0}.{1}"><fixture:geometry>'
                    '<gml:Polygon srsName="urn:ogc:def:crs:EPSG::3067"><gml:exterior><gml:LinearRing>'
                    '<gml:posList srsDimension="2">{2}</gml:posList></gml:LinearRing></gml:exterior>'
                    '</gml:Polygon></fixture:geometry>{3}</fixture:{0}></wfs:member>'
                ).format(source, record.get("_fixture_id", index), record["coordinates"].replace(",", " "), fields))
            return (
                '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
                'xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:fixture="urn:responsible-forest-planning:fixture" '
                'timeStamp="2026-10-27T00:00:00Z" numberMatched="{0}" numberReturned="{1}">'
                '{2}</wfs:FeatureCollection>'
            ).format(total, len(records), "".join(members))
        members = []
        for index, record in enumerate(records, 1):
            fields = "".join(
                '<fixture:{0}>{1}</fixture:{0}>'.format(name, escape(str(value)))
                for name, value in record["attributes"].items() if value is not None
            )
            members.append((
                '<gml:featureMember><fixture:{0} fid="{0}.{1}"><fixture:geometry>'
                '<gml:Polygon srsName="EPSG:3067"><gml:outerBoundaryIs><gml:LinearRing><gml:coordinates>'
                '{2}</gml:coordinates></gml:LinearRing></gml:outerBoundaryIs></gml:Polygon>'
                '</fixture:geometry>{3}</fixture:{0}></gml:featureMember>'
            ).format(source, record.get("_fixture_id", index), record["coordinates"], fields))
        return (
            '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs" '
            'xmlns:gml="http://www.opengis.net/gml" xmlns:fixture="urn:responsible-forest-planning:fixture" numberOfFeatures="{0}">'
            '{1}</wfs:FeatureCollection>'
        ).format(len(records), "".join(members))
