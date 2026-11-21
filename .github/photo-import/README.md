# Constantine’s Travels photo importer

## Try it on your Mac

1. In [GitHub Desktop](https://desktop.github.com/), clone `cmoskes/constantines-travels` if you do not already have a copy. Use **Current Branch** to switch to `feature/rainier-photo-import` and choose **Fetch origin** to get the latest version. Open the checkout with **Repository → Show in Finder**.
2. Install Python from [python.org](https://www.python.org/downloads/macos/) once if you need it. Python 3.12 or 3.13 is a good choice. In Finder, double-click **Open Photo Importer** at the top of the checkout. Keep the app alongside the rest of the checkout. The first launch downloads the image tools, then opens the importer in your browser. On a later launch it reuses the installed tools.
3. In Apple Photos, use **File → Export → Export Photos** at full size to include your edits, or **Export Unmodified Original** for the camera originals. Export still images. JPEG, PNG, WebP, HEIC and TIFF work with the included image tools. Export camera RAW as full-size JPEG or TIFF first.
4. Choose an existing gallery, select the files, and use **Earlier** or **Later** to set their order. Add descriptive text if you have it. Use **Retry with file** if one fails. **Approve and add to preview** becomes available after every file is ready.
5. Open the gallery preview from the batch receipt. Each filename has a link to its photo page and Pinterest image. Approval saves the batch on your computer, and the preview remains available across launches.

The importer runs locally. The first-launch and Finder steps need confirmation on a Mac. The checkout includes an unsigned launcher intended for this pilot. If macOS blocks it, record the message so the launch issue can be addressed. The prototype's saved workspace is in **Library/Application Support/Constantines Travels Importer**. To send batches from a workspace created by the earlier prototype, back up that workspace and re-import using a fresh workspace with a recorded starting version.

## Send an approved batch to GitHub

The check expects GitHub's website files to match the starting version of your preview or a previously submitted batch. The Mount Rainier restoration must be approved and merged first. Keep the importer on its separate branch.

1. Review your local gallery and individual photo pages from the batch receipt.
2. Open **Prepare a GitHub review**. For this prototype, [create a fine-grained GitHub access token](https://github.com/settings/personal-access-tokens/new) limited to `cmoskes/constantines-travels`. Give it **Contents** and **Pull requests** read and write access and use a short expiration. Enter it directly into the importer on your own Mac. The importer uses it for the request and does not save it.
3. Click **Check changes** to review the files. This step only reads GitHub. If a newer website edit overlaps, the importer stops so an older preview cannot overwrite it. If a draft for a previous batch is still open, finish reviewing that draft before merging a later batch. Recheck against the latest main each time.
4. Click **Approve and create draft pull request**. The draft includes the generated public files and excludes the importer, source exports, receipts and access token.
5. Open the draft in GitHub and review **Files changed**. Mark the draft ready and manually merge only when you want to publish. GitHub Pages deploys from main if the repository is configured for that branch. The importer never merges.

Pinterest-ready images, descriptions, and direct photo URLs remain available separately through **Pinterest CSV** and the receipt links. The CSV addresses use the future public URLs. A backup ZIP is available in the GitHub review panel.

## Development checks

With the requirements installed, run `python3 -B -m unittest discover -s .github/photo-import` from the repository root. For a disposable preview, run `python3 -B .github/photo-import/app.py --workspace /path/outside/checkout --port 8766`.
