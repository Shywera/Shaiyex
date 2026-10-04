# shaiyex.com

Osobna stranica: WoW paladin, nekoliko mini igara i vizualizacija. Statične
datoteke u `public/`, dvije serverless funkcije u `functions/`, alati za gradnju
u `tools/`. Bez frameworka i bez koraka gradnje za same stranice.

**Live:** https://shaiyex.com

## Pokretanje lokalno

```bash
cd public
python -m http.server 8080 --bind 127.0.0.1
```

Otvoriti `http://127.0.0.1:8080/`. Rute pod `/api/` neće raditi lokalno bez
`wrangler pages dev`, ali stranice su napisane tako da to prežive: leaderboard
padne na lokalne rezultate, a knjiga gostiju kaže da je zatvorena.

## Objava

Cloudflare Pages: **build command prazan**, **output directory `public`**.
Korijenska domena je jedan proxied CNAME na `shaiyex.pages.dev`, `www` nema zapis.

`wrangler.toml` u korijenu je konfiguracija Workera samo za statične datoteke,
ostatak ranijeg pokušaja preko Workersa. Pages ga ne koristi, ali ne šteti.

**Funkcije trebaju vezanje.** Obje u `functions/api/` traže jedan store vezan na
Pages projekt pod imenom **`SCORES`** (Workers KV je pravi odabir, R2 također
radi). Dok to vezanje ne postoji, vraćaju `503`, a stranice to podnose.

## Rute

| Ruta | Što je | Zvuk |
| --- | --- | --- |
| `/` | PvP početna, samo tamna tema: rekord po sezonama, Norayneov uspon, dva klipa, svi likovi (altovi), why invite me, blacklist, mini igre. Brojke iz `data/pvp.json` | `clips/holy.mp4`, `clips/unholy.mp4` |
| `/classic/` | Stara početna, sada samo tamna strana (svijetlo svetište je maknuto). Križ gore desno vodi natrag na `/` ("PvP side"); na novoj početnoj isti križ vodi ovamo ("PvE side"). Original je u tagu `backup-live-2026-10-04` | `mercy.mp3` |
| `/classic/why/` | Originalni glasni Why Me (Mythic+ verzija), linkan s tamne strane stare početne | `track.mp3`, `ach.mp3` |
| `/about/` | Who This Guy: M+ score, napredak po tierovima, logovi. Brojke dolaze s raider.io API-ja | |
| `/pitch/` | Why invite me: mirna, kratka verzija. Bez igre, bez zvuka, 7 kB | |
| `/why/` | Why Me, PvP verzija: glasna i namjerno neugodna, faze, glazba, 145 BPM. Vodi do nje duga ploča na početnoj | `track.mp3`, `ach.mp3` |
| `/the-quiet-part/` | Nije linkano niotkuda. Iskrena verzija, bez prodaje. Piše u knjigu preko `/api/vault` | |
| `/kick/` | Kick or Leave: prekid kao ulaznica. Pet zaredom i ulazite, dva promašaja i gotovo | `bg.mp3`, `shrine.mp3` |
| `/beat/` | Interrupt On The Beat: ritamska igra u četiri trake, leaderboard | 10 pjesama |
| `/raid/` | Abyss Training: učenje oblika s bossova, tri role, scoring po roli | |
| `/deplete/` | Key Depleted: post mortem nakon pokvarenog kljuca, brojač i lista | `neon.mp3`, `theme.mp3` |
| `/drift/` | Tokyo Drift: vizualizacija, svaka krivina pada na frazu, 180 BPM | `track.mp3` |
| `/loud/` | PLAY IT LOUD: vizualizacija, tri dropa i jedan tvrdi stop na 1:32, 190 BPM | `track.mp3` |
| `/overdrive/` | OVERDRIVE: vizualizacija, 210 BPM | `track.mp3` |
| `/miss/` | did i tell u that i miss u: vizualizacija bez teksta preko nje | `track.mp3` |
| `/anathema/` | Anathema: pečat koji se lomi, achievement na kraju | `track.mp3`, `ach.mp3` |

### Tri lica namjerno

`/pitch/`, `/why/` i `/the-quiet-part/` nose istu poruku u tri registra: pristojnom,
umišljenom i iskrenom. To nije nedosljednost nego cijela poanta, i `/the-quiet-part/`
to izgovori naglas. Ako se jedna od njih mijenja, mijenja se i odnos prema drugima.

## PvP podaci (`/data/pvp.json`)

Početna čita `public/data/pvp.json`. Puni ga `tools/pvp_snapshot.py`:

```bash
python tools/pvp_snapshot.py
```

- check-pvp.fr vraća `403` na svoj API izvan preglednika, pa skripta otvara profil u headless Edgeu, snimi mrežni log s tijelima odgovora i iz njega izvuče JSON koji je stranica sama dobila. Popis sezonskih titula čita iz iscrtanog DOM-a.
- Glavni lik je `MAIN` u skripti (sada Norayne). `FEATURED` su likovi čiji se trenutni Solo Shuffle prikazuje pod usponom.
- **Preimenovani likovi se spajaju.** check-pvp nakon preimenovanja ili prebacivanja na drugi realm prikazuje isti lik dvaput. Ista klasa, ista frakcija i isti 2v2 i 3v3 vrh znače isti lik: zadržava se najnovije ime, a vrhovi su najbolji preko svih imena. Stara imena idu u `formerly` i ispisuju se u tablici.
- Rated Battleground se ne prikazuje po liku jer check-pvp na svakom liku vraća račun-razinski achievement (1800).

