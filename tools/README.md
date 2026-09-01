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
