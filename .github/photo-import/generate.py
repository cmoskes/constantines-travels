"""Generate public files in a staged copy of Constantine's Travels."""
import csv
import hashlib
import html
import io
import json
import re
import shutil
import unicodedata
import warnings
from urllib.parse import urlencode

from PIL import Image, ImageCms, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
PREFIX = "window.TRAVEL_COLLECTIONS = "
BASE = "https://cmoskes.github.io/constantines-travels/"
CATALOG = "assets/collection-data.js"

def escape(value):
    return html.escape(value, quote=True)


def write_text(path, text):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def catalog(site):
    return json.loads((site / CATALOG).read_text().removeprefix(PREFIX).strip().removesuffix(";"))


def optimize(source, output):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source, formats=("JPEG", "PNG", "WEBP", "HEIF", "TIFF", "AVIF")) as original:
            if getattr(original, "n_frames", 1) > 1:
                raise ValueError("Export still photographs individually.")
            original.seek(0)
            image = ImageOps.exif_transpose(original)
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            alpha = image.convert("RGBA").getchannel("A") if has_alpha else None
            profile = image.info.get("icc_profile")
            if profile:
                color = image if image.mode in ("RGB", "CMYK", "L", "LAB") else image.convert("RGB")
                image = ImageCms.profileToProfile(color, io.BytesIO(profile), SRGB, outputMode="RGB")
            else:
                image = image.convert("RGB")
            if alpha is not None:
                image.putalpha(alpha)

    output.mkdir(parents=True, exist_ok=True)
    profile = SRGB.tobytes()
    sizes = {}
    for name, edge, quality in (("web", 2048, 88), ("thumb", 960, 82)):
        copy = image.copy()
        copy.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        copy.save(output / f"{name}.webp", quality=quality, icc_profile=profile)
        sizes[name] = list(copy.size)

    pin = Image.new("RGB", (1000, 1500), "#f5eee4")
    image.thumbnail((1000, 1500), Image.Resampling.LANCZOS)
    offset = ((pin.width - image.width) // 2, (pin.height - image.height) // 2)
    pin.paste(image, offset, image.getchannel("A") if "A" in image.getbands() else None)
    pin.save(output / "pin.jpg", quality=92, icc_profile=profile)
    return sizes


def picture(photo, *, full=False):
    thumb, web = photo["thumb_size"], photo["web_size"]
    src = photo["image"] if full else photo["thumb"]
    width, height = web if full else thumb
    sources = f'../{src} {width}w'
    if web[0] != thumb[0]:
        sources = f'../{photo["thumb"]} {thumb[0]}w, ../{photo["image"]} {web[0]}w'
    attrs = ('class="full-photo" fetchpriority="high"' if full else 'loading="lazy"')
    sizes = "(max-width:1100px) 90vw, 1000px" if full else "(max-width:600px) 90vw, (max-width:900px) 44vw, 30vw"
    return (f'<img src="../{src}" alt="{escape(photo["alt"])}" width="{width}" height="{height}" '
            f'srcset="{sources}" sizes="{sizes}" decoding="async" {attrs}>')


def card(photo, group, *, gallery=False):
    ident = photo["id"]
    orientation = "landscape-card" if photo["web_size"][0] >= photo["web_size"][1] else "portrait-card"
    attrs = (f' data-photo-id="{ident}" data-highlight="false"' if gallery else "")
    anchor = f'<span id="photo-{ident}" class="photo-return-anchor" aria-hidden="true"></span>' if gallery else ""
    return (f'<a class="card {orientation}" data-category="{escape(group)}" href="../{photo["path"]}"{attrs}>'
            f'{anchor}{picture(photo)}<span class="eyebrow">{escape(group)}</span>'
            f'<h3>{escape(photo["title"])}</h3><span class="photo-action" aria-hidden="true">View photo ↗</span></a>')


def step(direction, photo):
    label = "← Previous photo" if direction == "previous" else "Next photo →"
    return f'<a href="../{photo["path"]}" data-photo-direction="{direction}">{label}</a>' if photo else ""


def render_page(template, photo, group, previous, following, related):
    title = escape(photo["title"])
    description = escape(photo["description"])
    url = escape(photo["url"])
    image = escape(BASE + photo["image"])
    template = re.sub(r"<title>.*?</title>", lambda _: f"<title>{title} | Constantine’s Travels</title>", template, count=1)
    for field, value in {
        'name="description" content': description,
        'rel="canonical" href': url,
        'property="og:title" content': title,
        'property="og:description" content': description,
        'property="og:url" content': url,
        'property="og:image" content': image,
    }.items():
        template = re.sub(field + r'="[^"]*"', lambda _: f'{field}="{value}"', template, count=1)
    back = f'../{group["path"]}?{urlencode({"group": group["name"]})}#photo-{photo["id"]}'
    return_link = f'<a data-photo-return href="{escape(back)}">← Back to {escape(group["name"])}</a>'
    primary_return = return_link.replace("<a ", '<a class="back" ', 1)
    pinterest = "https://www.pinterest.com/pin/create/button/?" + urlencode({
        "url": photo["url"], "media": photo["pin_url"], "description": photo["description"],
    })
    related_markup = "".join(card(item, group["name"]) for item in related)
    main = (
        f'<article class="detail" id="top">{primary_return}'
        f'<p class="eyebrow">{escape(group["name"])}</p><h1>{title}</h1>'
        f'<p class="muted">Photographed by Constantine Moskes</p>{picture(photo, full=True)}'
        f'<div class="actions"><button id="share">Share this photo</button>'
        f'<a href="{escape(pinterest)}" target="_blank" rel="noopener noreferrer">Save to Pinterest</a></div>'
        f'<p id="share-status" role="status" aria-live="polite"></p><nav class="photo-nav" aria-label="Browse photographs">'
        f'{step("previous", previous)}{return_link}{step("next", following)}</nav></article>'
    )
    if related_markup:
        main += (f'<section class="wrap"><h2>More from {escape(group["name"])}</h2>'
                 f'<div class="grid">{related_markup}</div></section>')
    return re.sub(r'(<main id="main">).*?(</main>)', lambda match: match[1] + main + match[2], template, count=1, flags=re.S)


def destination_gallery(site, group):
    template = (site / "destinations/mount-rainier-national-park.html").read_text()
    name = escape(group["name"])
    url = BASE + group["path"]
    template = re.sub(r"<title>.*?</title>", lambda _: f"<title>{name} | Constantine’s Travels</title>", template, count=1)
    metadata = {
        'name="description" content': f"Travel photographs from {name}",
        'rel="canonical" href': url,
        'property="og:title" content': name,
        'property="og:description" content': f"Travel photographs from {name}",
        'property="og:type" content': "website",
        'property="og:url" content': url,
    }
    for field, value in metadata.items():
        template = re.sub(field + r'="[^"]*"', lambda _: f'{field}="{value}"', template, count=1)
    template = re.sub(r'<meta property="og:image"[^>]*>', '<!-- gallery-cover -->', template, count=1)
    gallery = (
        '<section class="wrap" id="top"><a class="back" href="../index.html#gallery">Destinations</a>'
        f'<h1>{name}</h1><div class="filters" role="group" aria-label="Filter photographs">'
        '<button type="button" aria-pressed="true" data-filter="All photos">All photos</button></div>'
        '<p class="muted" id="filter-status" role="status" aria-live="polite"></p>'
        f'<div class="grid curated-grid" id="photo-grid" data-collection="{group["path"]}"></div></section>'
    )
    return re.sub(r'(<main id="main">).*?(</main>)', lambda match: match[1] + gallery + match[2],
                  template, count=1, flags=re.S)


def select_group(site, data, group_key, name):
    existing = next((group for group in data["groups"] if group["key"] == group_key), None)
    if existing:
        return existing, False
    if not isinstance(group_key, str) or (group_key != "new-destination" and not group_key.startswith("new-group:")):
        raise ValueError("Choose an existing gallery or create a new one.")
    if not isinstance(name, str):
        raise ValueError("Enter a gallery or group name.")
    name = " ".join(name.split())
    if not 1 <= len(name) <= 80 or "|" in name or name.casefold() in {"all photos", "all groups"}:
        raise ValueError("Enter a gallery or group name of 1–80 characters.")
    if group_key == "new-destination":
        if any(group["collection"].casefold() == name.casefold() for group in data["groups"]):
            raise ValueError("That destination already exists. Choose it from the gallery list.")
        ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", errors="ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:60].rstrip("-")
        if not slug:
            slug = "gallery-" + hashlib.sha256(name.encode()).hexdigest()[:12]
        path = f"destinations/{slug}.html"
        if (site / path).exists():
            raise ValueError("That name would reuse an existing gallery address. Try a more specific name.")
        collection = name
    else:
        path = group_key.removeprefix("new-group:")
        groups = [group for group in data["groups"] if group["path"] == path]
        if not groups or any(group["name"].casefold() == name.casefold() for group in groups):
            raise ValueError("Choose an existing destination and a group name it does not already use.")
        collection = groups[0]["collection"]
    group = {"name": name, "collection": collection, "path": path, "ids": [], "key": f"{path}|{name}"}
    data["groups"].append(group)
    return group, group_key == "new-destination"


