// MAD Club site renderer: every page is built from content/*.json (edited via /admin).
const NAV = [["index.html","Home"],["events.html","Events"],["about.html","About"],["achievements.html","Achievements"],["team.html","Team"],["contact.html","Contact"]];
const SKINS = [["night","Night"],["pop","Pop"],["raw","Raw"]];
const root = document.documentElement;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const load = n => fetch(`content/${n}.json`).then(r => { if (!r.ok) throw new Error(n); return r.json(); });
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const page = document.body.dataset.page;
const semYear = s => (s.match(/^\d\d-\d\d/) || [""])[0];

root.classList.add("js");
try { root.dataset.skin = new URLSearchParams(location.search).get("skin") || localStorage.getItem("skin") || "night"; } catch { root.dataset.skin = "night"; }

function shell(site) {
  const cur = location.pathname.split("/").pop() || "index.html";
  document.body.insertAdjacentHTML("afterbegin", `<a class="skip" href="#main">Skip to content</a><div class="progress" id="progress"></div>
<header class="nav"><div class="wrap"><a class="brand" href="index.html">${esc(site.name)}<small>${esc(site.college_short)}</small></a>
<nav class="links" id="links" aria-label="Main">${NAV.map(([h,t])=>`<a href="${h}"${h===cur?' aria-current="page"':""}>${t}</a>`).join("")}</nav>
<div class="skins" role="group" aria-label="Site style">${SKINS.map(([k,t])=>`<button type="button" data-skin="${k}" aria-pressed="${root.dataset.skin===k}">${t}</button>`).join("")}</div>
<button class="burger" id="burger" type="button" aria-expanded="false" aria-controls="links">Menu</button></div></header>`);
  document.body.insertAdjacentHTML("beforeend", `<footer><div class="wrap"><div class="cols"><div><p class="foot-brand">${esc(site.full_name)}</p><p>${esc(site.college)} (${esc(site.college_short)}). Est. ${esc(site.established)}.</p><p><a href="${esc(site.instagram)}">${esc(site.instagram_handle)} on Instagram</a></p></div>
<ul><li><b>Explore</b></li>${NAV.map(([h,t])=>`<li><a href="${h}">${t}</a></li>`).join("")}</ul>
<ul><li><b>Event archives</b></li><li><a href="events.html?y=25-26">2025-26</a></li><li><a href="events.html?y=24-25">2024-25</a></li><li><a href="events.html?y=23-24">2023-24</a></li></ul></div>
<p class="legal">&copy; ${new Date().getFullYear()} ${esc(site.full_name)}, ${esc(site.college_short)} &middot; <a href="admin/">Admin</a></p></div></footer>`);
  const links = $("#links"), burger = $("#burger");
  const setMenu = o => { links.classList.toggle("open", o); burger.setAttribute("aria-expanded", o); };
  burger.onclick = () => setMenu(!links.classList.contains("open"));
  links.onclick = e => e.target.closest("a") && setMenu(false);
  document.addEventListener("keydown", e => { if (e.key === "Escape") { setMenu(false); } });
  $$(".skins button").forEach(b => b.onclick = () => {
    root.dataset.skin = b.dataset.skin;
    try { localStorage.setItem("skin", b.dataset.skin); } catch {}
    $$(".skins button").forEach(x => x.setAttribute("aria-pressed", x === b));
  });
  const bar = $("#progress");
  addEventListener("scroll", () => { bar.style.transform = `scaleX(${scrollY / Math.max(1, document.body.scrollHeight - innerHeight)})`; }, {passive:true});
  addEventListener("pointermove", e => { root.style.setProperty("--mx", e.clientX + "px"); root.style.setProperty("--my", e.clientY + "px"); }, {passive:true});
}

function activate() {
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), {threshold:.12});
  $$(".reveal").forEach(el => io.observe(el));
  const cio = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    cio.unobserve(e.target);
    const m = e.target.textContent.match(/^(\d+)(.*)$/); if (!m || reduced) return;
    const end = +m[1], t0 = performance.now();
    const tick = t => { const p = Math.min(1, (t - t0) / 1100); e.target.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))) + m[2]; if (p < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }), {threshold:.6});
  $$("[data-count]").forEach(el => cio.observe(el));
}

const head = (eyebrow, title, lead) => `<div class="page-head wrap"><p class="eyebrow">${esc(eyebrow)}</p><h1 class="reveal">${esc(title)}</h1>${lead ? `<p class="lead reveal">${esc(lead)}</p>` : ""}</div>`;
const eventRow = (e, i) => `<a class="row reveal" href="event.html?e=${encodeURIComponent(e.slug)}"><span class="idx">${String(i + 1).padStart(2, "0")}</span><span class="row-main"><b>${esc(e.name)}</b><span>${esc(e.description)}</span></span><span class="tag">${esc(e.semester)}</span></a>`;

