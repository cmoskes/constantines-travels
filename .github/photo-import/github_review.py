"""Prepare and submit a draft PR containing only generated public files."""
import base64
import hashlib
import json
import re
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_NAME = "cmoskes/constantines-travels"
API = f"https://api.github.com/repos/{REPO_NAME}"
PATH = re.compile(r"(?:assets/(?:collection-data\.js|(?:photo|thumb)-\d+-hq\.webp|pin-\d+\.jpg)|"
                  r"photos/photo-\d+\.html|destinations/[a-z0-9-]+\.html|sitemap\.xml|index\.html)")


# Verified Git blob IDs for the standalone repair in commit 6f71c58.
RAINIER_REPAIR = {
    "assets/collection-data.js": ("94bc3010b311a73da909b64ddba714bf8692a7e1", "d23585cc1981111e964137b4acb3939a6d6d9a6f"),
    "destinations/mount-rainier-national-park.html": ("0c8bd299ddab7d0f0bd26990a66c9d5b22f6886d", "9605b56204f325631407e9a3e8bb2e91feb5dce5"),
    "photos/photo-114.html": (None, "9a2c722977118d196abfaeeacec45bdfccdabcdd"),
    "photos/photo-115.html": (None, "692195a16e2a1af5c60c4550ee114ba883dd5444"),
    "photos/photo-117.html": (None, "66b816e366ee27485f26b9777eeb1d9bf7d3440c"),
}


def digest(content):
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def snapshot(site, only=None):
    return {name: digest(path.read_bytes()) for path in site.rglob("*")
            if path.is_file() and PATH.fullmatch(name := path.relative_to(site).as_posix())
            and (only is None or name in only)}


