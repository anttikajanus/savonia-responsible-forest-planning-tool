"""Small authenticated OGC API Features server for parcel display tests."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64
import json
from threading import Thread
from urllib.parse import parse_qs, urlsplit


class LocalOapif:
    def __init__(self):
        self.key = "fixture-mml-key"
        self.requests = []
        self.label_field = "kiinteistotunnuksenEsitysmuoto"
        self.geometry_type = "Polygon"
        self.identifier_geometry_type = "Point"
        self.identifier_label_field = "kiinteistotunnuksenEsitysmuoto"
        self.fail_identifiers = False
        self.fail = False
        self.accept_basic_auth = True
        self.challenge_auth = False
        self.unauthorized_paths = []
        self.basic_authenticated_paths = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parts = urlsplit(self.path)
                query = parse_qs(parts.query)
                fixture.requests.append((parts.path, query))
                expected_auth = "Basic " + base64.b64encode((fixture.key + ":").encode("utf-8")).decode("ascii")
                basic_authenticated = fixture.accept_basic_auth and self.headers.get("Authorization") == expected_auth
                if basic_authenticated:
                    fixture.basic_authenticated_paths.append(parts.path)
                if query.get("api-key") != [fixture.key] and not basic_authenticated:
                    fixture.unauthorized_paths.append(parts.path)
                    if fixture.challenge_auth:
                        self.send_response(401)
                        self.send_header("WWW-Authenticate", 'Basic realm="API-key required to access fixture"')
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                    else:
                        self.send_error(401)
                    return
                if fixture.fail or (fixture.fail_identifiers and "KiinteistotunnuksenSijaintitiedot" in parts.path):
                    self.send_error(503)
                    return
                payload, content_type = fixture.response(parts.path)
                data = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = "http://127.0.0.1:{0}/".format(self.server.server_port)
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def link(self, path, rel, content_type="application/json"):
        # Deliberately omit the key: the client must preserve connection parameters.
        return {"href": self.endpoint + path, "rel": rel, "type": content_type}

    def response(self, path):
        identifier = "KiinteistotunnuksenSijaintitiedot" in path
        collection_id = "KiinteistotunnuksenSijaintitiedot" if identifier else "PalstanSijaintitiedot"
        collection_path = "collections/" + collection_id
        collection = {
            "id": collection_id, "title": collection_id,
            "crs": ["http://www.opengis.net/def/crs/OGC/1.3/CRS84", "http://www.opengis.net/def/crs/EPSG/0/3067"],
            "extent": {"spatial": {"bbox": [[24, 60, 25, 61]],
                                    "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
            "links": [self.link(collection_path + "/items", "items", "application/geo+json")],
        }
        if path == "/":
            body = {"links": [self.link("api", "service-desc", "application/vnd.oai.openapi+json;version=3.0"),
                              self.link("collections", "data"), self.link("conformance", "conformance")]}
        elif path == "/api":
            body = {"openapi": "3.0.0", "info": {"title": "Fixture", "version": "1.0"},
                    "paths": {"/collections/{collectionId}/items": {"get": {"parameters": [
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 10, "maximum": 1000}},
                        {"name": "bbox", "in": "query", "schema": {"type": "array", "items": {"type": "number"}}},
                    ], "responses": {"200": {"description": "Features"}}}}}}
        elif path == "/conformance":
            body = {"conformsTo": ["http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
                                   "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
                                   "http://www.opengis.net/spec/ogcapi-features-2/1.0/conf/crs"]}
        elif path == "/collections":
            point_collection, _ = self.response("/collections/KiinteistotunnuksenSijaintitiedot")
            body = {"collections": [collection, point_collection], "links": []}
        elif path == "/" + collection_path:
            body = collection
        else:
            coordinates = [[[24.9, 60.1], [24.91, 60.1], [24.91, 60.11], [24.9, 60.11], [24.9, 60.1]]]
            geometry_type = self.identifier_geometry_type if identifier else self.geometry_type
            label_field = self.identifier_label_field if identifier else self.label_field
            if geometry_type == "Point":
                coordinates = [24.905, 60.105]
            body = {"type": "FeatureCollection", "numberMatched": 1, "numberReturned": 1,
                    "links": [], "features": [{"type": "Feature", "id": 1,
                        "geometry": {"type": geometry_type, "coordinates": coordinates},
                        "properties": {label_field: "123-456-7-8"}}]}
            return body, "application/geo+json"
        return body, "application/json"
