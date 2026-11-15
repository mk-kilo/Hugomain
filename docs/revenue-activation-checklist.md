# JXZNE revenue activation checklist

Status: 2026-11-15. This document is a deployment checklist, not a report of real revenue.

## A. Make website traffic and referral clicks measurable

1. Create or select a Google Analytics 4 web data stream for **jxzne.com** (or a Plausible site). Obtain the **public Measurement ID** in the form G-XXXXXXXX; this is not an API secret.
2. Set only one chosen measurement setting in `assets/analytics-config.js`:
   - `ga4MeasurementId: "G-XXXXXXXX"`, OR
   - `plausibleDomain: "jxzne.com"` after the Plausible site has been configured.
3. Deploy and inspect the analytics provider's real-time interface on **jxzne.com**, not just the browser console.
4. Open `/start-api.html?analytics_debug=1`, press the Ofox link, and inspect the developer console for an `affiliate_click` preview, including `page_path` and `cta_id`. **Debug output is not proof of an external analytics event being received.**
5. Confirm in GA4 DebugView or Plausible events that the `affiliate_click` event is recorded. If GA4 is used, create a key event only if the definition matches your reporting goals.
6. Record top entry pages, referrals, first-call checklist visits, affiliate clicks, and the corresponding weekly aggregated Partner dashboard counts.
7. Do not paste any API key, customer identity or account token into a public repo or website field. Comply with applicable analytics consent and privacy rules.

## B. Measure the real commercial funnel

Track these weekly aggregates separately:

- Unique website visitors and landing-page sessions (analytics).
- Referral outbound clicks (`affiliate_click`); **not** confirmed signup.
- Attributed Ofox registrations and first top-ups (Partner dashboard, if exposed).
- Referred active API consumers and actual API spend (Partner dashboard).
- Commission earned and paid out (Partner dashboard).

Only infer conversion percentages when both metrics share a comparable period and attribution definition. There is no Ofox Partner private-data connection to this repo, and JXZNE cannot see the user's actual purchases.

## C. Verify a real client before making compatibility promises

- `ofox-smoke-status.json` currently reports `overall: unverified`. Do not claim the API passes unless a real authenticated test confirms it.
- Use a securely stored `OFOX_API_KEY` in GitHub Actions secrets; never commit it. Run `.github/workflows/ofox-smoke.yml`.
- Distinguish Chat Completions results from Responses and Anthropic Messages; a pass for one does not prove compatibility with the other.
- Test the actual coding clients, streaming, tool calls, and failures separately, with redacted logs.
- Only promote a setup as confirmed after the evidence is available.

## D. Keep prices honest

- `scripts/refresh_ofox_public_catalog.py` refreshes unauthenticated public list rates into `ofox-public-prices.json` and refuses to overwrite the snapshot if source data is invalid or unavailable.
- Workflow: `.github/workflows/refresh-ofox-catalog.yml`.
- The public catalog is not the user's invoice or proof of supported endpoints. Confirm live model and checkout prices before buying.
- The country-level **subscription** snapshots are independent from model **API** usage pricing.

## E. Prioritized 30-day commercial experiment

- Week 1: Verify site reachability, analytics ingestion, Ofox link tracking and one real working API protocol.
- Week 2: Test two high-intent pages (`/start-api.html`, `/en/start-api.html`) with real developer users. Log reported difficulties without collecting secrets.
- Week 3: Publish verified screenshots or redacted logs and one source-linked, same-model API price comparison.
- Week 4: Evaluate landing-page traffic, completed referrals, active consumers and actual partner commissions. Then decide whether to invest in more SEO or direct enterprise outreach.

Do not buy traffic until website analytics and offsite Partner attribution have been separately checked. Nothing here guarantees any revenue.
