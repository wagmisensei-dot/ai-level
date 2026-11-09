/*
 * AI LEVEL MODEL
 * ---------------------------------------------------------------
 * AI's "level" (0–100) measures how close AI is to doing ALL valuable work:
 * Level 100 = no need for private companies, software products, or human manual labor.
 *
 * 1. SKILL TREES: the world's work is split into 7 domains. Each has a weight
 *    (its rough share of human economic labor) and a score from 0 to 100.
 * 2. BASELINE: a domain's starting score is the sum of the milestone points it has
 *    already reached (each domain's milestones add up to 100).
 * 3. XP DROPS: each new feature gets an Impact score from 1 to 5:
 *       impact = 0.4·Reach + 0.4·Leap + 0.2·Replace   (each rated 1–5)
 *    It adds XP to its domain, with diminishing returns as the domain nears mastery:
 *       xp = 10 × (impact/5)² × (1 − score/100)
 * 4. LEVEL = ½·Breadth + ½·Weakest-link
 *       Breadth      = weighted arithmetic mean of the domain scores
 *       Weakest-link = weighted geometric mean (a weak domain drags it down hard)
 *    Both equal 100 only when EVERY domain is at 100, so Level 100 can't be faked
 *    by maxing out the digital domains alone.
 *
 * Plain script: in the browser it sets window.AILevel, and Node can require() it,
 * so the daily pipeline and the site share one model.
 */
