# BLTF backend — full implementation

Covers all four pieces from the roadmap: volunteer hours & approval, the
secure API layer, PayFast donations, and certificate generation.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase + PayFast keys
```

Run both SQL files in your Supabase SQL editor (in order):
1. `sql/schema.sql` — users, volunteer_hours, certificates tables + RLS policies
2. `sql/donations.sql` — donations table

Create a **private** Storage bucket named `certificates` (Storage -> New bucket).

```bash
python app.py
```

## Auth

Every route except the PayFast webhook expects a Supabase session token:
`Authorization: Bearer <supabase-access-token>`. `auth/middleware.py` verifies
it against Supabase and looks up the caller's role in the `users` table.
`@require_auth` = any signed-in user. `@require_admin` = role must be `admin`.

## Endpoints

| Method & path | Auth | Purpose |
|---|---|---|
| `POST /api/hours` | volunteer | Submit hours (status: pending) |
| `GET /api/hours?status=pending` | admin | List all hour submissions |
| `GET /api/hours/mine` | volunteer | List your own submissions |
| `POST /api/hours/<id>/approve` | admin | Approve + auto-issue any newly-reached certificate |
| `POST /api/hours/<id>/reject` | admin | Reject + notify volunteer |
| `POST /api/donations/create` | none | Create a donation; returns signed PayFast fields for money donations |
| `POST /api/payfast-webhook` | none (PayFast calls this) | Verifies and finalizes a donation |
| `GET /api/certificates/<user_id>` | owner or admin | List certificates |
| `GET /api/certificates/download/<id>` | owner or admin | Signed download URL |

## How approval leads to certificate issuance

`routes/hours.py`'s `approve_hours()` calls
`services/certificate_issuer.issue_certificates_for_user()`, which:
1. Recalculates the volunteer's total approved hours (`services/milestones.py`)
2. Finds any tier (Bronze 10h / Silver 25h / Gold 50h / Platinum 100h) reached
   but not yet certified
3. Renders a PDF per newly-reached tier (`services/certificate_builder.py`)
4. Uploads it to the `certificates` Storage bucket and inserts a row
5. Emails the volunteer

A volunteer crossing two tiers in one approval gets both certificates in that
same call. Re-approving an already-approved entry never re-issues a tier —
enforced both in code and by a `unique (user_id, level)` constraint in the
database as a second line of defense.

## Security hardening applied

Beyond the base implementation, six gaps were closed:

1. **Pending/suspended users are rejected in `auth/middleware.py`** — a
   valid Supabase session alone isn't enough; the account's `status` in the
   `users` table must be `'approved'`.
2. **PayFast's `payment_status` must be `COMPLETE`** — `verify_itn()` now
   checks this explicitly. PayFast sends ITNs for `FAILED`/`CANCELLED`
   payments too, not just successful ones.
3. **Stronger PayFast IP validation** — `_host_matches_payfast()` now does
   forward-confirmed reverse DNS (reverse-resolve, then forward-resolve the
   result and require the original IP to appear), not just a bare reverse
   lookup, which is easier to spoof.
4. **Can't reject an already-approved hour entry** — `reject_hours()`
   returns 409 if the entry is already `approved`, since a certificate may
   already have been issued off those hours.
5. **Concurrent-approval race on certificate issuance is handled safely** —
   the `unique (user_id, level)` constraint in `schema.sql` is the actual
   safety net; `certificate_issuer.py` catches that specific duplicate-key
   error and treats it as "another request already issued this" instead of
   crashing.
6. **Failed email sends are reported, not swallowed** — `send_email()`
   returns `True`/`False` and every caller now surfaces that (e.g.
   `email_sent: false` in the approve/reject response) instead of assuming
   success.

## Testing

This was smoke-tested end-to-end with Supabase and PayFast mocked (auth,
hours submission/approval, tier crossing, duplicate prevention, cross-user
access control, actual PDF byte generation, pending/suspended user
rejection, the already-approved reject guard, the certificate-issuance race
condition, PayFast's payment_status check, and failed-email reporting all
verified). It has **not** been tested against a live Supabase project or
PayFast's real sandbox — do that next by filling in real keys in `.env` and
following the PayFast sandbox steps below.

## Files

| File | Purpose |
|---|---|
| `auth/middleware.py` | Verifies Supabase session, `@require_auth` / `@require_admin` |
| `routes/hours.py` | Hours submission, listing, approve/reject |
| `routes/certificates.py` | List + signed download URL |
| `routes/donations.py`, `routes/payfast_webhook.py` | Donation flow (see below) |
| `services/milestones.py` | Tier thresholds + "what's newly reached" logic |
| `services/certificate_builder.py` | Renders the actual PDF (reportlab) |
| `services/certificate_issuer.py` | Orchestrates check -> render -> upload -> store -> email |
| `services/payfast_service.py` | Signature generation + full ITN verification |
| `services/email_service.py` | Thin Resend wrapper used by every module above |
| `db/client.py` | Shared Supabase client (service role key — backend only) |
| `sql/schema.sql`, `sql/donations.sql` | Full database schema |
| `frontend_snippet_donate.js` | Drop-in replacement for `submitDonation()` |

---

## PayFast donation flow (detail)

To enable real donations via PayFast:

1. Register at https://www.payfast.co.za
2. Get your **Merchant ID** and **Merchant Key**
3. Drop `frontend_snippet_donate.js` into `donate.html`, replacing the
   existing `submitDonation()` — it calls the backend instead of building
   the PayFast form (and exposing the merchant key) in the browser.

**Sandbox URL for testing:** `https://sandbox.payfast.co.za/eng/process`

### Testing the donation flow locally

1. Use the PayFast sandbox (`PAYFAST_SANDBOX=true`, the default) with the
   sandbox merchant credentials from PayFast's docs.
2. Since PayFast needs a public URL to send the ITN to, use `ngrok http 5000`
   during local testing and set `PAYFAST_NOTIFY_URL` to the ngrok URL.
3. Complete a sandbox payment and confirm the donation's `status` flips to
   `complete` in Supabase, and that a receipt log/email fires.

### Note on `m_payment_id`

The donation's own UUID is passed to PayFast as `m_payment_id` and comes back
unchanged in the ITN — that's how the webhook matches the notification back
to the right row without trusting anything else in the payload.
