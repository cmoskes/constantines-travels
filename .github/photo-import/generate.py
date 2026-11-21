"""Generate public files in a staged copy of Constantine's Travels."""
import csv
import html
import io
import json
import re
import shutil
import warnings
from pathlib import Path
from urllib.parse import quote, urlencode

from PIL import Image, ImageCms, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
PREFIX = "window.TRAVEL_COLLECTIONS = "
BASE = "https://cmoskes.github.io/constantines-travels/"
CATALOG = "assets/collection-data.js"

def escape(value):
    return html.escape(value, quote=True)


def catalog(site):
    return json.loads((site / CATALOG).read_text().removeprefix(PREFIX).strip().removesuffix(";"))


def optimize(source, output):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source) as original:
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


def generate(site, group_key, rows, uploads):
    data = catalog(site)
    group = next((item for item in data["groups"] if item["key"] == group_key), None)
    if group is None:
        raise ValueError("Choose an existing destination group.")
    gallery_path = site / group["path"]
    gallery = gallery_path.read_text()
    last_id = group["ids"][-1]
    last_card = re.search(rf'<a\b[^>]*\bdata-photo-id="{re.escape(last_id)}"[^>]*>.*?</a>', gallery, re.S)
    if not last_card:
        raise ValueError("This gallery’s last photo could not be found. The preview was unchanged.")

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
    add_at = last_card.end()
    cards = "\n".join(card(photo, group["name"], gallery=True) for photo in photos)
    gallery = gallery[:add_at] + "\n" + cards + gallery[add_at:]
    gallery = re.sub(r'(<[^>]*id="filter-status"[^>]*>)[^<]*(</[^>]+>)',
                     lambda match: f"{match[1]}{len(sequence)} photographs{match[2]}", gallery, count=1)
    gallery_path.write_text(gallery)
    (site / CATALOG).write_text(PREFIX + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    template = (site / "photos/photo-114.html").read_text()
    for photo in photos:
        index = sequence.index(photo["id"])
        previous = data["photos"][sequence[index - 1]] if index else None
        following = data["photos"][sequence[index + 1]] if index + 1 < len(sequence) else None
        related = [item for item in photos if item is not photo][:3]
        (site / photo["path"]).write_text(render_page(template, photo, group, previous, following, related))
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
        (site / path).write_text(page)
        changes.add(path)

    sitemap_path = site / "sitemap.xml"
    sitemap = sitemap_path.read_text()
    if "</urlset>" not in sitemap:
        raise ValueError("The sitemap could not be updated.")
    urls = "".join(f'<url><loc>{photo["url"]}</loc></url>\n' for photo in photos)
    sitemap_path.write_text(sitemap.replace("</urlset>", urls + "</urlset>", 1))
    return photos, changes


def pinterest_csv(photos):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Photo ID", "Title", "Description", "Alt text", "Photo URL", "Image URL"])
    for photo in photos:
        values = [photo[key] for key in ("id", "title", "description", "alt", "url", "pin_url")]
        # Prevent draft text from being interpreted as a spreadsheet formula.
        writer.writerow(["'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    return output.getvalue().encode("utf-8-sig")
