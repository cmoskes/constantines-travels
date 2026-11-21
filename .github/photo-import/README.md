# Constantine’s Travels photo importer

This Mac prototype keeps an approved site preview and a history of imported photos on your computer. It works with the existing galleries and their established layouts.

## Open on your Mac

1. Use a local copy of the feature branch. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/macos/) if you need it.
2. In Finder, open the repository folder. Press **Command–Shift–.** to show hidden folders, then open **.github → photo-import → Open Photo Importer.command**. The launcher installs the pinned image tools on first use and opens the importer in your browser. Keep the Terminal window open while you work.
3. In Apple Photos, select the batch. Use **File → Export → Export Photos** at full size to include your edits, or **Export Unmodified Original** for the original files. Export still images only. JPEG, PNG, WebP, HEIC and TIFF work with the included image tools. Export camera RAW files as full-size JPEG or TIFF through Apple Photos first.
4. Choose a destination and group, select the exported files, and check the image previews. Use **Earlier** and **Later** to arrange them. Titles and descriptions are optional and use your words. Fix any failed file using **Retry with file**. Approval requires a successful conversion for every selected file, including files with identical contents.
5. Click **Approve and add to preview**. The receipt links each filename to its matching page and a Pinterest image. Preview the whole gallery or download the Pinterest CSV and a ZIP of the generated site changes.

Open the same launcher for the next batch. Approved batches and their assigned URLs persist in the preview workspace in **Library/Application Support/Constantines Travels Importer**. Keep this workspace while working on an unpublished collection. Unapproved batches use temporary working files. If you close or reload the importer before approval, select the originals again to rebuild that batch.

## Preview and publication

Each approved batch creates two WebP sizes, a permanent-numbered HTML page, gallery and navigation updates, sitemap entries, and a portrait Pinterest JPEG padded to retain the full composition. The original export is read once and stays in its source folder. Preview links work locally. The CSV uses the future public URL for each photo and its pin image.

The cumulative site-changes ZIP contains the changed public files relative to the feature checkout the workspace started from. It excludes the importer and the original exports. Review the ZIP against that baseline before publication. The importer has no GitHub or Pinterest credentials and cannot deploy the site or post pins. Keep the importer on a tooling branch or outside the root used for a public Pages deployment.

Use one preview workspace to assign new photo IDs until those changes have been carried forward. Separate workspaces copied from the same starting site can independently assign the same next number.

## Development checks

With the requirements installed, run `python3 -B -m unittest discover -s .github/photo-import` from the repository root. For a disposable preview, run `python3 -B .github/photo-import/app.py --workspace /path/outside/checkout --port 8766`. The importer listens on the local machine only.
