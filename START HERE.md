# START HERE · Constantine’s Travels

Use the importer to add your chosen photographs to a private preview. You can review the preview, send it to GitHub for another look, and decide when to publish. Your Apple Photos library and original exports stay where you left them.

## 1. Open the importer on your Mac

1. In **GitHub Desktop**, open your `constantines-travels` copy. Choose **Current Branch**, then `feature/photo-importer-ready`. Click **Fetch origin** and **Pull origin** if offered.
2. Choose **Repository → Show in Finder**. Double-click **Open Photo Importer**. Keep the app in that folder with the website files.
3. Your browser opens. The first launch of this version can take a minute while it installs the image tools for **Python 3.13**. Your existing Python 3.13.17 matches the launcher’s version check. Later launches reuse that installation.

Use **Close importer** in the browser when you are done, then close the tab. Approved batches stay saved when you close the app or shut down your Mac. An unapproved batch should be approved or selected again next time.

## 2. Export one destination from Apple Photos

1. In **Photos**, select the shots you want to include in the destination. Start with 2–3 photos for the first trial. When you are comfortable, try 50–100 per batch.
2. Choose **File → Export → Export Photos** for your edited versions. Choose **Full Size**, and keep the filenames if offered. JPEG at high or maximum quality is a simple choice. For the original camera files, choose **Export Unmodified Original**. Export RAW files as full-size JPEG or TIFF for the importer.
3. Make a new folder with the trip or destination name. Save the exports there. Select still image files during import, leaving any videos or sidecar files in the export folder.

## 3. Import, review and approve

1. Choose a **Destination gallery**. For a place already on the site, pick its group, or choose **Add a new group…** under that place. For a brand-new place choose **Add a new destination…** and type the name you want visitors to see.
2. Select the export files. The batch shows a row for every file, and counts **submitted**, **ready** and **failed**. A possible repeat is highlighted. The importer keeps repeated files in your batch. Exact copies are easiest to detect. An edited version or a new export of the same shot may look identical and still have different file data.
3. Use the arrows or enter a position to arrange the photos. Add a caption or description if you have one. If a photo fails, choose **Retry with file** on that row. The receipt keeps your original filename, as well as any replacement filename used to retry.
4. Click **Approve and add to preview** once every photo is ready. In **Import history**, open the new batch's gallery preview and try its individual photo links. Use the search box to find past uploads by filename, title or gallery. The preview lives on your Mac until you decide to send it to GitHub.

## 4. Publish when you are ready

If GitHub still has the exact files from before the Mount Rainier repair, the importer includes the three restored photo pages with your batch for one review. It stops if it finds overlapping website edits. The importer itself stays on its development branch.

1. Open the gallery from **Import history** and confirm the photos and order. Then open **Prepare a GitHub review**.
2. For the pilot, use a [fine-grained GitHub access token](https://github.com/settings/personal-access-tokens/new) limited to **cmoskes/constantines-travels**. Set a short expiry. Under **Repository permissions**, set only **Contents** and **Pull requests** to **Read and write**. GitHub includes read-only Metadata automatically. Paste the token into the importer on your Mac. Keep it private. The importer clears the token field after sending a draft and keeps it out of saved files.
3. Click **Check changes**. This reads GitHub and shows the files in your reviewed preview. When ready, click **Approve and create draft pull request**. A 50–100 photo batch can take several minutes. Keep the browser open.
4. Open the draft link. On GitHub, check **Files changed**. When you are ready for the site to go live, choose **Ready for review**, then **Merge pull request** and **Confirm merge**. GitHub Pages deploys after the changes reach `main` if Pages is configured to publish from that branch. Finish reviewing one draft before sending the next batch.

## 5. Confirm it is live

In the importer, choose **Refresh publication status** under **Prepare a GitHub review**. Its status is based on which batch photos have reached GitHub. Paste the token again if the field is empty.

- **Awaiting publication** means that batch is saved in your preview.
- **Draft pull request** means you can open the GitHub draft from the receipt.
- **Published to GitHub** means all the batch’s photo pages and their matching display images reached the site’s source branch. Click **Check first photo on the live site** to verify that GitHub Pages has finished deploying. Also open the public gallery and check the order.

Download **Pinterest CSV** or open the **Pin image** links whenever you want to prepare pins yourself. Each photo gets a direct address for Pinterest.

## If something goes wrong

| What you see | What to try |
|---|---|
| The launcher says an older importer is running | Restart your Mac once and reopen **Open Photo Importer**. Approved batches stay saved. |
| The launcher asks for Python | Install a stable **Python 3.13** release from [python.org](https://www.python.org/downloads/macos/) and reopen the app. Other Python versions can stay installed. |
| The launcher reports “Operation not permitted” or “Permission denied” | Follow **If macOS denies access to the checkout** below. |
| The app still does not open | Keep the exact message. If the launcher reports a start failure, the log is in **Library → Application Support → Constantines Travels Importer → launcher.log**. |
| A photo is marked as failed | Export that photo again as a full-size JPEG and choose it with **Retry with file**. The other files stay in the batch. |
| GitHub says the website has changed | Keep your preview. Ask for help reconciling it with the current website before retrying. |
| The connection drops while sending a draft | Reopen the importer, choose **Check changes** again, and retry with the same reviewed preview. Check **Pull requests** on GitHub for an existing draft. |
| A merged photo link is still missing | Wait for the Pages deployment to finish, then reload and check the public gallery. If it still fails, keep the draft link and photo URL for troubleshooting. |

Your saved preview lives in **Library → Application Support → Constantines Travels Importer**. Keep this folder when updating. A preview created by the very first prototype may lack a record of its starting site. It can still be opened and reviewed. If GitHub review reports that issue, ask for help before moving the workspace or re-importing.


### If macOS denies access to the checkout

Try the latest launcher from GitHub Desktop first. If it still reports a permission error and the checkout is in Documents, move the existing checkout to a folder directly inside your home folder. Leave all macOS security settings in place.

1. Quit GitHub Desktop. In Finder, choose **Go → Home**. Create a folder called **Projects** there.
2. In Finder, move the entire **constantines-travels** folder from **Documents → GitHub** into **Projects**. Move the whole folder so GitHub Desktop can keep using the same checkout.
3. Reopen GitHub Desktop. When it says the repository moved, choose **Locate…** and select the **constantines-travels** folder in **Projects**.
4. Choose **Repository → Show in Finder** and double-click **Open Photo Importer** again.

Move only the checkout. The importer finds your approved batches in Application Support automatically.
