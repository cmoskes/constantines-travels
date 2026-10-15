/* Each enhancement can be disabled independently for a focused rollback. */
(function () {
  'use strict';
  var features = { highlights: true, photoDock: true, eventTracking: true };
  var data = window.TRAVEL_COLLECTIONS;
  var root = new URL(document.currentScript.src).pathname.replace(/assets\/refresh\.js$/, '');
  function url(path) { return root + path; }
  function track(name, params) {
    if (!features.eventTracking || window['ga-disable-G-CFJ75QR0CY']) return;
    if (typeof window.gtag === 'function') window.gtag('event', name, params || {});
  }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  // Category and Highlights filters compose, while deep links return to all photos.
  var grid = document.querySelector('[data-collection]');
  if (grid && features.highlights) {
    var cards = Array.from(grid.querySelectorAll('.card[data-photo-id]'));
    var originalChildren = Array.from(grid.children);
    function layoutRows() {
      var perRow = window.innerWidth <= 520 ? 1 : window.innerWidth <= 900 ? 2 : 3;
      var fragment = document.createDocumentFragment(), pending = [];
      function flush() {
        if (!pending.length) return;
        var row = el('div', 'ref-photo-row' + (pending.length === 1 ? ' ref-single-row' : ''));
        pending.forEach(function (card) {
          var image = card.querySelector('img');
          var ratio = Number(image.getAttribute('width')) / Number(image.getAttribute('height')) || 1.5;
          card.style.flex = ratio + ' 1 0%';
          image.style.aspectRatio = String(ratio);
          row.append(card);
        });
        if (grid.dataset.collection === 'destinations/mount-rainier-national-park.html') {
          // Justified rows: every image keeps its ratio and the row has no vertical gaps.
          var gap = window.innerWidth <= 900 ? 14 : 20;
          var ratios = pending.map(function(card) {
            var img = card.querySelector('img');
            return (Number(img.getAttribute('width')) / Number(img.getAttribute('height'))) || 1.5;
          });
          var available = Math.max(200, grid.clientWidth - gap * (pending.length - 1));
          var h = Math.min(380, available / ratios.reduce(function(a,b){return a+b;},0));
          row.style.setProperty('height', h + 'px', 'important');
          row.style.setProperty('display', 'flex', 'important');
          row.style.setProperty('align-items', 'stretch', 'important');
          pending.forEach(function(card,i) {
            card.style.setProperty('width', (h * ratios[i]) + 'px', 'important');
            card.style.setProperty('flex', 'none', 'important');
            card.style.setProperty('height', h + 'px', 'important');
            var img = card.querySelector('img');
            img.style.setProperty('width','100%','important');
            img.style.setProperty('height','100%','important');
            img.style.setProperty('object-fit','cover','important');
          });
        }
        fragment.append(row);pending = [];
      }
      originalChildren.forEach(function (child) {
        if (child.matches('.card[data-photo-id]')) {
          if (child.hidden) { fragment.append(child); return; }
          pending.push(child);if (pending.length === perRow) flush();
        } else { flush();fragment.append(child); }
      });
      flush();grid.replaceChildren(fragment);grid.classList.add('ref-justified');
    }
    var resizeTimer;
    window.addEventListener('resize', function () { clearTimeout(resizeTimer);resizeTimer = setTimeout(layoutRows, 120); });
    var categories = Array.from(document.querySelectorAll('[data-filter]'));
    categories.forEach(function (button) { if (button.dataset.filter === 'All photos') button.textContent = 'All groups'; });
    var params = new URLSearchParams(location.search);
    var group = params.get('group') || 'All photos';
    if (categories.length && !categories.some(function (b) { return b.dataset.filter === group; })) group = 'All photos';
    var mode = params.get('view') === 'all' || params.has('group') || location.hash ? 'all' : 'highlights';
    if (params.get('view') === 'highlights') mode = 'highlights';
    var tools = el('div', 'ref-collection-tools');
    var switcher = el('div', 'ref-view-switch');
    switcher.setAttribute('role', 'group');
    switcher.setAttribute('aria-label', 'Collection view');
    var highlight = el('button', '', 'Highlights');
    var all = el('button', '', 'All photos');
    highlight.type = all.type = 'button';
    switcher.append(highlight, all);
    var filters = document.querySelector('.filters');
    var status = document.getElementById('filter-status');
    if (!status) {
      status = el('p', 'ref-collection-status');
      grid.before(status);
    }
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.before(tools);
    tools.append(switcher);
    if (filters) tools.append(filters);
    function apply(updateUrl) {
      var count = 0, total = 0;
      cards.forEach(function (card) {
        var matches = group === 'All photos' || card.dataset.category === group;
        if (matches) total++;
        card.hidden = !matches || mode === 'highlights' && card.dataset.highlight !== 'true';
        if (!card.hidden) count++;
        var target = new URL(card.href);
        if (mode === 'highlights') target.searchParams.set('view', 'highlights');
        else target.searchParams.delete('view');
        card.href = target.href;
      });
      document.querySelectorAll('[data-place]').forEach(function (heading) {
        heading.hidden = group !== 'All photos' && heading.dataset.place !== group;
      });
      categories.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.filter === group)); });
      highlight.setAttribute('aria-pressed', String(mode === 'highlights'));
      all.setAttribute('aria-pressed', String(mode === 'all'));
      status.textContent = mode === 'highlights' ? count + ' highlights from ' + total + ' photographs' : total + ' photographs';
      if (group !== 'All photos') status.textContent += ' · ' + group;
      grid.classList.toggle('showing-highlights', mode === 'highlights');
      layoutRows();
      if (updateUrl) {
        var state = new URL(location.href);
        state.searchParams.set('view', mode);
        if (group === 'All photos') state.searchParams.delete('group'); else state.searchParams.set('group', group);
        state.hash = '';
        history.replaceState(null, '', state.pathname + state.search);
        track('collection_filter', { collection_name: grid.dataset.collection, photo_group: group, view_mode: mode });
      }
    }
    highlight.addEventListener('click', function () { mode = 'highlights'; apply(true); });
    all.addEventListener('click', function () { mode = 'all'; apply(true); });
    categories.forEach(function (button) { button.addEventListener('click', function () { group = button.dataset.filter; apply(true); }); });
    apply(false);
  }

  // Main collection pages retain their own URLs, share controls and full images.
  var match = location.pathname.match(/photos\/photo-(\d+)\.html$/);
  if (match && data && data.photos[match[1]] && features.photoDock) {
    var id = match[1], info = data.photos[id];
    var query = new URLSearchParams(location.search);
    var favorite = query.get('tour') === 'favorites';
    var wildlife = query.get('from') === 'wildlife';
    var highlightsOnly = query.get('view') === 'highlights';
    var currentGroup = data.groups.find(function (g) { return g.key === info.group; });
    var relevantGroups = data.groups.filter(function (g) { return g.path === currentGroup.path; });
    var selected = relevantGroups.reduce(function (ids, g) { return ids.concat(g.ids); }, []);
    if (highlightsOnly && data.highlights[currentGroup.path]) selected = selected.filter(function (n) { return data.highlights[currentGroup.path].includes(n); });
    var sequence = favorite ? data.favorites : wildlife ? data.wildlife : selected;
    if (!sequence.includes(id)) sequence = selected = relevantGroups.reduce(function (ids, g) { return ids.concat(g.ids); }, []);
    var position = sequence.indexOf(id);
    var groupIds = favorite || wildlife ? sequence : currentGroup.ids.filter(function (n) { return sequence.includes(n); });
    var groupName = favorite ? 'A few favorites' : wildlife ? 'Wildlife' : currentGroup.name;
    var returnPath = favorite ? 'favorites.html' : wildlife ? 'wildlife.html#photo-' + id : currentGroup.path + '?group=' + encodeURIComponent(currentGroup.name) + '&view=' + (highlightsOnly ? 'highlights' : 'all') + '#photo-' + id;
    var suffix = favorite ? '?tour=favorites' : wildlife ? '?from=wildlife' : highlightsOnly ? '?view=highlights' : '';
    document.querySelectorAll('.photo-quick-nav,.photo-group-transition,.photo-new-group').forEach(function (node) { node.remove(); });
    var article = document.querySelector('.detail');
    var returnLinks = document.querySelectorAll('.detail .back,[data-photo-return]');
    returnLinks.forEach(function (a) { a.href = url(returnPath); a.textContent = '← Back to ' + groupName; });
    var duplicateNav = article.querySelector('.photo-nav');
    if (duplicateNav) duplicateNav.hidden = true;
    var bar = el('nav', 'ref-photo-dock');
    bar.setAttribute('aria-label', 'Browse photographs');
    var counter = el('div', 'ref-photo-position', groupName + ' · ' + (groupIds.indexOf(id) + 1) + ' of ' + groupIds.length);
    bar.append(counter);
    function direction(offset, className) {
      var targetId = sequence[position + offset];
      var a = el('a', className);
      if (targetId) {
        var targetGroup = data.groups.find(function (g) { return g.key === data.photos[targetId].group; });
        var crossGroup = !favorite && !wildlife && targetGroup.key !== currentGroup.key;
        a.href = url(data.photos[targetId].path + suffix);
        a.textContent = offset < 0 ? '← Previous' : crossGroup ? 'Next group →' : 'Next →';
        a.setAttribute('aria-label', crossGroup ? 'Continue to ' + targetGroup.name : offset < 0 ? 'Previous photograph' : 'Next photograph');
        if (offset > 0 && crossGroup) counter.textContent += ' · Next: ' + targetGroup.name;
        a.dataset.photoStep = offset < 0 ? 'previous' : 'next';
      } else {
        a.href = url(returnPath);
        a.textContent = offset < 0 ? '← Collection' : 'Finish ✓';
        a.setAttribute('aria-label', 'Return to ' + groupName);
      }
      return a;
    }
    var previous = direction(-1, 'ref-dock-prev');
    var next = direction(1, 'ref-dock-next');
    var toggle = el('button', 'ref-dock-browse', 'Thumbnails');
    toggle.type = 'button';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', 'ref-photo-thumbnails');
    bar.append(previous, toggle, next);
    var strip = el('div', 'ref-photo-thumbnails');
    strip.id = 'ref-photo-thumbnails';strip.hidden = true;
    var label = el('p', '', groupName + ' · choose a photograph');
    var row = el('div', 'ref-thumbnail-row');
    groupIds.forEach(function (n, index) {
      var a = el('a', n === id ? 'is-current' : '');
      a.href = url(data.photos[n].path + suffix);
      a.setAttribute('aria-label', 'Photo ' + (index + 1) + ': ' + data.photos[n].alt);
      if (n === id) a.setAttribute('aria-current', 'true');
      var image = el('img');image.src = url(data.photos[n].thumb);image.alt = '';image.loading = 'lazy';image.width = 96;image.height = 70;
      a.append(image, el('span', '', String(index + 1)));row.append(a);
    });
    strip.append(label, row);document.body.append(strip, bar);
    toggle.addEventListener('click', function () {
      strip.hidden = !strip.hidden;toggle.setAttribute('aria-expanded', String(!strip.hidden));
      if (!strip.hidden) { row.querySelector('.is-current').scrollIntoView({ block: 'nearest', inline: 'center' }); track('photo_thumbnails_open', { photo_id: id, photo_group: groupName }); }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { strip.hidden = true;toggle.setAttribute('aria-expanded', 'false');return; }
      if (event.altKey || event.ctrlKey || event.metaKey || /INPUT|TEXTAREA|SELECT|BUTTON/.test(event.target.tagName) || event.target.isContentEditable || document.querySelector('dialog[open]')) return;
      if (event.key === 'ArrowLeft' && position > 0) { event.preventDefault();previous.click(); }
      if (event.key === 'ArrowRight' && position < sequence.length - 1) { event.preventDefault();next.click(); }
    });
    document.body.classList.add('ref-has-photo-dock');
    track('photo_view', { photo_id: id, photo_group: groupName, view_mode: favorite ? 'favorites' : highlightsOnly ? 'highlights' : 'all' });
  }

  // Measure exploration without sending query strings or personal identifiers.
  if (features.eventTracking) {
    document.addEventListener('click', function (event) {
      var link = event.target.closest('a');
      if (!link) return;
      var dest = new URL(link.href, location.href);
      if (link.dataset.photoStep) track('photo_navigation', { direction: link.dataset.photoStep, destination_path: dest.pathname });
      else if (/pinterest\./.test(dest.hostname)) track(dest.pathname.includes('/pin/create') ? 'pinterest_save_click' : 'pinterest_follow_click', {});
      else if (dest.origin === location.origin && /\/(destinations|stories)\/|\/(favorites|stories)\.html/.test(dest.pathname)) track('collection_open', { destination_path: dest.pathname, link_label: link.textContent.trim().slice(0,80) });
    });
    var share = document.getElementById('share');
    if (share) share.addEventListener('click', function () { track('photo_share_click', { photo_id: match ? match[1] : '' }); });
    document.querySelectorAll('video').forEach(function (video, index) {
      var milestones = {};
      var label = video.getAttribute('aria-label') || 'Video ' + (index + 1);
      video.addEventListener('play', function () { if (!milestones.start) { milestones.start = true; track('travel_video_start', { video_title: label }); } });
      video.addEventListener('timeupdate', function () {
        if (!Number.isFinite(video.duration) || video.duration <= 0) return;
        [25,50,75].forEach(function (percent) { if (!milestones[percent] && video.currentTime/video.duration*100 >= percent) { milestones[percent] = true;track('travel_video_progress', { video_title: label, video_percent: percent }); } });
      });
      video.addEventListener('ended', function () { track('travel_video_complete', { video_title: label }); });
    });
  }
})();
