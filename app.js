(() => {
  const data = window.POWERUP_DATA || { powerups: [] };
  const M = window.AILevel;
  const model = M.compute(data.powerups, data.history || []);   // rarity, hype and XP come from the model
  const items = [...model.powerups].sort((a, b) => b.impact - a.impact);
  const domainById = Object.fromEntries(model.domains.map(d => [d.id, d]));
  const RARITIES = ["ALL", "LEGENDARY", "EPIC", "RARE", "COMMON"];
  const categories = ["ALL", ...new Set(items.map(p => p.category))];
  const state = { cat: "ALL", rarity: "ALL" };
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const f1 = n => n.toFixed(1);
  const lvlNow = model.after.level, lvlBefore = model.before.level;
  const lvlInt = Math.floor(lvlNow);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Player XP (per-viewer, stored locally; safe if storage is blocked) ----------
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
  };
  let xp = store.get("pud_xp", 0);
  const XP_PER_LEVEL = 100;
  function renderXP() {
    $("xp").textContent = xp;
    $("lvl").textContent = Math.floor(xp / XP_PER_LEVEL) + 1;
    $("xpfill").style.width = (xp % XP_PER_LEVEL) + "%";
  }
  function gainXP(n) {
    const before = Math.floor(xp / XP_PER_LEVEL);
    xp += n; store.set("pud_xp", xp); renderXP();
    if (Math.floor(xp / XP_PER_LEVEL) > before) {
      toast(`⬆ LEVEL UP! YOU ARE NOW LEVEL ${Math.floor(xp / XP_PER_LEVEL) + 1}!`);
      confetti(80);
    }
  }

  // ---------- Toast + confetti ----------
  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
  }
  function confetti(n = 40) {
    if (reduced) return;
    const box = $("confetti");
    const colors = ["#ff2e88", "#22e6ff", "#ffe14d", "#4dff9a", "#c25bff", "#ffb12e"];
    for (let i = 0; i < n; i++) {
      const c = document.createElement("i");
      c.style.left = Math.random() * 100 + "vw";
      c.style.background = colors[i % colors.length];
      c.style.animationDuration = 1.6 + Math.random() * 1.8 + "s";
      c.style.animationDelay = Math.random() * .4 + "s";
      box.appendChild(c);
      setTimeout(() => c.remove(), 4000);
    }
  }

  // ---------- Announcer voice (browser speech synthesis) ----------
  const synth = window.speechSynthesis;
  let speakingBtn = null;
  function pickVoice() {
    const voices = synth.getVoices().filter(v => /^en/i.test(v.lang));
    for (const re of [/Daniel/, /Fred/, /Alex/, /Google UK English Male/, /Male/i]) {
      const v = voices.find(v => re.test(v.name)); if (v) return v;
    }
    return voices[0] || null;
  }
  function speak(text, btn, fallback) {
    if (!$("voiceToggle").checked || !synth) { toast(fallback); return; }
    if (speakingBtn === btn) { synth.cancel(); return; }
    synth.cancel();
    const label = btn.textContent;
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice(); if (v) u.voice = v;
    u.rate = 1.12; u.pitch = 0.8;
    u.onstart = () => { speakingBtn = btn; btn.classList.add("speaking"); btn.textContent = "■ STOP"; };
    u.onend = u.onerror = () => { btn.classList.remove("speaking"); btn.textContent = label; if (speakingBtn === btn) speakingBtn = null; };
    synth.speak(u);
  }
  const levelLine = () => `AI has now reached LEVEL ${lvlInt} after today's big XP drop! That's plus ${f1(model.delta)} levels! Only ${100 - lvlInt} levels until AI TAKES OVER!`;

  // ---------- AI level: header, banner, dropdown ----------
  function countUp(el, from, to, ms, fmt) {
    if (reduced) { el.textContent = fmt(to); return; }
    const t0 = performance.now();
    const step = t => {
      const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(from + (to - from) * e);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderLevel() {
    $("bannerDelta").textContent = `(+${f1(model.delta)})`;
    $("miniLvl").textContent = `AI LVL ${lvlInt}`;
    $("toGo").textContent = 100 - lvlInt;
    countUp($("bannerLvl"), lvlBefore, lvlNow, 1800, n => Math.floor(n));
    countUp($("youNum"), lvlBefore, lvlNow, 1800, n => "LVL " + f1(n));
    $("ticks").innerHTML = M.TIERS.filter(t => t.min > 0 && t.min < 100).map(t =>
      `<span class="tick ${t === model.tier ? "cur" : ""}" style="left:${t.min}%">${t.min}<br><span class="nm">${t.name}</span></span>`).join("");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      $("aiLvlFill").style.width = `calc(${lvlBefore}% - 6px)`;
      $("aiLvlGain").style.left = `calc(${lvlBefore}% - 3px)`;
      $("aiLvlGain").style.width = `${model.delta}%`;
      $("youMarker").style.left = `${lvlNow}%`;
    }));

    $("pLevel").textContent = f1(lvlNow);
    $("pTier").textContent = model.tier.name;
    $("pTierDesc").textContent = model.tier.desc;
    $("pDrop").innerHTML = `TODAY'S XP DROP<br>LVL ${f1(lvlBefore)} → ${f1(lvlNow)} <span>(+${f1(model.delta)})</span><br>${100 - lvlInt} LEVELS TO GO`;
    $("pCalc").innerHTML =
      `Breadth ${f1(model.after.breadth)} · Weakest-link ${f1(model.after.weakest)}<br>` +
      `½×${f1(model.after.breadth)} + ½×${f1(model.after.weakest)} = ${f1(lvlNow)}`;

    $("pDomains").innerHTML = model.domains
      .slice().sort((a, b) => b.weight - a.weight)
      .map(d => `
        <details class="dom">
          <summary>
            <span class="dom-name">${d.icon} ${esc(d.name)}<em>weight ${Math.round(d.weight * 100)}%</em></span>
            <span class="dom-score">${f1(d.score)}${d.gained > 0 ? `<small>+${f1(d.gained)} TODAY</small>` : ""}</span>
            <span class="dom-bar"><i style="width:${d.base}%"></i><s style="left:${d.base}%;width:${d.gained}%"></s></span>
          </summary>
          <ul>${d.milestones.map(m => `<li class="${m.done ? "done" : ""}"><span>${esc(m.text)}</span><b>${m.pts}PT</b></li>`).join("")}</ul>
        </details>`).join("");

    $("pLadder").innerHTML = M.TIERS.map((t, i) => {
      const max = (M.TIERS[i + 1]?.min ?? 101) - 1;
      const rng = max === t.min ? `${t.min} 👑` : `${t.min}–${max}`;
      return `<li class="${t === model.tier ? "cur" : ""}"><span class="rng">${rng}</span><span><b>${t.name}</b>${esc(t.desc)}</span></li>`;
    }).join("");
  }

  function togglePanel(open) {
    const panel = $("lvlPanel"), btn = $("aiLvlBtn");
    open = open ?? panel.hidden;
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open);
    if (open) panel.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  }
  $("aiLvlBtn").onclick = () => togglePanel();
  $("miniLvl").onclick = () => window.scrollTo({ top: 0 });
  $("closeLvl").onclick = () => togglePanel(false);
  document.addEventListener("keydown", e => { if (e.key === "Escape") togglePanel(false); });
  $("announceLvl").onclick = e => speak(levelLine(), e.currentTarget, `⚡ AI HAS REACHED LEVEL ${lvlInt}!`);

  // ---------- Feed ----------
  function renderTicker() {
    const line = `⚡ AI HAS REACHED LEVEL ${lvlInt} (+${f1(model.delta)}) ` + items.map(p => `★ ${esc(p.headline)} `).join("");
    $("ticker").innerHTML = `<span>${line}</span><span>${line}</span>`;
  }

  function renderStats() {
    const leg = items.filter(p => p.rarity === "LEGENDARY").length;
    const totalXP = items.reduce((s, p) => s + p.xp, 0);
    const stat = (n, l) => `<div class="stat"><b>${n}</b><span>${l}</span></div>`;
    $("stats").innerHTML =
      stat(items.length, "Power-ups today") +
      stat(leg, "Legendary drops") +
      stat("+" + f1(totalXP), "Domain XP earned") +
      stat("+" + f1(model.delta), "AI levels gained");
    $("demoBadge").hidden = !data.demo;
    $("updated").textContent = data.updated || "today";
  }

  function renderChips() {
    const mk = (el, list, key) => {
      el.innerHTML = list.map(v => `<button class="chip" data-v="${esc(v)}" aria-pressed="${state[key] === v}">${esc(v)}</button>`).join("");
      el.onclick = e => {
        const b = e.target.closest(".chip"); if (!b) return;
        state[key] = b.dataset.v;
        el.querySelectorAll(".chip").forEach(c => c.setAttribute("aria-pressed", c.dataset.v === state[key]));
        renderGrid();
      };
    };
    mk($("categoryChips"), categories, "cat");
    mk($("rarityChips"), RARITIES.filter(r => r === "ALL" || items.some(p => p.rarity === r)), "rarity");
  }

  function cardHTML(p, i) {
    const d = domainById[p.domain];
    return `
      <article class="card ${esc(p.rarity)}" style="animation-delay:${i * 60}ms" data-id="${esc(p.id)}">
        <div class="card-top">
          <span class="rarity">${esc(p.rarity)}</span>
          <span class="cat">${esc(p.category)}</span>
        </div>
        <p class="unlocked">▶ NEW ABILITY UNLOCKED</p>
        <h3>${esc(p.headline)}</h3>
        <p class="desc">${esc(p.desc)}</p>
        <div class="means"><small>⚡ THIS MEANS…</small><p>${esc(p.means)}!</p></div>
        <div class="boss"><span class="ko">K.O.</span> <s>${esc(p.boss)}</s></div>
        <div class="hype"><span>HYPE</span><div class="hype-bar"><i data-w="${p.hype}"></i></div><b>${p.hype}</b></div>
        <div class="xpline" title="Impact = 0.4×Reach + 0.4×Leap + 0.2×Replace">
          <span>REACH ${p.reach} · LEAP ${p.leap} · REPLACE ${p.replace}</span>
          <span><b>+${f1(p.xp)} XP</b> → ${esc(d.name.split(" ")[0].toUpperCase())}</span>
        </div>
        <p class="tool-line">Try it in <a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">${esc(p.tool)} ↗</a>${p.sourceUrl
          ? ` · <a class="src-link" href="${esc(p.sourceUrl)}" target="_blank" rel="noopener noreferrer">source: ${esc(p.source)}</a>` : ""}</p>
        <div class="actions">
          <button class="btn hype-btn" data-act="hype">▶ HYPE IT</button>
          <a class="btn try-btn" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer" aria-label="Try it in ${esc(p.tool)}">TRY IT ↗</a>
          <button class="btn share-btn" data-act="share" aria-label="Copy share text">⧉</button>
        </div>
      </article>`;
  }

  function renderGrid() {
    const list = items.filter(p =>
      (state.cat === "ALL" || p.category === state.cat) &&
      (state.rarity === "ALL" || p.rarity === state.rarity));
    $("grid").innerHTML = list.length
      ? list.map(cardHTML).join("")
      : `<p class="empty">NO POWER-UPS HERE YET<br>TRY ANOTHER FILTER</p>`;
    requestAnimationFrame(() => requestAnimationFrame(() =>
      document.querySelectorAll(".hype-bar i").forEach(b => b.style.width = b.dataset.w + "%")));
  }

  function renderSide() {
    $("leader").innerHTML = items.slice(0, 5)
      .map(p => `<li><span>${esc(p.headline.split(" ").slice(0, 5).join(" "))}…</span><b>${p.hype}</b></li>`).join("");
    $("bosses").innerHTML = items.map(p => `<li><s>${esc(p.boss)}</s></li>`).join("");
  }

  $("grid").addEventListener("click", async e => {
    const btn = e.target.closest("[data-act]"); if (!btn) return;
    const p = items.find(x => x.id === btn.closest(".card").dataset.id);
    const d = domainById[p.domain];
    if (btn.dataset.act === "hype") {
      speak(`${p.script} Plus ${f1(p.xp)} XP to ${d.name}!`, btn, `📣 ${p.means}!`);
      gainXP(p.rarity === "LEGENDARY" ? 25 : p.rarity === "EPIC" ? 15 : 10);
      if (p.rarity === "LEGENDARY") confetti(50);
    } else {
      const text = `🎮 NEW AI POWER UNLOCKED: ${p.headline}! THIS MEANS ${p.means}! AI is now LEVEL ${lvlInt}. Try it: ${p.url} #AILevel`;
      try { await navigator.clipboard.writeText(text); toast("📋 COPIED! GO SPREAD THE HYPE!"); }
      catch { toast(text); }
    }
  });

  $("toTop").addEventListener("click", e => { e.preventDefault(); window.scrollTo({ top: 0 }); });

  renderXP(); renderLevel(); renderTicker(); renderStats(); renderChips(); renderGrid(); renderSide();
})();
