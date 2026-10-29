# MAD Club site

Static site with a visual editor at `/admin/` and a GitHub-backed CMS (Decap) at `/admin/cms/`. All text, events, team and photos live in `content/*.json` and `photos/`, and the pages are built from them in the browser.

## Two editors

**1. Testing editor at `/admin/` (login `admin` / `admin`).** Visual forms with a live preview (desktop, tablet, phone). Edits are saved as a draft in your own browser and show on the site in that browser only. The password check runs in the browser, so it is for testing, not security. To publish an edit for everyone, press **Download JSON** and replace the matching file in `content/`, then commit.

**2. Real publishing editor at `/admin/cms/` (GitHub login).** Edit and press **Publish**. Decap commits to the repo and the site redeploys in about a minute. Only GitHub users with write access to the repo can log in; add collaborators on GitHub to give access.

## One-time setup (for the GitHub editor)

1. Push this folder to a GitHub repo (branch `main`).
2. In `admin/cms/config.yml` replace `YOUR_GITHUB_USERNAME/YOUR_REPO` (three places).
3. Enable Pages: repo Settings, Pages, Source "GitHub Actions" (workflow is included).
4. Login needs an OAuth step, because GitHub Pages cannot do it alone. Pick one:
   - **Netlify (simplest).** Host the site on Netlify (drag the folder in or connect the repo), then Site settings, Access control, OAuth, Install provider: GitHub (create a GitHub OAuth app with callback `https://api.netlify.com/auth/done`). `/admin/cms/` then works with no other change.
   - **Stay on GitHub Pages.** Deploy a free OAuth proxy (for example `sterlingwes/decap-proxy` on Cloudflare Workers), then set `base_url` in `admin/cms/config.yml` to its URL.

## Edit locally without logging in

```
npx decap-server
python -m http.server 8000
```

Open `http://localhost:8000/admin/cms/`. `local_backend: true` skips login and edits the files directly.

## Looks

Three skins (Night, Pop, Raw) share one structure. Visitors switch with the control in the header, and the choice is remembered. Change the default in the inline script in each page's `<head>` and in `assets/site.js`.

## Interactions

Ctrl+K (or the Search button) opens a command menu for pages, events and styles. Press `/` on the Events page to jump to search. Cards tilt, buttons follow the pointer, and the phone on the home page is clickable.

## Other

- Contact form: set "Form endpoint" in the admin to a Formspree URL. Empty shows an Instagram notice instead.
- Open the site through a web server, not by double-clicking `index.html`, so the browser can read `content/`.
