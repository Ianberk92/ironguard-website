/* Ironguard IT — conversion event stub.
   Pushes events into window.dataLayer so a tag manager or GA4 gtag snippet can
   consume them the day one is added. Collects no personal information —
   only which controls were used, on which page (blueprint: track CTA clicks,
   form starts, form submissions, and phone/email clicks; nothing sensitive). */

(function () {
  'use strict';

  window.dataLayer = window.dataLayer || [];

  function track(event, params) {
    var payload = Object.assign({ page: location.pathname }, params || {});
    /* gtag (GA4) is the live pipeline; the dataLayer object push remains for a
       future tag manager. Both fire so neither integration starves the other. */
    if (typeof window.gtag === 'function') {
      window.gtag('event', event, payload);
    }
    window.dataLayer.push(Object.assign({ event: event }, payload));
  }

  // CTA, mailto, and tel clicks
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (href.indexOf('outlook.office.com/book') !== -1 || href.indexOf('bookings.cloud.microsoft') !== -1) {
      /* The booking scheduler is the primary conversion — tracked separately
         so GA4 can treat it as the key event. */
      track('booking_click', { label: a.textContent.trim() });
    } else if (a.classList.contains('btn')) {
      track('cta_click', { label: a.textContent.trim(), href: href });
    } else if (href.indexOf('mailto:') === 0) {
      track('email_click', { href: href });
    } else if (href.indexOf('tel:') === 0) {
      track('phone_click', { href: href });
    }
  });

  // Form start (first input) and submit attempts
  var form = document.querySelector('#plan-form');
  if (form) {
    var started = false;
    form.addEventListener('input', function () {
      if (!started) { started = true; track('form_start'); }
    });
    form.addEventListener('submit', function () {
      track('form_submit');
    });
  }
})();
