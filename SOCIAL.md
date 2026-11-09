# Connecting social accounts

Every day, after the scan, the workflow builds:
- **4 images** (1080×1350): the AI LEVEL card plus the top 3 power-ups.
- **1 vertical video** (1080×1920, about 45 s): a narrated announcer voice with a chiptune beat.

Then it posts them anywhere you've connected. Nothing posts until you add the secrets below, and each
platform posts at most once a day (logged in `data/posted.json`).

> You create the accounts and paste the secrets yourself. They're stored encrypted by GitHub and never appear in the code.
> Run each `gh secret set` command in your own terminal; it asks for the value, so it doesn't end up in your shell history.

---

## 1. Bluesky (about 5 minutes)

1. Create the account at https://bsky.app, e.g. `ailevel.bsky.social`. Add the profile picture and bio.
2. Go to **Settings → Privacy and security → App passwords → Add App Password**, name it `github-actions`, and copy it.
   This is a separate password just for the bot, and you can revoke it any time. **Don't use your login password.**
3. Save both as secrets:

```bash
gh secret set BLUESKY_HANDLE -R wagmisensei-dot/ai-level
```

```bash
gh secret set BLUESKY_APP_PASSWORD -R wagmisensei-dot/ai-level
```

---

## 2. Threads (about 20 minutes, done once)

Threads posts the **video**. Meta downloads it from your public site, which is why media is published under `/media/`.
If the video fails, it posts the 4 images as a carousel instead.

1. Create the Threads profile in the Threads app (it uses an Instagram account). Make it **public**.
2. Go to https://developers.facebook.com, choose **My Apps → Create App**, and pick the **"Access the Threads API"** use case.
3. In the app, open **Use cases → Access the Threads API → Customize**. Add the permissions
   **`threads_basic`** and **`threads_content_publish`**.
4. Under **App roles → Roles**, add your Threads account as a **Threads Tester**. Then in the Threads app, go to
   **Settings → Account → Website permissions → Invites** and accept it.
   Because you're a tester on your own app, you don't need Meta's app review to post to your own account.
5. Generate a **user access token** for your Threads account in the app's Threads settings (the token generator or the
   Graph API Explorer), with the two permissions above. Exchange it for a **long-lived token**, which lasts 60 days.
6. Find your Threads user ID: open this URL in a browser with your token pasted in, and copy the `id`:
   `https://graph.threads.com/v1.0/me?fields=id,username&access_token=YOUR_TOKEN`
7. Save both:

```bash
gh secret set THREADS_USER_ID -R wagmisensei-dot/ai-level
```

```bash
gh secret set THREADS_ACCESS_TOKEN -R wagmisensei-dot/ai-level
```

**Every ~50 days**, refresh the token before it expires. Open this URL, copy the new `access_token`, and set the secret again:
`https://graph.threads.com/refresh_access_token?grant_type=th_refresh_token&access_token=CURRENT_TOKEN`

Meta changes its developer dashboard often, so labels may differ slightly from the steps above.

---

## 3. Test it

GitHub → **Actions → Daily power-up scan → Run workflow**, and tick **force_media** so it builds and posts even
without new news. The run log shows `bluesky: at://…` and `threads: <id>` when a post succeeds.

## TikTok and YouTube Shorts (for now: manual, about 1 minute a day)

Their APIs only post **privately** until your app passes their review. Until then, after each run:
- the video is live at `https://wagmisensei-dot.github.io/ai-level/media/<date>/video.mp4`, and
- it's also attached to the workflow run as a download (**Actions → the run → Artifacts**).

Post it from your phone and paste the caption from `post.json` (the `instagram` field works well on TikTok too).
Turn on each app's **AI-generated content** label when you post.