(function (root) {
  const DOMAINS = [
    { id: "KNOWLEDGE", name: "Knowledge & Reasoning", icon: "🧠", weight: 0.14,
      milestones: [
        ["Passes professional exams (law, medicine)", 15, true],
        ["PhD-level science Q&A", 15, true],
        ["Olympiad-gold math", 15, true],
        ["Cited research reports in minutes", 15, true],
        ["Near-zero errors in high-stakes advice", 15, false],
        ["Makes original scientific discoveries on its own", 25, false] ] },
    { id: "CODING", name: "Coding & Software", icon: "💻", weight: 0.12,
      milestones: [
        ["Writes functions from a description", 10, true],
        ["Fixes most real-world GitHub issues", 20, true],
        ["Builds full apps end-to-end", 20, true],
        ["Works autonomously for hours in big codebases", 20, true],
        ["Runs production systems with no human review", 30, false] ] },
    { id: "CREATIVE", name: "Creative Media", icon: "🎨", weight: 0.10,
      milestones: [
        ["Photorealistic images", 15, true],
        ["Edit images by chatting", 10, true],
        ["Video clips with synced sound", 20, true],
        ["Full songs with vocals", 15, true],
        ["Consistent characters across long videos", 20, false],
        ["Feature-length film from a script", 20, false] ] },
    { id: "LANGUAGE", name: "Language & Voice", icon: "🗣️", weight: 0.10,
      milestones: [
        ["Human-level writing", 20, true],
        ["Real-time voice conversation", 20, true],
        ["Live speech translation", 20, true],
        ["Handles customer calls end-to-end at scale", 20, false],
        ["Expert-level negotiation and persuasion", 20, false] ] },
    { id: "AUTONOMY", name: "Agents & Autonomy", icon: "🤖", weight: 0.18,
      milestones: [
        ["Uses tools and APIs", 15, true],
        ["Operates a computer like a person", 15, true],
        ["Reliably finishes hour-long tasks", 20, true],
        ["Reliably finishes week-long projects", 25, false],
        ["Runs a small business autonomously", 25, false] ] },
    { id: "BUSINESS", name: "Business Operations", icon: "📊", weight: 0.12,
      milestones: [
        ["Drafts docs, slides and emails", 20, true],
        ["Spreadsheet analysis by chat", 20, true],
        ["Automates back-office workflows", 20, true],
        ["Replaces a team's whole software stack", 20, false],
        ["Makes accountable executive decisions", 20, false] ] },
    { id: "PHYSICAL", name: "Physical World & Touch", icon: "🦾", weight: 0.24,
      milestones: [
        ["Robots follow spoken instructions", 15, true],
        ["Driverless taxis in real cities", 20, true],
        ["General pick-and-place in any home", 15, false],
        ["Dexterous hands: cooking, folding, repair", 20, false],
        ["Affordable general-purpose humanoids at work", 30, false] ] }
  ].map(d => ({ ...d, milestones: d.milestones.map(([text, pts, done]) => ({ text, pts, done })) }));

  const TIERS = [
    { min: 0,  name: "CALCULATOR ERA", desc: "Answers when asked. Humans do all the work." },
    { min: 20, name: "INTERN",         desc: "Helpful drafts, but everything needs checking." },
    { min: 40, name: "COWORKER",       desc: "Does real digital work. The physical world is barely touched." },
    { min: 60, name: "DEPARTMENT",     desc: "Runs whole business functions. Most software products become optional." },
    { min: 80, name: "COMPANY",        desc: "Runs businesses end-to-end. Robots do most manual work." },
    { min: 95, name: "POST-LABOR",     desc: "Private companies and software products start to disappear. Manual labor is optional." },
    { min: 100, name: "AI TAKES OVER", desc: "Every skill tree maxed. AI can do almost anything, with words or with touch. No companies, products or manual labor needed." }
  ];

  const IMPACT_WEIGHTS = { reach: 0.4, leap: 0.4, replace: 0.2 };
  const RARITY_CUTS = [[4.2, "LEGENDARY"], [3.4, "EPIC"], [2.6, "RARE"], [0, "COMMON"]];
  const XP_SCALE = 10;

  const impact = p => IMPACT_WEIGHTS.reach * p.reach + IMPACT_WEIGHTS.leap * p.leap + IMPACT_WEIGHTS.replace * p.replace;
  const rarityOf = s => RARITY_CUTS.find(([cut]) => s >= cut)[1];
  const hypeOf = s => Math.round((s / 5) * 100);
  const xpGain = (s, current) => XP_SCALE * Math.pow(s / 5, 2) * (1 - current / 100);
  const baseScore = d => d.milestones.reduce((t, m) => t + (m.done ? m.pts : 0), 0);
  const tierOf = lvl => [...TIERS].reverse().find(t => lvl >= t.min);

  function levelOf(scores) {
    let breadth = 0, logSum = 0;
    for (const d of DOMAINS) {
      const s = Math.max(1, Math.min(100, scores[d.id]));   // floor of 1 keeps the log defined
      breadth += d.weight * s;
      logSum += d.weight * Math.log(s);
    }
    const weakest = Math.exp(logSum);
    return { breadth, weakest, level: 0.5 * breadth + 0.5 * weakest };
  }

  // Applies the drops in order, since each one changes the diminishing return for the next.
  // history = every earlier drop (oldest first). They build up the "before" level silently;
  // powerups = the latest day's drops, shown as cards and as today's gain.
  function compute(powerups, history = []) {
    const base = {}, now = {}, gained = {};
    DOMAINS.forEach(d => { now[d.id] = baseScore(d); gained[d.id] = 0; });
    for (const h of history) {
      if (!(h.domain in now)) continue;
      now[h.domain] = Math.min(100, now[h.domain] + xpGain(impact(h), now[h.domain]));
    }
    DOMAINS.forEach(d => { base[d.id] = now[d.id]; });
    const enriched = powerups.map(p => {
      const s = impact(p);
      const xp = xpGain(s, now[p.domain]);
      now[p.domain] = Math.min(100, now[p.domain] + xp);
      gained[p.domain] += xp;
      return { ...p, impact: s, rarity: rarityOf(s), hype: hypeOf(s), xp };
    });
    const before = levelOf(base), after = levelOf(now);
    return {
      domains: DOMAINS.map(d => ({ ...d, base: base[d.id], score: now[d.id], gained: gained[d.id] })),
      before, after, delta: after.level - before.level,
      tier: tierOf(after.level), powerups: enriched
    };
  }

  const api = { DOMAINS, TIERS, IMPACT_WEIGHTS, RARITY_CUTS, XP_SCALE, impact, rarityOf, hypeOf, xpGain, levelOf, tierOf, compute };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.AILevel = api;
})(typeof window !== "undefined" ? window : globalThis);
