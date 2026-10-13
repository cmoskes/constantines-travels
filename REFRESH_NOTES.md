# Browsing refresh — October 13, 2026

Baseline: 77b8fdfadd221dfd2b3df4b3103dc72f889c775f.
Backup branch: backup/before-browsing-refresh-2026-10-13.

The original photographs, photo URLs, collection order, bear-story viewer and analytics opt-out are retained.

Enhancements are isolated in assets/refresh.css and assets/refresh.js. The highlights, photoDock and eventTracking flags in refresh.js can be disabled separately. HTML presentation changes cover the homepage, story index, favorites, collection recommendations, gear copy and upcoming collections. Restore those sections from the backup branch to revert an individual design choice. Full rollback should use a new revert commit, never reset published history. Preserve any subsequent content additions and analytics changes.

New collection data is in assets/collection-data.js. When adding photographs, update the matching group, collection and photo entry there, plus the HTML gallery. Existing order must be retained. Highlights and favorites are explicit selections, separate from the complete archive.

Validation: 101 HTML pages checked for local links, one main/h1, one GA configuration, and refresh inclusion. JavaScript syntax checked. Analytics opt-out remains before the Google loader. Live interaction checks follow deployment.
