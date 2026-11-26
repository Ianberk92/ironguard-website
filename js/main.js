/* Ironguard IT — interactions
   Blueprint Section 6 rules: fast, run-once, reduced-motion aware,
   and nothing may delay a click, hide content, or shift layout. */

(function () {
  'use strict';

  /* ---------- Mobile navigation ---------- */
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav-mobile');

  if (toggle && menu) {
    var firstLink = menu.querySelector('a, button');

    function openMenu(fromKeyboard) {
      menu.classList.add('open');
      document.body.classList.add('menu-open'); // lock background scroll
      toggle.setAttribute('aria-expanded', 'true');
      // Keyboard users get focus moved into the menu; touch/mouse users don't
      // see a focus ring jump onto the first link.
      if (firstLink && fromKeyboard) firstLink.focus();
    }
    function closeMenu(returnFocus) {
      menu.classList.remove('open');
      document.body.classList.remove('menu-open');
      toggle.setAttribute('aria-expanded', 'false');
      if (returnFocus) toggle.focus();           // focus returns on close
    }

    toggle.addEventListener('click', function (e) {
      if (menu.classList.contains('open')) closeMenu(e.detail === 0);
      else openMenu(e.detail === 0);   // detail 0 = keyboard activation
    });

    // Close on Escape (keyboard accessible)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('open')) closeMenu(true);
    });

    // Close after choosing a destination
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) closeMenu(false);
    });
  }

  /* ---------- Dropdown menus (desktop) and grouped menu (phone) ----------
     Desktop: opens on hover, click/tap or keyboard; Escape and outside clicks close it.
     Phone: each group is a button that expands its links in place. */
  document.documentElement.classList.add('nav-js');
  var navItems = Array.prototype.slice.call(document.querySelectorAll('.nav-desktop .nav-item'));
  var hoverable = window.matchMedia && window.matchMedia('(hover: hover)').matches;

  function setOpen(item, open) {
    item.classList.toggle('open', open);
    var t = item.querySelector('.nav-trigger');
    if (t) t.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  function closeAll(except) { navItems.forEach(function (it) { if (it !== except) setOpen(it, false); }); }

  navItems.forEach(function (item) {
    var trigger = item.querySelector('.nav-trigger');
    var timer;
    trigger.addEventListener('click', function () {
      // A mouse click right after hover-open keeps the menu open instead of toggling it shut.
      var open = item.dataset.hover === '1' ? true : !item.classList.contains('open');
      item.dataset.hover = '';
      closeAll(item); setOpen(item, open);
    });
    if (hoverable) {
      item.addEventListener('mouseenter', function () { clearTimeout(timer); closeAll(item); item.dataset.hover = item.classList.contains('open') ? '' : '1'; setOpen(item, true); });
      item.addEventListener('mouseleave', function () { item.dataset.hover = ''; timer = setTimeout(function () { setOpen(item, false); }, 160); });
    }
    item.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && item.classList.contains('open')) { setOpen(item, false); trigger.focus(); }
      if (e.key === 'ArrowDown' && document.activeElement === trigger) {
        e.preventDefault(); setOpen(item, true);
        var first = item.querySelector('.nav-dd a'); if (first) first.focus();
      }
    });
    item.addEventListener('focusout', function (e) {
      if (!item.contains(e.relatedTarget)) setOpen(item, false);
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-item')) closeAll(null);
  });

  Array.prototype.forEach.call(document.querySelectorAll('.mnav-toggle'), function (btn) {
    btn.addEventListener('click', function () {
      var panel = document.getElementById(btn.getAttribute('aria-controls'));
      var open = btn.getAttribute('aria-expanded') !== 'true';
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (panel) panel.hidden = !open;
    });
  });

  /* ---------- Section reveal: 12px upward fade, runs once ---------- */
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealEls = document.querySelectorAll('.reveal');

  if (!reduced && 'IntersectionObserver' in window && revealEls.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target); // run once
        }
      });
    }, { threshold: 0.15 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    // Content is never hidden when motion is off or IO is unavailable
    revealEls.forEach(function (el) { el.classList.add('in'); });
  }

  /* ---------- Contact form: inline validation + clear confirmation ----------
     NOTE: The primary CTA destination (calendar, form handler, phone, or a
     routed combination) is an open item in the blueprint. Until that is
     decided, submission composes a pre-filled email to the Ironguard inbox
     so the inquiry path works without a backend. Swap the mailto for the
     real handler before launch. */
  var form = document.querySelector('#plan-form');
  if (form) {
    var INBOX = form.getAttribute('data-inbox') || 'contact@ironguardit.com';

    function fieldWrap(input) { return input.closest('.form-field'); }

    function validateField(input) {
      var wrap = fieldWrap(input);
      var ok = input.checkValidity();
      if (wrap) wrap.classList.toggle('invalid', !ok);
      return ok;
    }

    form.querySelectorAll('input, select, textarea').forEach(function (input) {
      input.addEventListener('change', function () { validateField(input); });
      input.addEventListener('blur', function () { validateField(input); });
      input.addEventListener('input', function () {
        if (fieldWrap(input) && fieldWrap(input).classList.contains('invalid')) {
          validateField(input);
        }
      });
    });

    var loadedAt = Date.now();

    /* ---------- Bot check (Cloudflare Turnstile) ----------
       The site is static, so the Power Automate address below is public, and
       the honeypot and timing checks only stop bots that use this page.
       Turnstile gives each real visitor a one-time token. The flow sends the
       token to Cloudflare to confirm it before any email goes out, so a request
       posted straight to the flow without a valid token is rejected there.
       TURNSTILE_SITEKEY is the public site key from the Cloudflare dashboard
       (never the secret key, which lives only in the flow). While it is empty
       the form works exactly as before: no widget, no token. */
    var TURNSTILE_SITEKEY = '';
    var ts = { requested: false, failed: false, token: '', askedOnce: false };

    function loadBotCheck() {
      if (!TURNSTILE_SITEKEY || ts.requested) return;
      ts.requested = true;
      var box = document.createElement('div');
      box.className = 'form-check';
      box.style.margin = '4px 0 18px';
      form.insertBefore(box, form.querySelector('button[type="submit"]'));
      window.igTurnstileReady = function () {
        try {
          window.turnstile.render(box, {
            sitekey: TURNSTILE_SITEKEY,
            action: 'contact',
            theme: 'dark',
            size: 'flexible',
            callback: function (token) { ts.token = token; },
            'expired-callback': function () { ts.token = ''; },
            'error-callback': function () { ts.token = ''; }
          });
        } catch (err) { ts.failed = true; }
      };
      var s = document.createElement('script');
      s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=igTurnstileReady';
      s.async = true;
      s.defer = true;
      s.onerror = function () { ts.failed = true; };
      document.head.appendChild(s);
    }

    /* Load the check when the form comes near the screen or gets focus, so the
       token is usually ready before the visitor presses send. */
    if ('IntersectionObserver' in window) {
      var tsObserver = new IntersectionObserver(function (entries) {
        if (entries.some(function (en) { return en.isIntersecting; })) {
          tsObserver.disconnect();
          loadBotCheck();
        }
      }, { rootMargin: '300px 0px' });
      tsObserver.observe(form);
    }
    form.addEventListener('focusin', loadBotCheck);

    /* Calls done(token) once a token exists, done('') when the check is off,
       or done(null) when there is no token after a short wait. */
    function withBotCheck(done) {
      if (!TURNSTILE_SITEKEY) { done(''); return; }
      loadBotCheck();
      var waited = 0;
      (function poll() {
        if (ts.token) { done(ts.token); return; }
        if (ts.failed || waited >= 5000) { done(null); return; }
        waited += 250;
        setTimeout(poll, 250);
      })();
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      /* Spam protection: hidden honeypot field + minimum-time gate.
         Bots that fill every field or submit instantly get a silent success. */
      var honeypot = form.querySelector('[name="website"]');
      var tooFast = (Date.now() - loadedAt) < 3000;
      var isSpam = (honeypot && honeypot.value !== '') || tooFast;

      var allValid = true;
      var firstInvalid = null;
      form.querySelectorAll('input:not([name="website"]), select, textarea').forEach(function (input) {
        if (!validateField(input)) {
          allValid = false;
          if (!firstInvalid) firstInvalid = input;
        }
      });

      if (!allValid) {
        if (firstInvalid) firstInvalid.focus();
        return;
      }

      var name = form.querySelector('#f-name').value.trim();
      var email = form.querySelector('#f-email').value.trim();
      var size = form.querySelector('#f-size') ? form.querySelector('#f-size').value : '';
      var driver = form.querySelector('#f-driver') ? form.querySelector('#f-driver').value : '';
      var details = form.querySelector('#f-details') ? form.querySelector('#f-details').value.trim() : '';
      /* Campaign landing pages mark what the visitor asked for (data-interest).
         It travels in the details text so the existing email flow needs no change. */
      var interest = form.getAttribute('data-interest') || '';
      if (interest) { details = '[Interest: ' + interest + '] ' + details; }
      /* Carry the first-touch source in the same text, so the inquiry email
         (and anything that reads it) knows which campaign produced the lead. */
      try {
        var src = JSON.parse(sessionStorage.getItem('ig_attr') || '{}');
        if (src.utm_source || src.utm_campaign) {
          details = '[Source: ' + (src.utm_source || '-') + ' / ' + (src.utm_medium || '-') + ' / ' + (src.utm_campaign || '-') + ' | landed on ' + (src.landing || '-') + '] ' + details;
        }
      } catch (e3) { /* attribution is best effort */ }

      /* Submission posts to a Power Automate flow that emails the inquiry.
         Spam (honeypot/too-fast) gets the same thank-you without a send.
         If the endpoint is unreachable, fall back to the mailto draft so
         no inquiry is ever silently dropped. */
      var ENDPOINT = 'https://default579ee38616f74687a68658259001b2.ee.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/07/workflows/35676cc09af445cc99e87d829a618ee4/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=VXwfeCbA_oX56ZxP-PLXvHfeexLxeQKATzv-wOsykPY';

      function showThanks(viaEmailDraft) {
        var prefix = document.querySelector('.article-body') ? '../' : '';
        form.innerHTML =
          '<h3 style="color: var(--white); font-family: var(--font-head); font-size: 22px; margin-bottom: 12px;">Got it' +
          (name ? ', ' + name.split(' ')[0] : '') + '.</h3>' +
          '<p style="color: #ccd3d9;">' + (viaEmailDraft
            ? 'Your email draft is open and ready to send. '
            : 'Your inquiry is in — ') +
          'A real person reads every inquiry — no sales queue, no drip campaign.</p>' +
          '<p style="margin-top: 16px;"><a class="btn btn-primary" href="https://bookings.cloud.microsoft/book/IronguardITFreeConsultation@Ironguardit.com/?ismsaljsauthenabled" target="_blank" rel="noopener">Pick a time now &mdash; schedule online</a></p>' +
          '<p style="margin-top: 12px;"><a href="' + prefix + 'thank-you.html" style="color: var(--trust-light);">What happens next &rarr;</a></p>';
        form.setAttribute('aria-live', 'polite');
      }

      function trackLead(method) {
        /* GA4 form_submit + Google Ads "Submit lead form" conversion.
           This is the ONLY place the Ads lead conversion is sent.
           Never called on the spam path — only real submissions count. */
        if (typeof window.gtag === 'function') {
          window.gtag('event', 'form_submit', { form_destination: method, page: location.pathname });
          /* Sent only while Google Ads is switched on in analytics.js. */
          if (window.IG_ADS_ENABLED) {
            window.gtag('event', 'conversion', {
              send_to: 'AW-18483507018/HXECCJbj-4odEMrez-1E',
              value: 1.0,
              currency: 'USD'
            });
          }
        }
      }

      function mailtoFallback() {
        trackLead('mailto_fallback');
        var subject = 'Ironguard inquiry — ' + (email.split('@')[1] || name);
        var body =
          'Name: ' + name + '\n' +
          'Work email: ' + email + '\n' +
          'Company size: ' + size + '\n' +
          (driver ? 'What is driving this: ' + driver + '\n' : '') +
          (details ? '\nWhat needs an owner:\n' + details + '\n' : '');
        window.location.href =
          'mailto:' + INBOX +
          '?subject=' + encodeURIComponent(subject) +
          '&body=' + encodeURIComponent(body);
        showThanks(true);
      }

      /* Tell HubSpot who this visitor is, so the inquiry is tied to their page
         history. Real submissions only; no-op if the HubSpot script is absent. */
      function identifyInHubSpot() {
        try {
          var attr = {};
          try { attr = JSON.parse(sessionStorage.getItem('ig_attr') || '{}'); } catch (e2) {}
          var _hsq = window._hsq = window._hsq || [];
          _hsq.push(['identify', {
            email: email,
            firstname: name.split(' ')[0] || '',
            lastname: name.split(' ').slice(1).join(' '),
            company_size: size,
            inquiry_driver: driver,
            service_interest: interest,
            conversion_page: location.pathname,
            first_touch_source: attr.utm_source || '',
            first_touch_medium: attr.utm_medium || '',
            first_touch_campaign: attr.utm_campaign || '',
            first_touch_landing_page: attr.landing || ''
          }]);
          _hsq.push(['trackPageView']);
        } catch (e) { /* best effort */ }
      }

      if (isSpam) { showThanks(false); return; }

      var sendBtn = form.querySelector('button[type="submit"]');
      var statusEl = form.querySelector('.form-status');
      if (sendBtn) sendBtn.disabled = true;

      withBotCheck(function (token) {
        if (token === null) {
          /* No token yet. If the check loaded but is still waiting on the
             visitor, ask once. If it could not load (blocked, offline) or is
             still missing on the second try, open the email draft instead,
             so no inquiry is ever lost. */
          if (!ts.failed && !ts.askedOnce) {
            ts.askedOnce = true;
            if (sendBtn) sendBtn.disabled = false;
            if (statusEl) {
              statusEl.textContent = 'One quick check: finish the security box above the button, then press it again.';
              statusEl.focus();
            }
            return;
          }
          identifyInHubSpot();
          mailtoFallback();
          return;
        }

        identifyInHubSpot();

        /* The flow rejects anything without a valid token, a filled honeypot
           or out-of-range fields, and answers with an error. Any error here
           opens the email draft, so a real visitor still reaches us. */
        fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name, email: email, size: size,
            driver: driver, details: details, page: location.pathname,
            attribution: (function () {
              try { return JSON.parse(sessionStorage.getItem('ig_attr') || '{}'); }
              catch (e) { return {}; }
            })(),
            turnstileToken: token,
            website: honeypot ? honeypot.value : ''
          })
        }).then(function (res) {
          if (res.ok) { trackLead('power_automate'); showThanks(false); } else { mailtoFallback(); }
        }).catch(function () { mailtoFallback(); });
      });
    });
  }

  /* ---------- First-touch attribution (for CRM lead records) ---------- */
  try {
    if (!sessionStorage.getItem('ig_attr')) {
      var q = new URLSearchParams(location.search);
      var attr = {
        utm_source: q.get('utm_source') || '',
        utm_medium: q.get('utm_medium') || '',
        utm_campaign: q.get('utm_campaign') || '',
        utm_term: q.get('utm_term') || '',
        gclid: q.get('gclid') || '',
        referrer: document.referrer || '',
        landing: location.pathname
      };
      sessionStorage.setItem('ig_attr', JSON.stringify(attr));
    }
  } catch (e) { /* storage blocked: attribution is best-effort */ }

  /* ---------- Footer year ---------- */
  var yearEl = document.querySelector('#year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());
})();
