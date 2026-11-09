#!/usr/bin/env python3
"""
Posts the day's kit (built by scripts/media.py) to social media. Free APIs only.

  Bluesky : 4 images (level card + top 3 power-ups) with a clickable site link.
            Needs secrets BLUESKY_HANDLE and BLUESKY_APP_PASSWORD (an *app password*, not your login password).
  Threads : the narrated video; falls back to an image carousel if the video fails.
            Needs secrets THREADS_USER_ID and THREADS_ACCESS_TOKEN. Threads downloads the media from the
            public site, so the GitHub Pages deploy must run before this script.

A platform with no secrets set is skipped. Each platform posts at most once per day: successes are
recorded in data/posted.json, so re-running the workflow never double-posts.

Usage:
  python scripts/post.py --dry-run     # show what would be posted, call nothing
  python scripts/post.py               # post for real
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE_URL = "https://wagmisensei-dot.github.io/ai-level"
POSTED = ROOT / "data" / "posted.json"
THREADS_API = "https://graph.threads.com/v1.0"


def _ctx() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


CTX = _ctx()


def http(method: str, url: str, *, body: bytes | None = None, headers: dict | None = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        raise RuntimeError(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {detail}") from None


# ---------------------------------------------------------------- Bluesky

def post_bluesky(kit: dict, folder: Path, dry: bool) -> str:
    handle, password = os.environ.get("BLUESKY_HANDLE", ""), os.environ.get("BLUESKY_APP_PASSWORD", "")
    pds = os.environ.get("BLUESKY_PDS", "https://bsky.social").rstrip("/")
    text = kit["bluesky"]
    images = kit["images"][:4]
    if dry:
        return f"[dry-run] Bluesky: {len(images)} images, {len(text)} chars"
    if not (handle and password):
        raise LookupError("BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set")

    sess = http("POST", f"{pds}/xrpc/com.atproto.server.createSession",
                body=json.dumps({"identifier": handle, "password": password}).encode(),
                headers={"Content-Type": "application/json"})
    auth = {"Authorization": f"Bearer {sess['accessJwt']}"}

    embeds = []
    for name, alt in zip(images, kit["alt"]):
        blob = http("POST", f"{pds}/xrpc/com.atproto.repo.uploadBlob", body=(folder / name).read_bytes(),
                    headers={**auth, "Content-Type": "image/jpeg"})["blob"]
        embeds.append({"alt": alt[:1000], "image": blob, "aspectRatio": {"width": 1080, "height": 1350}})

    # Make the site address clickable: facets use UTF-8 byte offsets
    facets = []
    link_text = SITE_URL.replace("https://", "")
    b = text.encode("utf-8")
    start = b.find(link_text.encode("utf-8"))
    if start >= 0:
        facets.append({"index": {"byteStart": start, "byteEnd": start + len(link_text.encode("utf-8"))},
                       "features": [{"$type": "app.bsky.richtext.facet#link", "uri": SITE_URL}]})

    record = {"$type": "app.bsky.feed.post", "text": text, "langs": ["en"], "facets": facets,
              "createdAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
              "embed": {"$type": "app.bsky.embed.images", "images": embeds}}
    res = http("POST", f"{pds}/xrpc/com.atproto.repo.createRecord",
               body=json.dumps({"repo": sess["did"], "collection": "app.bsky.feed.post", "record": record}).encode(),
               headers={**auth, "Content-Type": "application/json"})
    return res["uri"]


# ---------------------------------------------------------------- Threads

def _threads(method: str, path: str, token: str, **params) -> dict:
    params["access_token"] = token
    if method == "GET":
        return http("GET", f"{THREADS_API}/{path}?{urllib.parse.urlencode(params)}")
    return http("POST", f"{THREADS_API}/{path}", body=urllib.parse.urlencode(params).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"})


def _wait_ready(container: str, token: str, limit_s: int = 300) -> None:
    t0 = time.time()
    while time.time() - t0 < limit_s:
        st = _threads("GET", container, token, fields="status,error_message")
        if st.get("status") == "FINISHED":
            return
        if st.get("status") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Threads media {st.get('status')}: {st.get('error_message')}")
        time.sleep(10)
    raise RuntimeError("Threads media still processing after 5 minutes")


def _wait_public(url: str, limit_s: int = 240) -> None:
    """Threads fetches media from the live site; make sure the Pages deploy is serving it."""
    t0 = time.time()
    while time.time() - t0 < limit_s:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20, context=CTX) as r:
                if r.status == 200:
                    return
        except urllib.error.URLError:
            pass
        time.sleep(15)
    raise RuntimeError(f"media not reachable on the site yet: {url}")


def post_threads(kit: dict, folder: Path, dry: bool) -> str:
    uid, token = os.environ.get("THREADS_USER_ID", ""), os.environ.get("THREADS_ACCESS_TOKEN", "")
    base = f"{SITE_URL}/media/{kit['date']}"
    text = kit["threads"]
    if dry:
        return f"[dry-run] Threads: video {base}/{kit['video']} + {len(text)} chars (carousel fallback)"
    if not (uid and token):
        raise LookupError("THREADS_USER_ID / THREADS_ACCESS_TOKEN not set")

    if kit.get("video"):
        try:
            url = f"{base}/{kit['video']}"
            _wait_public(url)
            c = _threads("POST", f"{uid}/threads", token, media_type="VIDEO", video_url=url, text=text)["id"]
            _wait_ready(c, token)
            return _threads("POST", f"{uid}/threads_publish", token, creation_id=c)["id"]
        except Exception as e:  # fall back to images rather than skip the day
            print(f"  Threads video failed ({e}); posting image carousel instead")

    children = []
    for name in kit["images"]:
        url = f"{base}/{name}"
        _wait_public(url)
        children.append(_threads("POST", f"{uid}/threads", token, media_type="IMAGE", image_url=url,
                                 is_carousel_item="true")["id"])
    parent = _threads("POST", f"{uid}/threads", token, media_type="CAROUSEL",
                      children=",".join(children), text=text)["id"]
    time.sleep(30)          # Meta recommends ~30 s before publishing
    _wait_ready(parent, token)
    return _threads("POST", f"{uid}/threads_publish", token, creation_id=parent)["id"]


# ---------------------------------------------------------------- main

PLATFORMS = {"bluesky": post_bluesky, "threads": post_threads}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=list(PLATFORMS), help="post to one platform only")
    args = ap.parse_args()

    latest = ROOT / "media" / "latest.json"
    if not latest.exists():
        print("No media kit built today; nothing to post.")
        return 0
    folder = ROOT / json.loads(latest.read_text())["dir"]
    kit = json.loads((folder / "post.json").read_text())
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else {}
    day = posted.setdefault(kit["date"], {})

    failures = 0
    for name, fn in PLATFORMS.items():
        if args.only and name != args.only:
            continue
        if name in day:
            print(f"{name}: already posted for {kit['date']} ({day[name]}), skipping")
            continue
        try:
            ref = fn(kit, folder, args.dry_run)
            print(f"{name}: {ref}")
            if not args.dry_run:
                day[name] = ref
        except LookupError as e:
            print(f"{name}: skipped ({e})")
        except Exception as e:
            failures += 1
            print(f"{name}: FAILED: {e}")

    if not args.dry_run:
        POSTED.parent.mkdir(exist_ok=True)
        POSTED.write_text(json.dumps(posted, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
