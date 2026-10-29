// Testing admin: admin/admin login, schema-driven forms, live preview.
// Edits are saved to localStorage ("mad_content_<file>"), which the site reads in this browser.
// To publish for everyone, download the JSON and replace the file in content/ (or use the GitHub editor in admin/cms/).
const USER = "admin", PASS = "admin";
const $ = (s, el = document) => el.querySelector(s);
const KEY = n => "mad_content_" + n;
const str = (key, label, extra = {}) => ({ t: "string", key, label, ...extra });
const txt = (key, label) => ({ t: "text", key, label });
const list = (key, label, fields, summary, blank, sub) => ({ t: "list", key, label, fields, summary, blank, sub });
const pair = [str("title", "Title"), txt("text", "Text")];

const TABS = [
  { id: "home", label: "Home page", file: "site", preview: "../index.html", defs: [
    txt("hero_title", "Headline"), txt("hero_lead", "Intro paragraph"),
    list("stats", "Statistics", [str("value", "Figure (e.g. 150+)"), str("label", "Label")], i => `${i.value} ${i.label}`),
    list("highlights", "Highlights", pair, i => i.title),
    str("why_title", "Why-join heading"), txt("why_lead", "Why-join intro"),
    list("why", "Why-join points", pair, i => i.title),
    str("cta_title", "Call-to-action heading"), str("cta_text", "Call-to-action text")] },
  { id: "about", label: "About page", file: "site", preview: "../about.html", defs: [
    { t: "object", key: "about", label: "About page text", fields: [
      txt("who", "Who we are"), txt("objective", "Objective"), txt("outcomes", "Outcomes"),
      list("functions", "What we do", pair, i => i.title)] }] },
  { id: "contact", label: "Contact and basics", file: "site", preview: "../contact.html", defs: [
    str("name", "Short name"), str("full_name", "Full club name"), str("college", "College"), str("college_short", "College short name"),
    str("established", "Year established"), str("tagline", "Tagline"), str("instagram", "Instagram URL"), str("instagram_handle", "Instagram handle"),
    { t: "object", key: "contact", label: "Contact page", fields: [
      str("coordinators", "Coordinators"),
      str("form_endpoint", "Form endpoint (Formspree URL; leave empty to hide the form)")] }] },
  { id: "events", label: "Events", file: "events", preview: "../events.html", defs: [
    list("events", "Events", [
      str("slug", "URL slug (letters, numbers, dashes)"), str("name", "Name"), str("semester", "Semester (e.g. 24-25 Odd Sem)"),
      { t: "bool", key: "flagship", label: "Flagship event" }, txt("description", "Description"),
      { t: "images", key: "photos", label: "Photos" }],
      i => i.name, () => ({ slug: "new-event", name: "New event", semester: "25-26 Odd Sem", flagship: false, description: "", photos: [] }),
      i => i.semester)] },
  { id: "team", label: "Team", file: "team", preview: "../team.html", defs: [
    str("current_year", "Current team year"),
    list("current", "Current team", [str("name", "Name"), str("role", "Role")], i => i.name, null, i => i.role),
    list("earlier", "Earlier teams", [str("name", "Name"), str("role", "Role"), str("year", "Year")], i => i.name, null, i => `${i.role}, ${i.year}`)] },
  { id: "achievements", label: "Achievements", file: "achievements", preview: "../achievements.html", defs: [
    list("stats", "Figures", [str("value", "Figure"), str("label", "Label")], i => `${i.value} ${i.label}`),
    list("apps", "Apps built by members", [str("name", "Name"), txt("text", "Description")], i => i.name)] }
];

const data = {};
let cur = TABS[0], timer;

async function getFile(n) {
  if (data[n]) return data[n];
  try { const d = localStorage.getItem(KEY(n)); if (d) return data[n] = JSON.parse(d); } catch {}
  const r = await fetch(`../content/${n}.json`);
  return data[n] = await r.json();
}
const hasDraft = n => { try { return !!localStorage.getItem(KEY(n)); } catch { return false; } };

