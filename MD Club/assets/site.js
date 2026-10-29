// Shared header/footer, theme toggle, reveal-on-scroll, event data.
const NAV = [["index.html","Home"],["events.html","Events"],["about.html","About"],["achievements.html","Achievements"],["team.html","Team"],["contact.html","Contact"]];
const INSTA = "https://www.instagram.com/md_club_nhce/";

// slug -> event; photos = count from the original galleries (original images are not bundled)
const EVENTS = {
  "mindspark23":{name:"Mindspark'23",sem:"23-24 Odd Sem",photos:11,hue:262,desc:"Our first flagship event: WikiWhiz, UI Clash and CodeMaze over 3 rounds with 150+ participants."},
  "innowave24":{name:"InnoWave'24",sem:"23-24 Odd Sem",photos:9,hue:190,desc:"Trivial Battle and Pitchpoint over 2 rounds with 150+ participants. Photos from January 2024."},
  "techsync24":{name:"TechSync'24",sem:"23-24 Even Sem",photos:11,hue:300,desc:"A cross-club event with 4 clubs: Visual Recall, Car Racing and Construction over 3 rounds."},
  "connect24":{name:"Connect'24",sem:"23-24 Even Sem",photos:0,hue:210,desc:"Flagship networking and collaboration event."},
  "pixel-pursuit24":{name:"Pixel Pursuit'24",sem:"24-25 Odd Sem",photos:0,hue:340,desc:"A pixel-themed challenge event."},
  "codathon":{name:"Codathon",sem:"24-25 Even Sem",photos:0,hue:150,desc:"A coding marathon for all students."},
  "appsylum25":{name:"Appsylum'25",sem:"25-26 Odd Sem",photos:0,hue:20,desc:"App building showdown."},
  "game-design26":{name:"Game Design'26",sem:"25-26 Even Sem",photos:0,hue:280,desc:"Game design challenge."},
  "gitout26":{name:"Gitout'26",sem:"25-26 Even Sem",photos:0,hue:100,desc:"Hands-on Git and collaboration event."}
};

const page = location.pathname.split("/").pop() || "index.html";
const header = document.createElement("header");
header.className = "nav";
header.innerHTML = `<div class="wrap"><a class="brand" href="index.html">MAD Club<small>NHCE</small></a>
<nav class="links" id="links" aria-label="Main">${NAV.map(([h,t])=>`<a href="${h}"${h===page?' aria-current="page"':""}>${t}</a>`).join("")}
<button class="text-btn" id="theme" type="button">Theme</button></nav>
<button class="text-btn burger" id="burger" type="button" aria-expanded="false" aria-controls="links">Menu</button></div>`;
const skip = document.createElement("a");
skip.className = "skip"; skip.href = "#main"; skip.textContent = "Skip to content";
document.body.prepend(header);
document.body.prepend(skip);

const footer = document.createElement("footer");
footer.innerHTML = `<div class="wrap"><div class="cols"><div><b>Mobile App Development Club</b><br>New Horizon College of Engineering (NHCE) &middot; Est. 2023<br><a href="${INSTA}">@md_club_nhce on Instagram</a></div>
<ul><li><b>Explore</b></li>${NAV.map(([h,t])=>`<li><a href="${h}">${t}</a></li>`).join("")}</ul>
<ul><li><b>Event archives</b></li><li><a href="events.html#25-26">2025-26</a></li><li><a href="events.html#24-25">2024-25</a></li><li><a href="events.html#23-24">2023-24</a></li></ul></div>
<p class="legal">&copy; ${new Date().getFullYear()} Mobile App Development Club, NHCE</p></div>`;
document.body.append(footer);

const linksEl = document.getElementById("links"), burger = document.getElementById("burger");
const setMenu = open => { linksEl.classList.toggle("open", open); burger.setAttribute("aria-expanded", open); };
burger.onclick = () => setMenu(!linksEl.classList.contains("open"));
linksEl.addEventListener("click", e => e.target.closest("a") && setMenu(false));
document.addEventListener("keydown", e => { if (e.key === "Escape") { setMenu(false); burger.focus(); } });
const root = document.documentElement;
try { const t = localStorage.getItem("theme"); if (t) root.dataset.theme = t; } catch {}
document.getElementById("theme").onclick = () => {
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  const n = dark ? "light" : "dark";
  root.dataset.theme = n;
  try { localStorage.setItem("theme", n); } catch {}
};

const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && e.target.classList.add("in")), {threshold:.12});
document.querySelectorAll(".reveal").forEach(el => io.observe(el));

// Render event cards into any [data-events] container
document.querySelectorAll("[data-events]").forEach(c => {
  const sems = (c.dataset.events || "").split(",").filter(Boolean);
  c.innerHTML = Object.entries(EVENTS).filter(([,e]) => !sems.length || sems.includes(e.sem)).map(([k,e]) =>
    `<a class="card reveal" href="event.html?e=${k}"><h3>${e.name}</h3><p>${e.desc}</p><span class="tag">${e.sem}</span></a>`).join("");
  c.querySelectorAll(".reveal").forEach(el => io.observe(el));
});
