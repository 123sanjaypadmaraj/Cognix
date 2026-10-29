# Autopilot status

Project: MAD Club website (Mobile App Development Club, New Horizon College of Engineering).
Static HTML/CSS/JS, no build step, deployed to GitHub Pages via `.github/workflows/pages.yml`.

Redesign ground rules (apply to every task below):
- No emojis anywhere (content, JS templates, CSS `content:`), and no emoji-like decorative pictographs.
- No AI-generated or placeholder logos. The brand is a plain typographic wordmark set in the site's own type.
- No gradient blobs, no purple/cyan gradients, no gradient text. Flat colour, one accent, real hierarchy.
- Stay static: plain HTML/CSS/vanilla JS, no framework, no bundler, no npm.
- Content facts must stay accurate: est. 2023, 150+ participants per event, 4 flagships (Mindspark'23, InnoWave'24, TechSync'24, Connect'24), TechSync'24 with 4 clubs, 11 core-team roles, Instagram @md_club_nhce, the existing event list in `assets/site.js` EVENTS and the team names in `team.html`. Do not invent new numbers, quotes, sponsors, dates or people.

Design decisions already made (so no task needs to ask):
- Type: IBM Plex Sans (400/500/600/700) for text and headings, IBM Plex Mono (400/500) for labels, numbers and the tagline; loaded from Google Fonts with `display=swap` and a system-ui / ui-monospace fallback stack.
- Colour: light theme is the default (also follow `prefers-color-scheme`, then the saved toggle). Light: background #FAFAF7, surface #FFFFFF, text #111418, muted #5A616B, border #E3E3DE. Dark: background #0F1113, surface #171A1D, text #ECEDEE, muted #9BA1A8, border #2A2E33. Single accent: #C2410C (burnt orange) in light, #F97316 in dark; used only for links, active nav, focus rings, primary button and small labels. All text/background pairs must meet WCAG AA.
- Shape: radius 6px for cards/buttons/inputs (no 18-28px pill-ish cards), 1px borders, no drop-shadow glow, hover = border/underline change, not lift-and-scale.
- Wordmark: the text "MAD Club" in Plex Sans 700 with tight letter-spacing, optionally followed by a small mono "NHCE" label. No box, badge, monogram tile or image.
- Card icons are replaced by a small mono index label ("01", "02", ...) or nothing; no icon font, no SVG icon set.

## Task list

- [done] **Establish the design system in `assets/style.css`**
  Replace the `:root` / `[data-theme=light]` tokens with the palette, type, radius and spacing scale defined above (add `--space-*` and `--font-sans` / `--font-mono` variables); delete `--grad`, `--accent2`, `.grad`, the `.hero::before/::after` radial blobs and every `linear-gradient`/`radial-gradient` in the file; add the Google Fonts `<link rel="preconnect">` + stylesheet link to all 7 HTML heads. Done when `grep -i gradient assets/style.css` is empty, every page renders in Plex with no gradient, and both themes pass AA contrast for body text, muted text and accent links.

- [done] **Sweep out all emojis, pictograph glyphs and the placeholder "MAD" logo tile**
  Remove every `.ico` emoji in `index.html` (7) and `achievements.html` (2) and the trophy emoji in the `[data-events]` card template in `assets/site.js`, replacing them with a mono index label (`<span class="idx">01</span>`) or nothing; replace the `<span class="logo">MAD</span>` tile and `.logo` CSS with the typographic wordmark; replace the `◐` theme and `☰` menu glyphs with text buttons ("Theme" / "Menu") or a two-line CSS-drawn burger; replace the gradient initial `.avatar` circles in `team.html` with neutral surface initials. Done when a Unicode grep for U+2190-21FF, U+2600-27BF, U+25D0-25FF and U+1F300-1FAFF across `*.html`/`*.js`/`*.css` returns nothing (plain "<-"/"->" text or CSS arrows are fine).

- [done] **Rebuild the shared header and footer in `assets/site.js` for a professional, accessible shell**
  Header: wordmark left, nav right, active page marked with `aria-current="page"` plus an accent underline (not a filled pill), a "Skip to content" link before the header targeting `<main id="main">` (add the id on all pages), burger button with `aria-expanded`/`aria-controls` that also closes on Escape and on link click. Footer: three columns (club name + NHCE + est. 2023 + Instagram, Explore links, Event archives by year) collapsing to one column under 640px, plus a bottom line "(c) <current year> Mobile App Development Club, NHCE" computed in JS. Done when keyboard-only navigation works through the whole header at 360px and 1280px widths and no layout shift occurs when the header is injected (reserve its 64px height in CSS).