function phone(events) {
  const rows = events.slice(0, 5).map((e, i) => `<li class="${i === 0 ? "on" : ""}"><b>${esc(e.name)}</b><span>${esc(e.semester)}</span></li>`).join("");
  return `<div class="stage" aria-hidden="true"><div class="phone"><div class="notch"></div><div class="screen"><p class="s-title">Events</p><ul class="s-list">${rows}</ul><div class="s-bar"><i></i><i></i><i></i></div></div></div>
<pre class="code"><span class="c1">class</span> <span class="c2">MadClub</span> <span class="c1">extends</span> StatelessWidget {
  <span class="c3">Widget</span> build(context) =&gt;
    <span class="c2">Text</span>(<span class="c4">'Code. Fun. Repeat.'</span>);
}</pre></div>`;
}

const pages = {
  async home(site) {
    const { events } = await load("events");
    const flags = events.filter(e => e.flagship);
    const words = site.hero_title.split(" ").map((w, i) => `<span class="w" style="--i:${i}">${esc(w)}</span>`).join(" ");
    const marquee = [...events, ...events].map(e => `<span>${esc(e.name)}</span>`).join("");
    return `<section class="hero wrap"><div class="hero-copy"><p class="tagline">&gt; ${esc(site.tagline)}_</p><h1 class="split">${words}</h1><p class="lead">${esc(site.hero_lead)}</p>
<p><a class="btn primary" href="contact.html">Join the club</a><a class="btn" href="events.html">See our events</a></p></div>${phone(events)}</section>
<div class="marquee" aria-hidden="true"><div class="track">${marquee}</div></div>
<section class="wrap"><div class="stats">${site.stats.map(s => `<div class="stat reveal"><b data-count>${esc(s.value)}</b><span>${esc(s.label)}</span></div>`).join("")}</div></section>
<section class="wrap"><p class="eyebrow">What makes us tick</p><div class="big-list">${site.highlights.map((h, i) => `<div class="big reveal"><span class="idx">${String(i + 1).padStart(2, "0")}</span><h2>${esc(h.title)}</h2><p>${esc(h.text)}</p></div>`).join("")}</div></section>
<section class="wrap"><div class="sec-head"><div><p class="eyebrow">Flagship events</p><h2>Open to every student, every semester.</h2></div><a class="btn" href="events.html">All events</a></div><div class="rows">${flags.map(eventRow).join("")}</div></section>
<section class="wrap"><p class="eyebrow">${esc(site.why_title)}</p><h2 class="why-h">${esc(site.why_lead)}</h2><div class="grid">${site.why.map((w, i) => `<div class="card reveal"><span class="idx">${String(i + 1).padStart(2, "0")}</span><h3>${esc(w.title)}</h3><p>${esc(w.text)}</p></div>`).join("")}</div></section>
<section class="wrap"><div class="cta reveal"><h2>${esc(site.cta_title)}</h2><p class="lead">${esc(site.cta_text)}</p><a class="btn primary" href="contact.html">Register now</a><a class="btn" href="${esc(site.instagram)}">${esc(site.instagram_handle)}</a></div></section>`;
  },

  async events() {
    const { events } = await load("events");
    const years = [...new Set(events.map(e => semYear(e.semester)))].sort().reverse();
    const sel = new URLSearchParams(location.search).get("y") || "all";
    const chip = (v, t) => `<a class="chip" href="events.html${v === "all" ? "" : "?y=" + v}"${sel === v ? ' aria-current="true"' : ""}>${t}</a>`;
    const sems = [...new Set(events.filter(e => sel === "all" || semYear(e.semester) === sel).map(e => e.semester))].sort().reverse();
    return head("Events", "Everything we have run.", "Every event, newest first. Open one for its photos.") +
      `<div class="wrap chips">${chip("all", "All")}${years.map(y => chip(y, "20" + y.replace("-", "-20"))).join("")}</div>
<div class="wrap">${sems.map(s => `<h2 class="sem">${esc(s)}</h2><div class="rows">${events.filter(e => e.semester === s).map(eventRow).join("")}</div>`).join("") || "<p class='lead'>No events for that year yet.</p>"}</div>`;
  },

  async event() {
    const { events } = await load("events");
    const e = events.find(x => x.slug === new URLSearchParams(location.search).get("e"));
    if (!e) { document.title = "Event not found | MAD Club"; return head("Events", "Event not found") + `<div class="wrap"><a class="btn" href="events.html">All events</a></div>`; }
    document.title = `${e.name} | MAD Club`;
    const ph = e.photos || [];
    return head(e.semester, e.name, e.description) + `<div class="wrap">${ph.length ? `<div class="gallery">${ph.map((p, i) => `<button type="button" class="shot" data-src="${esc(p)}"><img loading="lazy" decoding="async" src="${esc(p)}" alt="${esc(e.name)}, photo ${i + 1}"></button>`).join("")}</div>` : `<div class="empty">No photos yet. Add them in the admin panel under Events.</div>`}
<p class="back"><a class="btn" href="events.html">All events</a></p></div><dialog id="lb"><img alt=""><form method="dialog"><button class="btn">Close</button></form></dialog>`;
  },

  async about(site) {
    const a = site.about;
    return head("About us", site.full_name, `${site.college}. Established ${site.established}.`) +
      `<div class="wrap"><div class="grid">${[["Who we are", a.who], ["Our objective", a.objective], ["Outcomes", a.outcomes]].map(([t, p], i) => `<div class="card reveal"><span class="idx">${String(i + 1).padStart(2, "0")}</span><h3>${t}</h3><p>${esc(p)}</p></div>`).join("")}</div>
<h2 class="sem">What we do</h2><div class="rows">${a.functions.map((f, i) => `<div class="row reveal"><span class="idx">${String(i + 1).padStart(2, "0")}</span><span class="row-main"><b>${esc(f.title)}</b><span>${esc(f.text)}</span></span></div>`).join("")}</div>
<p class="back"><a class="btn primary" href="contact.html">Join us</a></p></div>`;
  },

  async achievements() {
    const a = await load("achievements"), { events } = await load("events");
    return head("Achievements", "What we have shipped.") +
      `<div class="wrap"><div class="stats">${a.stats.map(s => `<div class="stat reveal"><b data-count>${esc(s.value)}</b><span>${esc(s.label)}</span></div>`).join("")}</div>
<h2 class="sem">Flagship events</h2><div class="rows">${events.filter(e => e.flagship).map(eventRow).join("")}</div>
<h2 class="sem">Apps built by members</h2><div class="grid">${a.apps.map((p, i) => `<div class="card reveal"><span class="idx">${String(i + 1).padStart(2, "0")}</span><h3>${esc(p.name)}</h3><p>${esc(p.text)}</p></div>`).join("")}</div></div>`;
  },

  async team() {
    const t = await load("team");
    const ini = n => n.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join("");
    const person = (p, sub) => `<div class="card person reveal"><div class="avatar">${esc(ini(p.name))}</div><b>${esc(p.name)}</b><small>${esc(sub)}</small></div>`;
    return head("The team", "The people behind MAD.") +
      `<div class="wrap"><h2 class="sem">Core team ${esc(t.current_year)}</h2><div class="grid">${t.current.map(p => person(p, p.role)).join("")}</div>
<h2 class="sem">Earlier teams</h2><div class="grid">${t.earlier.map(p => person(p, `${p.role}, ${p.year}`)).join("")}</div></div>`;
  },

  async notfound() {
    return head("404", "Page not found.", "That page does not exist.") + `<div class="wrap"><a class="btn primary" href="index.html">Home</a><a class="btn" href="events.html">Events</a></div>`;
  },

  async contact(site) {
    const c = site.contact, ep = (c.form_endpoint || "").trim();
    const form = ep ? `<form action="${esc(ep)}" method="POST" class="form"><label>Name<input name="name" autocomplete="name" required></label><label>Email<input name="email" type="email" autocomplete="email" required></label><label>Why do you want to join?<textarea name="message" rows="4"></textarea></label><button class="btn primary" type="submit">Send</button></form>`
      : `<div class="empty">Online registration opens soon. Message us on <a href="${esc(site.instagram)}">${esc(site.instagram_handle)}</a> to join.</div>`;
    return head("Contact us", "Join MAD Club.", "New members are welcome every semester.") +
      `<div class="wrap"><div class="grid"><div class="card"><h3>Instagram</h3><p><a href="${esc(site.instagram)}">${esc(site.instagram_handle)}</a></p></div><div class="card"><h3>Coordinators</h3><p>${esc(c.coordinators)}</p></div><div class="card"><h3>Where</h3><p>${esc(site.college)}</p></div></div>
<h2 class="sem">Register interest</h2>${form}</div>`;
  }
};

(async () => {
  const main = $("#main");
  try {
    const site = await load("site");
    shell(site);
    main.innerHTML = await pages[page](site);
    if (page !== "event" && page !== "events") document.title = (page === "home" ? "" : $("h1", main)?.textContent.replace(/\.$/, "") + " | ") + site.name + " | " + site.college_short;
    main.addEventListener("click", e => {
      const b = e.target.closest(".shot"); if (!b) return;
      const d = $("#lb"); $("img", d).src = b.dataset.src; d.showModal();
    });
    // cycle the highlighted row inside the hero phone
    const li = $$(".s-list li");
    if (li.length && !reduced) { let n = 0; setInterval(() => { li[n].classList.remove("on"); n = (n + 1) % li.length; li[n].classList.add("on"); }, 1800); }
    activate();
  } catch (err) {
    main.innerHTML = `<div class="wrap page-head"><h1>Could not load content</h1><p class="lead">Open the site through a web server (not by double-clicking the file) so it can read the content folder.</p></div>`;
  }
})();
