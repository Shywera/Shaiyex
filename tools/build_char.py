"""
Rebuild public/model/char.json from what the character actually looks like.

The Armory page carries the whole Blizzard profile in a <script id="model">
blob, and that blob is the only public place the transmog shows up: every gear
slot has a "transmog" object naming the item whose appearance is worn. What is
equipped is not what anybody sees, so the transmog wins wherever there is one.

An item id is not a display id, so each one goes through wago.tools:

    item id       -> ItemModifiedAppearance -> ItemAppearanceID
                  -> ItemAppearance         -> ItemDisplayInfoID
    item id       -> ItemSparse             -> InventoryType

InventoryType matters more than it looks: a robe is not a chest. Sent as a
chest it renders with the skirt missing.

Everything is checked against Wowhead's own meta files before it is written,
so a slot that would render as a hole shows up here instead of on the page.

    python tools/build_char.py
"""

import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ARMORY = "https://worldofwarcraft.blizzard.com/en-gb/character/eu/argent-dawn/shaiyex"

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "model", "char.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

# InventoryType out of ItemSparse -> the slot number the model viewer wants.
# Anything not in here is not drawn on a character: neck, rings, trinkets, bags.
WORN = {
    1: 1,    # head
    3: 3,    # shoulder
    4: 4,    # shirt
    5: 5,    # chest
    20: 20,  # robe, and it has to stay 20
    6: 6,    # waist
    7: 7,    # legs
    8: 8,    # feet
    9: 9,    # wrist
    10: 10,  # hands
    16: 16,  # back
    19: 19,  # tabard
}

# Weapons and the off hand are always left off, whatever is equipped or
# transmogged into them. Nothing gets held.
HANDS = ("weapon", "offhand")

# If they ever go back: held things are filed under meta/item, everything worn
# under meta/armor/<slot>. 21 is the main hand, 22 the off hand.
HELD = {21, 22}

# Anything in here is left off, by item id.
SKIP = set()

# Appearance modifier per item id, for when the default pick is the wrong tint.
MODIFIER = {}

# The hidden-slot items exist to draw nothing. Do not make the renderer try.
HIDDEN = re.compile(r"^Hidden\b", re.I)


def get(url, headers=None, tries=3):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
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
    q = urllib.parse.quote("filter[%s]" % field)
    return csv_rows(get("https://wago.tools/db2/%s/csv?%s=%s" % (table, q, value)))


def profile():
    """The character, out of the blob the Armory ships its own page with."""
    html = get(ARMORY, HEADERS)
    m = re.search(r'<script[^>]*id="model"[^>]*>\s*model = (\{.*?\});?\s*</script>',
                  html, re.S)
    if not m:
        raise SystemExit("the Armory page no longer carries a model blob")
    blob = json.loads(m.group(1))
    return blob["reactMounts"][0]["initialState"]["character"]


def appearance_of(item_id):
    """item id -> ItemDisplayInfoID for its base appearance."""
    rows = [r for r in db2("ItemModifiedAppearance", "ItemID", item_id)
            if r.get("ItemID") == str(item_id)]
    if not rows:
        return None, "no appearance rows"

    want = MODIFIER.get(item_id)
    if want is not None:
        pick = next((r for r in rows
                     if r["ItemAppearanceModifierID"] == str(want)), None)
        if pick is None:
            return None, "no modifier %s" % want
    else:
        # source type 1 is the one you can actually transmog, and the lowest
        # modifier is the base tint
        real = [r for r in rows if r.get("TransmogSourceTypeEnum") == "1"] or rows
        pick = min(real, key=lambda r: int(r["ItemAppearanceModifierID"]))
    return from_appearance(pick["ItemAppearanceID"])


def from_appearance(app):
    if app in ("0", "", None):
        return None, "appearance 0"
    rows = [r for r in db2("ItemAppearance", "ID", app) if r.get("ID") == str(app)]
    if not rows:
        return None, "appearance %s missing" % app
    did = int(rows[0]["ItemDisplayInfoID"])
    return (did, None) if did else (None, "display 0")


def exact_appearance(modified_appearance_id):
    """The equipped item's own appearance, no guessing about which tint."""
    mai = str(modified_appearance_id)
    rows = [r for r in db2("ItemModifiedAppearance", "ID", mai) if r.get("ID") == mai]
    if not rows:
        return None, "modified appearance %s missing" % mai
    return from_appearance(rows[0]["ItemAppearanceID"])


def inventory_type(item_id):
    rows = [r for r in db2("ItemSparse", "ID", item_id) if r.get("ID") == str(item_id)]
    if not rows:
        return None
    try:
        return int(rows[0]["InventoryType"])
    except (KeyError, ValueError):
        return None


def drawn(slot, did):
    """Does Wowhead hold a model for this slot and display id?"""
    tail = "item/%s" % did if slot in HELD else "armor/%s/%s" % (slot, did)
    url = "https://wow.zamimg.com/modelviewer/live/meta/%s.json" % tail
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    ch = profile()
    print("%s - %s %s, %s equipped" % (
        ch["name"], ch["race"]["name"], ch["class"]["name"], ch["averageItemLevel"]))
    print()

    items, notes = [], []

    for where, g in sorted(ch["gear"].items()):
        tm = (g.get("transmog") or {}).get("item")
        shown = tm or {"id": g["id"], "name": g.get("name", "")}
        name = shown.get("name", "")
        item_id = shown["id"]

        if item_id in SKIP:
            notes.append("%s: %s skipped by hand" % (where, name))
            continue

        # a hidden-slot item is a request for nothing to be there
        if tm and HIDDEN.match(name or ""):
            notes.append("%s: %s, so the slot is left empty" % (where, name))
            continue

        if where in HANDS:
            notes.append("%s: %s, weapons are always left off" % (where, name))
            continue

        inv = inventory_type(item_id)
        if inv is None:
            notes.append("%s: %s has no ItemSparse row" % (where, name))
            continue
        if inv not in WORN:
            continue  # neck, rings, trinkets: nothing to draw
        slot = WORN[inv]

        # the transmog only names an item, the equipped piece names its exact
        # appearance, so use the exact one whenever there is no transmog
        if tm or not g.get("modified_appearance_id"):
            did, why = appearance_of(item_id)
        else:
            did, why = exact_appearance(g["modified_appearance_id"])

        if did is None:
            notes.append("%s: %s (%s)" % (where, name, why))
            continue
        if not drawn(slot, did):
            notes.append("%s: %s (display %s not on wowhead)" % (where, name, did))
            continue

        print("  %-13s slot %-3s item %-7s display %-8s %s%s" % (
            where, slot, item_id, did, name, "  [transmog]" if tm else ""))
        items.append([slot, did])

    items.sort()

    char = {
        "_": "generated by tools/build_char.py, do not hand edit",
        "name": ch["name"],
        "realm": ch.get("realm", {}).get("name", ""),
        "spec": ch.get("spec", {}).get("name", ""),
        "class": ch["class"]["name"],
        "ilvl": ch["averageItemLevel"],
        "race": ch["race"]["id"],
        "gender": ch["gender"]["id"],
        # option name -> choice index, straight out of
        # /mv/live/meta/charactercustomization/<race*2-1+gender>.json.
        # Nothing public exposes these, so they are set by eye.
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

    print("\nwrote %s with %d visible slots" % (os.path.normpath(OUT), len(items)))
    if notes:
        print("left out:")
        for n in notes:
            print("  -", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
