"use strict";

const group = document.querySelector("#group");
const galleryName = document.querySelector("#gallery-name");
const galleryNameField = document.querySelector("#gallery-name-field");
const historySearch = document.querySelector("#history-search");
const moreHistory = document.querySelector("#more-history");
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
let historyRecords = [];
let publications = {};
let historyLimit = 8;
const destinations = new Map();

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

function receiptCard(receipt, query) {
  const article = document.createElement("article");
  article.className = "receipt";
  const title = document.createElement("strong");
  const name = receipt.group?.split("|").slice(1).join("|") || receipt.gallery.split("/").pop().replace(".html", "").replaceAll("-", " ");
  const date = receipt.approved_at ? new Date(receipt.approved_at).toLocaleDateString() : "";
  title.textContent = [name, date].filter(Boolean).join(" · ");
  const status = document.createElement("span");
  status.className = "status";
  const publication = publications[receipt.batch];
  status.textContent = {published: "Published to GitHub", review: "Draft pull request", closed: "Draft closed · awaiting publication"}[publication?.status] || "Awaiting publication";
  const count = document.createElement("p");
  count.textContent = `${receipt.submitted} submitted · ${receipt.imported} imported · 0 failed`;
  const gallery = document.createElement("p");
  gallery.append(link("Open gallery preview", `/preview/${receipt.gallery}#photo-${receipt.photos[0].id}`));
  if (["review", "closed"].includes(publication?.status) && publication.url) {
    gallery.append(" · ", link("Open GitHub draft", publication.url));
  }
  if (publication?.status === "published") {
    gallery.append(" · ", link("Check first photo on the live site", receipt.photos[0].url));
  }
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Individual photos and Pinterest images";
  const matchingPhotos = receipt.photos.filter(photo => photoMatches(photo, query));
  details.append(summary);
  details.addEventListener("toggle", () => {
    if (!details.open || details.querySelector("ul")) return;
    const list = document.createElement("ul");
    for (const photo of matchingPhotos.length ? matchingPhotos : receipt.photos) {
      const row = document.createElement("li");
      const filename = photo.submitted_filename && photo.submitted_filename !== photo.filename
        ? `${photo.submitted_filename} → ${photo.filename}` : photo.filename;
      row.append(`${filename} — `, link(photo.title, `/preview/${photo.path}`), " · ", link("Pin image", `/preview/${photo.pin}`));
      list.append(row);
    }
    details.append(list);
  });
  if (query && matchingPhotos.length) details.open = true;
  article.append(title, " ", status, count, gallery, details);
  return article;
}

function photoMatches(photo, query) {
  return [photo.filename, photo.submitted_filename, photo.title].some(value => value?.toLocaleLowerCase().includes(query));
}

function renderHistory() {
  history.hidden = !historyRecords.length;
  const query = historySearch.value.trim().toLocaleLowerCase();
  const matches = historyRecords.filter(receipt =>
    !query || receipt.gallery.toLocaleLowerCase().includes(query) ||
      receipt.group?.toLocaleLowerCase().includes(query) || receipt.photos.some(photo => photoMatches(photo, query)));
  const published = historyRecords.filter(receipt => publications[receipt.batch]?.status === "published").length;
  document.querySelector("#history-count").textContent = `${matches.length} of ${historyRecords.length} batches · ${published} published to GitHub · ${historyRecords.length - published} awaiting publication`;
  receipts.replaceChildren(...matches.slice(0, historyLimit).map(receipt => receiptCard(receipt, query)));
  moreHistory.hidden = matches.length <= historyLimit;
}

historySearch.addEventListener("input", () => {
  historyLimit = 8;
  renderHistory();
});
moreHistory.addEventListener("click", () => {
  historyLimit += 8;
  renderHistory();
});

function addGallery(item) {
  if (Array.from(group.options).some(option => option.value === item.key)) return;
  if (!destinations.has(item.path)) {
    const destination = document.createElement("optgroup");
    destination.label = item.collection;
    destination.append(new Option("Add a new group…", `new-group:${item.path}`));
    destinations.set(item.path, destination);
    group.append(destination);
  }
  const destination = destinations.get(item.path);
  destination.insertBefore(new Option(item.name, item.key), destination.lastElementChild);
}

function addingGallery() {
  return group.value === "new-destination" || group.value.startsWith("new-group:");
}

