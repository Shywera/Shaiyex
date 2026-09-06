"""
Rebuild public/model/char.json from what the character is actually wearing.

Raider.IO knows the equipped item ids. It does not know display ids, and the
model viewer only speaks display ids, so every item goes through wago.tools:

    item id -> ItemModifiedAppearance -> ItemAppearanceID
            -> ItemAppearance         -> ItemDisplayInfoID

The result is checked against Wowhead's own meta files before it is written,
so a slot that would render as a hole in the model shows up here instead of
on the page.

    python tools/build_char.py
"""

import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REGION = "eu"
REALM = "argent-dawn"
NAME = "Shaiyex"

# Lightforged Draenei, female. raceGender = race * 2 - 1 + gender.
RACE = 30
GENDER = 1

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "model", "char.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# raider.io slot name -> model viewer INVENTORY_TYPE. Neck, rings and trinkets
# are not drawn on a character so they are simply left out.
SLOTS = {
    "head": 1,
    "shoulder": 3,
    "shirt": 4,
    "chest": 5,
    "waist": 6,
    "legs": 7,
    "feet": 8,
    "wrist": 9,
    "hands": 10,
    "back": 16,
    "tabard": 19,
    "mainhand": 21,
    "offhand": 22,
}

# Anything in here is skipped, for when a real item ruins the silhouette.
SKIP = set()

# Appearance modifier per item id, when the default pick is the wrong tint.
MODIFIER = {}


def get(url, tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - the report is the point
            last = e
            time.sleep(1 + i)
    raise last


def csv_rows(text):
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    head = lines[0].split(",")
    return [dict(zip(head, l.split(","))) for l in lines[1:]]


def db2(table, field, value):
    q = urllib.parse.quote(f"filter[{field}]")
    return csv_rows(get(f"https://wago.tools/db2/{table}/csv?{q}={value}"))


def display_id(item_id):
    """item id -> ItemDisplayInfoID, or None when nothing is drawn for it."""
    rows = db2("ItemModifiedAppearance", "ItemID", item_id)
    rows = [r for r in rows if r.get("ItemID") == str(item_id)]
    if not rows:
        return None, "no appearance rows"

    want = MODIFIER.get(item_id)
    if want is not None:
        pick = next((r for r in rows
                     if r["ItemAppearanceModifierID"] == str(want)), None)
        if pick is None:
            return None, f"no modifier {want}"
    else:
        # source type 1 is the one you can actually transmog, and the lowest
        # modifier is the base tint.
        real = [r for r in rows if r.get("TransmogSourceTypeEnum") == "1"] or rows
        pick = min(real, key=lambda r: int(r["ItemAppearanceModifierID"]))

    app = pick["ItemAppearanceID"]
    if app in ("0", ""):
        return None, "appearance 0"

    ar = [r for r in db2("ItemAppearance", "ID", app) if r.get("ID") == app]
    if not ar:
        return None, f"appearance {app} missing"
    did = int(ar[0]["ItemDisplayInfoID"])
    return (did, None) if did else (None, "display 0")


# weapons and off hands are filed under meta/item, everything worn is
# under meta/armor/<slot>.
HELD = {13, 14, 15, 21, 22, 23}


def drawn(slot, did):
    """Does Wowhead hold a model for this slot and display id?"""
    tail = f"item/{did}" if slot in HELD else f"armor/{slot}/{did}"
    url = f"https://wow.zamimg.com/modelviewer/live/meta/{tail}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    prof = json.loads(get(
        "https://raider.io/api/v1/characters/profile"
        f"?region={REGION}&realm={REALM}&name={NAME}&fields=gear"))

    print(f"{prof['name']} - {prof['race']} {prof['class']}, "
          f"{prof['gear']['item_level_equipped']:.1f} equipped")

    items, missing = [], []
    for name, slot in SLOTS.items():
        it = prof["gear"]["items"].get(name)
        if not it or it["item_id"] in SKIP:
            continue
        item_id = it["item_id"]
        did, why = display_id(item_id)
        if did is None:
            missing.append(f"{name}: {it['name']} ({why})")
            continue
        ok = drawn(slot, did)
        print(f"  {name:<9} slot {slot:<3} item {item_id:<7} display {did:<8}"
              f" {'ok' if ok else 'NOT ON WOWHEAD'}  {it['name']}")
        if not ok:
            missing.append(f"{name}: {it['name']} (display {did} not on wowhead)")
            continue
        items.append([slot, did])

    char = {
        "_": "generated by tools/build_char.py, do not hand edit",
        "name": prof["name"],
        "realm": prof["realm"],
        "spec": prof.get("active_spec_name", ""),
        "class": prof.get("class", ""),
        "ilvl": round(prof["gear"]["item_level_equipped"], 1),
        "race": RACE,
        "gender": GENDER,
        # option name -> choice index, straight out of
        # meta/charactercustomization/<race*2-1+gender>.json
        "options": {
            "Face": 3,
            "Skin Color": 2,
            "Hair Style": 6,
            "Hair Color": 3,
            "Horns": 4,
            "Eye Color": 2,
            "Tattoo": 0,
            "Tendrils": 0,
            "Tail": 1,
            "Jewelry Color": 5,
        },
        "items": items,
    }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(char, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(f"\nwrote {os.path.normpath(OUT)} with {len(items)} visible slots")
    if missing:
        print("left out:")
        for m in missing:
            print("  -", m)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
