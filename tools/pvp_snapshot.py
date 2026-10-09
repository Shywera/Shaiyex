"""Snapshot PvP data from check-pvp.fr into public/data/pvp.json.

check-pvp.fr answers its own API with 403 unless the request comes from a
browser session on the site, so this renders the profile pages in headless
Edge, records the network log with response bodies, and reads the JSON the
page itself received. The rendered DOM gives the season-title list.

    python tools/pvp_snapshot.py

Renamed or transferred characters show up on check-pvp as separate alts
with the same history. They are merged here: same class, same faction and
the same 2v2 and 3v3 peaks means one character. The newest name wins and
the peaks are the best across all names.
"""
import base64
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "data" / "pvp.json"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

MAIN = ("eu", "Argent Dawn", "Norayne")
# characters that get their own detail block (spec-level shuffle ratings)
FEATURED = [("eu", "Argent Dawn", "Shaiyex"), ("eu", "Argent Dawn", "Besthealer")]

CLASSES = {1: "Warrior", 2: "Paladin", 3: "Hunter", 4: "Rogue", 5: "Priest",
           6: "Death Knight", 7: "Shaman", 8: "Mage", 9: "Warlock", 10: "Monk",
           11: "Druid", 12: "Demon Hunter", 13: "Evoker"}
SPECS = {65: "Holy", 66: "Protection", 70: "Retribution", 250: "Blood",
         251: "Frost", 252: "Unholy", 253: "Beast Mastery", 254: "Marksmanship",
         255: "Survival"}
RACES = {1: "Human", 3: "Dwarf", 4: "Night Elf", 7: "Gnome", 11: "Draenei",
         22: "Worgen", 29: "Void Elf", 30: "Lightforged Draenei", 34: "Dark Iron Dwarf",
         37: "Mechagnome", 52: "Dracthyr", 2: "Orc", 5: "Undead", 6: "Tauren",
         8: "Troll", 9: "Goblin", 10: "Blood Elf", 27: "Nightborne",
         28: "Highmountain Tauren", 31: "Zandalari Troll", 35: "Vulpera",
         36: "Mag'har Orc", 85: "Earthen"}


def read_netlog(path, wait=20):
    """Load Edge's net log. It can still be flushing when --dump-dom returns,
    and a log Edge never closed just stops after the last event, so wait for
    it to settle and then close the events array ourselves if we must."""
    last, text = -1, ""
    for _ in range(wait * 2):
        size = os.path.getsize(path) if os.path.exists(path) else 0
        if size and size == last:
            break
        last = size
        time.sleep(0.5)
    text = open(path, encoding="utf-8", errors="ignore").read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # one event per line: drop lines off the end until the rest closes cleanly
    lines = text.rstrip().split("\n")
    for _ in range(5):
        try:
            return json.loads("\n".join(lines).rstrip().rstrip(",") + "]}")
        except json.JSONDecodeError:
            lines.pop()
    raise RuntimeError(f"net log at {path} is not readable")


def capture(region, realm, name):
    """Render one profile; return (character json, rendered dom).
    The character request sometimes lands after the virtual time budget runs
    out, so try again with a longer budget before giving up."""
    for budget in (20000, 35000, 50000):
        found = capture_once(region, realm, name, budget)
        if found:
            return found
    raise RuntimeError(f"no character json captured for {name}-{realm}")


def capture_once(region, realm, name, budget):
    url = f"https://check-pvp.fr/{region}/{realm.replace(' ', '%20')}/{name}"
    # Edge's helper processes can outlive the main one and keep the profile
    # locked, so cleanup failures are not worth crashing over.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        log = os.path.join(tmp, "net.json")
        dom = subprocess.run(
            [EDGE, "--headless=new", "--disable-gpu", f"--virtual-time-budget={budget}",
             f"--user-data-dir={os.path.join(tmp, 'profile')}",
             f"--log-net-log={log}", "--net-log-capture-mode=Everything",
             "--dump-dom", url],
            capture_output=True, timeout=240).stdout.decode("utf-8", "replace")
        net = read_netlog(log)
    types = {v: k for k, v in net["constants"]["logEventTypes"].items()}
    urls, chunks = {}, {}
    for e in net["events"]:
        t, sid, p = types.get(e["type"]), e["source"]["id"], e.get("params", {})
        if t == "URL_REQUEST_START_JOB" and "url" in p:
            urls[sid] = p["url"]
        elif t in ("URL_REQUEST_JOB_FILTERED_BYTES_READ", "URL_REQUEST_JOB_BYTES_READ") and "bytes" in p:
            chunks.setdefault((sid, t), []).append(base64.b64decode(p["bytes"]))
    want = f"/api/characters/{region}/"
    for sid, u in urls.items():
        if want not in u or not u.lower().endswith("/" + name.lower()):
            continue
        # the filtered stream is the decompressed body; fall back to the raw one
        for t in ("URL_REQUEST_JOB_FILTERED_BYTES_READ", "URL_REQUEST_JOB_BYTES_READ"):
            try:
                return json.loads(b"".join(chunks.get((sid, t), []))), dom
            except ValueError:
                continue
    return None


