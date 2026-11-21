# Photo importer development

Start with the [beginner guide](../../START%20HERE.md) for the Finder launcher and publishing walkthrough.

- Use stable Python 3.13. The Finder launcher uses a dedicated runtime under macOS Application Support. It installs pinned, hash-verified wheels and leaves the preview and history in the existing workspace.
- Run `python3.13 -B -m unittest discover -s .github/photo-import` with the requirements installed. For a disposable development preview, run `python3.13 -B .github/photo-import/app.py --workspace /path/outside/checkout --port 8766`.
- The importer serves the loopback interface. Image decoders receive only the files selected in the browser, with file-size and decompression limits. Approved web assets omit source EXIF and use a standard display color profile. Batch backups and original filenames stay in the local workspace.
- GitHub traffic is limited to the configured repository. The access token is held only for the browser session/request and is never written to preview state. The importer checks remote file hashes, restricts release paths, and uploads through a draft-only path. Status compares GitHub source files with approved photo pages and matching display assets. GitHub Pages deployment is checked separately on the public site.
- Preview versions share unchanged files by hard link. Generators must replace edited files atomically in the staging version. Photo IDs assume one active publishing workspace. Separate workspaces starting from the same site may assign the same future IDs, so GitHub review checks for conflicts before making changes.
- Keep the launcher and importer on the development branch. Generated website changes are sent through draft pull requests with only the public files included.