- [pending] **Redesign the home page hero and sections (`index.html`)**
  Hero: left-aligned, mono tagline "> Code. Fun. Repeat._" kept as text, headline without gradient text, one-paragraph lead, primary "Join the club" + secondary text-link "See past events"; stats become a single bordered row of 4 figures (150+ / 4 / 11 / 2023) in mono numerals with hairline dividers, not 4 floating cards. Sections: "Learn by building" and "Why join us" become a numbered two-column list (index label + title + one line) instead of icon cards; "Flagship events" shows the 4 flagships as a clean list/table (name, semester, one-line description, link) rendered from EVENTS; final CTA band uses flat surface colour. Done when the page has no `style=` attributes left (move them to classes) and all copy/facts match the current page.

- [pending] **Redesign the events listing and event detail/gallery pages**
  `events.html`: semester groups become a year-by-year archive (semester heading in mono, then compact rows or 3-up cards with name, description, "Photos (n)" or "No photos yet"); semesters with zero events are hidden by `site.js` instead of showing an empty grid. `event.html` + `site.js`: remove the `hue` field from EVENTS and the coloured gradient tiles; render real `<img loading="lazy" decoding="async">` from `photos/<slug>/<n>.jpg` in a uniform 4:3 grid with a neutral surface placeholder and an `alt` of "<Event name>, photo n", show a proper empty state when `photos` is 0, and for unknown/missing `?e=` show "Event not found" with a link back and set `<meta name="robots" content="noindex">`. Add a short `photos/README.md` explaining the folder convention. Done when no event-specific colours remain and every event slug in EVENTS opens without console errors.

- [pending] **Redesign About, Team and Achievements pages**
  `about.html`: two-column layout (heading left, prose right) for "Who we are / Objective / Outcomes", restyle the timeline with a plain 1px rule and small accent squares instead of gradient dots, list the four committees (Program, Project, Marketing, Review) as a definition list. `team.html`: move the inline `T` array and render script into `site.js` (or a `data-team` container), show the 11 core roles as a tidy grid of name + role with neutral initials, keep "Earlier teams" (Chiranjeevi, Likitha K, 2024-25), and change the closing note so it no longer claims a 26-27 team exists (say "Each year's team follows the same 11 roles: ..."). `achievements.html`: stats as the same bordered figure row used on home, flagship list matching the events style, member apps (Evently, Treasure-hunt app) as plain project cards. Done when these pages have no inline `style=`/`<script>` blocks beyond the shared `site.js` and all names/numbers are unchanged.

- [pending] **Redesign the Contact page and make the join form safe while unconfigured**
  Move the inline `<style>` from `contact.html` into `style.css`; give inputs visible `<label>`s (not placeholder-only), 6px radius, accent focus ring, and an `autocomplete` attribute on name/email. In `site.js`, if the form `action` still contains `YOUR_FORM_ID`, replace the form with a short notice "Online registration opens soon - message us on Instagram @md_club_nhce" linking to the Instagram URL, so visitors never submit to a dead endpoint; keep the HTML comment explaining how to configure Formspree. Done when submitting is impossible while unconfigured and the form works unchanged once a real id is pasted in.

- [pending] **Accessibility and responsiveness pass across all pages**
  Add `:focus-visible` outlines (2px accent, 2px offset) on links/buttons/inputs; wrap `.reveal` animation and `scroll-behavior:smooth` in `@media (prefers-reduced-motion: no-preference)` and make `.reveal` content visible by default when JS is off (add a `js` class on `<html>` from site.js and only hide `.reveal` under `.js`); prevent theme flash by moving the saved-theme read into a tiny inline `<script>` in each `<head>`; ensure one `<h1>` per page and no skipped heading levels (the `h3.sem` group headings under `h1` should become `h2`); check layouts at 360, 768 and 1280px with no horizontal scroll and tap targets >= 44px. Done when a manual keyboard pass and Lighthouse accessibility score >= 95 on index, events and contact.

- [pending] **Add SEO/social meta, a typographic favicon and a 404 page**
  Give every page a unique `<title>` and `<meta name="description">` (based on its existing copy), `<meta name="theme-color">`, Open Graph/Twitter tags (`og:title`, `og:description`, `og:type`, `og:url` using the GitHub Pages URL derived from the repo remote, falling back to relative), and `<link rel="canonical">`. Add `favicon.svg` containing only the text "M" in the site font on a flat accent square (typographic, not an illustration) and link it. Add `404.html` in the site shell ("Page not found" + links to Home and Events, uses `site.js`, all asset paths root-relative-safe for GitHub Pages project sites), plus `robots.txt` and a hand-written `sitemap.xml` listing the 7 pages. Done when every page has the full meta set and visiting a non-existent path on Pages shows the styled 404.