def season_titles(dom):
    """Expansion -> [(title, season, range)] from the achievements panel."""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", dom, flags=re.S)
    lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", s)).split("\n") if l.strip()]
    out, current = [], None
    for i, l in enumerate(lines):
        if l in ("Midnight", "The War Within", "Dragonflight", "Shadowlands",
                 "Battle for Azeroth", "Legion") and i + 1 < len(lines) and lines[i + 1] == "expand_more":
            current = {"expansion": l, "seasons": []}
            out.append(current)
            continue
        m = re.match(r"^(.+?) : Season (\d+)$", l)
        if m and current:
            desc = lines[i + 1] if i + 1 < len(lines) else ""
            r = re.search(r"(\d{4})(?: and (\d{4}))?", desc)
            current["seasons"].append({
                "title": m.group(1), "season": int(m.group(2)),
                "from": int(r.group(1)) if r else None,
                "to": int(r.group(2)) if r and r.group(2) else None})
        if l.startswith("Alts ("):
            break
    return out


def account_achievements(dom):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", dom, flags=re.S)
    lines = [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", s)).split("\n") if l.strip()]
    keep = ("Just the Two of Us", "Three's Company", "Elite", "Knight-Captain", "Gladiator",
            "Duelist", "Rival", "Challenger")
    out = []
    for i, l in enumerate(lines[:-1]):
        if l.startswith("Midnight"):
            break
        if l.startswith(keep) and lines[i + 1].startswith("Earn "):
            out.append({"name": l, "desc": lines[i + 1]})
    return out


def merge_alts(rerolls):
    groups = {}
    for r in rerolls:
        key = (r["class"], r["faction"], r["ratemax2v2"], r["ratemax3v3"])
        if r["ratemax2v2"] == 0 and r["ratemax3v3"] == 0:
            key = (r["class"], r["faction"], r["name"], r["realm"])  # no history to match on
        groups.setdefault(key, []).append(r)
    alts = []
    for members in groups.values():
        members.sort(key=lambda r: r["lastModified"], reverse=True)
        head = members[0]
        alts.append({
            "name": head["name"], "realm": head["realm"], "region": head["region"],
            "class": CLASSES.get(head["class"], str(head["class"])), "classId": head["class"],
            "faction": "Alliance" if head["faction"] == 1 else "Horde",
            "level": max(m["level"] for m in members),
            "max2v2": max(m["ratemax2v2"] for m in members),
            "max3v3": max(m["ratemax3v3"] for m in members),
            "maxShuffle": max(m["ratemaxshuffle"] for m in members),
            "maxBlitz": max(m["ratemaxblitz"] for m in members),
            "curShuffle": max(m["rateatmshuffle"] for m in members),
            "curBlitz": max(m["rateatmblitz"] for m in members),
            "formerly": [f'{m["name"]}-{m["realm"]}' for m in members[1:]],
            "seen": head["lastModified"],
        })
    alts.sort(key=lambda a: max(a["max2v2"], a["max3v3"], a["maxShuffle"], a["maxBlitz"]), reverse=True)
    return alts


def brief(c):
    return {
        "name": c["name"], "realm": c["realm"], "level": c["level"],
        "class": CLASSES.get(c["class"]), "spec": SPECS.get(c["activeSpecId"], ""),
        "race": RACES.get(c["race"], ""), "faction": "Alliance" if c["faction"] == 1 else "Horde",
        "ilvl": c["averageItemLevelEquipped"], "pvpIlvl": c["pvpGear"],
        "max2v2": c["ratemax2v2"], "max3v3": c["ratemax3v3"], "maxRbg": c["ratemaxrbg"],
        "maxShuffle": c["ratemaxshuffle"], "maxBlitz": c["ratemaxblitz"],
        "curShuffle": c["rateatmshuffle"], "curBlitz": c["rateatmblitz"],
        "shuffle": [{"spec": SPECS.get(s["specId"], str(s["specId"])), "rating": s["rating"],
                     "best": s["maxRating"], "win": s["win"], "lose": s["lose"]}
                    for s in c.get("soloshuffles") or []],
        "blitz": [{"spec": SPECS.get(s["specId"], str(s["specId"])), "rating": s["rating"],
                   "best": s["maxRating"], "win": s["win"], "lose": s["lose"]}
                  for s in c.get("soloBlitzs") or []],
    }


def main():
    main_json, main_dom = capture(*MAIN)
    seasons, account = season_titles(main_dom), account_achievements(main_dom)
    if not seasons:
        # Edge 154 stopped printing --dump-dom on Windows. Past season titles
        # never change, so the previous snapshot's list is still right; the
        # running season only gets a title once it ends.
        prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
        seasons, account = prev.get("seasons", []), prev.get("account", [])
        print("warning: page text was empty, kept season titles from the previous snapshot",
              file=sys.stderr)
    data = {
        "source": "check-pvp.fr",
        "updated": time.strftime("%Y-%m-%d"),
        "main": brief(main_json),
        "achievementPoints": main_json["achievementPoints"],
        "account": account,
        "seasons": seasons,
        "climb": [{"t": h["date"], "rating": h["rating"], "rank": h["rank"],
                   "win": h["win"], "lose": h["lose"]}
                  for a in main_json.get("activity", []) for h in reversed(a["history"])
                  if a["bracket"] == "blitz"],
        "featured": [],
        "altsRaw": len(main_json["rerolls"]),
        "alts": merge_alts(main_json["rerolls"]),
    }
    for who in FEATURED:
        try:
            c, _ = capture(*who)
            data["featured"].append(brief(c))
        except Exception as e:  # a missing alt should not sink the snapshot
            print(f"skip {who[2]}: {e}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    merged = [a for a in data["alts"] if a["formerly"]]
    print(f"wrote {OUT.relative_to(ROOT)}: {data['altsRaw']} alts on check-pvp, "
          f"{len(data['alts'])} after merging renames")
    for a in merged:
        print(f"  {a['name']}-{a['realm']} absorbs {', '.join(a['formerly'])}")


if __name__ == "__main__":
    main()
