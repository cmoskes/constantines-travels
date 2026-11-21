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
        with self.assertRaisesRegex(ValueError, "Every submitted"):
            self.workspace.approve(request)
        self.assertEqual(self.workspace.current.resolve(), previous)
        self.workspace.upload(batch, second, io.BytesIO(original), self.root / "uploads")
        with self.assertRaisesRegex(ValueError, "Every submitted"):
            self.workspace.approve({**request, "photos": rows[:1]})
        with self.assertRaisesRegex(ValueError, "Choose an existing"):
            self.workspace.approve({**request, "group": "unknown"})
        self.assertEqual(self.workspace.current.resolve(), previous)

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
