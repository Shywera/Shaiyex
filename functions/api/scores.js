/**
 * Live leaderboard for /beat/.
 *
 * Runs on Cloudflare Pages Functions. Needs one store bound to the Pages
 * project under the name SCORES. Workers KV is the right choice, an R2
 * bucket also works. Until that binding exists this returns 503 and the
 * page quietly falls back to local best scores.
 *
 *   GET  /api/scores?g=kr        -> { normal: [...], heroic: [...], mythic: [...] }
 *   GET  /api/scores?board=total -> { hall: [...], boards: n, at: iso }
 *   POST /api/scores             -> { ok: true, board: [...] }
 *        body { g, d, n, s, a, c }
 *
 * An entry is { n: name, s: score, a: accuracy, c: combo, t: date }
 */

const DUNGEONS = ["kr", "rlp", "vsa", "sd", "disc", "sd2", "nok", "fd", "iffa", "chea"];
const DIFFS = ["normal", "heroic", "mythic"];
const KEEP = 25;
const MAX_SCORE = 5000000;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

const key = (g, d) => `board:${g}|${d}`;

/**
 * Works with either store, so it does not matter which you bind as SCORES:
 *   Workers KV  get() hands back a string
 *   R2          get() hands back an object you read with .text()
 * put() takes a string on both, so writing needs no special case.
 */
async function board(store, g, d) {
  const v = await store.get(key(g, d));
  if (v == null) return [];
  let raw = v;
  if (typeof v !== "string") {
    if (typeof v.text === "function") raw = await v.text();
    else return [];
  }
  try {
    const list = JSON.parse(raw);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function cleanName(v) {
  const s = String(v == null ? "" : v)
    .replace(/[\x00-\x1f\x7f]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 14);
  return s || "Anonymous";
}

function num(v, max) {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  const i = Math.floor(n);
  return i >= 0 && i <= max ? i : null;
}

/**
 * Everyone's total across the whole site: their best on each dungeon at
 * each difficulty, added up. A name that has only run one key is on the
 * same table as someone who has run all thirty, which is the point.
 */
async function hall(store) {
  const lists = await Promise.all(
    DUNGEONS.map((g) => DIFFS.map((d) => board(store, g, d))).flat()
  );

  const by = new Map();
  for (const list of lists) {
    for (const e of list) {
      const id = e.n.toLowerCase();
      let row = by.get(id);
      if (!row) {
        row = { n: e.n, s: 0, runs: 0, best: 0, acc: 0 };
        by.set(id, row);
      }
      row.s += e.s;
      row.runs += 1;
      row.acc += e.a;
      if (e.s > row.best) {
        row.best = e.s;
        row.n = e.n; // however they spelled it on their best run
      }
    }
  }

  const rows = [...by.values()].map((r) => ({
    n: r.n,
    s: r.s,
    runs: r.runs,
    acc: r.runs ? Math.round(r.acc / r.runs) : 0,
  }));
  rows.sort((x, y) => y.s - x.s || y.runs - x.runs);
  return rows.slice(0, KEEP);
}

export async function onRequestGet({ request, env }) {
  if (!env.SCORES) return json({ error: "no store" }, 503);
  const q = new URL(request.url).searchParams;

  if (q.get("board") === "total") {
    return json({
      hall: await hall(env.SCORES),
      boards: DUNGEONS.length * DIFFS.length,
      at: new Date().toISOString(),
    });
  }

  const g = q.get("g");
  if (!DUNGEONS.includes(g)) return json({ error: "bad dungeon" }, 400);

  const out = {};
  await Promise.all(
    DIFFS.map(async (d) => {
      out[d] = await board(env.SCORES, g, d);
    })
  );
  return json(out);
}

export async function onRequestPost({ request, env }) {
  if (!env.SCORES) return json({ error: "no store" }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "bad body" }, 400);
  }

  const g = body.g;
  const d = body.d;
  if (!DUNGEONS.includes(g)) return json({ error: "bad dungeon" }, 400);
  if (!DIFFS.includes(d)) return json({ error: "bad difficulty" }, 400);

  const s = num(body.s, MAX_SCORE);
  const a = num(body.a, 100);
  const c = num(body.c, 20000);
  if (s === null || a === null || c === null) return json({ error: "bad numbers" }, 400);

  const entry = {
    n: cleanName(body.n),
    s,
    a,
    c,
    t: new Date().toISOString().slice(0, 10),
  };

  const list = await board(env.SCORES, g, d);

  // one row per name, keep their best
  const i = list.findIndex((e) => e.n.toLowerCase() === entry.n.toLowerCase());
  if (i >= 0) {
    if (list[i].s >= entry.s) {
      return json({ ok: true, board: list, kept: true });
    }
    list[i] = entry;
  } else {
    list.push(entry);
  }

  list.sort((x, y) => y.s - x.s);
  const trimmed = list.slice(0, KEEP);

  await env.SCORES.put(key(g, d), JSON.stringify(trimmed));
  return json({ ok: true, board: trimmed });
}