class GitHub:
    def __init__(self, token):
        if not isinstance(token, str) or not re.fullmatch(r"github_pat_[A-Za-z0-9_]{20,300}", token):
            raise ValueError("Enter a fine-grained GitHub access token.")
        self.token = token
        self.last_write = 0

    def request(self, route, data=None, *, missing=False):
        if data is not None:
            time.sleep(max(0, 1.1 - (time.monotonic() - self.last_write)))
            self.last_write = time.monotonic()
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                   "Content-Type": "application/json", "User-Agent": "Constantines-Travels-Importer",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if sys.platform == "darwin":
            return self.mac_request(route, headers, data, missing=missing)
        req = Request(API + route, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with build_opener(NoRedirect()).open(req, timeout=25) as response:
                return json.load(response)
        except HTTPError as error:
            return github_http_error(error.code, missing=missing,
                                     rate_limited=bool(error.headers.get("Retry-After")))
        except (URLError, TimeoutError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            if isinstance(reason, ssl.SSLCertVerificationError):
                message = "Python could not verify GitHub’s HTTPS certificate."
            elif isinstance(reason, TimeoutError):
                message = "The GitHub API request timed out."
            elif isinstance(reason, OSError) and reason.strerror and reason.errno is not None:
                message = f"The GitHub API connection failed ({type(reason).__name__}, error {reason.errno}: {reason.strerror})."
            else:
                message = f"The GitHub API connection failed ({type(reason).__name__})."
            raise ValueError(message) from None

    def mac_request(self, route, headers, data, *, missing):
        # Use the macOS HTTPS client so certificate trust matches a system curl check.
        # The token and payload travel via stdin, never in the process arguments.
        config = [f"header = {json.dumps(f'{key}: {value}')}" for key, value in headers.items()]
        if data is not None:
            config.append(f"data-binary = {json.dumps(json.dumps(data))}")
        try:
            result = subprocess.run(
                ["/usr/bin/curl", "--disable", "--silent", "--show-error", "--proto", "=https",
                 "--max-time", "25", "--write-out", "\n%{http_code}", "--config", "-", API + route],
                input="\n".join(config) + "\n", capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30, check=False,
            )
        except FileNotFoundError:
            raise ValueError("The macOS HTTPS client was not found at /usr/bin/curl.") from None
        except subprocess.TimeoutExpired:
            raise ValueError("The GitHub API request timed out.") from None
        if result.returncode:
            proxy_status = re.search(r"CONNECT tunnel failed, response ([1-5][0-9]{2})", result.stderr)
            if proxy_status:
                raise ValueError(f"The network proxy refused GitHub’s HTTPS tunnel (HTTP {proxy_status[1]}).")
            details = {
                5: "macOS could not resolve the configured proxy.",
                6: "macOS could not resolve api.github.com.",
                7: "macOS could not connect to api.github.com.",
                28: "The GitHub API request timed out.",
                35: "macOS could not establish a secure HTTPS connection to GitHub.",
                60: "macOS could not verify GitHub’s HTTPS certificate.",
                77: "The macOS HTTPS client could not read its configured certificate file.",
            }.get(result.returncode, "The macOS HTTPS client could not complete the GitHub request.")
            raise ValueError(f"{details} (curl error {result.returncode})")
        body, _, status = result.stdout.rpartition("\n")
        if not re.fullmatch(r"[1-5][0-9]{2}", status):
            raise ValueError("The macOS HTTPS client returned no valid HTTP status for GitHub.")
        if not status.startswith("2"):
            return github_http_error(int(status), missing=missing, rate_limited=(
                int(status) == 403 and "rate limit" in body.lower()
            ))
        try:
            return json.loads(body)
        except ValueError:
            raise ValueError("GitHub returned a response that was not valid API JSON.") from None


def github_http_error(status, *, missing, rate_limited=False):
    if missing and status == 404:
        return None
    if status == 429 or rate_limited:
        raise ValueError(f"GitHub limited the request (HTTP {status}). Wait a few minutes and try again.")
    details = {
        401: "GitHub rejected the token. Check whether it expired or was copied completely.",
        403: "GitHub denied access. Check that the token covers Constantine’s Travels and has the required permissions.",
        404: "GitHub could not find the repository or branch with this token. Check the selected repository and its permissions.",
        422: "GitHub rejected the requested change. Check GitHub for an existing review and retry.",
    }.get(status, "GitHub rejected the API request.")
    raise ValueError(f"{details} (HTTP {status})")


def main_tree(github):
    base = github.request("/branches/main")["commit"]
    tree = base["commit"]["tree"]["sha"]
    listing = github.request(f"/git/trees/{tree}?recursive=1")
    if listing["truncated"]:
        raise ValueError("GitHub could not return the complete website tree.")
    return base, {entry["path"]: entry["sha"] for entry in listing["tree"] if entry["type"] == "blob"}


def publication_status(remote, receipts, site, previous):
    result = {}
    for batch_id, receipt in receipts.items():
        photos = receipt["photos"]
        confirmed = bool(photos) and all(
            photo["path"] in remote
            and remote.get(photo["image"]) == (photo.get("git_image") or digest((site / photo["image"]).read_bytes()))
            for photo in photos
        )
        if confirmed:
            result[batch_id] = {"status": "published"}
        elif previous.get(batch_id, {}).get("status") in {"review", "closed"}:
            result[batch_id] = previous[batch_id]
        else:
            result[batch_id] = {"status": "pending"}
    return result


def refresh_drafts(github, publications):
    checked = {}
    for info in publications.values():
        if info["status"] not in {"review", "closed"}:
            continue
        number = re.fullmatch(r"https://github.com/cmoskes/constantines-travels/pull/(\d+)", info.get("url", ""))
        if not number:
            continue
        if number[1] not in checked:
            checked[number[1]] = github.request(f"/pulls/{number[1]}")["state"]
        info["status"] = "review" if checked[number[1]] == "open" else "closed"


def plan(github, paths, site, baseline, checkpoints, remote_tree=None):
    paths = sorted(set(paths))
    if not paths or any(PATH.fullmatch(path) is None for path in paths):
        raise ValueError("Approve a photo batch before preparing it for GitHub.")
    base, remote = remote_tree or main_tree(github)
    tree = base["commit"]["tree"]["sha"]
    known = [baseline, *({**baseline, **checkpoint} for checkpoint in checkpoints)]
    # A batch started from the repaired preview. If main still has the exact
    # pre-repair files, review the repair and batch together as one change.
    if not any(all(remote.get(path) == candidate.get(path) for path in paths) for candidate in known):
        repair_matches = all(
            remote.get(path) == before and baseline.get(path) == after
            and (path in paths or ((site / path).is_file() and digest((site / path).read_bytes()) == after))
            for path, (before, after) in RAINIER_REPAIR.items()
        )
        other_paths_match = all(remote.get(path) == baseline.get(path) for path in paths if path not in RAINIER_REPAIR)
        if not (repair_matches and other_paths_match):
            raise ValueError("GitHub main has website edits that differ from this preview. The importer stopped to protect those edits.")
        paths = sorted(set(paths) | RAINIER_REPAIR.keys())
    current = {path: digest((site / path).read_bytes()) for path in paths}
    changed = [path for path in paths if remote.get(path) != current[path]]
    if not changed:
        raise ValueError("These preview files are already on GitHub main.")
    fingerprint = hashlib.sha256(json.dumps([base["sha"], current], sort_keys=True).encode()).hexdigest()
    return {"fingerprint": fingerprint, "files": changed, "base": base["sha"], "tree": tree, "current": current}


def submit(github, review, site, previous_blobs=(), remember=None):
    branch = "photos/review-" + review["fingerprint"][:20]
    query = urlencode({"state": "all", "head": f"cmoskes:{branch}", "base": "main"})
    previous = github.request("/pulls?" + query)
    if previous:
        if previous[0]["state"] == "open":
            return previous[0]["html_url"]
        raise ValueError("This exact review was already closed on GitHub. Reopen it there to continue.")
    tree_entries = []
    uploaded = set(previous_blobs)
    for path in review["files"]:
        content = (site / path).read_bytes()
        expected = review["current"][path]
        if digest(content) != expected:
            raise ValueError("A file no longer matches the reviewed preview.")
        if expected not in uploaded:
            blob = github.request("/git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
            if blob["sha"] != expected:
                raise ValueError("An uploaded file did not match the reviewed preview.")
            uploaded.add(expected)
            if remember:
                remember(expected)
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": expected})

    tree = github.request("/git/trees", {"base_tree": review["tree"], "tree": tree_entries})["sha"]
    ref = github.request(f"/git/ref/heads/{branch}", missing=True)
    if ref:
        # A previous attempt may have created the branch just before its connection dropped.
        commit = github.request(f'/git/commits/{ref["object"]["sha"]}')
        if commit["tree"]["sha"] != tree or [parent["sha"] for parent in commit["parents"]] != [review["base"]]:
            raise ValueError("The review branch changed on GitHub. Open GitHub to check it.")
    else:
        commit = github.request("/git/commits", {"message": "Add approved travel photographs",
                                                "tree": tree, "parents": [review["base"]]})
        github.request("/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
    if github.request("/branches/main")["commit"]["sha"] != review["base"]:
        raise ValueError("Main changed during upload. Check the preview again before opening a pull request.")
    pull = github.request("/pulls", {
        "base": "main", "head": branch, "draft": True, "title": "Review travel photo additions",
        "body": "Generated from an approved local gallery preview. Review the changes and merge only when ready to publish.",
    })
    return pull["html_url"]