function save() {
  try { localStorage.setItem(KEY(cur.file), JSON.stringify(data[cur.file])); } catch { setStatus("Could not save: browser storage is full or blocked. Download the JSON instead.", true); return; }
  setStatus("Draft saved in this browser. Preview updated.", true);
  clearTimeout(timer);
  timer = setTimeout(() => { try { $("#frame").contentWindow.location.reload(); } catch { $("#frame").src = cur.preview; } }, 350);
}
function setStatus(msg, dirty) { const s = $("#status"); s.textContent = msg; s.classList.toggle("dirty", !!dirty); }

function field(def, obj, onChange) {
  if (def.t === "string" || def.t === "text") {
    const w = document.createElement("label"); w.className = "field";
    w.innerHTML = `<span></span>`; $("span", w).textContent = def.label;
    const i = document.createElement(def.t === "text" ? "textarea" : "input");
    i.value = obj[def.key] ?? "";
    i.oninput = () => { obj[def.key] = i.value; onChange(); };
    w.append(i); return w;
  }
  if (def.t === "bool") {
    const w = document.createElement("label"); w.className = "check";
    const i = document.createElement("input"); i.type = "checkbox"; i.checked = !!obj[def.key];
    i.onchange = () => { obj[def.key] = i.checked; onChange(); };
    w.append(i, document.createTextNode(def.label)); return w;
  }
  if (def.t === "object") {
    const fs = document.createElement("fieldset"); const lg = document.createElement("legend"); lg.textContent = def.label;
    obj[def.key] ||= {};
    fs.append(lg, ...def.fields.map(f => field(f, obj[def.key], onChange))); return fs;
  }
  if (def.t === "images") return images(def, obj, onChange);
  return listField(def, obj, onChange);
}

function listField(def, obj, onChange) {
  const wrap = document.createElement("div"); wrap.className = "field";
  const lab = document.createElement("span"); lab.textContent = def.label;
  const box = document.createElement("div"); box.className = "list";
  const add = document.createElement("button"); add.type = "button"; add.className = "btn add"; add.textContent = "Add " + def.label.toLowerCase().replace(/s$/, "");
  obj[def.key] ||= [];
  const arr = obj[def.key];
  const draw = () => {
    const open = [...box.querySelectorAll("details")].map(d => d.open);
    box.innerHTML = "";
    arr.forEach((item, n) => {
      const d = document.createElement("details"); d.className = "item"; d.open = open[n] ?? false;
      const sm = document.createElement("summary");
      const sub = def.sub ? def.sub(item) : "";
      sm.innerHTML = `<span></span><small></small>`; $("span", sm).textContent = def.summary(item) || "(empty)"; $("small", sm).textContent = sub || "";
      const body = document.createElement("div"); body.className = "item-body";
      body.append(...def.fields.map(f => field(f, item, () => {
        $("span", sm).textContent = def.summary(item) || "(empty)"; $("small", sm).textContent = def.sub ? def.sub(item) : ""; onChange();
      })));
      const tools = document.createElement("div"); tools.className = "item-tools";
      const mk = (t, cls, fn) => { const b = document.createElement("button"); b.type = "button"; b.textContent = t; if (cls) b.className = cls; b.onclick = fn; tools.append(b); };
      mk("Move up", "", () => { if (n > 0) { [arr[n - 1], arr[n]] = [arr[n], arr[n - 1]]; draw(); onChange(); } });
      mk("Move down", "", () => { if (n < arr.length - 1) { [arr[n + 1], arr[n]] = [arr[n], arr[n + 1]]; draw(); onChange(); } });
      mk("Delete", "del", () => { if (confirm("Delete this item?")) { arr.splice(n, 1); draw(); onChange(); } });
      body.append(tools); d.append(sm, body); box.append(d);
    });
  };
  add.onclick = () => {
    arr.unshift(def.blank ? def.blank() : Object.fromEntries(def.fields.map(f => [f.key, f.t === "bool" ? false : f.t === "images" ? [] : ""])));
    draw(); box.querySelector("details").open = true; onChange();
  };
  def.summary ||= i => i.name || i.title;
  wrap.append(lab, add, box); draw(); return wrap;
}

