"""Downloader acceptance checks using a local HTTP server, never provider services."""

from contextlib import redirect_stderr, redirect_stdout
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
import zipfile


SPEC = importlib.util.spec_from_file_location("download_references", Path(__file__).resolve().parents[1] / "download_references.py")
downloader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(downloader)
SCHEMA = b'<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"/>'
CAPABILITIES = b'<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0"/>'
OWS_ERROR = b'<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1"/>'


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                cls.requests.append(self.path)
                responses = cls.responses[self.path]
                status, body = responses.pop(0) if len(responses) > 1 else responses[0]
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.responses = type(self).responses = {}
        self.requests = type(self).requests = []
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name)

    def entry(self, name, responses):
        route = "/" + name
        self.responses[route] = responses
        return {"path": name, "url": f"http://127.0.0.1:{self.server.server_port}{route}"}

    def run_downloads(self, entries, **kwargs):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            return downloader.run(entries, destination=self.destination, timeout=2, retries=0, **kwargs)

    def test_download_cache_and_explicit_refresh_with_provenance(self):
        entry = self.entry("provider/type.xsd", [(200, SCHEMA)])
        self.assertEqual(self.run_downloads([entry]), 0)
        records = json.loads((self.destination / "retrievals.json").read_text())
        self.assertEqual(records[entry["path"]]["url"], entry["url"])
        self.assertEqual(records[entry["path"]]["sha256"], hashlib.sha256(SCHEMA).hexdigest())
        self.assertTrue(records[entry["path"]]["retrieved_at"].endswith("+00:00"))
        self.assertEqual(self.run_downloads([entry]), 0)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.run_downloads([entry], refresh=True), 0)
        self.assertEqual(len(self.requests), 2)

    def test_failed_refresh_keeps_existing_file_and_provenance_and_continues(self):
        good = self.entry("existing.xsd", [(200, SCHEMA)])
        self.assertEqual(self.run_downloads([good]), 0)
        metadata = (self.destination / "retrievals.json").read_bytes()
        self.responses["/existing.xsd"] = [(200, OWS_ERROR)]
        other = self.entry("other.xml", [(200, CAPABILITIES)])
        self.assertEqual(self.run_downloads([good, other], refresh=True), 1)
        self.assertEqual((self.destination / "existing.xsd").read_bytes(), SCHEMA)
        self.assertEqual((self.destination / "other.xml").read_bytes(), CAPABILITIES)
        current = json.loads((self.destination / "retrievals.json").read_bytes())
        self.assertEqual(current["existing.xsd"], json.loads(metadata)["existing.xsd"])
        self.assertEqual(list(self.destination.glob(".download-*")), [])

    def test_invalid_cache_is_repaired_but_older_valid_cache_has_no_invented_date(self):
        (self.destination / "bad.xsd").write_bytes(b"<html>Error</html>")
        bad = self.entry("bad.xsd", [(200, SCHEMA)])
        (self.destination / "old.xsd").write_bytes(SCHEMA)
        old = self.entry("old.xsd", [(500, b"unused")])
        self.assertEqual(self.run_downloads([bad, old]), 0)
        self.assertEqual(self.requests, ["/bad.xsd"])
        self.assertNotIn("old.xsd", json.loads((self.destination / "retrievals.json").read_bytes()))

    def test_html_instead_of_pdf_and_http_failures_are_not_saved(self):
        entries = [self.entry("error.pdf", [(200, b"<html>Error</html>")]),
                   self.entry("missing.xsd", [(404, b"Not found")])]
        self.assertEqual(self.run_downloads(entries), 1)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_only_transient_http_failures_are_retried(self):
        retry = self.entry("retry.xsd", [(503, b"Busy"), (200, SCHEMA)])
        missing = self.entry("missing.xsd", [(404, b"Not found")])
        with patch.object(downloader.time, "sleep"):
            self.assertEqual(downloader.fetch(retry["url"], timeout=2, retries=1), SCHEMA)
            with self.assertRaisesRegex(ValueError, "HTTP 404"):
                downloader.fetch(missing["url"], timeout=2, retries=2)
        self.assertEqual(self.requests.count("/retry.xsd"), 2)
        self.assertEqual(self.requests.count("/missing.xsd"), 1)

    def test_binary_validation_rejects_truncated_downloads(self):
        downloader.validate(b"%PDF-1.7\nfixture\n%%EOF", "valid.pdf")
        with self.assertRaises(ValueError):
            downloader.validate(b"%PDF-1.7\ntruncated", "broken.pdf")
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("xl/workbook.xml", "<workbook/>")
            archive.writestr("[Content_Types].xml", "<Types/>")
        downloader.validate(stream.getvalue(), "valid.xlsx")
        with self.assertRaises(ValueError):
            downloader.validate(stream.getvalue()[:30], "broken.xlsx")

    def test_wmts_capabilities_are_cached_and_exception_reports_rejected(self):
        capabilities = b'<Capabilities xmlns="http://www.opengis.net/wmts/1.0"/>'
        entry = self.entry("mml/wmts/get-capabilities.xml", [(200, capabilities)])
        self.assertEqual(self.run_downloads([entry]), 0)
        self.assertEqual(self.run_downloads([entry]), 0)
        self.assertEqual(len(self.requests), 1)
        self.responses["/mml/wmts/get-capabilities.xml"] = [(200, OWS_ERROR)]
        self.assertEqual(self.run_downloads([entry], refresh=True), 1)
        self.assertEqual((self.destination / entry["path"]).read_bytes(), capabilities)

    def test_mml_key_is_sent_only_to_map_service_as_basic_auth(self):
        with patch.dict(downloader.os.environ, {"MML_API_KEY": "private-key"}):
            with patch.object(downloader, "urlopen") as opened:
                opened.return_value.__enter__.return_value.read.return_value = CAPABILITIES
                for url, expected in (
                    ("https://avoin-karttakuva.maanmittauslaitos.fi/avoin/wmts/1.0.0/WMTSCapabilities.xml",
                     "Basic " + base64.b64encode(b"private-key:").decode()),
                    ("https://example.org/capabilities.xml", None),
                ):
                    downloader.fetch(url, 2, 0)
                    request = opened.call_args.args[0]
                    self.assertEqual(request.get_header("Authorization"), expected)
                    self.assertNotIn("private-key", request.full_url)

    def test_identifier_is_only_sent_to_syke_wfs_and_not_logged(self):
        url = "https://paikkatiedot.ymparisto.fi/geoserver/test/wfs?service=WFS"
        self.assertIn("sykeuserid=example+id", downloader.request_url(url, "example id"))
        other = "https://www.metsakeskus.fi/test.pdf"
        self.assertEqual(downloader.request_url(other, "example id"), other)
        entry = self.entry("schema.xsd", [(200, SCHEMA)])
        entry["url"] = url
        with patch.dict(downloader.os.environ, {"SYKE_USER_ID": "private-id"}), patch.object(downloader, "fetch", return_value=SCHEMA) as fetch:
            self.assertEqual(self.run_downloads([entry]), 0)
        self.assertIn("sykeuserid=private-id", fetch.call_args.args[0])
        self.assertNotIn("private-id", (self.destination / "retrievals.json").read_text())

    def test_manifest_paths_and_offline_listing(self):
        entries = downloader.load_manifest()
        self.assertEqual(len(entries), 29)
        self.assertEqual(len([entry for entry in entries if entry["path"].startswith("syke/shoreline/")]), 4)
        with patch.object(downloader, "fetch", side_effect=AssertionError("Listing must work offline")), redirect_stdout(StringIO()) as output:
            self.assertEqual(downloader.main(["--list", "--only", "syke/groundwater/"]), 0)
        self.assertIn("groundwater/describe-feature-type.xsd", output.getvalue())
        manifest = self.destination / "manifest.json"
        for name in ("../outside.xsd", "C:/outside.xsd", "bad\\file.xsd"):
            manifest.write_text(json.dumps([{"path": name, "url": "https://example.org/schema"}]))
            with self.assertRaises(ValueError):
                downloader.load_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
