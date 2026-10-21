/* Ironguard IT — v3 interactions: header state, counters, hero parallax.
   Nav/menu, reveal, and the contact form live in main.js. */
(function () {
  'use strict';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Header: transparent over the hero, solid once scrolled */
  var header = document.querySelector('.site-header');
  function onScroll() { if (header) header.classList.toggle('scrolled', window.scrollY > 24); }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('load', onScroll);
  window.addEventListener('hashchange', function () { setTimeout(onScroll, 50); });
  setTimeout(onScroll, 300);

  /* Hero parallax: glows and cards drift with the pointer (desktop only) */
  var hero = document.querySelector('.hero');
  if (hero && !reduced && window.matchMedia('(pointer: fine)').matches) {
    var glows = hero.querySelectorAll('.glow');
    var cards = hero.querySelectorAll('.card-glass');
    hero.addEventListener('mousemove', function (e) {
      var r = hero.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5;
      var y = (e.clientY - r.top) / r.height - 0.5;
      glows.forEach(function (g, i) { g.style.transform = 'translate(' + (x * (i ? -40 : 30)) + 'px,' + (y * (i ? -30 : 24)) + 'px)'; });
      cards.forEach(function (c, i) { c.style.marginLeft = (x * (8 + i * 4)) + 'px'; c.style.marginTop = (y * (6 + i * 3)) + 'px'; });
    });
  }
})();

/* Scorecard preview: live score for the three homepage questions.
   Scoring mirrors scorecard.html (0/1/2 per question). */
(function () {
  var box = document.getElementById('sc-preview');
  if (!box) return;
  var pts = document.getElementById('sc-pts'), fill = document.getElementById('sc-fill'), msg = document.getElementById('sc-msg');
  var MSG = {
    6: '<strong>Strong start.</strong> See whether the other nine hold up.',
    5: '<strong>Mostly owned.</strong> One gap already showing; the full Scorecard pinpoints the rest.',
    4: '<strong>Real gaps.</strong> Each low answer is where the next incident starts.',
    3: '<strong>Ownership is unclear.</strong> Finish the Scorecard to see which areas need a named owner.',
    2: '<strong>Nobody clearly owns this.</strong> The full Scorecard maps every gap in two minutes.',
    1: '<strong>Nobody clearly owns this.</strong> The full Scorecard maps every gap in two minutes.',
    0: '<strong>Nobody clearly owns this.</strong> The full Scorecard maps every gap in two minutes.'
  };
  box.addEventListener('change', function () {
    var groups = ['p0', 'p1', 'p2'], total = 0, answered = 0;
    groups.forEach(function (g) {
      var c = box.querySelector('input[name="' + g + '"]:checked');
      if (c) { answered++; total += +c.value; }
    });
    pts.textContent = total;
    fill.style.width = (total / 6 * 100) + '%';
    if (answered === 3) {
      msg.innerHTML = MSG[total];
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ event: 'scorecard_preview_complete', score: total });
    } else {
      msg.textContent = (3 - answered) + (answered === 2 ? ' question left.' : ' questions left.');
    }
  });
})();

/* Pricing estimator: headcount × published range ($150–$200 per user). */
(function () {
  var r = document.getElementById('est-users'); if (!r) return;
  var out = document.getElementById('est-users-out'), range = document.getElementById('est-range');
  function fmt(n) { return '$' + n.toLocaleString('en-US'); }
  function update() {
    var n = +r.value;
    out.textContent = n === 300 ? '300+' : n;
    range.innerHTML = fmt(n * 150) + ' &ndash; ' + fmt(n * 200);
  }
  r.addEventListener('input', update); update();
})();

/* Reveal safety net: content must never stay hidden. Anchor jumps and
   in-page links show everything immediately; a timer covers any observer miss. */
(function () {
  function showAll() { document.querySelectorAll('.reveal:not(.in)').forEach(function (el) { el.classList.add('in'); }); }
  if (location.hash) showAll();
  window.addEventListener('hashchange', showAll);
  document.addEventListener('click', function (e) { var a = e.target.closest('a[href^="#"]'); if (a) showAll(); });
  setTimeout(showAll, 2500);
})();
