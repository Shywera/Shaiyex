/**
 * The book in the back room.
 *
 * Same store as the leaderboard, different keys, so it needs no new
 * binding: SCORES is bound to the Pages project already. Until that
 * binding exists this returns 503 and the page says the book is shut.
 *
 *   GET  /api/vault  -> { book: [...] }
 *   POST /api/vault  -> { ok: true, book: [...] }
 *        body { n, l }
 *
 * An entry is { n: name, l: line, t: date }.
 */

const KEY = "vault:book";
const KEEP = 80;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });

/** works with either store, the same way the leaderboard does */
async function read(store) {
  const v = await store.get(KEY);
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

function clean(v, max) {
  return String(v == null ? "" : v)
    .replace(/[\x00-\x1f\x7f]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}

export async function onRequestGet({ env }) {
  if (!env.SCORES) return json({ error: "no store" }, 503);
  return json({ book: await read(env.SCORES) });
}

export async function onRequestPost({ request, env }) {
  if (!env.SCORES) return json({ error: "no store" }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "bad body" }, 400);
  }

  const n = clean(body.n, 16);
  const l = clean(body.l, 140);
  if (!n) return json({ error: "no name" }, 400);
  if (!l) return json({ error: "no line" }, 400);

  const book = await read(env.SCORES);

  /* one line per name. signing again replaces what you wrote rather
     than filling the page with the same person. */
  const i = book.findIndex((e) => e.n.toLowerCase() === n.toLowerCase());
  const entry = { n, l, t: new Date().toISOString().slice(0, 10) };
  if (i >= 0) book[i] = entry;
  else book.unshift(entry);

  const trimmed = book.slice(0, KEEP);
  await env.SCORES.put(KEY, JSON.stringify(trimmed));
  return json({ ok: true, book: trimmed });
}
