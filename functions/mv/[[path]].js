/**
 * A hole in Wowhead's wall, exactly the size of one character.
 *
 * wow.zamimg.com serves the model viewer and its data happily to a plain
 * request and returns 403 the moment a browser attaches an Origin header,
 * which is every fetch the viewer makes from our page. So the page asks us
 * instead: /mv/live/... comes here, we ask for it without an Origin, and hand
 * it back same-origin. The upstream prefix is fixed, so this cannot be pointed
 * at anything but the model viewer tree.
 *
 *   /mv/live/viewer/viewer.min.js
 *   /mv/live/meta/charactercustomization/60.json
 *   /mv/live/meta/armor/1/743286.json
 *   /mv/live/textures/...
 *
 * The data belongs to Wowhead. This is one character on one personal page.
 */

const UPSTREAM = "https://wow.zamimg.com/modelviewer/";

/* the viewer only ever asks for paths that look like this */
const SANE = /^[A-Za-z0-9][A-Za-z0-9._-]*(\/[A-Za-z0-9][A-Za-z0-9._-]*)*$/;

/* a month in the browser, and let the edge hold it too */
const TTL = 2592000;

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

/* everything worth passing on. no set-cookie, no origin echo. */
const KEEP = [
  "content-type",
  "content-length",
  "content-range",
  "accept-ranges",
  "etag",
  "last-modified",
];

const no = (status, why) =>
  new Response(why + "\n", {
    status,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });

export async function onRequest({ request, params }) {
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET, HEAD, OPTIONS",
        "access-control-max-age": "86400",
      },
    });
  }
  if (request.method !== "GET" && request.method !== "HEAD") {
    return no(405, "get and head only");
  }

  const parts = [].concat(params.path || []);
  const path = parts.join("/");
  if (!path || path.includes("..") || !SANE.test(path)) {
    return no(400, "not a model path");
  }

  const search = new URL(request.url).search;
  const target = UPSTREAM + path + search;

  const send = { "user-agent": UA, accept: "*/*" };
  const range = request.headers.get("range");
  if (range) send.range = range;

  let up;
  try {
    up = await fetch(target, {
      method: request.method,
      headers: send,
      redirect: "follow",
      cf: { cacheEverything: true, cacheTtl: TTL },
    });
  } catch {
    return no(502, "wowhead did not answer");
  }

  const out = new Headers();
  for (const h of KEEP) {
    const v = up.headers.get(h);
    if (v) out.set(h, v);
  }
  out.set("access-control-allow-origin", "*");
  out.set("x-content-type-options", "nosniff");
  out.set(
    "cache-control",
    up.ok ? `public, max-age=${TTL}, immutable` : "public, max-age=300"
  );

  return new Response(request.method === "HEAD" ? null : up.body, {
    status: up.status,
    headers: out,
  });
}
