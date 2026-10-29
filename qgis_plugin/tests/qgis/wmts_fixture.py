"""Small authenticated WMTS with national-grid PNG/JPEG tiles."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from qgis.PyQt.QtCore import QBuffer, QIODevice
from qgis.PyQt.QtGui import QColor, QImage


class LocalWmts:
    def __init__(self):
        self.key = "fixture-mml-key"
        self.requests = []
        self.rejected = []
        self.fail = False
        self.tiles = {}
        for product, image_format, color in (
            ("maastokartta", "PNG", "#aacc88"), ("ortokuva", "JPEG", "#447755"),
        ):
            image = QImage(256, 256, QImage.Format.Format_RGB32)
            image.fill(QColor(color))
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, image_format)
            self.tiles[product] = bytes(buffer.data())
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                fixture.requests.append(self.path)
                authorization = "Basic " + base64.b64encode((fixture.key + ":").encode()).decode()
                if self.headers.get("Authorization") != authorization:
                    fixture.rejected.append(self.path)
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="MML fixture"')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if fixture.fail:
                    self.send_error(503)
                    return
                if "WMTSCapabilities.xml" in self.path:
                    body, mime = fixture.capabilities().encode(), "text/xml"
                else:
                    product = "ortokuva" if "/ortokuva/" in self.path else "maastokartta"
                    body = fixture.tiles[product]
                    mime = "image/jpeg" if product == "ortokuva" else "image/png"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.endpoint = "http://127.0.0.1:{0}/wmts/1.0.0/".format(self.server.server_port)
        self.capabilities_url = self.endpoint + "WMTSCapabilities.xml"
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def capabilities(self):
        layers = []
        for product, mime, extension in (
            ("ortokuva", "image/jpeg", "jpg"), ("maastokartta", "image/png", "png"),
        ):
            layers.append('''<Layer><ows:Title>{product}</ows:Title><ows:Identifier>{product}</ows:Identifier>
              <ows:WGS84BoundingBox><ows:LowerCorner>19 59</ows:LowerCorner><ows:UpperCorner>32 71</ows:UpperCorner></ows:WGS84BoundingBox>
              <Style isDefault="true"><ows:Identifier>default</ows:Identifier></Style><Format>{mime}</Format>
              <TileMatrixSetLink><TileMatrixSet>ETRS-TM35FIN</TileMatrixSet></TileMatrixSetLink>
              <ResourceURL format="{mime}" resourceType="tile"
                template="{endpoint}{product}/default/{{TileMatrixSet}}/{{TileMatrix}}/{{TileRow}}/{{TileCol}}.{extension}"/>
              </Layer>'''.format(product=product, mime=mime, endpoint=self.endpoint, extension=extension))
        matrices = []
        for level in range(2):
            matrices.append('''<TileMatrix><ows:Identifier>{level}</ows:Identifier>
              <ScaleDenominator>{scale}</ScaleDenominator><TopLeftCorner>-548576 8388608</TopLeftCorner>
              <TileWidth>256</TileWidth><TileHeight>256</TileHeight>
              <MatrixWidth>{size}</MatrixWidth><MatrixHeight>{size}</MatrixHeight></TileMatrix>'''.format(
                  level=level, scale=8192 / (2 ** level) / 0.00028, size=2 ** level))
        return '''<?xml version="1.0" encoding="UTF-8"?>
          <Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1"
            xmlns:xlink="http://www.w3.org/1999/xlink" version="1.0.0">
          <ows:ServiceIdentification><ows:Title>MML fixture</ows:Title><ows:ServiceType>OGC WMTS</ows:ServiceType>
            <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion></ows:ServiceIdentification>
          <Contents>{layers}<TileMatrixSet><ows:Identifier>ETRS-TM35FIN</ows:Identifier>
            <ows:SupportedCRS>urn:ogc:def:crs:EPSG::3067</ows:SupportedCRS>{matrices}</TileMatrixSet></Contents>
          </Capabilities>'''.format(layers="".join(layers), matrices="".join(matrices))
