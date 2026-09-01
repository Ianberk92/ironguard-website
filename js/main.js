/* Ironguard IT — interactions
   Blueprint Section 6 rules: fast, run-once, reduced-motion aware,
   and nothing may delay a click, hide content, or shift layout. */

(function () {
  'use strict';

  /* ---------- Mobile navigation ---------- */
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav-mobile');

  if (toggle && menu) {
    var firstLink = menu.querySelector('a');

    function openMenu() {
      menu.classList.add('open');
      document.body.classList.add('menu-open'); // lock background scroll
      toggle.setAttribute('aria-expanded', 'true');
      if (firstLink) firstLink.focus();          // focus moves into menu
    }
    function closeMenu(returnFocus) {
      menu.classList.remove('open');
      document.body.classList.remove('menu-open');
      toggle.setAttribute('aria-expanded', 'false');
      if (returnFocus) toggle.focus();           // focus returns on close
    }

    toggle.addEventListener('click', function () {
      if (menu.classList.contains('open')) closeMenu(true);
      else openMenu();
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
    var INBOX = form.getAttribute('data-inbox') || 'sales@ironguardit.com';

    function fieldWrap(input) { return input.closest('.form-field'); }

    function validateField(input) {
      var wrap = fieldWrap(input);
      var ok = input.checkValidity();
      if (wrap) wrap.classList.toggle('invalid', !ok);
      return ok;
    }

    form.querySelectorAll('input, textarea').forEach(function (input) {
      input.addEventListener('blur', function () { validateField(input); });
      input.addEventListener('input', function () {
        if (fieldWrap(input) && fieldWrap(input).classList.contains('invalid')) {
          validateField(input);
        }
      });
    });

    var loadedAt = Date.now();

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      /* Spam protection: hidden honeypot field + minimum-time gate.
         Bots that fill every field or submit instantly get a silent success. */
      var honeypot = form.querySelector('[name="website"]');
      var tooFast = (Date.now() - loadedAt) < 3000;
      var isSpam = (honeypot && honeypot.value !== '') || tooFast;

      var allValid = true;
      var firstInvalid = null;
      form.querySelectorAll('input:not([name="website"]), textarea').forEach(function (input) {
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

      if (!isSpam) {
        var subject = 'IT Ownership Review request — ' + (email.split('@')[1] || name);
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
      }

      /* Inline thank-you experience replaces the form */
      var prefix = document.querySelector('.article-body') ? '../' : '';
      form.innerHTML =
        '<h3 style="color: var(--white); font-family: var(--font-head); font-size: 22px; margin-bottom: 12px;">Got it' +
        (name ? ', ' + name.split(' ')[0] : '') + '.</h3>' +
        '<p style="color: #ccd3d9;">Your email draft is open and ready to send. A real person reads every inquiry — no sales queue, no drip campaign.</p>' +
        '<p style="margin-top: 16px;"><a class="btn btn-primary" href="https://outlook.office.com/book/IronguardITSupport@Ironguardit.com/?ismsaljsauthenabled" target="_blank" rel="noopener">Pick a time now &mdash; schedule online</a></p>' +
        '<p style="margin-top: 12px;"><a href="' + prefix + 'thank-you.html" style="color: var(--trust-light);">What happens next &rarr;</a></p>';
      form.setAttribute('aria-live', 'polite');
    });
  }

  /* ---------- Footer year ---------- */
  var yearEl = document.querySelector('#year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());
})();
