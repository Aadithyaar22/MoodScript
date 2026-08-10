"""Jamendo client: resolves mood-arc stages to actual playable tracks.

WHY JAMENDO
-----------
Everything on Jamendo is Creative Commons licensed, so the audio can be streamed inside
the app without a licensing agreement. Spotify would give recognisable music, but its
`/audio-features` and `/recommendations` endpoints were closed to new applications in late
2024 — precisely the valence/energy signal this feature is built on — and its embed player
cannot be sequenced into an arc anyway.

The trade is catalogue: these are unknown independent artists. For ambience and for an
emotional arc that is acceptable; for "play me the song I love" it is not, which is why
this is framed in the UI as a soundtrack rather than a recommendation.

DEGRADING WITHOUT A KEY
-----------------------
`JAMENDO_CLIENT_ID` is optional. Without it — or if Jamendo is down, slow, or returns
nothing for a tag combination — this returns stage descriptors with an empty track list
rather than raising. The soundtrack is a side feature; it must never be capable of
breaking the journalling path, and a user who asks for one and gets an apology is in a
much better position than one whose entry failed to save.

Jamendo's `fuzzytags` matches loosely across community tags, which suits us: the arc's
tags are moods, not genres, and an exact-match query on them returns almost nothing.
"""
from __future__ import annotations

import asyncio
import html
import os
import random
import time
import urllib.parse

import httpx

API = "https://api.jamendo.com/v3.0/tracks"
TIMEOUT = httpx.Timeout(6.0, connect=3.0)


def _client_id() -> str:
    """Read lazily, not at import. Binding this at module level would capture the
    value before load_dotenv() runs depending on import order, which fails locally
    in exactly the way that looks like "the key is wrong"."""
    return os.getenv("JAMENDO_CLIENT_ID", "")

# Jamendo's own vocabulary for "how fast". Mapping energy onto it lets the query
# constrain tempo as well as mood, which fuzzytags alone does not do well.
def _speed(energy: float) -> str:
    if energy < 0.35:
        return "verylow"
    if energy < 0.50:
        return "low"
    if energy < 0.70:
        return "medium"
    return "high"


def configured() -> bool:
    return bool(_client_id())


async def _search(client: httpx.AsyncClient, tags: list[str], energy: float,
                  limit: int) -> list[dict]:
    """One tag query, with a retry for Jamendo's silent-empty behaviour.

    Jamendo silently empties rapid successive requests: the response is HTTP 200 with
    `status: "success"`, `code: 0`, no warning, and zero results. Measured directly, a
    burst of identical queries returns 5, 0, 0, 0 — and a bare one-word query with no
    filters returns 0, 0, 0 when it is not first in the burst. So this is RATE-based,
    not query-based; broadening the tags does not help, and only spacing does.

    Hence retry with a short backoff rather than a single immediate retry. Caching in
    `_pool_for` is what actually removes the problem; this is the safety net for a cold
    pool.

    Always offset 0: this fetches the candidate POOL, and variety comes from sampling
    that pool per request rather than from paging deeper into an unknown-length result
    set (a random offset can silently land past the end of a narrow tag query).
    """
    for _, pause in enumerate((0.0, 0.35, 0.8)):
        if pause:
            await asyncio.sleep(pause)
        params = {
            "client_id": _client_id(),
            "format": "json",
            "limit": str(limit),
            "fuzzytags": "+".join(tags),
            "speed": _speed(energy),
            "audioformat": "mp32",
            "include": "musicinfo",
            "groupby": "artist_id",   # avoid three tracks by the same artist in one arc
            "order": "popularity_total",
            "offset": "0",
        }
        r = await client.get(API, params=params)
        r.raise_for_status()
        results = r.json().get("results", []) or []
        if results:
            return results
    return []


def _clean(s):
    """Jamendo returns HTML-escaped text — an artist called "Cabeza&Cabal" arrives as
    "Cabeza&amp;Cabal". React escapes on render, so without this the ampersand shows
    up literally as "&amp;" in the UI."""
    return html.unescape(s) if isinstance(s, str) else s


def _track(raw: dict, stage: dict) -> dict:
    title = _clean(raw.get("name")) or ""
    artist = _clean(raw.get("artist_name")) or ""
    # A YouTube SEARCH, not a video link. Matching a Jamendo track to a specific
    # YouTube video would need the YouTube Data API and, for independent Creative
    # Commons artists, would often match nothing or the wrong upload. A search is
    # honest about what it is and cannot silently point at the wrong song.
    query = urllib.parse.quote_plus(f"{artist} {title}".strip())
    return {
        "id": raw.get("id"),
        "title": title,
        "artist": artist,
        "audio": raw.get("audio"),
        "duration": raw.get("duration"),
        "image": raw.get("album_image") or raw.get("image"),
        "share_url": raw.get("shareurl"),      # the real track page — always correct
        "youtube": f"https://www.youtube.com/results?search_query={query}" if query else None,
        "license": raw.get("license_ccurl"),
        "stage": stage["stage"],
    }


