"""
Three-step matching pipeline, in this order (do not skip ahead):

  1. Parse every pending video's title into (id, title, year, org).
     A video with no year in its title can't be filed under a year in
     gmv_videos.json regardless of what it shows -- skip steps 2 and 3
     for it entirely, no point guessing a MuscleMemory title.
  2. For each row that has a year, fetch that org's contest list ONCE via
     /api/org?name={org} (cached across all rows sharing the org) and pick
     the single best name match within it by token overlap. This is what
     prevents cross-org false merges like "WFF World Championships" ->
     "World Championships - NABBA" -- if the title's org isn't in
     MuscleMemory's org list at all, the video is flagged not-tracked and
     step 3 is skipped entirely for it.
  3. ONLY for that one chosen name (not for runner-up candidates), check
     /api/contest/years?name={name} to see if the video's year is on file.

Writes pending_year_org.md, a review table with columns YouTube ID / Year /
Org / Proposed MuscleMemory Title / Title (populated only for rows that
made it through steps 2-3), and gmv_videos_suggestions.json with the same
info in a form Claude turns into match/skip decisions (see
apply_decisions.py).

Usage: python3 suggest_match.py
"""
import json
import os
import re
import urllib.parse
import urllib.request

from ensure_local_server import BASE_URL, ensure_server
from extract_year_org import UNTRACKED_ORGS, YEAR_RE, fetch_db_orgs, find_org

SKILL_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PENDING_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_pending.json")
SUGGESTIONS_FILE = os.path.join(SKILL_DATA_DIR, "gmv_videos_suggestions.json")
TABLE_FILE = os.path.join(SKILL_DATA_DIR, "pending_year_org.md")

TRAILING_NOISE = [
    r"\bfrom gmv (bodybuilding|productions)\b.*$",
    r"\bat gmv\b.*$",
    r"\bfrom gmv\b\s*$",
    r"\bavailable\b\s*$",
]
SPLIT_SUFFIXES = re.compile(
    r"\s*[–\-:]\s*(part\s*#?\s*\d+|prejudging|finals?(\s*#\s*\d+)?|highlights?|"
    r"qualifier|men'?s?\s*(show|fitness|physique)?|women'?s?\s*(show|fitness|physique)?)\s*$",
    re.IGNORECASE,
)

# Below this, the top candidate is too weak to bother checking years for.
MIN_SCORE_TO_CHECK_YEARS = 0.75


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


# Country/region adjective -> the noun form MuscleMemory contest names use
# (e.g. GMV titles say "Australian Nationals", the DB says "Australia").
# Plain word-token matching treats these as unrelated words otherwise.
DEMONYMS = {
    "australian": "australia", "american": "america", "canadian": "canada",
    "mexican": "mexico", "european": "europe", "asian": "asia",
    "african": "africa", "italian": "italy", "german": "germany",
    "russian": "russia", "korean": "korea", "japanese": "japan",
    "chinese": "china", "brazilian": "brazil", "british": "britain",
    "irish": "ireland", "scottish": "scotland", "welsh": "wales",
    "dutch": "holland", "spanish": "spain", "french": "france",
    "swedish": "sweden", "norwegian": "norway", "finnish": "finland",
    "polish": "poland", "hungarian": "hungary", "austrian": "austria",
    "swiss": "switzerland",
}


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    words = [DEMONYMS.get(w, w) for w in s.split()]
    return " ".join(words)


# Words too generic to mean much on their own -- shared by dozens of
# unrelated contest names ("Pro", "International", "Championships"...).
# Deliberately does NOT include words that are actually distinctive just
# because they're common English words (e.g. "Games" only ever appears in
# "World Games" among these contest names -- treating it as filler let an
# unrelated contest outscore the real, correct-but-absent match).
FILLER_WORDS = {
    "pro", "international", "invitational", "championships", "championship",
    "classic", "cup", "grand", "prix", "open", "nationals", "national",
    "show", "supershow", "super", "masters", "amateur", "natural", "the",
    "and", "of", "world", "state", "states", "regional",
}


