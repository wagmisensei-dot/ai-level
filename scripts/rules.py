"""
Rule-based editor: the free, no-API version of the Claude step in scan.py.

It works like a stock screener:
  1. FILTER   keep items that mention AI AND look like a launch; drop drama, money and opinion.
  2. SCORE    rank what's left by how launch-like it is, merge near-duplicate stories.
  3. CLASSIFY keyword maps pick the skill tree (domain) and the card category.
  4. RATE     Reach / Leap / Replace from simple signal words (1-5, conservative).
  5. WRITE    hype copy from templates; the pick is stable per story, so reruns don't reshuffle.

It returns the same shape as the Claude editor, so scan.py validates and saves both the same way.
The copy is more generic than Claude's, so expect repeated "THIS MEANS..." lines.
"""
from __future__ import annotations

import hashlib
import re

MAX_DROPS = 6          # fewer than Claude's 12: rules are less sure what matters
MAX_PRODUCT_HUNT = 2   # Product Hunt is a firehose of small apps; keep it to the best two
MIN_SCORE = 4


def _rx(words: list[str]) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(words) + r")", re.IGNORECASE)


AI_WORDS = _rx([r"ai\b", r"a\.i\.", "artificial intelligence", "gpt", "llm", "chatgpt", "openai", "claude",
                "anthropic", "gemini", "deepmind", "copilot", "llama", "mistral", "grok", "machine learning",
                "neural", "generative", "chatbot", "agent", "agentic", "diffusion", "sora", "veo", "midjourney",
                "suno", "robot", "humanoid", "self-driving", "robotaxi", "model", "transformer", "hugging ?face"])

LAUNCH_WORDS = _rx(["launch", "introduc", "unveil", "releas", "rolls? out", "rolling out", "now available",
                    "available (?:now|today)", "now lets", "lets you", "can now", "now can", "debut", "ships",
                    "new feature", "adds?\\b", "brings", "open[- ]sourc", "show hn", "beta", "preview",
                    "announc", "meet ", "now supports", "arrives", "expands"])

# Titles that are questions, explainers or profiles, not launches
TITLE_BLOCK = re.compile(r"^(?:how|why|what|when|where|who|is|are|can|should|does|do|will|inside|the case|"
                         r"the wizard|meet the|opinion|exclusive)\b|\?", re.IGNORECASE)
# Product Hunt taglines often skip the word "AI" but describe an AI ability
ABILITY_WORDS = _rx(["one sentence", "one prompt", "a prompt", "generat", "automatic", "instantly", "in seconds",
                     "from text", "from a photo", "turns? (?:any|your)", "writes", "edits your", "summariz"])

BLOCK_WORDS = _rx(["invest", "partnership", "startup forum", "rais(?:e|es|ed|ing)\\b", "funding", "valuation", "investor", "lawsuit", "sue[sd]?\\b", "suing",
                   "court", "judge", "investigat", "spy", "ceo\\b", "memo", "layoff", "fired", "resign", "hiring",
                   "acqui", "ipo\\b", "stock", "shares", "earnings", "revenue", "bubble", "opinion", "why ",
                   "how i ", "i'm ", "i am ", "my ", "ethic", "regulat", "ban\\b", "bans\\b", "policy", "senate",
                   "congress", "lawmaker", "election", "interview", "podcast", "pulling", "goodbye", "doom",
                   "dies?\\b", "death", "crash", "outage", "breach", "hack", "scam", "fraud", "deepfake",
                   "copyright", "rights holders", "union", "strike", "protest", "warns?", "fear", "risk"])

BIG_BRANDS = {
    "ChatGPT": "https://chatgpt.com", "OpenAI": "https://openai.com", "Claude": "https://claude.ai",
    "Gemini": "https://gemini.google.com", "Google": "https://gemini.google.com", "Copilot": "https://copilot.microsoft.com",
    "Microsoft": "https://copilot.microsoft.com", "Meta AI": "https://www.meta.ai", "Meta": "https://www.meta.ai", "Siri": "https://www.apple.com/siri/",
    "Alexa": "https://www.amazon.com/alexa", "Grok": "https://grok.com", "Perplexity": "https://www.perplexity.ai",
    "Midjourney": "https://www.midjourney.com", "Suno": "https://suno.com", "Sora": "https://sora.com",
    "NVIDIA": "https://www.nvidia.com", "Hugging Face": "https://huggingface.co", "GitHub": "https://github.com",
    "Notion": "https://www.notion.com", "Canva": "https://www.canva.com", "Adobe": "https://www.adobe.com",
    "YouTube": "https://www.youtube.com", "WhatsApp": "https://www.whatsapp.com", "Instagram": "https://www.instagram.com",
}
BIG_SOURCES = {"OpenAI News", "Google AI Blog", "Google DeepMind", "Microsoft AI News", "NVIDIA Blog"}

