# Islamic Inheritance Will Creator (UK)

Cross-platform app (Flutter + Firebase + Python Cloud Functions) that
guides Muslims in England & Wales through creating an Islamic will
(wasiyya + faraid), calculates Sharia shares per madhhab, generates a
Wills Act 1837-compliant document, tracks the will lifecycle, and
verifies uploaded wet-signed scans with OCR.

> **Disclaimer (shown throughout the app and on every generated will):**
> This tool does not constitute legal or religious advice. Have your will
> reviewed by a qualified solicitor and, for religious matters, a
> qualified scholar.

## Status

| Milestone | State |
|-----------|-------|
| M2 Faraid engine (Sunni ×4 + Ja'fari) | ✅ complete — **689 tests passing**, see `docs/VALIDATION.md` |
| Website prototype | ✅ working — `website/index.html` (JS engine parity-tested against 1,235 Python fixtures: `node website/parity_test.js`) |
| M1 Repo/CI/auth scaffold | 🏗 scaffolded (Flutter skeleton, CI, rules, seed script) |
| M3 Wizard + calculation UI | ✅ implemented in Flutter (wizard, s.15 witness check, wasiyya cap slider, heirs questionnaire, fl_chart pie + explanations, lifecycle stepper) — compile with `flutter run`; demo mode until Firebase is configured |
| M4 PDF generation | 🏗 stub (`generate_will_pdf`) — weasyprint + Noto fonts, English operative + translation "for reference only" |
| M5 Uploads + OCR verification | 🏗 stub (`verify_signed_upload`) — Tesseract + rapidfuzz + OpenCV heuristic |
| M6 Admin portal | 🏗 rules + roles + seed in place |
| M7 GDPR/security/deploy | 🏗 DSAR export function, DPIA template, checklist below |

## Layout

```
functions/faraid_engine/   # the calculation engine (pure Python, exact fractions)
functions/main.py          # Cloud Functions (Python 3.12)
functions/seed_admins.py   # seed super_admin + reporting (env-var credentials)
app/                       # Flutter (iOS/Android/web), Riverpod + go_router, en/ar/ur/bn ARB
firestore.rules            # owners write; admins read-only; append-only audit log
storage.rules              # per-user upload scoping, type/size limits
docs/VALIDATION.md         # 50+ sourced scenarios backing the engine
.github/workflows/ci.yml   # engine tests, flutter analyze/test/build, APK, hosting deploy
```

## Website prototype

Open `website/index.html` in any browser (or `firebase deploy --only
hosting` after pointing hosting at `website/`). Fully client-side:
madhhab selection, estate/liabilities, wasiyya slider (1/3 hard cap),
guided heirs questionnaire, pie chart + explained shares, and a
printable Wills Act-structured will preview. The JavaScript engine is a
line-by-line port of the Python engine, parity-tested on 1,235 fixtures.

## Flutter app

`cd app && flutter pub get && flutter run` (Chrome, Android or iOS).
Runs in demo mode out of the box (sample calculation with a clear
banner); switch `faraidServiceProvider` to `CloudFaraidService()` in
`lib/src/state/providers.dart` once Firebase + Cloud Functions are
deployed — the app then uses the verified Python engine server-side.

## Engine quickstart

```bash
cd functions
python -m pytest faraid_engine/tests   # 689 tests
python - <<'PY'
from faraid_engine import calculate, HeirInput, Rel
r = calculate("hanafi", [HeirInput(Rel.WIFE), HeirInput(Rel.SON), HeirInput(Rel.DAUGHTER)])
for s in r.shares: print(s.relationship.value, s.total, "-", s.reason)
PY
```

Documented fiqh settings (`Settings`): `radd_includes_spouse` (default
False, classical majority), `radd_to_sole_spouse` (default True,
contemporary practice), `jafari_wife_land_note`. The engine emits
warnings whenever a ruling needs scholar confirmation — never silent
guesses.

## Firebase setup (Spark/minimal-Blaze)

1. `firebase projects:create` → enable Auth (email, phone, Google;
   Apple feature-flagged until an Apple Developer account exists — it is
   mandatory on iOS once other social logins are offered), Firestore,
   Storage, App Check.
2. `firebase deploy --only firestore:rules,storage`
3. `cd functions && pip install -r requirements.txt && firebase deploy --only functions`
4. Seed admins: `SEED_SUPER_ADMIN_EMAIL=... SEED_SUPER_ADMIN_PASSWORD=... SEED_REPORTING_EMAIL=... SEED_REPORTING_PASSWORD=... python seed_admins.py`
5. Single-active-will rule + status transitions are enforced server-side
   (Cloud Functions with Admin SDK); clients can only edit drafts.

## GDPR / ICO checklist

- [ ] Register with the ICO (data protection fee) — ico.org.uk
- [ ] Publish privacy policy (`docs/privacy-policy-outline.md`); note
      Firestore encryption at rest
- [ ] DPIA completed (`docs/DPIA_template.md`) — special category data
      (religion) is processed; identify lawful basis (explicit consent)
- [ ] DSAR export (`export_user_data`) and deletion flow tested
- [ ] Retention config for archived wills + purge job
- [ ] Never store full bank account numbers or NI numbers (bank name +
      nickname + masked sort code only)

## Legal notes baked into the generated will

Revocation clause; executor + substitute; guardianship; Islamic funeral
wishes; debts/mahr/zakat first; wasiyya ≤ 1/3 with hadith explanation;
faraid schedule + fallback wording to the chosen school; Wills Act 1837
s.9 attestation clause; s.15 witness-beneficiary validation in the UI;
Inheritance (Provision for Family and Dependants) Act 1975 note; IHT
note; "Find a solicitor" info page.
