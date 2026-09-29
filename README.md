# Ironguard IT — Brand & Website Build

Built from the **Ironguard Brand & Website Blueprint** (August 2026). This now covers
the blueprint's full sitemap plus the 31–60 day marketing assets.

## Website (22 pages)

| File | Blueprint source |
|---|---|
| `index.html` | Homepage — Section 1 structure, Section 7 copy |
| `managed-it.html` | Managed IT landing page — Section 3 copy in full |
| `services.html` | Service-system hub linking the six areas |
| `cybersecurity.html` | Security & identity — "secure by default," no fear-selling |
| `microsoft-365.html` | M365/Entra/Intune governance, licensing, lifecycle |
| `networks-infrastructure.html` | Sites, Wi-Fi, firewalls, cabling, projects |
| `automation-ai.html` | Onboarding/offboarding automation, software visibility, AI governance |
| `industries.html` | Energy, engineering, construction, technology |
| `why-ironguard.html` | Ownership model, six commitments, honest fit/not-fit, process |
| `case-studies.html` | Proof structure; working proof flagged pending approval |
| `insights.html` + `insights/*.html` | Hub + first six articles (Section 5 series) |
| `about.html` | Founder story + operating principles |
| `contact.html` | "Working session, not a sales call" + the plan form |
| `client-support.html` | Existing-client routes, separated from the sales CTA |
| `privacy.html`, `terms.html` | Drafts — **legal review required before launch** |
| `sitemap.xml`, `robots.txt` | Placeholder domain `ironguardit.com` — confirm |

System files: `css/styles.css` (Section 2 identity + Section 6 interactions),
`js/main.js` (menu, reveals, form), `js/analytics.js` (dataLayer events: cta_click,
email_click, phone_click, form_start, form_submit — point GTM/GA4 at it),
`assets/favicon.svg` (Direction A "Ironguard Frame" monogram).

## Marketing assets

- `social/` — six LinkedIn templates per the Section 6 design system: opinion card,
  executive checklist, before/after, field note, metric proof, and a 7-slide
  carousel. `social/rendered/` holds example PNGs and a LinkedIn-ready
  `carousel.pdf`. Edit the HTML text, re-screenshot at 1200×1200 (or reprint the
  carousel), post.
- `lead-magnet/executive-it-ownership-checklist.html` + `.pdf` — the executive
  checklist lead magnet (five checks a COO/CFO can run).
- `marketing/linkedin.md` — company + founder profile copy and the first four
  Tuesday founder posts, ready to paste.

## Run locally

```bash
python3 -m http.server 8642 --directory /Users/ianberkowitz/Downloads/ironguard-website
```

## Verified (Section 8 quality check)

- All 22 pages: zero broken links or anchors, unique titles and meta descriptions,
  zero console errors.
- No horizontal scroll at 320/375/768/1024/1440 px; body text ≥16 px; tap targets ≥44 px.
- Mobile menu locks scroll, manages focus, closes on Escape; forms validate inline.
- Reveals run once, 280 ms, disabled under prefers-reduced-motion; content never hidden.
- WCAG AA contrast on text (Deep Ember for small orange, Forge for large accents only).
- Signal Green used only for healthy-state indicators.

## Decisions still needed before public launch (blueprint open items)

1. **Mailbox confirmed** — everything (form, support page, legal contacts) routes to
   `support@ironguardit.com`. If sales inquiries should later land in a separate
   inbox, change the `data-inbox` attribute on the three `#plan-form` forms.
   The `ironguardit.com` domain in sitemap.xml still needs confirming.
2. **Form destination** — currently composes a pre-filled email. Swap the mailto in
   `js/main.js` for a calendar link or form handler; add spam protection then.
3. **Public pricing** — discovery-based variant is live; the starting-at-$150/user sentence is
   preserved in a comment in `managed-it.html`.
4. **Client proof** — the anonymized energy-org paragraph (managed-it, case-studies)
   is flagged pending approval. Verify every fact; replace with the approved case
   study (before/change/result with three metrics).
5. **Photography** — hero diagram, founder tile, and the field-note template photo
   slot await the real photo library.
6. **Legal** — privacy/terms first drafts are accepted as working copy;
   counsel review still recommended before public launch.
7. **Metric-proof template** — contains `XX%` placeholders; only publish with an
   approved, verified number.
8. **Existing logo decision** — blueprint open item: compare the Frame monogram
   against any existing mark before committing.