# Order matters: the first domain with the most keyword hits wins; KNOWLEDGE is the fallback.
DOMAIN_WORDS = {
    "PHYSICAL": ["robot", "humanoid", "self-driving", "robotaxi", "waymo", "drone", "autonomous vehicle",
                 "warehouse", "manipulat", "gripper", "embodied"],
    "CREATIVE": ["video", "image", "photo", "picture", "music", "song", "art\\b", "design", "animat", "3d",
                 "film", "movie", "sora", "veo", "midjourney", "suno", "draw", "illustrat", "editing"],
    "CODING":   ["code", "coding", "coder", "developer", "github", "programm", "\\bide\\b", "\\bapi\\b",
                 "\\bsdk\\b", "terminal", "pull request", "\\bpr\\b", "repo", "debug", "software engineer"],
    "AUTONOMY": ["agent", "agentic", "autonom", "computer use", "browser", "automat", "workflow",
                 "on your behalf", "operator", "tasks? for you"],
    "BUSINESS": ["spreadsheet", "excel", "sheets", "docs", "slides", "presentation", "email", "inbox", "meeting",
                 "crm", "sales", "office", "notion", "calendar", "invoice", "productivity", "customer support"],
    "LANGUAGE": ["voice", "speech", "translat", "language", "writing", "write", "transcri", "podcast audio",
                 "talk", "conversation", "dubbing", "accent"],
    "KNOWLEDGE": ["research", "reason", "math", "science", "search", "answer", "learn", "study", "tutor",
                  "medical", "health", "doctor", "benchmark"],
}
DOMAIN_RX = {d: _rx(w) for d, w in DOMAIN_WORDS.items()}

CATEGORY_WORDS = [
    ("VIDEO", _rx(["video", "film", "movie", "sora", "veo", "animat"])),
    ("AUDIO", _rx(["music", "song", "audio", "suno", "sound"])),
    ("IMAGE", _rx(["image", "photo", "picture", "art\\b", "design", "draw", "illustrat", "midjourney"])),
    ("VOICE", _rx(["voice", "speech", "translat", "talk", "dubbing"])),
    ("ROBOTICS", _rx(["robot", "humanoid", "self-driving", "robotaxi", "drone"])),
]
DOMAIN_CATEGORY = {"CODING": "CODING", "AUTONOMY": "AGENTS", "BUSINESS": "PRODUCTIVITY",
                   "KNOWLEDGE": "RESEARCH", "LANGUAGE": "CHAT", "CREATIVE": "IMAGE", "PHYSICAL": "ROBOTICS"}

REACH_UP = _rx(["free", "everyone", "all users", "available (?:now|today)", "now available", "worldwide",
                "globally", "rolling out to", "rolls out to", "for all"])
REACH_DOWN = _rx(["waitlist", "preview", "research", "beta", "limited", "select users", "enterprise",
                  "early access", "pilot", "paper"])
LEAP_UP = _rx(["new model", "first", "can now", "now lets", "now can", "introduc", "unveil", "brand[- ]new"])
LEAP_BIG = _rx(["breakthrough", "world'?s first", "state[- ]of[- ]the[- ]art", "real[- ]time", "autonomous",
                "end[- ]to[- ]end", "fully"])
LEAP_DOWN = _rx(["update", "improv", "faster", "tweak", "minor", "small", "fix"])
REPLACE_UP = _rx(["automat", "agent", "replace", "without", "no need", "hands[- ]free", "end[- ]to[- ]end",
                  "for you", "on your behalf", "in seconds", "instantly", "one click", "one prompt"])

