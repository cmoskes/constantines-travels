import io
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

from PIL import Image

from app import REPO, Workspace
from generate import catalog, pinterest_csv

GROUP = "destinations/mount-rainier-national-park.html|Arriving at Mount Rainier"


class ImportTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = Workspace(self.root / "preview")
        self.addCleanup(self.workspace.lock.close)

    def test_restore_rainier_links_and_order(self):
        data = catalog(self.workspace.site)
        group = next(item for item in data["groups"] if item["key"] == GROUP)
        self.assertEqual(group["ids"][:6], ["113", "114", "115", "116", "117", "118"])
        for ident in ("114", "115", "117"):
            self.assertTrue((self.workspace.site / data["photos"][ident]["path"]).is_file())
            with Image.open(REPO / f"assets/photo-{ident}-hq.webp") as image:
                self.assertEqual(image.size, (2048, 1365))
                image.verify()

    def test_new_destination_batch_and_duplicate_history(self):
        source = io.BytesIO()
        Image.new("RGB", (80, 60), "#28704c").save(source, format="JPEG")
        image = source.getvalue()

        def album(size, group, name=""):
            batch = str(uuid4())
            keys = [str(uuid4()) for _ in range(size)]
            self.workspace.begin({"batch": batch, "files": keys})
            rows = []
            for number, key in enumerate(keys):
                result = self.workspace.upload(batch, key, io.BytesIO(image), self.root / "uploads")
                rows.append({"key": key, "filename": f"Export {number}.jpg", "title": "", "alt": ""})
            return self.workspace.approve({"batch": batch, "group": group, "gallery_name": name, "photos": rows}), result

        receipt, last = album(100, "new-destination", "Côte & Mountains 2026")
        self.assertEqual(receipt["submitted"], 100)
        self.assertEqual(receipt["imported"], 100)
        self.assertEqual(len({photo["url"] for photo in receipt["photos"]}), 100)
        self.assertEqual(len({photo["source_hash"] for photo in receipt["photos"]}), 1)
        self.assertEqual(last["prior_matches"], [])
        path = receipt["gallery"]
        gallery = (self.workspace.site / path).read_text()
        self.assertEqual(gallery.count("data-photo-id="), 100)
        self.assertIn("Côte &amp; Mountains 2026", (self.workspace.site / "index.html").read_text())
        self.assertNotIn(path, (REPO / "index.html").read_text())
        self.assertIn(path, (self.workspace.site / "sitemap.xml").read_text())
        followup, found = album(1, "new-group:" + path, "Coast morning")
        self.assertIn("Export 0.jpg", found["prior_matches"])
        self.assertEqual(followup["imported"], 1)
        self.assertIn('data-filter="Coast morning"', (self.workspace.site / path).read_text())
        self.assertIn(followup["photos"][0]["path"],
                      (self.workspace.site / receipt["photos"][-1]["path"]).read_text())

    def test_approve_all_files_once_and_keep_checkout_unchanged(self):
        batch, first, second = (str(uuid4()) for _ in range(3))
        self.workspace.begin({"batch": batch, "files": [first, second]})
        source = REPO / "assets/photo-114-hq.webp"
        original = source.read_bytes()
        self.workspace.upload(batch, first, io.BytesIO(original), self.root / "uploads")
        with self.assertRaisesRegex(ValueError, "could not be opened"):
            self.workspace.upload(batch, second, io.BytesIO(b"bad image"), self.root / "uploads")
        rows = [
            {"key": second, "filename": "second.webp", "title": 'A & B < C', "alt": "Park entrance"},
            {"key": first, "filename": "first.webp", "title": "", "alt": ""},
        ]
        request = {"batch": batch, "group": GROUP, "photos": rows}
        previous = self.workspace.current.resolve()
        old_index = (previous / "site/index.html").read_bytes()
        old_sitemap = (previous / "site/sitemap.xml").read_bytes()
        with self.assertRaisesRegex(ValueError, "Every submitted"):
            self.workspace.approve(request)
        self.assertEqual(self.workspace.current.resolve(), previous)
        self.workspace.upload(batch, second, io.BytesIO(original), self.root / "uploads")
        with self.assertRaisesRegex(ValueError, "Every submitted"):
            self.workspace.approve({**request, "photos": rows[:1]})
        with self.assertRaisesRegex(ValueError, "Choose an existing"):
            self.workspace.approve({**request, "group": "unknown"})
        self.assertEqual(self.workspace.current.resolve(), previous)
        self.assertEqual((previous / "site/index.html").read_bytes(), old_index)
        self.assertEqual((previous / "site/sitemap.xml").read_bytes(), old_sitemap)

        receipt = self.workspace.approve(request)
        self.assertEqual(receipt["submitted"], 2)
        self.assertEqual(receipt["imported"], 2)
        self.assertEqual(self.workspace.approve(request), receipt)
        site = self.workspace.site
        first_page, second_page = receipt["photos"]
        self.assertEqual([first_page["filename"], second_page["filename"]], ["second.webp", "first.webp"])
        self.assertNotEqual(first_page["url"], second_page["url"])
        self.assertIn("A &amp; B &lt; C", (site / first_page["path"]).read_text())
        self.assertIn(second_page["path"], (site / first_page["path"]).read_text())
        urls = {node.text for node in ElementTree.parse(site / "sitemap.xml").findall(".//{*}loc")}
        self.assertIn(first_page["url"], urls)
        self.assertIn(first_page["pin_url"].encode(), pinterest_csv(receipt["photos"]))
        for photo in receipt["photos"]:
            with Image.open(site / photo["pin"]) as pin:
                self.assertEqual(pin.size, (1000, 1500))
            self.assertFalse((REPO / photo["path"]).exists())
        self.assertEqual(source.read_bytes(), original)

        self.workspace.lock.close()
        reopened = Workspace(self.root / "preview")
        self.addCleanup(reopened.lock.close)
        self.assertEqual(reopened.approve(request), receipt)


if __name__ == "__main__":
    unittest.main()
