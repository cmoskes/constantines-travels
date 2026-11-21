import tempfile
from copy import deepcopy
import unittest
from base64 import b64decode
from pathlib import Path

from github_review import digest, plan, publication_status, submit

CATALOG = "assets/collection-data.js"
PHOTO = "photos/photo-196.html"


class FakeGitHub:
    def __init__(self):
        self.main = "base"
        self.remote = {CATALOG: digest(b"original")}
        self.writes = []
        self.pull = []
        self.ref = None

    def request(self, route, data=None, *, missing=False):
        if data is not None:
            self.writes.append((route, data))
        if route == "/branches/main":
            return {"commit": {"sha": self.main, "commit": {"tree": {"sha": "base-tree"}}}}
        if route == "/git/trees/base-tree?recursive=1":
            return {"truncated": False, "tree": [
                {"path": path, "sha": sha, "type": "blob"} for path, sha in self.remote.items()
            ]}
        if route.startswith("/pulls?"):
            return self.pull
        if route == "/git/blobs":
            return {"sha": digest(b64decode(data["content"]))}
        if route == "/git/trees":
            return {"sha": "review-tree"}
        if route.startswith("/git/ref/heads/photos/review-"):
            return self.ref
        if route == "/git/commits":
            return {"sha": "review-commit"}
        if route == "/git/refs":
            self.ref = {"object": {"sha": data["sha"]}}
            return self.ref
        if route == "/pulls":
            self.pull = [{"state": "open", "html_url": "https://example.test/pull/1"}]
            return self.pull[0]
        raise AssertionError((route, data))


class GitHubReviewTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.site = Path(temporary.name)
        for path, data in ((CATALOG, b"new catalog"), (PHOTO, b"new photo")):
            target = self.site / path
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
        self.github = FakeGitHub()
        self.baseline = {CATALOG: digest(b"original")}

    def review(self, checkpoints=()):
        return plan(self.github, [CATALOG, PHOTO], self.site, self.baseline, checkpoints)

    def test_read_only_plan_and_confirmed_draft(self):
        review = self.review()
        self.assertEqual(review["files"], [CATALOG, PHOTO])
        self.assertEqual(self.github.writes, [])
        url = submit(self.github, review, self.site)
        self.assertEqual(url, "https://example.test/pull/1")
        self.assertEqual(len(self.github.writes), 6)
        pulls = self.github.writes[-1][1]
        self.assertTrue(pulls["draft"])
        self.assertEqual(pulls["base"], "main")
        self.assertTrue(pulls["head"].startswith("photos/review-"))
        self.assertTrue(self.github.writes[-2][1]["ref"].startswith("refs/heads/photos/review-"))
        self.assertEqual(submit(self.github, review, self.site), url)
        self.assertEqual(len(self.github.writes), 6)

    def test_conflicts_and_later_batches(self):
        first = self.review()
        self.github.remote[CATALOG] = digest(b"unrelated edit")
        with self.assertRaisesRegex(ValueError, "different website files"):
            self.review()
        self.assertEqual(self.github.writes, [])

        self.github.remote = first["current"]
        self.github.main = "merged"
        with self.assertRaisesRegex(ValueError, "already on GitHub main"):
            self.review([first["current"]])
        (self.site / CATALOG).write_bytes(b"another batch")
        next_review = self.review([first["current"]])
        self.assertEqual(next_review["files"], [CATALOG])
        self.assertNotEqual(next_review["fingerprint"], first["fingerprint"])

    def test_resume_blob_upload(self):
        review = self.review()
        remembered = []
        self.assertIsNotNone(submit(self.github, review, self.site, [review["current"][CATALOG]], remembered.append))
        self.assertEqual(remembered, [review["current"][PHOTO]])

    def test_publication_requires_matching_photo_and_image(self):
        image = "assets/photo-196-hq.webp"
        (self.site / image).write_bytes(b"optimized image")
        receipts = {"sample": {"photos": [{"path": PHOTO, "image": image}]}}
        draft = {"sample": {"status": "review", "url": "https://example.test/pull/1"}}
        remote = {PHOTO: digest(b"new photo"), image: digest(b"wrong image")}
        self.assertEqual(publication_status(remote, receipts, self.site, deepcopy(draft)), draft)
        remote[image] = digest(b"optimized image")
        self.assertEqual(publication_status(remote, receipts, self.site, draft)["sample"]["status"], "published")
        del remote[PHOTO]
        self.assertEqual(publication_status(remote, receipts, self.site, {})["sample"]["status"], "pending")

    def test_excludes_tooling(self):
        with self.assertRaisesRegex(ValueError, "Approve a photo batch"):
            plan(self.github, [".github/photo-import/app.py"], self.site, self.baseline, [])
        self.assertEqual(self.github.writes, [])


if __name__ == "__main__":
    unittest.main()