# Cached candidate pools, keyed by (tags, speed). Retrying a throttled API is treating
# the symptom; the cause is that the same handful of mood queries is issued over and
# over. There are only a few dozen distinct (tag, speed) combinations the arc can
# produce, and Creative Commons catalogues do not change minute to minute, so each is
# fetched once per TTL and then sampled from. That removes nearly all API traffic,
# makes a warm soundtrack near-instant, and — because the sample is random per request
# — gives MORE variety than paging ever did, not less.
_POOL: dict[tuple, tuple[float, list]] = {}
_POOL_TTL = 3600.0     # seconds
_POOL_SIZE = 30        # candidates cached per mood


async def _pool_for(client: httpx.AsyncClient, tags: list[str],
                    energy: float) -> list[dict]:
    key = (tuple(tags), _speed(energy))
    hit = _POOL.get(key)
    if hit and (time.time() - hit[0]) < _POOL_TTL:
        return hit[1]
    results = await _search(client, tags, energy, _POOL_SIZE)
    playable = [r for r in results if r.get("audio")]
    if playable:                      # never cache an empty (throttled) response
        _POOL[key] = (time.time(), playable)
    return playable


async def prewarm() -> int:
    """Populate every mood pool in the background at startup.

    The cache lives in the process, and this service sleeps when idle — so on a
    low-traffic app almost every soundtrack request would otherwise hit a COLD cache
    and pay the 1.5-2.5s API round trip. Caching alone does not help when the process
    keeps restarting; the pools have to be filled before anyone asks.

    There are only ~13 distinct (tags, speed) combinations across all seven emotions,
    so this is a small, bounded warm-up. Runs detached: failures are logged and
    ignored, never surfaced, and never block startup or a request.
    """
    from models.music import EMOTION_VE, build_arc

    wanted, seen_keys = [], set()
    for emo in EMOTION_VE:
        for stage in build_arc([{"emotion": emo, "confidence": 1.0}]):
            key = (tuple(stage["tags"]), _speed(stage["energy"]))
            if key not in seen_keys:
                seen_keys.add(key)
                wanted.append(stage)

    filled = 0
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for stage in wanted:
            try:
                if await _pool_for(client, stage["tags"], stage["energy"]):
                    filled += 1
            except Exception as e:
                print(f"[jamendo] prewarm {stage['tags']}: {type(e).__name__}: {e}")
            await asyncio.sleep(0.25)     # unhurried; nobody is waiting on this
    print(f"[jamendo] prewarmed {filled}/{len(wanted)} mood pools")
    return filled


async def resolve(arc: list[dict], per_stage: int = 2) -> dict:
    """Turn arc waypoints into tracks. Never raises; reports why it is empty."""
    stages = [dict(s, tracks=[]) for s in arc]
    if not configured():
        return {"stages": stages, "available": False,
                "reason": "JAMENDO_CLIENT_ID is not set"}

    seen: set = set()
    reason = None
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Fetch the three stages concurrently. Measured: 3.3-3.8s sequential against
            # 1.5-2.5s concurrent, with identical result counts — the rate limiting that
            # empties rapid SEQUENTIAL repeats does not penalise parallel distinct
            # queries. Only matters on a cold pool; warm requests never get here.
            pools = await asyncio.gather(
                *(_pool_for(client, s["tags"], s["energy"]) for s in stages),
                return_exceptions=True,
            )
            for stage, pool in zip(stages, pools):
                if isinstance(pool, Exception):   # one stage failing is not fatal
                    reason = f"{type(pool).__name__} on stage '{stage['stage']}'"
                    continue
                candidates = [r for r in pool if r.get("id") not in seen]
                random.shuffle(candidates)        # variety across requests
                for raw in candidates[:per_stage]:
                    seen.add(raw.get("id"))
                    stage["tracks"].append(_track(raw, stage))
    except Exception as e:
        return {"stages": stages, "available": False,
                "reason": f"{type(e).__name__}: {e}"}

    found = sum(len(s["tracks"]) for s in stages)
    if not found:
        reason = reason or "no Jamendo tracks matched these moods"
    return {"stages": stages, "available": bool(found), "reason": reason}
