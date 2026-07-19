# Data Protection Impact Assessment (template)

## 1. Processing description
Wills containing identity data, family relationships, financial
summaries, and **special category data (religious belief)** for users in
England & Wales. Storage: Firestore/Cloud Storage (encrypted at rest).

## 2. Lawful basis
UK GDPR Art. 6(1)(b) contract + Art. 9(2)(a) explicit consent for
religious data (consent screen at onboarding; withdrawal = account
deletion flow).

## 3. Risks & mitigations
| Risk | Mitigation |
|------|------------|
| Unauthorised access to will content | Per-user security rules; admins read-only; App Check; session timeout |
| Excessive retention | Configurable retention for archived wills + purge job |
| Special category exposure | Data minimisation; no full bank/NI numbers; masked sort codes |
| OCR uploads contain signatures | Storage scoped per user; verification labelled "document consistency check", not certification |
| Sub-processor transfer | Google Cloud (Firebase) UK/EU region selection; SCCs |

## 4. Sign-off
DPO/owner, date, review cycle (annual).
