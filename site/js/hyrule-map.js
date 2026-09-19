/* =============================================================================
 * Carte interactive d'Hyrule — Ocarina Nexus
 *
 * Le composant se monte sur <div class="hymap" id="hyruleMap"> et construit
 * lui-même sa barre d'époque, ses repères et son incrustation 3D. Deux fichiers
 * l'alimentent :
 *   - data/locations.json            (repères, époques, scènes noclip)
 *   - assets/img/hyrule/hyrule-map.svg (fond, injecté en ligne pour que le CSS
 *     puisse masquer les calques .era-child / .era-adult)
 *
 * Les scènes 3D viennent de noclip.website, en mode intégré :
 *   https://noclip.website/embed.html#<groupe>/<scène>
 *   groupe `zelview` = version Nintendo 64, `oot3d` = version 3DS.
 * L'iframe est détruite à la fermeture : sans ça, chaque ouverture laisse un
 * contexte WebGL vivant et le navigateur finit par refuser d'en créer un autre.
 * ========================================================================== */
(function () {
  'use strict';

  var ERAS = { child: 'Enfant', adult: 'Adulte' };
  var DUNGEONS = /temple|caverne|arbre mojo|ventre|puits/i;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function mount(root) {
    var dataUrl = root.dataset.src || 'data/locations.json';
    var cfg = null;
    var locations = [];
    var era = root.dataset.era || 'child';
    var visible = [];
    var current = -1;
    var platform = 'n64';

    /* ---------------------------------------------------------------- vue */
    var bar = el('div', 'hymap-bar');
    var eras = el('div', 'hymap-eras');
    eras.setAttribute('role', 'tablist');
    eras.setAttribute('aria-label', "Époque de la carte");
    var eraButtons = {};
    Object.keys(ERAS).forEach(function (key) {
      var b = el('button', null, ERAS[key]);
      b.type = 'button';
      b.setAttribute('role', 'tab');
      b.addEventListener('click', function () { setEra(key); });
      eraButtons[key] = b;
      eras.appendChild(b);
    });
    var count = el('p', 'hymap-count');
    bar.appendChild(eras);
    bar.appendChild(count);

    var surface = el('div', 'hymap-surface is-loading');
    var pins = el('div', 'hymap-pins');
    surface.appendChild(pins);

    var note = el('p', 'hymap-note');
    note.innerHTML = 'Un repère = une ligne de <code>gold.dim_location</code>. ' +
      'Les scènes 3D sont servies par <a href="https://noclip.website" rel="noopener" ' +
      'target="_blank">noclip.website</a> — déplacement ZQSD/WASD, souris pour regarder, ' +
      'Maj pour accélérer.';

    root.appendChild(bar);
    root.appendChild(surface);
    root.appendChild(note);

    /* -------------------------------------------------------- incrustation */
    var view = el('div', 'hyview');
    view.hidden = true;
    var scrim = el('div', 'hyview-scrim');
    var panel = el('div', 'hyview-panel');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');

    var close = el('button', 'hyview-close', '\u00d7');
    close.type = 'button';
    close.setAttribute('aria-label', 'Fermer');

    var stage = el('div', 'hyview-stage');
    var frame = el('div', 'hyview-frame');
    var stagebar = el('div', 'hyview-stagebar');
    var tabs = el('div', 'hyview-tabs');
    var tools = el('div', 'hyview-tools');
    var fs = el('button', null, 'Plein écran');
    fs.type = 'button';
    var out = el('a', null, 'Ouvrir sur noclip');
    out.target = '_blank';
    out.rel = 'noopener';
    tools.appendChild(fs);
    tools.appendChild(out);
    stagebar.appendChild(tabs);
    stagebar.appendChild(tools);
    var hint = el('p', 'hyview-hint',
      'Clic dans la vue pour prendre la main, Échap pour la rendre. La scène pèse ' +
      'plusieurs dizaines de méga-octets : le premier chargement prend un moment.');
    stage.appendChild(frame);
    stage.appendChild(stagebar);
    stage.appendChild(hint);

    var doc = el('div', 'hyview-doc');
    var region = el('p', 'hyview-region');
    var title = el('h3');
    title.id = 'hyviewTitle';
    panel.setAttribute('aria-labelledby', 'hyviewTitle');
    var summary = el('p', 'hyview-summary');
    var meta = el('dl', 'hyview-meta');
    var nav = el('div', 'hyview-nav');
    var prev = el('button', null, '\u2039  Lieu précédent');
    var next = el('button', null, 'Lieu suivant  \u203a');
    prev.type = next.type = 'button';
    nav.appendChild(prev);
    nav.appendChild(next);
    doc.appendChild(region);
    doc.appendChild(title);
    doc.appendChild(summary);
    doc.appendChild(meta);
    doc.appendChild(nav);

    panel.appendChild(close);
    panel.appendChild(stage);
    panel.appendChild(doc);
    view.appendChild(scrim);
    view.appendChild(panel);
    document.body.appendChild(view);

    /* -------------------------------------------------------------- rendu */
    function setEra(key) {
      era = key;
      root.dataset.era = key;
      Object.keys(eraButtons).forEach(function (k) {
        eraButtons[k].setAttribute('aria-selected', String(k === key));
      });
      renderPins();
      if (!view.hidden && current >= 0) open(current);
    }

    function renderPins() {
      pins.innerHTML = '';
      visible = locations.filter(function (l) { return l.era.indexOf(era) !== -1; });
      visible.forEach(function (loc, i) {
        var b = el('button', 'hymap-pin');
        b.type = 'button';
        b.style.left = loc.x + '%';
        b.style.top = loc.y + '%';
        b.dataset.kind = DUNGEONS.test(loc.name) ? 'dungeon' : 'place';
        if (loc.x > 74) b.dataset.side = 'left';
        else if (loc.x < 24) b.dataset.side = 'right';
        b.setAttribute('aria-label', loc.name + ' — ouvrir la fiche');
        b.appendChild(el('span', 'hymap-dot'));
        b.appendChild(el('span', 'hymap-tip', loc.name));
        b.addEventListener('click', function () { open(i); });
        pins.appendChild(b);
      });
      count.textContent = visible.length + ' lieux visitables à l\u2019âge ' +
        ERAS[era].toLowerCase();
    }

    function scenesFor(loc) {
      var own = loc.scenes && loc.scenes[era];
      if (own && Object.keys(own).length) return { set: own, borrowed: null };
      var other = era === 'child' ? 'adult' : 'child';
      var alt = loc.scenes && loc.scenes[other];
      if (alt && Object.keys(alt).length) return { set: alt, borrowed: other };
      return { set: null, borrowed: null };
    }

    function load(sceneId) {
      frame.innerHTML = '';
      frame.classList.add('is-loading');
      var url = (cfg.noclip.base || 'https://noclip.website') + '/embed.html#' + sceneId;
      var f = document.createElement('iframe');
      f.src = url;
      f.title = 'Scène 3D — ' + sceneId;
      f.allow = 'fullscreen; xr-spatial-tracking; gamepad';
      f.addEventListener('load', function () { frame.classList.remove('is-loading'); });
      frame.appendChild(f);
      out.href = (cfg.noclip.base || 'https://noclip.website') + '/#' + sceneId;
    }

    function unload() {
      frame.innerHTML = '';
      frame.classList.remove('is-loading');
    }

    function open(i) {
      current = ((i % visible.length) + visible.length) % visible.length;
      var loc = visible[current];
      var found = scenesFor(loc);

      region.textContent = loc.region;
      title.textContent = loc.name;
      summary.textContent = loc.summary;

      meta.innerHTML = '';
      [['Identifiant', loc.entity_id],
       ['Époques', loc.era.map(function (e) { return ERAS[e]; }).join(' · ')],
       ['Scène', found.set ? Object.values(found.set)[0].split('/')[1] : '—']
      ].forEach(function (row) {
        var wrap = el('div');
        wrap.appendChild(el('dt', null, row[0]));
        wrap.appendChild(el('dd', null, row[1]));
        meta.appendChild(wrap);
      });

      tabs.innerHTML = '';
      unload();
      if (!found.set) {
        frame.innerHTML = '';
        frame.appendChild(el('p', 'hyview-empty',
          'Aucune scène 3D disponible pour ce lieu sur noclip.website.'));
        out.removeAttribute('href');
        stagebar.hidden = true;
        hint.hidden = true;
      } else {
        stagebar.hidden = false;
        hint.hidden = false;
        var keys = Object.keys(found.set);
        if (keys.indexOf(platform) === -1) platform = keys[0];
        keys.forEach(function (key) {
          var t = el('button', null, cfg.noclip.groups[key] || key);
          t.type = 'button';
          t.setAttribute('aria-selected', String(key === platform));
          t.addEventListener('click', function () {
            platform = key;
            Array.prototype.forEach.call(tabs.children, function (c) {
              c.setAttribute('aria-selected', String(c === t));
            });
            load(found.set[key]);
          });
          tabs.appendChild(t);
        });
        load(found.set[platform]);
      }

      if (found.borrowed) {
        var warn = el('div');
        warn.appendChild(el('dt', null, 'Note'));
        warn.appendChild(el('dd', null, 'scène ' + ERAS[found.borrowed].toLowerCase()));
        meta.appendChild(warn);
      }

      view.hidden = false;
      document.body.style.overflow = 'hidden';
      close.focus();
    }

    function shut() {
      view.hidden = true;
      unload();
      document.body.style.overflow = '';
      var pin = pins.children[current];
      if (pin) pin.focus();
    }

    close.addEventListener('click', shut);
    scrim.addEventListener('click', shut);
    prev.addEventListener('click', function () { open(current - 1); });
    next.addEventListener('click', function () { open(current + 1); });
    fs.addEventListener('click', function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (frame.requestFullscreen) frame.requestFullscreen();
    });
    document.addEventListener('keydown', function (e) {
      if (view.hidden) return;
      if (e.key === 'Escape' && !document.fullscreenElement) shut();
      if (e.key === 'ArrowRight') open(current + 1);
      if (e.key === 'ArrowLeft') open(current - 1);
    });

    /* ------------------------------------------------------------ données */
    fetch(dataUrl)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + ' sur ' + dataUrl);
        return r.json();
      })
      .then(function (data) {
        cfg = data;
        locations = data.locations || [];
        return fetch(data.map.src);
      })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + ' sur le fond de carte');
        return r.text();
      })
      .then(function (svg) {
        surface.classList.remove('is-loading');
        surface.insertAdjacentHTML('afterbegin', svg);
        setEra(era);
      })
      .catch(function (err) {
        surface.classList.remove('is-loading');
        surface.appendChild(el('p', 'hyview-empty',
          'La carte n\u2019a pas pu être chargée (' + err.message + '). ' +
          'Servez le dossier site/ via un serveur HTTP : les requêtes fetch sont ' +
          'bloquées sur file://.'));
      });
  }

  function boot() {
    Array.prototype.forEach.call(document.querySelectorAll('.hymap'), mount);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