function update() {
  files.disabled = busy || Boolean(batch);
  group.disabled = busy;
  clear.disabled = busy;
  galleryNameField.hidden = !addingGallery();
  galleryName.disabled = busy;
  document.querySelector("#gallery-name-label").textContent = group.value === "new-destination" ? "New destination name" : "New group name";
  review.hidden = !batch;
  if (!batch) return;
  const ready = batch.photos.filter(photo => photo.state === "ready").length;
  const failed = batch.photos.filter(photo => photo.state === "failed").length;
  const pending = batch.photos.length - ready - failed;
  const hasGallery = group.value && (!addingGallery() || galleryName.value.trim());
  const fingerprints = new Map();
  for (const photo of batch.photos) {
    if (photo.state === "ready" && photo.fingerprint) {
      fingerprints.set(photo.fingerprint, (fingerprints.get(photo.fingerprint) || 0) + 1);
    }
  }
  counts.textContent = `${batch.photos.length} submitted · ${ready} ready · ${failed} failed${pending ? ` · ${pending} preparing` : ""}`;
  approve.disabled = busy || !hasGallery || ready !== batch.photos.length;
  approvalNote.textContent = ready === batch.photos.length && hasGallery
    ? "This adds the batch to your private preview."
    : "Choose a gallery and wait until every photo is ready.";
  batch.photos.forEach((photo, index) => {
    const position = photo.node.querySelector(".order");
    position.value = index + 1;
    position.max = batch.photos.length;
    const warning = photo.node.querySelector(".duplicate-warning");
    const messages = [];
    if (photo.state === "ready" && photo.priorMatches?.length) {
      messages.push(`Possible repeat of an earlier import (${photo.priorMatches.join(", ")}).`);
    }
    if (photo.state === "ready" && fingerprints.get(photo.fingerprint) > 1) messages.push("This file also appears in this batch.");
    warning.hidden = !messages.length;
    warning.textContent = messages.length ? messages.join(" ") + " It will still be included." : "";
    photo.node.querySelector(".earlier").disabled = busy || index === 0;
    photo.node.querySelector(".later").disabled = busy || index === batch.photos.length - 1;
    for (const field of photo.node.querySelectorAll("input, textarea")) field.disabled = busy;
  });
}

function move(photo, target) {
  const current = batch.photos.indexOf(photo);
  if (busy || !Number.isInteger(target) || target < 0 || target >= batch.photos.length || target === current) {
    update();
    return;
  }
  batch.photos.splice(current, 1);
  batch.photos.splice(target, 0, photo);
  photoList.insertBefore(photo.node, batch.photos[target + 1]?.node || null);
  update();
  photo.node.querySelector(".order").focus();
}

