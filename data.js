// DEMO DATA. The daily pipeline will overwrite this file with real, sourced entries.
// Loaded as a plain script (not fetched JSON) so the site also works when opened straight from disk.
//
// Each power-up is rated 1–5 on three criteria (see model.js):
//   reach   - how many people can use it today (1 = niche lab demo, 5 = free for everyone)
//   leap    - how big a jump over what was possible before (1 = minor tweak, 5 = brand-new ability)
//   replace - how much paid software or human labor it makes optional (1 = none, 5 = whole job or product)
// Rarity, hype and the XP it adds to its domain are calculated from these ratings, not hand-picked.
// domain is one of: KNOWLEDGE, CODING, CREATIVE, LANGUAGE, AUTONOMY, BUSINESS, PHYSICAL
window.POWERUP_DATA = {
  updated: "2026-11-09",
  demo: true,
  powerups: [
    {
      id: "text-to-video-sound",
      category: "VIDEO", domain: "CREATIVE",
      reach: 4, leap: 5, replace: 5,
      tool: "Google Veo", url: "https://deepmind.google/models/veo/",
      headline: "YOU CAN NOW MAKE A MOVIE SCENE FROM ONE SENTENCE",
      desc: "Type a prompt, get a cinematic clip with camera moves, dialogue AND sound effects baked in.",
      means: "YOUR PHONE IS NOW A FILM STUDIO",
      boss: "Stock footage subscriptions",
      script: "Ladies and gentlemen, hold onto your controllers! You type ONE sentence, and the AI makes a full movie scene. With SOUND. Your phone is now a FILM STUDIO. Stock footage? DEFEATED!"
    },
    {
      id: "computer-use-agents",
      category: "AGENTS", domain: "AUTONOMY",
      reach: 4, leap: 5, replace: 5,
      tool: "Claude", url: "https://claude.ai",
      headline: "AI CAN NOW CLICK AROUND YOUR COMPUTER FOR YOU",
      desc: "Agents that open apps, fill forms, and finish multi-step tasks while you grab a snack.",
      means: "THE BORING HALF OF YOUR JOB JUST GOT A ROBOT",
      boss: "Copy-paste busywork",
      script: "WARNING! WARNING! The AI has learned to USE YOUR COMPUTER! It clicks! It types! It fills out forms! The boring half of your job just got a ROBOT! Copy paste busywork has been ELIMINATED!"
    },
    {
      id: "coding-agents-full-apps",
      category: "CODING", domain: "CODING",
      reach: 4, leap: 5, replace: 4,
      tool: "Claude Code", url: "https://claude.com/claude-code",
      headline: "DESCRIBE AN APP, WATCH IT GET BUILT",
      desc: "Coding agents plan, write, test and fix whole projects from a plain-English description.",
      means: "YOUR APP IDEA IS NO LONGER JUST AN IDEA",
      boss: "\"I'd build it if I could code\"",
      script: "Listen up, future billionaire! You DESCRIBE the app, and the AI BUILDS it! It writes the code! It tests the code! It FIXES the code! Your app idea is no longer just an idea. EXCUSES: DESTROYED!"
    },
    {
      id: "spreadsheet-agent",
      category: "PRODUCTIVITY", domain: "BUSINESS",
      reach: 5, leap: 3, replace: 4,
      tool: "Copilot in Excel", url: "https://www.microsoft.com/en-us/microsoft-365/excel",
      headline: "TALK TO YOUR SPREADSHEET LIKE IT'S A PERSON",
      desc: "Ask questions in plain English and get formulas, pivot tables and charts built for you.",
      means: "YOU WILL NEVER HAVE TO WRITE A VLOOKUP AGAIN",
      boss: "Excel formula panic",
      script: "Attention, spreadsheet warriors! You can now just TALK to your spreadsheet! Formulas? Pivot tables? Charts? DONE! You will NEVER have to write a V-LOOKUP AGAIN! Formula panic: K.O.!"
    },
    {
      id: "live-voice-translation",
      category: "VOICE", domain: "LANGUAGE",
      reach: 5, leap: 3, replace: 4,
      tool: "Google Translate", url: "https://translate.google.com",
      headline: "SPEAK ANY LANGUAGE. LIVE.",
      desc: "Real-time voice translation that keeps the conversation flowing with barely any delay.",
      means: "YOU CAN NOW TRAVEL ANYWHERE WITHOUT A PHRASEBOOK",
      boss: "Awkward pointing at menus",
      script: "Passport ready? Because the AI now translates you LIVE! In real time! You can talk to ANYONE on the PLANET! Awkward pointing at menus? That boss is DOWN!"
    },
    {
      id: "music-generation",
      category: "AUDIO", domain: "CREATIVE",
      reach: 3, leap: 4, replace: 4,
      tool: "Suno", url: "https://suno.com",
      headline: "YOU CAN NOW MAKE A FULL SONG WITH VOCALS",
      desc: "Pick a genre and a vibe, and get a complete track with lyrics, vocals and instruments.",
      means: "EVERY VIDEO YOU MAKE GETS ITS OWN THEME SONG",
      boss: "Hunting for royalty-free music",
      script: "Drop the BEAT! The AI now makes FULL SONGS! With VOCALS! Every video you make gets its own THEME SONG! Hunting for royalty free music? GAME OVER!"
    },
    {
      id: "deep-research",
      category: "RESEARCH", domain: "KNOWLEDGE",
      reach: 3, leap: 3, replace: 4,
      tool: "ChatGPT", url: "https://chatgpt.com",
      headline: "AI READS 100 WEBSITES SO YOU DON'T HAVE TO",
      desc: "Research modes that search, read, compare and hand you a cited report in minutes.",
      means: "THAT 40-TAB RABBIT HOLE IS NOW A 5-MINUTE REPORT",
      boss: "Forty open browser tabs",
      script: "Researchers, ASSEMBLE! The AI now reads a HUNDRED websites and hands you a REPORT. With SOURCES! That forty tab rabbit hole? Now a five minute report! Browser tabs: CLOSED!"
    },
    {
      id: "chat-image-editing",
      category: "IMAGE", domain: "CREATIVE",
      reach: 3, leap: 3, replace: 3,
      tool: "Gemini", url: "https://gemini.google.com",
      headline: "EDIT PHOTOS JUST BY ASKING",
      desc: "\"Remove the guy in the background, make it sunset.\" Done. No layers, no masks.",
      means: "YOU DON'T NEED TO LEARN PHOTO EDITING SOFTWARE",
      boss: "Hours of manual masking",
      script: "Photo needs fixing? Just ASK! Remove that photobomber! Make it sunset! BOOM! Done! Hours of manual masking: OBLITERATED!"
    },
    {
      id: "instant-slide-decks",
      category: "PRODUCTIVITY", domain: "BUSINESS",
      reach: 3, leap: 2, replace: 4,
      tool: "Gamma", url: "https://gamma.app",
      headline: "A WHOLE SLIDE DECK FROM ONE PROMPT",
      desc: "Outline, design, charts and speaker notes generated from a single description.",
      means: "SUNDAY NIGHT PRESENTATION PANIC IS CANCELLED",
      boss: "Dragging text boxes around",
      script: "Presentation due tomorrow? NOT A PROBLEM! One prompt, one FULL slide deck! Design! Charts! Speaker notes! Sunday night panic is CANCELLED!"
    }
  ]
};
