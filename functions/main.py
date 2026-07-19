"""Firebase Cloud Functions (Python 3.12).

M2 (faraid engine) is complete and fully unit-tested. The endpoints for
M4/M5 (PDF, OCR) are structured stubs with the pipeline documented -
implement per milestone plan. All admin writes append to auditLog.
"""
import json
from fractions import Fraction

from firebase_admin import firestore, initialize_app
from firebase_functions import https_fn, options

from faraid_engine import (ENGINE_VERSION, EstateInput, FaraidError,
                           HeirInput, Rel, Settings, calculate, monetize,
                           settle_estate)

initialize_app()
options.set_global_options(max_instances=2)  # free-tier friendly


def _heirs_from_json(payload):
    return [HeirInput(Rel(h["relationship"]), h.get("count", 1),
                      h.get("isMuslim", True), h.get("causedDeath", False))
            for h in payload]


@https_fn.on_call()
def calculate_faraid(req: https_fn.CallableRequest):
    """Callable: {'madhhab', 'heirs': [...], 'estate': {...}?}."""
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in required.")
    try:
        data = req.data
        result = calculate(data["madhhab"], _heirs_from_json(data["heirs"]))
        out = result.to_dict()
        estate = data.get("estate")
        if estate:
            b = settle_estate(EstateInput(
                gross_estate=Fraction(str(estate.get("grossEstate", 0))),
                funeral_costs=Fraction(str(estate.get("funeralCosts", 0))),
                debts=Fraction(str(estate.get("debts", 0))),
                unpaid_mahr=Fraction(str(estate.get("unpaidMahr", 0))),
                unpaid_zakat=Fraction(str(estate.get("unpaidZakat", 0))),
                kaffarat=Fraction(str(estate.get("kaffarat", 0))),
                fidya=Fraction(str(estate.get("fidya", 0))),
                wasiyya_fraction=Fraction(
                    str(estate.get("wasiyyaFraction", 0)))))
            out["estate"] = {
                "netEstate": float(b.net_estate),
                "wasiyyaAmount": float(b.wasiyya_amount),
                "distributable": float(b.distributable),
                "rows": monetize(result, b.distributable),
            }
        out["engineVersion"] = ENGINE_VERSION
        return out
    except FaraidError as e:
        raise https_fn.HttpsError("invalid-argument", str(e))


@https_fn.on_call()
def generate_will_pdf(req: https_fn.CallableRequest):
    """M4: render will HTML template (English operative + chosen language
    'for reference only'), weasyprint -> PDF with Noto Naskh Arabic /
    Noto Sans Bengali, page numbers + initials line, store under
    users/{uid}/wills/{willId}/generated/, set status finalized."""
    raise https_fn.HttpsError("unimplemented", "M4 milestone.")


@https_fn.on_call()
def verify_signed_upload(req: https_fn.CallableRequest):
    """M5: merge images/PDFs (Pillow+img2pdf+pypdf) -> single PDF; OCR
    via Tesseract (eng+ara+urd+ben); rapidfuzz similarity vs generated
    text (threshold ~85); page count check; OpenCV ink-density check in
    the attestation signature boxes -> passed | needs_review | failed.
    Only a super admin then flips status to signed_uploaded_verified.
    Documented upgrade path: Google Cloud Vision OCR."""
    raise https_fn.HttpsError("unimplemented", "M5 milestone.")


@https_fn.on_call()
def export_user_data(req: https_fn.CallableRequest):
    """GDPR DSAR: export the caller's whole account tree as JSON."""
    if req.auth is None:
        raise https_fn.HttpsError("unauthenticated", "Sign in required.")
    db = firestore.client()
    doc = db.collection("accounts").document(req.auth.uid).get()
    tree = {"account": doc.to_dict() or {}, "testators": []}
    for t in db.collection("accounts").document(req.auth.uid)\
              .collection("testators").stream():
        entry = {"profile": t.to_dict(), "wills": [
            w.to_dict() for w in t.reference.collection("wills").stream()]}
        tree["testators"].append(entry)
    return json.loads(json.dumps(tree, default=str))