# Copy pools per skill tree. The pick is stable per story (hash of the link).
MEANS = {
    "CREATIVE": ["YOUR PHONE JUST BECAME A CREATIVE STUDIO", "ONE PROMPT IS NOW A WHOLE PRODUCTION CREW",
                 "YOU DON'T NEED A PRO EDITOR FOR THIS ANYMORE", "YOUR WILDEST IDEA IS NOW ONE SENTENCE AWAY"],
    "CODING":   ["YOUR APP IDEA JUST GOT CLOSER TO REAL", "LESS TIME DEBUGGING, MORE TIME BUILDING",
                 "THE BORING PART OF CODING JUST GOT SHORTER", "YOU CAN SHIP FASTER THAN EVER"],
    "AUTONOMY": ["THE BORING HALF OF YOUR TO-DO LIST JUST GOT A ROBOT", "AI CAN NOW DO MORE OF THE CLICKING FOR YOU",
                 "YOUR BUSYWORK JUST GOT AUTOMATED", "YOU GET TO BE THE BOSS, AI DOES THE TASKS"],
    "BUSINESS": ["YOUR OFFICE WORK JUST GOT A SPEED BOOST", "LESS TIME IN SPREADSHEETS AND SLIDES",
                 "THAT WEEKLY REPORT NEARLY WRITES ITSELF NOW", "MEETINGS AND EMAILS JUST GOT LIGHTER"],
    "LANGUAGE": ["YOU CAN TALK TO MORE PEOPLE, MORE EASILY", "WORDS ARE NOW EASIER THAN EVER",
                 "LANGUAGE BARRIERS JUST GOT SMALLER", "YOUR VOICE JUST GOT SUPERPOWERS"],
    "KNOWLEDGE": ["YOUR AI JUST GOT SMARTER", "ANSWERS GET FASTER AND BETTER",
                  "THAT RABBIT HOLE IS NOW A SHORTCUT", "YOUR PERSONAL GENIUS JUST LEVELED UP"],
    "PHYSICAL": ["ROBOTS JUST GOT ONE STEP CLOSER TO YOUR HOUSE", "AI IS LEARNING TO USE ITS HANDS",
                 "THE PHYSICAL WORLD JUST GOT A LITTLE MORE AUTOMATED", "MANUAL LABOR JUST TOOK A HIT"],
}
BOSSES = {
    "CREATIVE": ["Expensive editing software", "Hours of manual editing", "Stock content subscriptions"],
    "CODING": ["Endless debugging sessions", "Boilerplate code", "Waiting on code reviews"],
    "AUTONOMY": ["Copy-paste busywork", "Repetitive clicking", "Tab-switching marathons"],
    "BUSINESS": ["Spreadsheet panic", "Slide-deck all-nighters", "Inbox overload"],
    "LANGUAGE": ["Language barriers", "Blank-page syndrome", "Awkward phrasebooks"],
    "KNOWLEDGE": ["Forty open browser tabs", "Endless googling", "Not knowing the answer"],
    "PHYSICAL": ["Boring manual chores", "Repetitive physical tasks", "Driving yourself everywhere"],
}
OPENERS = ["Ladies and gentlemen!", "WARNING! WARNING!", "Hold onto your controllers!", "Attention, players!",
           "Breaking news from the arena!", "Stop what you're doing!"]
CLOSERS = ["NEW POWER UNLOCKED!", "LEVEL UP!", "GAME ON!", "THE CROWD GOES WILD!", "FLAWLESS VICTORY!"]


def _pick(options: list[str], key: str, salt: str = "") -> str:
    h = int(hashlib.sha1((salt + key).encode()).hexdigest(), 16)
    return options[h % len(options)]


def _hits(rx: re.Pattern, text: str) -> int:
    return len(rx.findall(text))


def _clamp(n: int) -> int:
    return max(1, min(5, n))


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3}


def _first_sentence(s: str, limit: int = 220, min_len: int = 35) -> str:
    """First sentence long enough to say something (skips greetings like 'Hi HN!')."""
    s = s.strip()
    parts = re.split(r"(?<=[.!?])\s+", s)
    s = next((p for p in parts if len(p) >= min_len), parts[0] if parts else s)
    return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "…"


def _clean_title(t: str) -> str:
    t = re.sub(r"^(?:launch|show|ask) hn:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\((?:yc )?[sfwx]\d{2}\)", "", t, flags=re.IGNORECASE)    # "(YC S23)"
    return t.strip()


NOT_NAMES = {"The", "A", "An", "New", "AI", "US", "UK", "EU", "How", "Why", "What", "This", "Now", "Your", "You",
              "Here", "Its", "It", "With", "And", "For", "Today", "Introducing", "Meet", "Show", "HN", "Says"}


def _tool(c: dict, text: str) -> tuple[str, str]:
    title = _clean_title(c["title"])
    if c["source"] == "Product Hunt":
        return title.split(" - ")[0].split(":")[0].strip()[:40], c["link"]
    brand_in = lambda s: next((n for n in BIG_BRANDS if re.search(r"\b" + re.escape(n) + r"\b", s)), None)
    if (name := brand_in(title)):                       # a big brand named in the headline
        return name, BIG_BRANDS[name]
    # Otherwise the first proper noun in the headline, linking to the article
    for m in re.finditer(r"\b[A-Z][\w.\-]*[a-zA-Z0-9](?:\s[A-Z][\w\-]+)?", title):
        name = m.group(0)
        if name.split()[0] not in NOT_NAMES:
            return name[:40], c["link"]
    if (name := brand_in(text)):
        return name, BIG_BRANDS[name]
    return "the announcement", c["link"]