async function upload(photo, file) {
  const status = photo.node.querySelector(".file-status");
  const thumbnail = photo.node.querySelector("img");
  const placeholder = photo.node.querySelector(".placeholder");
  const retry = photo.node.querySelector(".retry");
  const filename = photo.node.querySelector(".filename");
  photo.filename = file.name;
  filename.textContent = photo.originalFilename === file.name ? file.name : `${photo.originalFilename} → ${file.name}`;
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
    photo.fingerprint = result.fingerprint;
    photo.priorMatches = result.prior_matches;
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
  const photo = {key: crypto.randomUUID(), node, state: "pending", originalFilename: file.name};
  node.querySelector(".filename").textContent = file.name;
  node.querySelector(".earlier").addEventListener("click", () => move(photo, batch.photos.indexOf(photo) - 1));
  node.querySelector(".later").addEventListener("click", () => move(photo, batch.photos.indexOf(photo) + 1));
  const position = node.querySelector(".order");
  position.addEventListener("change", () => move(photo, position.valueAsNumber - 1));
  position.addEventListener("keydown", event => {
    if (event.key === "Enter") position.blur();
  });
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
group.addEventListener("change", () => {
  galleryName.value = "";
  update();
});
galleryName.addEventListener("input", update);
approve.addEventListener("click", async () => {
  if (approve.disabled) return;
  busy = true;
  error();
  update();
  try {
    const result = await post("/api/approve", {
      batch: batch.id,
      group: group.value,
      gallery_name: galleryName.value,
      photos: batch.photos.map(photo => ({
        key: photo.key,
        filename: photo.filename,
        submitted_filename: photo.originalFilename,
        title: photo.node.querySelector(".title").value,
        alt: photo.node.querySelector(".alt").value,
      })),
    });
    addGallery({path: result.gallery, key: result.group, name: result.group_name, collection: result.collection});
    group.value = result.group;
    galleryName.value = "";
    historyRecords.unshift(result);
    historySearch.value = "";
    historyLimit = 8;
    renderHistory();
    clearGitHubPlan();
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
    group.add(new Option("Add a new destination…", "new-destination"));
    for (const item of state.groups) addGallery(item);
    historyRecords = state.receipts.reverse();
    publications = state.publications || {};
    renderHistory();
    update();
  } catch (problem) {
    error(problem.message);
  }
}

init();

const githubToken = document.querySelector("#github-token");
const githubStatus = document.querySelector("#github-status");
const githubRefresh = document.querySelector("#github-refresh");
const githubCheck = document.querySelector("#github-check");
const githubSubmit = document.querySelector("#github-submit");
const githubPlan = document.querySelector("#github-plan");
let reviewedFingerprint = null;

function clearGitHubPlan() {
  reviewedFingerprint = null;
  githubPlan.hidden = true;
  githubStatus.replaceChildren();
}

githubToken.addEventListener("input", clearGitHubPlan);
githubCheck.addEventListener("click", async () => {
  clearGitHubPlan();
  githubStatus.textContent = "Checking GitHub main against your preview…";
  githubCheck.disabled = true;
  githubRefresh.disabled = true;
  githubToken.disabled = true;
  try {
    const plan = await post("/api/github/check", {token: githubToken.value.trim()});
    if (plan.publications) publications = plan.publications;
    renderHistory();
    reviewedFingerprint = plan.fingerprint;
    document.querySelector("#github-summary").textContent = `${plan.files.length} changed files`;
    const items = plan.files.map(path => {
      const item = document.createElement("li");
      item.append(link(path, "/preview/" + path));
      return item;
    });
    document.querySelector("#github-files").replaceChildren(...items);
    githubStatus.textContent = "GitHub matches your preview’s starting files. Review the changes below.";
    githubPlan.hidden = false;
  } catch (problem) {
    githubStatus.textContent = problem.message;
  } finally {
    githubToken.disabled = false;
    githubCheck.disabled = false;
    githubRefresh.disabled = false;
  }
});

githubSubmit.addEventListener("click", async () => {
  if (!reviewedFingerprint) return;
  const token = githubToken.value.trim();
  const reviewedFingerprintForSubmit = reviewedFingerprint;
  clearGitHubPlan();
  githubToken.value = "";
  githubStatus.textContent = "Creating a draft pull request. Large batches can take several minutes. Keep this tab open.";
  githubCheck.disabled = true;
  githubRefresh.disabled = true;
  githubToken.disabled = true;
  try {
    const result = await post("/api/github/submit", {token, fingerprint: reviewedFingerprintForSubmit});
    if (result.publications) publications = result.publications;
    renderHistory();
    githubStatus.replaceChildren(link("Open the draft pull request on GitHub", result.url));
  } catch (problem) {
    githubStatus.textContent = problem.message;
  } finally {
    githubCheck.disabled = false;
    githubRefresh.disabled = false;
    githubToken.disabled = false;
  }
});

githubRefresh.addEventListener("click", async () => {
  clearGitHubPlan();
  githubStatus.textContent = "Checking which batches are on GitHub…";
  githubRefresh.disabled = true;
  githubCheck.disabled = true;
  githubToken.disabled = true;
  try {
    const result = await post("/api/github/status", {token: githubToken.value.trim()});
    publications = result.publications;
    renderHistory();
    githubStatus.textContent = "Publication status updated. Use a live photo link to check the website.";
  } catch (problem) {
    githubStatus.textContent = problem.message;
  } finally {
    githubRefresh.disabled = false;
    githubCheck.disabled = false;
    githubToken.disabled = false;
  }
});

document.querySelector("#quit").addEventListener("click", async () => {
  if (busy || githubCheck.disabled) {
    error("Wait for the current operation to finish before closing.");
    return;
  }
  if (batch && !window.confirm("Close and discard this unapproved batch? Approved batches are saved.")) return;
  try {
    await post("/api/quit", {});
    for (const element of document.querySelectorAll("main > :not(#closed), header")) element.hidden = true;
    document.querySelector("#closed").hidden = false;
  } catch (problem) {
    error(problem.message);
  }
});