Klipovi u `public/clips/` su prekodirani za web (H.264, CRF 23, max 4.8 Mbps, `+faststart`) jer Cloudflare Pages ne prima datoteke veće od 25 MiB.

## `/beat/`

Četiri trake, jedna po osobi u grupi. `D` i `F` za lijeve dvije, `J` i `K` za desne.
Tipka se pritisne kad cast dođe do linije. Svaki cast u igri je pravi cast iz
dungeona i svaki je prekidljiv.

- Tri težine po pjesmi: normal, heroic, mythic.
- `Esc` pauza i izlaz, `R` restart, poseban ekran za kalibraciju odmaka.
- **Sat igre je `audio.currentTime`, ne `performance.now()`.** Nota pogađa kad je
  zvuk tu, a ne kad je sličica tu, inače se razilaze na dugoj pjesmi.
- Zvuk udarca ide kroz WebAudio buffer (`decodeAudioData` jednom, pa
  `createBufferSource` po udarcu), jer `<audio>` element za kratke zvukove kasni.
  Duga pjesma ostaje na `<audio>` elementu, zbog streaminga i skakanja po pjesmi.
- Opcija **calm** gasi treperenje, za one koji to ne žele ili ne mogu gledati.

Stanje u `localStorage`: `beat.name`, `beat.dung`, `beat.diff`, `beat.keys`,
`beat.keyset`, `beat.offset`, `beat.calm`, `beat.scores`, `beat.shyplus`.

### Kako se dodaje pjesma

Note **nisu** u zasebnoj datoteci u produkciji: `public/beat/index.html` je
**generiran**, a note su u njemu kao JS polja (`KR_N`, `KR_H`, `KR_M`, `CR_N`, ...).
Ne uređivati ga ručno za note.

```bash
# 1 · iz osu mape: bira najgušću težinu, dijeli na tri, izravna zvuk,
#     doda zapis u tools/dungeons.json
python tools/add_maps.py "<mapa s beatmap mapama>"

# 2 · ili jedna karta ručno
python tools/osu2chart.py <file.osu|file.osz|folder> [--diff "ime"] [--out chart.txt]

# 3 · pa ponovna gradnja stranice iz dungeons.json + tools/charts/
python tools/build_beat.py
```

**Note se čuvaju u sekundama, ne u taktovima.** Dio osu karata mijenja tempo
usred pjesme, pa jedna dužina takta ne opisuje cijelu pjesmu. Pozicija u taktu se
i dalje računa, ali samo da podjela po težinama zna razlikovati notu na taktu od
one između.

Ostali alati: `verify.py` (provjera chartova), `checkgrid.py`, `osu_difficulties.py`,
`inspect_map.py`, `extract.py`, `outdiff.py`, `migrate_seconds.py` (jednokratna
migracija iz taktova u sekunde), `add_favicon.py`, `classguard.py`,
`beat_template.html`.

## `/kick/` i `/raid/`

`/kick/` je ulaznica: traka se puni, pritisni `SPACE` prije nego se napuni. Pet
zaredom i pozvan si, dva promašaja i razgovor je gotov. Rezultat se ne šalje nikamo.

`/raid/` uči **oblike**, ne bossove: swirl, konus, krafna, soak, zraka, prsten koji
se širi, fixate. Bira se rola i svaka se ocjenjuje drugačije: damage po uptimeu
(svaki korak koji nisi morao napraviti je dio killa), tank po tome što ga slijedi,
heal po tome da nitko ne umre.

## `functions/api/`

| Ruta | Metoda | Što radi |
| --- | --- | --- |
| `/api/scores?g=<dungeon>` | GET | tri liste, po jednoj za svaku težinu |
| `/api/scores?board=total` | GET | zbirna lista kroz sve dungeone |
| `/api/scores` | POST | `{ g, d, n, s, a, c }`, vraća osvježenu listu |
| `/api/vault` | GET | knjiga gostiju, `{ book: [...] }` |
| `/api/vault` | POST | `{ n, l }` |

Zapis rezultata je `{ n: ime, s: score, a: točnost, c: combo, t: datum }`, drži se
25 po listi. Knjiga drži 80 zapisa. Dungeoni su fiksni popis u `scores.js`
(`kr, rlp, vsa, sd, disc, sd2, nok, fd, iffa, chea`), a najveći dopušteni score je
ograničen, da lista ne primi besmislicu.

Obje funkcije dijele isti store, samo pod različitim ključevima, pa nema potrebe
za drugim vezanjem.

## Zamke

| Zamka | Što s tim |
| --- | --- |
| Nema `.gitignore`, a `.git` je narastao na 87 MB | Sve mp3 datoteke su u povijesti. Za nove velike datoteke razmisliti o LFS-u ili o tome da audio ne ide u repozitorij |
| `tools/build_beat.py` ima apsolutni put (`ROOT = "C:/Users/krist/shaiyex"`) | Radi samo na ovom računalu. Na drugom prepisati u put izveden iz `__file__` |
| `public/beat/index.html` je generiran | Ručne izmjene nota se izgube pri sljedećem `build_beat.py`. Mijenjati `dungeons.json` i `tools/charts/` |
| Zvuk ne smije krenuti sam | Preglednici blokiraju autoplay. Svaka stranica sa zvukom čeka prvi klik. Ne "popravljati" to |
| `chrome.log` u korijenu | Ostatak otklanjanja greške, nema veze sa stranicom, može ići |
| Rute pod `/api/` lokalno vraćaju 503 | Očekivano bez `wrangler pages dev`. Stranice to podnose, pa ne treba zaobilaziti |
