/**
 * The character, actually standing there.
 *
 * Wowhead ships the renderer that draws every model on their site. This file
 * loads it, feeds it one character built out of char.json, and gets out of the
 * way. It is a small rewrite of the wow-model-viewer npm package
 * (github.com/Miorey/wow-model-viewer) rather than the package itself, because
 * that one hard codes which customisation options it is willing to pass and
 * this character has horns.
 *
 * Nothing runs on load. Call WMV.summon() when you actually want it, because
 * it pulls about a megabyte before the first frame.
 */
(function (global) {
  "use strict";

  /* /mv/ is our proxy at functions/mv/[[path]].js. Wowhead 403s anything with
     an Origin header on it, which is every fetch made from a page. */
  var BASE = "/mv/live/";

  var CHARACTER = 16; /* modelingType.CHARACTER */

  var loading = {};

  function script(src) {
    if (loading[src]) return loading[src];
    loading[src] = new Promise(function (ok, bad) {
      var s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = function () { ok(); };
      s.onerror = function () { bad(new Error("could not load " + src)); };
      document.head.appendChild(s);
    });
    return loading[src];
  }

  function json(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  /* the renderer expects a slice of Wowhead's own page globals to exist */
  function shim() {
    if (!global.CONTENT_PATH) global.CONTENT_PATH = BASE;
    if (global.WH && global.WH.Wow) return;

    global.WH = global.WH || {};
    global.WH.debug = function () {};
    global.WH.defaultAnimation = "Stand";
    global.WH.WebP = { getImageExtension: function () { return ".webp"; } };
    global.WH.Wow = {
      Item: {
        INVENTORY_TYPE_HEAD: 1, INVENTORY_TYPE_NECK: 2,
        INVENTORY_TYPE_SHOULDERS: 3, INVENTORY_TYPE_SHIRT: 4,
        INVENTORY_TYPE_CHEST: 5, INVENTORY_TYPE_WAIST: 6,
        INVENTORY_TYPE_LEGS: 7, INVENTORY_TYPE_FEET: 8,
        INVENTORY_TYPE_WRISTS: 9, INVENTORY_TYPE_HANDS: 10,
        INVENTORY_TYPE_FINGER: 11, INVENTORY_TYPE_TRINKET: 12,
        INVENTORY_TYPE_ONE_HAND: 13, INVENTORY_TYPE_SHIELD: 14,
        INVENTORY_TYPE_RANGED: 15, INVENTORY_TYPE_BACK: 16,
        INVENTORY_TYPE_TWO_HAND: 17, INVENTORY_TYPE_BAG: 18,
        INVENTORY_TYPE_TABARD: 19, INVENTORY_TYPE_ROBE: 20,
        INVENTORY_TYPE_MAIN_HAND: 21, INVENTORY_TYPE_OFF_HAND: 22,
        INVENTORY_TYPE_HELD_IN_OFF_HAND: 23, INVENTORY_TYPE_PROJECTILE: 24,
        INVENTORY_TYPE_THROWN: 25, INVENTORY_TYPE_RANGED_RIGHT: 26,
        INVENTORY_TYPE_QUIVER: 27, INVENTORY_TYPE_RELIC: 28,
        INVENTORY_TYPE_PROFESSION_TOOL: 29,
        INVENTORY_TYPE_PROFESSION_ACCESSORY: 30
      }
    };
  }

  /**
   * Every customisation the race has, with our choice where we made one and
   * the first choice where we did not. Passing the whole list means the model
   * is fully described and does not inherit whatever the renderer felt like.
   */
  function options(full, wanted) {
    var list = (full && full.Options) || [];
    var out = [];
    for (var i = 0; i < list.length; i++) {
      var opt = list[i];
      if (!opt.Choices || !opt.Choices.length) continue;
      var want = wanted[opt.Name];
      var pick = opt.Choices[typeof want === "number" ? want % opt.Choices.length : 0];
      if (pick) out.push({ optionId: opt.Id, choiceId: pick.Id });
    }
    return out;
  }

  /* the renderer's own object, reached past two layers of minified names */
  function actor(v) {
    try { return v.renderer.actors[0]; } catch (e) { return null; }
  }

  /**
   * The actor object turns up almost immediately and is useless until its
   * model has downloaded. Animations do not exist before isLoaded() is true,
   * and asking anyway throws out of the minified internals.
   */
  function ready(v, ms) {
    var until = Date.now() + (ms || 25000);
    return Promise.all(v.renderer.actorPromises || []).catch(function () {})
      .then(function () {
        return new Promise(function (ok) {
          (function look() {
            var a = actor(v);
            var done = false;
            try { done = !!(a && a.isLoaded()); } catch (e) { done = false; }
            if (done || Date.now() > until) return ok(a);
            setTimeout(look, 60);
          })();
        });
      });
  }

  function animations(v) {
    var a = actor(v);
    if (!a) return [];
    var names = [];
    try {
      var n = a.getNumAnimations();
      for (var i = 0; i < n; i++) {
        var name = a.getAnimation(i);
        if (typeof name === "string" && name) names.push(name);
      }
    } catch (e) {
      names = [];
    }
    return names.filter(function (n, i) { return names.indexOf(n) === i; });
  }

  function play(v, name) {
    var a = actor(v);
    if (!a) return false;
    try { a.setAnimation(name); return true; } catch (e) { return false; }
  }

  /**
   * @param opts.container  element or selector the model draws into
   * @param opts.char       url of char.json, or the object itself
   * @param opts.animation  what to play once it is up, default Dance
   */
  function summon(opts) {
    opts = opts || {};
    var box = typeof opts.container === "string"
      ? document.querySelector(opts.container)
      : opts.container;
    if (!box) return Promise.reject(new Error("no container"));

    shim();

    var wantAnim = opts.animation || "EmoteDance";
    global.WH.defaultAnimation = wantAnim;

    var char = typeof opts.char === "object"
      ? Promise.resolve(opts.char)
      : json(opts.char || "/model/char.json");

    return script("/model/jquery.js")
      .then(function () { return script(BASE + "viewer/viewer.min.js"); })
      .then(function () { return char; })
      .then(function (c) {
        var raceGender = c.race * 2 - 1 + c.gender;
        return json(BASE + "meta/charactercustomization/" + raceGender + ".json")
          .then(function (full) {
            return { c: c, full: full.data || full, raceGender: raceGender };
          });
      })
      .then(function (bits) {
        var c = bits.c;
        var r = box.getBoundingClientRect();
        var view = new global.ZamModelViewer({
          type: 2,
          contentPath: BASE,
          container: global.jQuery(box),
          aspect: Math.max(r.width, 1) / Math.max(r.height, 1),
          hd: true,
          items: c.items || [],
          models: { id: bits.raceGender, type: CHARACTER },
          charCustomization: { options: options(bits.full, c.options || {}) }
        });

        return ready(view).then(function () {
          var have = animations(view);
          var pick = have.length && have.indexOf(wantAnim) < 0
            ? (have.indexOf("Stand") > -1 ? "Stand" : have[0])
            : wantAnim;
          play(view, pick);

          view.wmv = {
            character: c,
            animations: have,
            play: function (n) { return play(view, n); },
            pause: function (on) {
              var a = actor(view);
              try { a.setAnimPaused(!!on); return true; } catch (e) { return false; }
            },
            distance: function (d) {
              try { view.renderer.distance = d; return true; } catch (e) { return false; }
            }
          };
          return view;
        });
      });
  }

  global.WMV = { summon: summon, base: BASE };
})(window);
