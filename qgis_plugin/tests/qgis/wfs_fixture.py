"""Tiny loopback WFS 1.0 fixture; no external network or source data.

The server returns configured polygons regardless of request filters. The real
workflow still transforms/clips them. Only the operations used by these tests are
implemented; this is not a general WFS implementation.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from xml.sax.saxutils import escape


class LocalWfs:
    def __init__(self, sources, records=None):
        self.sources = sources
        self.records = records
        self.requests = []
        self.feature_failures = set()
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
                    if request == "getfeature" and source in fixture.feature_failures:
                        self.send_error(503, "Controlled fixture retrieval failure")
                        return
                    body = fixture.schema(source) if request == "describefeaturetype" else fixture.features(source)
                payload = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/xml; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = "http://127.0.0.1:{0}/wfs".format(self.server.server_port)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def capabilities(self):
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
        return (
            '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:gml="http://www.opengis.net/gml" xmlns:fixture="urn:responsible-forest-planning:fixture" '
            'targetNamespace="urn:responsible-forest-planning:fixture" elementFormDefault="qualified">'
            '<xsd:complexType name="{0}Type"><xsd:complexContent><xsd:extension base="gml:AbstractFeatureType">'
            '<xsd:sequence><xsd:element name="geometry" type="gml:PolygonPropertyType"/>{1}'
            '</xsd:sequence></xsd:extension></xsd:complexContent></xsd:complexType>'
            '<xsd:element name="{0}" type="fixture:{0}Type" substitutionGroup="gml:_Feature"/>'
            '</xsd:schema>'
        ).format(source, fields)

    def features(self, source):
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
            ).format(source, index, record["coordinates"], fields))
        return (
            '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs" '
            'xmlns:gml="http://www.opengis.net/gml" xmlns:fixture="urn:responsible-forest-planning:fixture" numberOfFeatures="{0}">'
            '{1}</wfs:FeatureCollection>'
        ).format(len(records), "".join(members))
