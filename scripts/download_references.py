#!/usr/bin/env python3
"""Populate the ignored local reference cache using only the Python standard library."""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO


HTTP_USER_AGENT = "Savonia-reference-downloader/1.0"
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "docs" / "references" / "service-metadata"
MANIFEST = REFERENCE_DIR / "manifest.json"
RETRIEVALS = REFERENCE_DIR / "retrievals.json"


def load_manifest(path=MANIFEST):
    entries = json.loads(path.read_text(encoding="utf-8"))
    seen = set()
    for entry in entries:
        name = entry["path"]
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name
                or ":" in name or not relative.parts or name in seen):
            raise ValueError(f"Unsafe or duplicate reference path: {name}")
        if relative.suffix not in {".xml", ".xsd", ".pdf", ".xlsx"}:
            raise ValueError(f"Unsupported reference format: {name}")
        url = urlsplit(entry["url"])
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError(f"Reference URL must be public HTTPS: {name}")
        if any(key.lower() == "sykeuserid" for key, _ in parse_qsl(url.query)):
            raise ValueError(f"Keep SYKE_USER_ID outside the manifest: {name}")
        seen.add(name)
    return entries


def validate(data, name):
    """Reject error responses, including HTTP-200 OWS exceptions."""
    suffix = PurePosixPath(name).suffix
    if suffix in {".xml", ".xsd"}:
        try:
            root = ET.fromstring(data)
        except ET.ParseError as error:
            raise ValueError("Response is not well-formed XML") from error
        expected = ({"{http://www.w3.org/2001/XMLSchema}schema"} if suffix == ".xsd"
                    else {"{http://www.opengis.net/wfs/2.0}WFS_Capabilities",
                          "{http://www.opengis.net/wmts/1.0}Capabilities"})
        if root.tag not in expected:
            raise ValueError(f"Unexpected XML root {root.tag}; expected {expected}")
    elif suffix == ".pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise ValueError("Response is not a complete PDF")
    elif suffix == ".xlsx":
        try:
            with zipfile.ZipFile(BytesIO(data)) as workbook:
                if ("xl/workbook.xml" not in workbook.namelist()
                        or "[Content_Types].xml" not in workbook.namelist()
                        or workbook.testzip() is not None):
                    raise ValueError("Response is not a valid XLSX workbook")
        except (zipfile.BadZipFile, EOFError) as error:
            raise ValueError("Response is not a valid XLSX workbook") from error


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".download-", delete=False) as stream:
            temp_path = Path(stream.name)
            stream.write(data)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def request_url(url, syke_user_id):
    parts = urlsplit(url)
    if parts.hostname == "paikkatiedot.ymparisto.fi" and syke_user_id:
        query = parse_qsl(parts.query, keep_blank_values=True)
        query.append(("sykeuserid", syke_user_id))
        return urlunsplit(parts._replace(query=urlencode(query)))
    return url


def fetch(url, timeout, retries):
    for attempt in range(retries + 1):
        try:
            headers = {"User-Agent": HTTP_USER_AGENT}
            mml_key = os.environ.get("MML_API_KEY", "").strip()
            if urlsplit(url).hostname == "avoin-karttakuva.maanmittauslaitos.fi" and mml_key:
                headers["Authorization"] = "Basic " + base64.b64encode((mml_key + ":").encode("utf-8")).decode("ascii")
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as error:
            if attempt == retries or (error.code != 429 and error.code < 500):
                raise ValueError(f"HTTP {error.code}") from error
        except (URLError, TimeoutError, OSError, HTTPException) as error:
            if attempt == retries:
                # Do not print an exception URL containing the SYKE identifier.
                raise ValueError(f"Network request failed ({type(error).__name__})") from error
        time.sleep(min(2 ** attempt, 8))


def run(entries, destination=REFERENCE_DIR, refresh=False, timeout=45, retries=2):
    retrieval_path = destination / RETRIEVALS.name
    records = json.loads(retrieval_path.read_text(encoding="utf-8")) if retrieval_path.exists() else {}
    downloaded = skipped = failed = 0
    for entry in entries:
        name = entry["path"]
        target = destination / name
        try:
            # Prevent symlinked cache directories from writing outside the destination.
            target.resolve().relative_to(destination.resolve())
            if target.is_file() and not refresh:
                try:
                    validate(target.read_bytes(), name)
                except ValueError:
                    print(f"REPAIR {name}: invalid cached format")
                else:
                    print(f"CACHED {name}")
                    skipped += 1
                    continue
            data = fetch(request_url(entry["url"], os.environ.get("SYKE_USER_ID", "")), timeout, retries)
            validate(data, name)
            atomic_write(target, data)
            records[name] = {
                "url": entry["url"],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            # Persist provenance as downloads finish, including on a partial run.
            atomic_write(retrieval_path, (json.dumps(records, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
            downloaded += 1
            print(f"SAVED  {name} ({len(data)} bytes)")
        except (ValueError, OSError) as error:
            failed += 1
            print(f"FAILED {name}: {error}", file=sys.stderr)
    print(f"Downloaded {downloaded}; cached {skipped}; failed {failed}.")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List paths and public URLs without network access")
    parser.add_argument("--refresh", action="store_true", help="Replace cached files after successful validation")
    parser.add_argument("--only", default="", metavar="PREFIX", help="Select a relative path or prefix, e.g. syke/groundwater/")
    parser.add_argument("--timeout", type=float, default=45, help="Network socket timeout in seconds (default: 45)")
    parser.add_argument("--retries", type=int, default=2, help="Retries for transient network errors (default: 2)")
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.retries < 0:
        parser.error("--timeout must be positive and --retries must be nonnegative")
    try:
        entries = [entry for entry in load_manifest() if entry["path"].startswith(args.only)]
        if not entries:
            parser.error("--only did not match any reference path; use --list to see paths")
        if args.list:
            for entry in entries:
                print(f"{entry['path']}\n  {entry['url']}")
            return 0
        return run(entries, refresh=args.refresh, timeout=args.timeout, retries=args.retries)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Cannot load reference manifest or retrieval metadata: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled; completed downloads remain cached.", file=sys.stderr)
        sys.exit(130)