function images(def, obj, onChange) {
  const w = document.createElement("div"); w.className = "field";
  w.innerHTML = `<span></span><div class="thumbs"></div><input type="file" accept="image/*" multiple><p class="hint">Photos are shrunk to 1400px and kept in this browser for testing. For the live site use the GitHub editor so files are committed to the photos folder.</p>`;
  $("span", w).textContent = def.label;
  const th = $(".thumbs", w), inp = $("input", w);
  obj[def.key] ||= [];
  const draw = () => {
    th.innerHTML = "";
    obj[def.key].forEach((src, n) => {
      const d = document.createElement("div"); d.className = "thumb";
      const im = new Image(); im.src = src; im.alt = "";
      const b = document.createElement("button"); b.type = "button"; b.textContent = "Remove";
      b.onclick = () => { obj[def.key].splice(n, 1); draw(); onChange(); };
      d.append(im, b); th.append(d);
    });
  };
  inp.onchange = async () => {
    for (const f of inp.files) obj[def.key].push(await shrink(f));
    inp.value = ""; draw(); onChange();
  };
  draw(); return w;
}
function shrink(file) {
  return new Promise(res => {
    const r = new FileReader();
    r.onload = () => {
      const im = new Image();
      im.onload = () => {
        const k = Math.min(1, 1400 / Math.max(im.width, im.height));
        const c = document.createElement("canvas"); c.width = im.width * k; c.height = im.height * k;
        c.getContext("2d").drawImage(im, 0, 0, c.width, c.height);
        res(c.toDataURL("image/jpeg", .72));
      };
      im.src = r.result;
    };
    r.readAsDataURL(file);
  });
}

async function open(tab) {
  cur = tab;
  document.querySelectorAll("#tabs button").forEach(b => b.setAttribute("aria-current", b.dataset.id === tab.id));
  $("#title").textContent = tab.label;
  const obj = await getFile(tab.file);
  const form = $("#form"); form.innerHTML = "";
  form.append(...tab.defs.map(d => field(d, obj, save)));
  setStatus(hasDraft(tab.file) ? "You have a saved draft in this browser." : "Showing the published content. Edits save as a draft here.", hasDraft(tab.file));
  $("#frame").src = tab.preview;
}

function start() {
  $("#login").hidden = true; $("#app").hidden = false;
  $("#tabs").innerHTML = TABS.map(t => `<button type="button" data-id="${t.id}">${t.label}</button>`).join("");
  $("#tabs").onclick = e => { const b = e.target.closest("button"); if (b) open(TABS.find(t => t.id === b.dataset.id)); };
  $("#dl").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data[cur.file], null, 2) + "\n"], { type: "application/json" }));
    a.download = cur.file + ".json"; a.click(); URL.revokeObjectURL(a.href);
    setStatus(`Downloaded ${cur.file}.json. Replace content/${cur.file}.json with it and commit to publish.`, false);
  };
  $("#reset").onclick = async () => {
    if (!confirm("Discard your saved draft for this file and go back to the published content?")) return;
    try { localStorage.removeItem(KEY(cur.file)); } catch {}
    delete data[cur.file]; await open(cur);
  };
  $("#dev").onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    document.querySelectorAll("#dev button").forEach(x => x.setAttribute("aria-pressed", x === b));
    $("#frame").style.width = b.dataset.w;
  };
  $("#logout").onclick = () => { try { sessionStorage.removeItem("mad_admin"); } catch {} location.reload(); };
  open(TABS[0]);
}

let authed = false;
try { authed = sessionStorage.getItem("mad_admin") === "1"; } catch {}
if (authed) start();
else {
  $("#login").hidden = false;
  $("#login-form").onsubmit = e => {
    e.preventDefault();
    if ($("#u").value === USER && $("#p").value === PASS) {
      try { sessionStorage.setItem("mad_admin", "1"); } catch {}
      start();
    } else $("#err").hidden = false;
  };
}
