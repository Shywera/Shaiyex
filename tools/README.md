# Adding a dungeon to /beat/

Everything is data. The page is generated, not hand edited.

    tools/dungeons.json     one entry per dungeon
    tools/charts/*.txt      the note charts, [beat,lane] pairs
    tools/beat_template.html the page with one __DUNGEONS__ slot
    tools/build_beat.py     writes public/beat/index.html

## From an osu beatmap (preferred)

An osu map gives an exact BPM and offset plus hand placed notes, which beats
guessing a grid from the audio. osu!mania maps are best because the columns
become our four lanes directly. Standard maps work too, we take the times and
lay the lanes out with hand alternation.

    python tools/osu_difficulties.py "<path to .osu>" XX

That writes charts/XX_N.txt, XX_H.txt, XX_M.txt. Normal keeps the beat,
heroic adds the half beat, mythic is the map as charted.

## Audio

    ffmpeg -i song.mp3 -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
           -c:a libmp3lame -b:a 128k -ar 44100 -ac 2 public/beat/name.mp3

Every track is levelled to the same loudness so switching dungeons does not
jump in volume.

## Then

Add an entry to dungeons.json with the dungeon name, the track file, the grid
from the map, and the pull list, then

    python tools/build_beat.py
    python tools/verify.py     # only after a no-op rebuild

## Checking a build

    python tools/outdiff.py    # what changed outside the generated block

---

# The character in /about/

The alcove on the about page draws the live model. Three moving parts:

    public/model/char.json    what the character is wearing, generated
    public/model/wmv.js       loads Wowhead's renderer and feeds it char.json
    public/model/jquery.js    the renderer will not start without it
    functions/mv/[[path]].js  proxy, because zamimg 403s anything with an Origin

## Refreshing the look

    python tools/build_char.py

What is equipped is not what anybody sees, so the transmog wins wherever there
is one. The only public place it appears is the blob the Armory ships inside
its own page, in a `<script id="model">` tag, where every gear slot carries a
`transmog` object naming the item whose appearance is worn.

From there wago.tools turns each item id into a display id, and into an
InventoryType, which matters more than it looks: a robe is not a chest, and
sent as a chest it renders with the skirt missing. Every display id is checked
against Wowhead's own meta files before it is written, so a slot that would
render as a hole is reported and left out rather than shipped.

Weapons and the off hand are always left off, in `HANDS`. A slot transmogged to
one of the Hidden items is left empty, which is what those items are for.

Face, hair and horns are not in any public API, so the customisation indexes in
char.json are set by hand. They are indexes into

    /mv/live/meta/charactercustomization/60.json

where 60 is race * 2 - 1 + gender. Change a number, reload, look.

## Animations

The renderer names them the way the game files do: the dance is `EmoteDance`,
not `Dance`. The full list for a loaded model is `view.wmv.animations`.
