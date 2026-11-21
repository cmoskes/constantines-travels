"""Prepare and submit a draft PR containing only generated public files."""
import base64
import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_NAME = "cmoskes/constantines-travels"
API = f"https://api.github.com/repos/{REPO_NAME}"
PATH = re.compile(r"(?:assets/(?:collection-data\.js|(?:photo|thumb)-\d+-hq\.webp|pin-\d+\.jpg)|"
                  r"photos/photo-\d+\.html|destinations/[a-z-]+\.html|sitemap\.xml)")


def digest(content):
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def snapshot(site):
    return {name: digest(path.read_bytes()) for path in site.rglob("*")
            if path.is_file() and PATH.fullmatch(name := path.relative_to(site).as_posix())}


class GitHub:
    def __init__(self, token):
        if not isinstance(token, str) or not re.fullmatch(r"github_pat_[A-Za-z0-9_]{20,300}", token):
            raise ValueError("Enter a fine-grained GitHub access token.")
        self.token = token

    def request(self, route, data=None, *, missing=False):
        req = Request(API + route, data=None if data is None else json.dumps(data).encode(),
                      headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                               "Content-Type": "application/json", "User-Agent": "Constantines-Travels-Importer",
                               "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with build_opener(NoRedirect()).open(req, timeout=25) as response:
                return json.load(response)
        except HTTPError as error:
            if missing and error.code == 404:
                return None
            raise ValueError(f"GitHub returned HTTP {error.code}. Check repository access or retry if GitHub is busy.") from None
        except URLError:
            raise ValueError("GitHub could not be reached. Try again when your connection is available.") from None


def plan(github, paths, site, baseline, checkpoints):
    paths = sorted(set(paths))
    if not paths or any(PATH.fullmatch(path) is None for path in paths):
        raise ValueError("Approve a photo batch before preparing it for GitHub.")
    base = github.request("/branches/main")["commit"]
    tree = base["commit"]["tree"]["sha"]
    listing = github.request(f"/git/trees/{tree}?recursive=1")
    if listing["truncated"]:
        raise ValueError("GitHub could not return the complete website tree.")
    remote = {entry["path"]: entry["sha"] for entry in listing["tree"] if entry["type"] == "blob"}
    current = {path: digest((site / path).read_bytes()) for path in paths}
    known = [baseline, *({**baseline, **checkpoint} for checkpoint in checkpoints)]
    # Include the central catalog and sitemap in the comparison even when they are identical.
    if not any(all(remote.get(path) == candidate.get(path) for path in paths) for candidate in known):
        raise ValueError("The live branch has different website files from this preview. Reconcile the preview with main before sending a batch. The Mount Rainier repair must be in main first.")
    changed = [path for path in paths if remote.get(path) != current[path]]
    if not changed:
        raise ValueError("These preview files are already on GitHub main.")
    fingerprint = hashlib.sha256(json.dumps([base["sha"], current], sort_keys=True).encode()).hexdigest()
    return {"fingerprint": fingerprint, "files": changed, "base": base["sha"], "tree": tree, "current": current}


def submit(github, review, site):
    branch = "photos/review-" + review["fingerprint"][:20]
    query = urlencode({"state": "all", "head": f"cmoskes:{branch}", "base": "main"})
    previous = github.request("/pulls?" + query)
    if previous:
        if previous[0]["state"] == "open":
            return previous[0]["html_url"]
        raise ValueError("This exact review was already closed on GitHub. Reopen it there to continue.")
    tree_entries = []
    for path in review["files"]:
        content = (site / path).read_bytes()
        blob = github.request("/git/blobs", {"content": base64.b64encode(content).decode(), "encoding": "base64"})
        if blob["sha"] != review["current"][path]:
            raise ValueError("An uploaded file did not match the reviewed preview.")
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})

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