def token_score(norm_base, key):
    if not norm_base or not key:
        return 0.0

    def weights(s):
        return {t: (0.3 if t in FILLER_WORDS or len(t) < 3 else 1.0) for t in s.split()}

    wa, wb = weights(norm_base), weights(key)
    all_tokens = set(wa) | set(wb)
    inter = sum(min(wa.get(t, 0), wb.get(t, 0)) for t in all_tokens)
    union = sum(max(wa.get(t, 0), wb.get(t, 0)) for t in all_tokens)
    jaccard = inter / union if union else 0.0

    bonus = 0.0
    padded_base, padded_key = f" {norm_base} ", f" {key} "
    if padded_key in padded_base or padded_base in padded_key:
        bonus = 0.35

    return round(min(jaccard + bonus, 1.0), 3)


def strip_title_noise(title, org_token):
    text = title
    for pat in TRAILING_NOISE:
        text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()

    year_match = YEAR_RE.search(text)
    remainder = text
    if year_match:
        remainder = (text[:year_match.start()] + " " + text[year_match.end():]).strip()

    for _ in range(2):
        new_remainder = SPLIT_SUFFIXES.sub("", remainder).strip()
        if new_remainder == remainder:
            break
        remainder = new_remainder

    for part in org_token.split("/"):
        remainder = re.sub(r"\b" + re.escape(part) + r"\b", "", remainder, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", remainder).strip(" -–:")


def fetch_org_contests(org, cache):
    if org in cache:
        return cache[org]
    try:
        data = fetch_json(f"{BASE_URL}/api/org?name={urllib.parse.quote(org)}")
        names = data.get("data", {}).get("contests", [])
    except Exception:
        names = []
    cache[org] = names
    return names


def fetch_years(contest_full_name):
    url = f"{BASE_URL}/api/contest/years?name={urllib.parse.quote(contest_full_name)}"
    try:
        data = fetch_json(url)
        return [str(y) for y in data.get("data", {}).get("years", [])]
    except Exception:
        return []


def parse_rows(pending, known_orgs):
    rows = []
    for video in pending:
        title = video["title"]
        year_match = YEAR_RE.search(title)
        year_guess = year_match.group(0) if year_match else ""
        org_guess = find_org(title, known_orgs, year_match) or "IFBB"
        rows.append({"id": video["id"], "title": title, "year": year_guess, "org": org_guess})
    print(f"Step 1: parsed {len(rows)} rows "
          f"({sum(1 for r in rows if not r['year'])} have no year -- skipping steps 2-3 for those)")
    return rows


def write_table(prelim):
    with open(TABLE_FILE, "w", encoding="utf-8") as f:
        f.write("| YouTube ID | Year | Org | Proposed MuscleMemory Title | Title |\n")
        f.write("|---|---|---|---|---|\n")
        for r in prelim:
            # Only show a proposal once it cleared the confidence bar to be
            # worth checking years for -- a weak top-of-a-bad-list candidate
            # (e.g. score 0.2 because two unrelated names share a filler
            # word) isn't a proposal, it's noise.
            strong = r.get("best_name") and r.get("score", 0) >= MIN_SCORE_TO_CHECK_YEARS
            proposed = r["best_name"] if strong else ""
            f.write(f"| {r['id']} | {r['year']} | {r['org']} | {proposed} | "
                    f"{r['title'].replace('|', chr(92)+'|')} |\n")
    print(f"Wrote {TABLE_FILE} ({len(prelim)} rows)")


def main():
    if not ensure_server():
        print("ERROR: could not reach or start the local musmem server. Aborting.")
        return

    if not os.path.exists(PENDING_FILE):
        print(f"No pending file at {PENDING_FILE} -- run find_pending.py first.")
        return
    with open(PENDING_FILE, encoding="utf-8") as f:
        pending = json.load(f)

    if not pending:
        print("No pending videos to suggest matches for.")
        return

    db_orgs = fetch_db_orgs()
    known_orgs = db_orgs | UNTRACKED_ORGS

    # Step 1
    rows = parse_rows(pending, known_orgs)

    # Step 2: org-scoped name matching (no /api/contest/years calls yet)
    org_contests_cache = {}
    prelim = []
    for r in rows:
        if not r["year"]:
            # No year in the title -> can't be filed under a year even if
            # we found a name match, so don't bother guessing one.
            prelim.append({**r, "no_year": True, "org_tracked": False,
                            "best_name": None, "score": 0, "runner_up": None})
            continue

        org_parts = r["org"].split("/")
        tracked_parts = [p for p in org_parts if p in db_orgs]

        if not tracked_parts:
            prelim.append({**r, "no_year": False, "org_tracked": False,
                            "best_name": None, "score": 0, "runner_up": None})
            continue

        base_guess = strip_title_noise(r["title"], r["org"])
        norm_base = normalize(base_guess)

        candidates = []
        for org in tracked_parts:
            for full_name in fetch_org_contests(org, org_contests_cache):
                name = full_name.rsplit(" - ", 1)[0] if " - " in full_name else full_name
                score = token_score(norm_base, normalize(name))
                if score > 0:
                    candidates.append((score, len(normalize(name).split()), full_name))
        # On a tied score (common at 1.0, since containment makes both a
        # name and a longer superset of it score the same -- e.g. "Night of
        # Champions" and "California Night of Champions" both contain the
        # title's exact words) prefer the SHORTER name: the title didn't
        # mention "California", so the plain contest is the more literal
        # match, not an arbitrary pick from whatever order the API returned.
        candidates.sort(key=lambda t: (-t[0], t[1]))
        candidates = [(score, name) for score, _wc, name in candidates]

        best = candidates[0] if candidates else None
        runner_up = candidates[1] if len(candidates) > 1 else None
        prelim.append({
            **r, "no_year": False, "org_tracked": True, "base_guess": base_guess,
            "best_name": best[1] if best else None,
            "score": best[0] if best else 0,
            "runner_up": f"{runner_up[1]} ({runner_up[0]})" if runner_up else None,
        })

    no_year_count = sum(1 for p in prelim if p["no_year"])
    print(f"Step 2: matched within org for {sum(1 for p in prelim if p['org_tracked'])} videos "
          f"({sum(1 for p in prelim if not p['org_tracked'] and not p['no_year'])} have an untracked org, "
          f"{no_year_count} skipped -- no year in title)")

    # Step 3: check years ONLY for the single chosen name per video, and
    # only when the name match was strong enough to be worth checking.
    suggestions = []
    years_checked = 0
    for p in prelim:
        entry = {
            "id": p["id"], "title": p["title"],
            "year_guess": p["year"] or None, "org_guess": p["org"],
            "no_year": p["no_year"], "org_tracked": p["org_tracked"],
        }
        if p["no_year"] or not p["org_tracked"]:
            entry["best_match"] = None
            suggestions.append(entry)
            continue

        entry["base_guess"] = p["base_guess"]
        entry["runner_up"] = p["runner_up"]

        if p["best_name"] and p["score"] >= MIN_SCORE_TO_CHECK_YEARS:
            years = fetch_years(p["best_name"])
            years_checked += 1
            entry["best_match"] = {
                "contest": p["best_name"],
                "score": p["score"],
                "db_years_span": f"{years[0]}-{years[-1]} ({len(years)} yrs)" if years else "",
                "year_in_db": p["year"] in years if p["year"] else False,
            }
        else:
            entry["best_match"] = {
                "contest": p["best_name"], "score": p["score"],
                "db_years_span": "(not checked -- score too low)", "year_in_db": False,
            } if p["best_name"] else None

        suggestions.append(entry)

    print(f"Step 3: checked /api/contest/years for {years_checked} videos (1 call each, best match only)")

    os.makedirs(SKILL_DATA_DIR, exist_ok=True)
    write_table(prelim)
    with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {SUGGESTIONS_FILE} ({len(suggestions)} videos)")


if __name__ == "__main__":
    main()