## Run log

### 2026-10-29 - planner run (redesign plan)
- Surveyed: all 7 HTML pages, `assets/style.css`, `assets/site.js`, `.github/workflows/pages.yml`, recent git log (the enclosing Downloads repo's history is about the separate Club App project, so no MD Club-specific momentum to follow), grep for TODO/FIXME (only the `YOUR_FORM_ID` Formspree placeholder in `contact.html`), and a Unicode grep for emojis/pictographs. No prior `.claude/autopilot-status.md` existed, so this file was created fresh; nothing to deduplicate against.
- Findings driving the plan: 10 emoji occurrences (7 in index.html, 2 in achievements.html, 1 in the site.js event-card template) plus `◐`/`☰` glyphs; a gradient "MAD" logo tile; purple-to-cyan `--grad` used on buttons, stat numbers, avatars, timeline dots and gradient text; two radial-gradient hero blobs; per-event `hue` gradient gallery tiles while no `photos/` folder exists; no favicon, OG tags, 404, skip link, focus styles or reduced-motion handling; content hidden by `.reveal` when JS is off; burger lacks `aria-expanded`; many inline `style=` attributes; contact form posts to a placeholder endpoint; team page claims a 26-27 team.
- Added 9 tasks, ordered so the design system lands first and later tasks build on it:
  1. Design system - every other visual task depends on the tokens; removes all gradients at the source.
  2. Emoji/logo sweep - hard rule from the dispatch; scoped with a verifiable Unicode grep.
  3. Header/footer - shared shell on every page, plus the a11y gaps in the nav.
  4. Home page - highest-traffic page; replaces icon cards and floating stat cards.
  5. Events + gallery - removes the hue-gradient placeholders and handles empty/unknown events.
  6. About/Team/Achievements - layout + fixes the inaccurate 26-27 team claim.
  7. Contact - prevents submissions to the unconfigured Formspree id.
  8. Accessibility/responsiveness - focus, motion, no-JS visibility, heading order, theme flash.
  9. SEO/meta/404 - no meta beyond index's description today; Pages needs a 404.html.
- Decisions made without asking: IBM Plex Sans/Mono (distinctive but neutral, avoids the overused Inter/Space Grotesk look), light-first palette with a single burnt-orange accent, 6px radius, mono index numbers instead of any icons, keep header/footer injected by `site.js` (single source of truth for 7 pages) but make content visible without JS, unconfigured form falls back to Instagram.
- Deliberately not added: a photo lightbox or real photography (no photos are in the repo; the gallery task only makes the folder convention work), a build step / templating / framework (forbidden), new content such as testimonials, sponsor logos or extra stats (would risk inaccurate facts), and a CI lint/link-check job (low value until the redesign lands; can be proposed in a later run).

### 2026-10-29 - autopilot run 1 (branch autopilot/md-club-redesign)
- Picked up tasks 1-3 (design system, emoji/logo sweep, header/footer shell).
- Did: rewrote `assets/style.css` with the Plex/flat/burnt-orange token system (no gradients); added Google Fonts links and `id="main"` to all 7 pages; replaced emoji icons with mono index labels; typographic "MAD Club NHCE" wordmark; text Theme/Menu buttons; skip link, `aria-current`, `aria-expanded` burger closing on Escape/link click, three-column footer with computed year; removed gradient tiles from `event.html`.
- Verification (project has no test suite, so used each task's done-when checks): grep for gradient/--grad/.grad empty; Unicode pictograph grep empty; `node --check assets/site.js` ok; headless Chrome screenshot of index.html rendered correctly. Lighthouse and 360px checks not yet run (task 8).
- Not done: tasks 4-9. Known leftovers: inline `style=` attributes and index-numbering across two sections on home (04-07) are replaced in task 4; `hue` field in EVENTS is unused until task 5 removes it.
- Next session: tasks 4 (home), 5 (events/gallery), 6 (about/team/achievements).

### 2026-10-29 - direction change (user request)
- Superseded the Plex/burnt-orange plan above (tasks 4-9 are obsolete). New direction: three switchable skins (Night, Pop, Raw), content-driven pages (content/*.json) and a Decap CMS at /admin (GitHub login). Loop stopped.
- Built: content/*.json, admin/ (Decap 3.1.10 + config.yml), assets/site.js renderer, assets/style.css skins, regenerated 8 page shells, favicon, robots.txt, README.md setup.
- Verified: node --check ok; headless screenshots of all three skins; /admin/ renders the Decap login. Not verified: real GitHub login (needs repo + OAuth setup), 360px mobile, Lighthouse.
- Next: user sets repo/OAuth in README; then mobile and a11y pass; add real event photos via /admin.
