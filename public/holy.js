/* The light side runs one track across the whole site. The position lives in
   sessionStorage, so moving between pages picks up where the last one stopped
   rather than starting the fade in again. The dark side handles its own music
   on the front page, so this bows out entirely when the theme is on. */
(function () {
  var SRC = '/tirion.mp3';
  var KEY = 'shy.holy.t';
  var VOL = 0.34;

  var dark = false;
  try { dark = localStorage.getItem('shy.tekk') === '1'; } catch (e) {}
  if (dark) return;

  var a = document.getElementById('holyAudio');
  if (!a) {
    a = document.createElement('audio');
    a.id = 'holyAudio';
    a.src = SRC;
    a.loop = true;
    a.preload = 'auto';
    a.style.display = 'none';
    document.body.appendChild(a);
  }
  a.volume = VOL;

  var at = 0;
  try { at = parseFloat(sessionStorage.getItem(KEY) || '0') || 0; } catch (e) {}
  if (at > 0) {
    var seek = function () { try { a.currentTime = at; } catch (e) {} };
    if (a.readyState > 0) seek();
    else a.addEventListener('loadedmetadata', seek, { once: true });
  }

  function go() {
    var p = a.play();
    if (p && p['catch']) p['catch'](function () {});
  }
  go();

  /* browsers will not always take the first attempt, so the next click or
     keypress on the page gets one more go */
  var once = function () {
    go();
    window.removeEventListener('pointerdown', once);
    window.removeEventListener('keydown', once);
  };
  window.addEventListener('pointerdown', once);
  window.addEventListener('keydown', once);

  function save() {
    try { sessionStorage.setItem(KEY, a.currentTime.toFixed(2)); } catch (e) {}
  }
  var last = 0;
  a.addEventListener('timeupdate', function () {
    var now = Date.now();
    if (now - last < 900) return;
    last = now;
    save();
  });
  window.addEventListener('pagehide', save);
  window.addEventListener('beforeunload', save);
})();