def generate(site, group_key, rows, uploads, name=""):
    data = catalog(site)
    group, new_destination = select_group(site, data, group_key, name)
    group_key = group["key"]
    gallery_path = site / group["path"]
    gallery = destination_gallery(site, group) if new_destination else gallery_path.read_text()
    prior_group_ids = [ident for item in data["groups"] if item["path"] == group["path"] for ident in item["ids"]]
    new_group = not group["ids"]
    last_id = (prior_group_ids[-1] if prior_group_ids else None) if new_group else group["ids"][-1]
    if last_id:
        position = re.search(rf'<a\b[^>]*\bdata-photo-id="{re.escape(last_id)}"[^>]*>.*?</a>', gallery, re.S)
    else:
        position = re.search(r'<div[^>]+data-collection="[^"]+"[^>]*>', gallery)
    if not position:
        raise ValueError("The gallery could not be updated. Your saved preview is still available.")

    existing_ids = [int(path.stem.split("-")[-1]) for path in (site / "photos").glob("photo-*.html")
                    if path.stem.split("-")[-1].isdigit()]
    reserved_assets = [int(match[1]) for path in (site / "assets").iterdir()
                       if (match := re.fullmatch(r"(?:photo|thumb|pin)-(\d+)(?:-hq)?\.[^.]+", path.name))]
    start = max([*existing_ids, *reserved_assets, *map(int, data["photos"])], default=0) + 1
    photos = []
    changes = {group["path"], CATALOG, "sitemap.xml"}
    for number, row in enumerate(rows, start):
        upload = uploads[row["key"]]
        ident = str(number).zfill(2)
        title = row["title"].strip() or f'Photograph {ident} · {group["name"]}'
        alt = row["alt"].strip() or title
        photo = {
            "id": ident, "group": group_key, "alt": alt, "title": title, "description": alt,
            "path": f"photos/photo-{ident}.html", "thumb": f"assets/thumb-{ident}-hq.webp",
            "image": f"assets/photo-{ident}-hq.webp", "pin": f"assets/pin-{ident}.jpg",
            "web_size": upload["web"], "thumb_size": upload["thumb"],
        }
        photo["url"] = BASE + photo["path"]
        photo["pin_url"] = BASE + photo["pin"]
        for source, target in (("web.webp", "image"), ("thumb.webp", "thumb"), ("pin.jpg", "pin")):
            shutil.copyfile(upload["directory"] / source, site / photo[target])
            changes.add(photo[target])
        photos.append(photo)
        data["photos"][ident] = {key: photo[key] for key in ("id", "group", "alt", "thumb", "path")}

    new_ids = [photo["id"] for photo in photos]
    group["ids"].extend(new_ids)
    sequence = [ident for item in data["groups"] if item["path"] == group["path"] for ident in item["ids"]]
    data["collections"][group["path"]] = sequence
    add_at = position.end()
    cards = "\n".join(card(photo, group["name"], gallery=True) for photo in photos)
    gallery = gallery[:add_at] + "\n" + cards + gallery[add_at:]
    gallery = re.sub(r'(<[^>]*id="filter-status"[^>]*>)[^<]*(</[^>]+>)',
                     lambda match: f"{match[1]}{len(sequence)} photographs{match[2]}", gallery, count=1)
    if new_group:
        button = f'<button type="button" aria-pressed="false" data-filter="{escape(group["name"])}">{escape(group["name"])}</button>'
        filters = re.search(r'<div class="filters"[^>]*>.*?</div>', gallery, re.S)
        if filters:
            offset = filters.end() - len("</div>")
            gallery = gallery[:offset] + button + gallery[offset:]
        else:
            offset = re.search(r'<div[^>]+data-collection="[^"]+"[^>]*>', gallery).start()
            existing = [item for item in data["groups"] if item["path"] == group["path"] and item is not group]
            other = "".join(f'<button type="button" aria-pressed="false" data-filter="{escape(item["name"])}">{escape(item["name"])}</button>'
                            for item in existing)
            gallery = (gallery[:offset] + '<div class="filters" role="group" aria-label="Filter photographs">'
                       '<button type="button" aria-pressed="true" data-filter="All photos">All photos</button>'
                       + other + button + '</div>' + gallery[offset:])
    if new_destination:
        gallery = gallery.replace("<!-- gallery-cover -->", f'<meta property="og:image" content="{BASE}{photos[0]["image"]}">')
        home = site / "index.html"
        contents = home.read_text()
        nav = re.search(r'<nav class="ref-browse-links"[^>]*>.*?</nav>', contents, re.S)
        if not nav:
            raise ValueError("The homepage destination links could not be updated.")
        offset = nav.end() - len("</nav>")
        link = f'<a href="{group["path"]}">{escape(group["name"])}</a>'
        write_text(home, contents[:offset] + link + contents[offset:])
        changes.add("index.html")
    write_text(gallery_path, gallery)
    write_text(site / CATALOG, PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    template = (site / "photos/photo-114.html").read_text()
    for photo in photos:
        index = sequence.index(photo["id"])
        previous = data["photos"][sequence[index - 1]] if index else None
        following = data["photos"][sequence[index + 1]] if index + 1 < len(sequence) else None
        related = [item for item in photos if item is not photo][:3]
        write_text(site / photo["path"], render_page(template, photo, group, previous, following, related))
        changes.add(photo["path"])

    # The public photo dock uses the catalog. Update the adjacent in-page links too.
    for ident, direction, replacement in (
        (last_id, "next", photos[0]),
        (sequence[sequence.index(new_ids[-1]) + 1] if sequence[-1] != new_ids[-1] else None, "previous", photos[-1]),
    ):
        if ident is None:
            continue
        path = data["photos"][ident]["path"]
        page = (site / path).read_text()
        pattern = rf'<a\b[^>]*data-photo-direction="{direction}"[^>]*>.*?</a>'
        page, count = re.subn(pattern, lambda _: step(direction, replacement), page, count=1, flags=re.S)
        if not count:
            position = re.search(r'<nav class="photo-nav"[^>]*>.*?</nav>', page, re.S)
            if not position:
                continue
            offset = position.end() - len("</nav>") if direction == "next" else page.index(">", position.start()) + 1
            page = page[:offset] + step(direction, replacement) + page[offset:]
        write_text(site / path, page)
        changes.add(path)

    sitemap_path = site / "sitemap.xml"
    sitemap = sitemap_path.read_text()
    if "</urlset>" not in sitemap:
        raise ValueError("The sitemap could not be updated.")
    urls = "".join(f'<url><loc>{photo["url"]}</loc></url>\n' for photo in photos)
    if new_destination:
        urls = f'<url><loc>{BASE}{group["path"]}</loc></url>\n' + urls
    write_text(sitemap_path, sitemap.replace("</urlset>", urls + "</urlset>", 1))
    return photos, changes


def pinterest_csv(photos):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Photo ID", "Title", "Description", "Alt text", "Photo URL", "Image URL", "Original filename"])
    for photo in photos:
        values = [photo[key] for key in ("id", "title", "description", "alt", "url", "pin_url")]
        values.append(photo.get("submitted_filename") or photo.get("filename", ""))
        # Prevent draft text from being interpreted as a spreadsheet formula.
        writer.writerow(["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    return output.getvalue().encode("utf-8-sig")
