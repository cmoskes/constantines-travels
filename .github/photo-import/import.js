"use strict";

const group = document.querySelector("#group");
const files = document.querySelector("#files");
const review = document.querySelector("#review");
const counts = document.querySelector("#counts");
const photoList = document.querySelector("#photos");
const template = document.querySelector("#photo-template");
const approve = document.querySelector("#approve");
const approvalNote = document.querySelector("#approval-note");
const clear = document.querySelector("#clear");
const notice = document.querySelector("#error");
const history = document.querySelector("#history");
const receipts = document.querySelector("#receipts");

let batch = null;
let busy = false;

function error(message = "") {
  notice.textContent = message;
  notice.hidden = !message;
}

async function post(path, payload) {
  const binary = payload instanceof Blob;
  const response = await fetch(path, {
    method: "POST",
    headers: {"X-Photo-Importer": "1", "Content-Type": binary ? "application/octet-stream" : "application/json"},
    body: binary ? payload : JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The importer did not accept the request.");
  return result;
}

function link(text, href) {
  const item = document.createElement("a");
  item.textContent = text;
  item.href = href;
  item.target = "_blank";
  item.rel = "noopener";
  return item;
}

function addReceipt(receipt) {
  if (document.getElementById(`receipt-${receipt.batch}`)) return;
  const article = document.createElement("article");
  article.className = "receipt";
  article.id = `receipt-${receipt.batch}`;
  const count = document.createElement("strong");
  count.textContent = `${receipt.submitted} submitted · ${receipt.imported} imported · 0 failed`;
  const gallery = document.createElement("p");
  gallery.append(link("Open gallery preview", `/preview/${receipt.gallery}#photo-${receipt.photos[0].id}`));
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Individual photos and Pinterest images";
  const list = document.createElement("ul");
  for (const photo of receipt.photos) {
    const row = document.createElement("li");
    row.append(`${photo.filename} — `, link(photo.title, `/preview/${photo.path}`), " · ", link("Pin image", `/preview/${photo.pin}`));
    list.append(row);
  }
  details.append(summary, list);
  article.append(count, gallery, details);
  receipts.prepend(article);
  history.hidden = false;
}

function update() {
  files.disabled = busy || Boolean(batch);
  group.disabled = busy;
  clear.disabled = busy;
  review.hidden = !batch;
  if (!batch) return;
  const ready = batch.photos.filter(photo => photo.state === "ready").length;
  const failed = batch.photos.filter(photo => photo.state === "failed").length;
  counts.textContent = `${batch.photos.length} submitted · ${ready} ready · ${failed} failed`;
  approve.disabled = busy || !group.value || ready !== batch.photos.length;
  approvalNote.textContent = ready === batch.photos.length && group.value
    ? "This adds the batch to your private preview."
    : "Choose a gallery and wait until every photo is ready.";
  batch.photos.forEach((photo, index) => {
    photo.node.querySelector(".order").textContent = index + 1;
    photo.node.querySelector(".earlier").disabled = busy || index === 0;
    photo.node.querySelector(".later").disabled = busy || index === batch.photos.length - 1;
    for (const field of photo.node.querySelectorAll("input, textarea")) field.disabled = busy;
  });
}

function move(photo, offset) {
  const index = batch.photos.indexOf(photo);
  const other = batch.photos[index + offset];
  if (busy || !other) return;
  batch.photos[index] = other;
  batch.photos[index + offset] = photo;
  if (offset < 0) photoList.insertBefore(photo.node, other.node);
  else photoList.insertBefore(other.node, photo.node);
  update();
  const intended = photo.node.querySelector(offset < 0 ? ".earlier" : ".later");
  const alternative = photo.node.querySelector(offset < 0 ? ".later" : ".earlier");
  (intended.disabled ? alternative : intended).focus();
}

async function upload(photo, file) {
  const status = photo.node.querySelector(".file-status");
  const thumbnail = photo.node.querySelector("img");
  const placeholder = photo.node.querySelector(".placeholder");
  const retry = photo.node.querySelector(".retry");
  const filename = photo.node.querySelector(".filename");
  photo.filename = file.name;
  filename.textContent = file.name;
  photo.state = "processing";
  status.textContent = "Preparing web and Pinterest copies…";
  placeholder.textContent = "Preparing preview…";
  placeholder.hidden = false;
  thumbnail.hidden = true;
  retry.hidden = true;
  try {
    if (!batch.registered) {
      await post("/api/begin", {batch: batch.id, files: batch.photos.map(item => item.key)});
      batch.registered = true;
    }
    const result = await post(`/api/upload/${batch.id}/${photo.key}`, file);
    thumbnail.src = `${result.preview}?v=${Date.now()}`;
    thumbnail.hidden = false;
    placeholder.hidden = true;
    photo.state = "ready";
    status.textContent = "Ready for approval";
  } catch (problem) {
    photo.state = "failed";
    status.textContent = problem.message;
    placeholder.textContent = "Preview unavailable";
    retry.hidden = false;
  }
  photo.node.dataset.state = photo.state;
  update();
}

function newPhoto(file) {
  const node = template.content.firstElementChild.cloneNode(true);
  const photo = {key: crypto.randomUUID(), node, state: "pending"};
  node.querySelector(".filename").textContent = file.name;
  node.querySelector(".earlier").addEventListener("click", () => move(photo, -1));
  node.querySelector(".later").addEventListener("click", () => move(photo, 1));
  const retry = node.querySelector(".retry input");
  retry.addEventListener("change", async () => {
    const replacement = retry.files[0];
    retry.value = "";
    if (busy || !replacement) return;
    busy = true;
    update();
    await upload(photo, replacement);
    busy = false;
    update();
  });
  photoList.append(node);
  return photo;
}

files.addEventListener("change", async () => {
  const selection = Array.from(files.files);
  if (!selection.length || batch || busy) return;
  error();
  if (selection.length > 500) {
    error(`${selection.length} photographs selected. Choose batches of up to 500 so every photograph can be reviewed.`);
    files.value = "";
    return;
  }
  batch = {id: crypto.randomUUID(), photos: selection.map(newPhoto)};
  busy = true;
  update();
  for (const [index, file] of selection.entries()) await upload(batch.photos[index], file);
  busy = false;
  update();
});

function reset() {
  batch = null;
  files.value = "";
  photoList.replaceChildren();
  error();
  update();
}

clear.addEventListener("click", async () => {
  if (busy || !window.confirm("Discard this unapproved batch and start again?")) return;
  busy = true;
  update();
  try {
    if (batch.registered) await post("/api/discard", {batch: batch.id});
    reset();
  } catch (problem) {
    error(problem.message);
  } finally {
    busy = false;
    update();
  }
});
group.addEventListener("change", update);
approve.addEventListener("click", async () => {
  if (approve.disabled) return;
  busy = true;
  error();
  update();
  try {
    const result = await post("/api/approve", {
      batch: batch.id,
      group: group.value,
      photos: batch.photos.map(photo => ({
        key: photo.key,
        filename: photo.filename,
        title: photo.node.querySelector(".title").value,
        alt: photo.node.querySelector(".alt").value,
      })),
    });
    addReceipt(result);
    reset();
    document.querySelector("#history-title").focus();
  } catch (problem) {
    error(problem.message);
  } finally {
    busy = false;
    update();
  }
});

async function init() {
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error("The importer could not load the preview workspace.");
    const state = await response.json();
    for (const item of state.groups) {
      const label = item.collection === item.name ? item.name : `${item.collection} — ${item.name}`;
      group.add(new Option(label, item.key));
    }
    for (const receipt of state.receipts) addReceipt(receipt);
    update();
  } catch (problem) {
    error(problem.message);
  }
}

init();
