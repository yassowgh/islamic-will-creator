# Manual QA script (per milestone)

## M2 engine (run now)
1. `cd functions && python -m pytest faraid_engine/tests` → 689 pass.
2. Spot-check umariyyatan, akdariyya (shafii vs hanafi), mushtaraka
   (maliki vs hanbali), Ja'fari husband+parents vs Sunni.

## M3 wizard
- Witness = beneficiary → blocked with Wills Act 1837 s.15 explanation.
- Wasiyya slider cannot exceed 33.33%; 1/3 exactly allowed.
- Joint-tenancy education shown when jointlyOwned=true.
- Madhhab switch recalculates and re-labels explanations.

## M4 PDF
- RTL rendering for ar/ur; Bengali glyphs; page numbers "Page X of Y";
  initials line every page; English operative + translation reference.

## M5 upload/OCR
- Photos → single merged PDF; similarity <85% → needs_review queue;
  page-count mismatch → failed with reason.

## M6 admin
- Reporting user sees anonymized IDs only; super admin cannot edit will
  content (attempt → permission denied); every admin action in auditLog.

## M7
- DSAR export JSON completeness; account deletion; security-rules
  emulator suite green; screen-reader pass on wizard.
