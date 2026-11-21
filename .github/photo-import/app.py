"""Run the local photo importer. Approved batches go to a separate preview."""
import argparse
import fcntl
import io
import json
import mimetypes
import re
import shutil
import tempfile
import threading
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageCms

from generate import catalog, generate, optimize, pinterest_csv

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]
MAX_FILE = 100 * 1024 * 1024
KEY = re.compile(r"[a-f0-9-]{36}")
DEFAULT_WORKSPACE = Path.home() / "Library" / "Application Support" / "Constantines Travels Importer"


class Workspace:
    def __init__(self, directory):
        self.directory = directory
        if directory == REPO or REPO in directory.parents:
            raise ValueError("Choose a preview workspace outside the checkout.")
        directory.mkdir(parents=True, exist_ok=True)
        self.lock = (directory / ".lock").open("a")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.current = directory / "current"
        self.batches = {}
        if not self.current.is_symlink():
            version = self.new_version()
            for folder in ("assets", "destinations", "photos", "stories"):
                shutil.copytree(REPO / folder, version / "site" / folder)
            for source in [*REPO.glob("*.html"), REPO / "sitemap.xml", REPO / "robots.txt", REPO / ".nojekyll"]:
                shutil.copyfile(source, version / "site" / source.name)
            self.activate(version, {"receipts": {}, "changes": []})

    def new_version(self):
        return Path(tempfile.mkdtemp(prefix="preview-", dir=self.directory))

    def activate(self, version, state):
        (version / "state.json").write_text(json.dumps(state, ensure_ascii=False))
        previous = self.current.resolve() if self.current.is_symlink() else None
        temporary = version / ".current"
        temporary.symlink_to(version)
        temporary.replace(self.current)
        if previous and previous.parent == self.directory and previous.name.startswith("preview-"):
            shutil.rmtree(previous, ignore_errors=True)

    @property
    def site(self):
        return self.current / "site"

    def state(self):
        return json.loads((self.current / "state.json").read_text())

    def begin(self, request):
        batch_id, keys = request.get("batch"), request.get("files")
        if (not is_key(batch_id) or not isinstance(keys, list) or not 1 <= len(keys) <= 500
                or not all(is_key(key) for key in keys) or len(set(keys)) != len(keys)):
            raise ValueError("Select 1–500 photographs.")
        if batch_id in self.state()["receipts"]:
            raise ValueError("This batch was already approved.")
        if batch_id in self.batches:
            if self.batches[batch_id]["keys"] != set(keys):
                raise ValueError("The queued files have changed. Start a new batch.")
            return
        self.batches[batch_id] = {"keys": set(keys), "uploads": {}}

    def upload(self, batch_id, key, source, temporary):
        batch = self.batches.get(batch_id)
        if batch is None or key not in batch["keys"]:
            raise ValueError("This photograph is outside the current batch.")
        uploads = batch["uploads"]
        uploads.pop(key, None)
        output = temporary / batch_id / key
        try:
            sizes = optimize(source, output)
        except (OSError, ValueError, SyntaxError, ImageCms.PyCMSError,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ValueError("This file could not be opened or converted. Try exporting it again from Apple Photos.") from error
        uploads[key] = {"directory": output, **sizes}
        return {"preview": f"/thumbnail/{batch_id}/{key}"}

    def approve(self, request):
        batch_id = request.get("batch")
        if not is_key(batch_id):
            raise ValueError("Invalid batch.")
        state = self.state()
        if batch_id in state["receipts"]:
            return state["receipts"][batch_id]
        batch = self.batches.get(batch_id)
        rows = request.get("photos")
        if (batch is None or not isinstance(rows, list)
                or not all(isinstance(row, dict) and is_key(row.get("key")) for row in rows)
                or len(rows) != len(batch["keys"]) or {row["key"] for row in rows} != batch["keys"]
                or batch["uploads"].keys() != batch["keys"]):
            raise ValueError("Every submitted photograph must be processed before approval.")
        if any(not isinstance(row.get(field), str) or len(row[field]) > limit for row in rows
               for field, limit in (("filename", 1024), ("title", 100), ("alt", 500))):
            raise ValueError("Photo text is too long.")

        version = self.new_version()
        try:
            site = version / "site"
            shutil.copytree(self.site, site)
            photos, changes = generate(site, request.get("group"), rows, batch["uploads"])
            for photo, row in zip(photos, rows, strict=True):
                photo["filename"] = row["filename"]
            receipt = {
                "batch": batch_id, "submitted": len(rows), "imported": len(photos), "gallery": photos[0]["group"].split("|", 1)[0],
                "photos": photos,
            }
            state["receipts"][batch_id] = receipt
            state["changes"] = sorted(set(state["changes"]) | changes)
            self.activate(version, state)
        except Exception:
            shutil.rmtree(version, ignore_errors=True)
            raise
        del self.batches[batch_id]
        return receipt


def is_key(value):
    return isinstance(value, str) and KEY.fullmatch(value) is not None


class Handler(BaseHTTPRequestHandler):
    def send_headers(self, length, kind, *, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def respond(self, payload, kind, *, status=200, headers=None):
        self.send_headers(len(payload), kind, status=status, headers=headers)
        self.wfile.write(payload)

    def json(self, value, status=200):
        self.respond(json.dumps(value, ensure_ascii=False).encode(), "application/json; charset=utf-8", status=status)

    def file(self, path, headers=None):
        if not path.is_file():
            self.send_error(404)
            return
        with path.open("rb") as source:
            self.send_headers(path.stat().st_size, mimetypes.guess_type(path)[0] or "application/octet-stream", headers=headers)
            shutil.copyfileobj(source, self.wfile)

    def valid_host(self):
        return self.headers.get("Host") == self.server.address

    def do_GET(self):
        if not self.valid_host():
            self.send_error(403)
            return
        path = unquote(urlsplit(self.path).path)
        space = self.server.workspace
        if path in ("/", "/import.css", "/import.js"):
            return self.file(TOOL / (path[1:] or "index.html"))
        if path == "/api/state":
            groups = catalog(space.site)["groups"]
            return self.json({"groups": groups, "receipts": list(space.state()["receipts"].values())})
        if path.startswith("/preview/"):
            site = space.site.resolve()
            target = (site / (path.removeprefix("/preview/") or "index.html")).resolve()
            if target.is_relative_to(site):
                return self.file(target, {"Content-Security-Policy": "script-src 'self' 'unsafe-inline'; connect-src 'self'"})
        match = re.fullmatch(r"/thumbnail/([a-f0-9-]{36})/([a-f0-9-]{36})", path)
        if match:
            upload = space.batches.get(match[1], {}).get("uploads", {}).get(match[2])
            if upload:
                return self.file(upload["directory"] / "thumb.webp")
        if path in ("/downloads/pinterest.csv", "/downloads/site-changes.zip"):
            state = space.state()
            photos = [photo for receipt in state["receipts"].values() for photo in receipt["photos"]]
            if path.endswith(".csv"):
                return self.respond(pinterest_csv(photos), "text/csv; charset=utf-8",
                                    headers={"Content-Disposition": 'attachment; filename="pinterest.csv"'})
            with tempfile.TemporaryFile() as output:
                with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name in state["changes"]:
                        archive.write(space.site / name, name)
                length = output.tell()
                output.seek(0)
                self.send_headers(length, "application/zip",
                                  headers={"Content-Disposition": 'attachment; filename="site-changes.zip"'})
                shutil.copyfileobj(output, self.wfile)
                return
        self.send_error(404)

    def do_POST(self):
        # Accept browser writes only from the loopback app itself.
        if (not self.valid_host() or self.headers.get("Origin") != f"http://{self.server.address}"
                or self.headers.get("X-Photo-Importer") != "1"):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        space = self.server.workspace
        try:
            length = int(self.headers.get("Content-Length", "0"))
            match = re.fullmatch(r"/api/upload/([a-f0-9-]{36})/([a-f0-9-]{36})", path)
            limit = MAX_FILE if match else 1024 * 1024
            if not 0 < length <= limit:
                raise ValueError("The file is empty or exceeds the 100 MB limit." if match else "Invalid batch request.")
            self.connection.settimeout(60)
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("The upload was interrupted. Please retry it.")
            if match:
                return self.json(space.upload(match[1], match[2], io.BytesIO(body), self.server.staging))
            request = json.loads(body)
            if not isinstance(request, dict):
                raise ValueError("Invalid batch request.")
            if path == "/api/begin":
                space.begin(request)
                return self.json({"ready": True})
            if path == "/api/discard" and is_key(request.get("batch")):
                space.batches.pop(request["batch"], None)
                shutil.rmtree(self.server.staging / request["batch"], ignore_errors=True)
                return self.json({"discarded": True})
            if path == "/api/approve":
                receipt = space.approve(request)
                shutil.rmtree(self.server.staging / receipt["batch"], ignore_errors=True)
                return self.json(receipt)
            self.send_error(404)
        except ValueError as error:
            self.json({"error": str(error)}, 400)
        except Exception as error:
            self.log_error("%r", error)
            self.json({"error": "The operation failed. Your approved preview is still available. You can retry."}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--open", action="store_true", help="Open the importer in the default browser.")
    args = parser.parse_args()
    directory = args.workspace.expanduser().resolve()
    with HTTPServer(("127.0.0.1", args.port), Handler) as server, tempfile.TemporaryDirectory() as temp:
        server.address = f"127.0.0.1:{server.server_port}"
        server.workspace = Workspace(directory)
        server.staging = Path(temp)
        url = f"http://{server.address}/"
        print(f"Photo importer available at {url}", flush=True)
        if args.open:
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