def _summary(c: dict) -> str:
    return re.sub(r"\s*Discussion\s*\|\s*Link\s*$", "", c.get("summary", "")).strip()


def score(c: dict) -> int:
    title, summary = c["title"], _summary(c)
    text = title + " " + summary
    ph = c["source"] == "Product Hunt"
    if TITLE_BLOCK.search(title) or _hits(BLOCK_WORDS, title):
        return -1
    if not (_hits(AI_WORDS, text) or (ph and _hits(ABILITY_WORDS, text))):
        return -1
    if ph:                                    # every Product Hunt post is a launch by definition
        return 3 + min(3, _hits(AI_WORDS, text) + _hits(ABILITY_WORDS, text))
    if not _hits(LAUNCH_WORDS, title):        # news must SAY it's a launch in the headline
        return -1
    launch = _hits(LAUNCH_WORDS, title) * 2 + min(2, _hits(LAUNCH_WORDS, summary))
    return launch + min(3, _hits(AI_WORDS, text)) + (1 if c["source"] in BIG_SOURCES else 0)


def edit(cands: list[dict]) -> list[dict]:
    """Same output shape as scan.ask_claude(): a list of power-up dicts with a 'candidate' index."""
    ranked = sorted(((score(c), i) for i, c in enumerate(cands)), reverse=True)
    picked: list[int] = []
    ph_count = 0
    for s, i in ranked:
        if s < MIN_SCORE or len(picked) >= MAX_DROPS:
            break
        if cands[i]["source"] == "Product Hunt":
            if ph_count >= MAX_PRODUCT_HUNT:
                continue
        w = _words(cands[i]["title"])
        if any(len(w & _words(cands[j]["title"])) / max(1, len(w | _words(cands[j]["title"]))) > 0.4 for j in picked):
            continue                                   # same story from another outlet
        picked.append(i)
        ph_count += cands[i]["source"] == "Product Hunt"

    out = []
    for i in picked:
        c = {**cands[i], "summary": _summary(cands[i])}
        text = c["title"] + " " + c["summary"]
        key = c["link"]

        domain = max(DOMAIN_RX, key=lambda d: _hits(DOMAIN_RX[d], text))
        if _hits(DOMAIN_RX[domain], text) == 0:
            domain = "KNOWLEDGE"
        category = next((cat for cat, rx in CATEGORY_WORDS if _hits(rx, text)), DOMAIN_CATEGORY[domain])

        big = c["source"] in BIG_SOURCES or any(re.search(r"\b" + re.escape(b) + r"\b", text, re.I) for b in BIG_BRANDS)
        reach = _clamp(2 + (_hits(REACH_UP, text) > 0) + big - (_hits(REACH_DOWN, text) > 0))
        leap = _clamp(2 + (_hits(LEAP_UP, text) > 0) + (_hits(LEAP_BIG, text) > 0) - (_hits(LEAP_DOWN, c["title"]) > 0))
        replace = _clamp(2 + (_hits(REPLACE_UP, text) > 0) + (domain in ("AUTONOMY", "PHYSICAL")))
        if c["source"] == "Product Hunt":      # small new apps: cap the hype
            reach, leap = min(reach, 3), min(leap, 3)

        tool, url = _tool(c, text)
        title = _clean_title(c["title"])
        if c["source"] == "Product Hunt" and c.get("summary"):
            title = f"{tool}: {_first_sentence(c['summary'], 90).rstrip('.')}"
        headline = " ".join(title.split()[:14]).upper()
        means = _pick(MEANS[domain], key)
        boss = _pick(BOSSES[domain], key, "boss")
        script = (f"{_pick(OPENERS, key, 'o')} {tool} just dropped a new power! {title.rstrip('.!')}! "
                  f"That means {means}! {boss}? DEFEATED! {_pick(CLOSERS, key, 'c')}")

        out.append({
            "candidate": i, "category": category, "domain": domain,
            "reach": reach, "leap": leap, "replace": replace,
            "tool": tool, "url": url, "headline": headline,
            # HN post bodies open with "I'm X from Y", so the headline describes it better
            "desc": title if c["source"].startswith("Hacker News") or len(c["summary"]) < 35
                    else _first_sentence(c["summary"]),
            "means": means, "boss": boss, "script": script,
        })
    return out
