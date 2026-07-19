"""Sunni faraid engine: Hanafi, Maliki, Shafi'i, Hanbali.

Implements: fard shares (Qur'an 4:11, 4:12, 4:176), hajb (exclusion),
ta'sib (residue, male:female 2:1), umariyyatan, awl, radd, sisters
ma'a al-ghayr, grandfather-with-siblings (muqasama / third-of-residue /
sixth "best-of" for Maliki/Shafi'i/Hanbali; Hanafi: grandfather blocks
siblings), al-akdariyya, al-mushtaraka (Maliki/Shafi'i), and the barriers
of religion and homicide. See docs/VALIDATION.md for sourced scenarios.
"""
from __future__ import annotations

from fractions import Fraction

from .model import (
    Blocked, CalculationResult, DESCENDANTS, FEMALE_DESCENDANTS, FaraidError,
    MALE_DESCENDANTS, Madhhab, Rel, Settings, Share, SIBLING_RELS, UTERINE,
    validate_heirs,
)

F = Fraction

_ORDER = [
    Rel.HUSBAND, Rel.WIFE, Rel.FATHER, Rel.MOTHER, Rel.GRANDFATHER,
    Rel.PATERNAL_GRANDMOTHER, Rel.MATERNAL_GRANDMOTHER, Rel.SON,
    Rel.DAUGHTER, Rel.SONS_SON, Rel.SONS_DAUGHTER, Rel.FULL_BROTHER,
    Rel.FULL_SISTER, Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER,
    Rel.MATERNAL_BROTHER, Rel.MATERNAL_SISTER, Rel.FULL_NEPHEW,
    Rel.PATERNAL_NEPHEW, Rel.FULL_UNCLE, Rel.PATERNAL_UNCLE,
    Rel.FULL_COUSIN, Rel.PATERNAL_COUSIN,
]


class _Alloc:
    """Accumulates shares per relationship."""

    def __init__(self):
        self.data = {}   # rel -> [Fraction, [reasons], residuary]

    def add(self, rel, frac, reason, residuary=False):
        if frac < 0:
            raise FaraidError(f"negative share for {rel.value}")
        if rel not in self.data:
            self.data[rel] = [F(0), [], residuary]
        self.data[rel][0] += frac
        if reason:
            self.data[rel][1].append(reason)
        self.data[rel][2] = self.data[rel][2] or residuary

    def total(self):
        return sum((v[0] for v in self.data.values()), F(0))

    def scale(self, factor):
        for v in self.data.values():
            v[0] *= factor

    def to_shares(self, counts):
        shares = []
        for rel in _ORDER:
            if rel in self.data:
                frac, reasons, residuary = self.data[rel]
                shares.append(Share(rel, counts.get(rel, 1), frac,
                                    "; ".join(reasons), residuary))
        return shares


def calculate_sunni(madhhab: Madhhab, heirs, settings: Settings = None
                    ) -> CalculationResult:
    if madhhab == Madhhab.JAFARI:
        raise FaraidError("Use calculate_jafari for the Ja'fari school.")
    settings = settings or Settings()
    validate_heirs(heirs)
    res = CalculationResult(madhhab=madhhab)
    n = {}
    religion_flag = False
    for h in heirs:
        if not h.is_muslim:
            res.blocked.append(Blocked(
                h.relationship, h.count,
                "Barrier: difference of religion - a non-Muslim relative "
                "does not inherit by faraid (consider a wasiyya provision)."))
            religion_flag = True
        elif h.caused_death:
            res.blocked.append(Blocked(
                h.relationship, h.count,
                "Barrier: homicide - one who caused the death of the "
                "deceased is barred from inheriting."))
        else:
            n[h.relationship] = n.get(h.relationship, 0) + h.count
    if religion_flag:
        res.warnings.append(
            "One or more relatives are barred by difference of religion. "
            "You may provide for them through the wasiyya (up to 1/3).")

    def c(rel):
        return n.get(rel, 0)

    def block(rel, reason):
        if n.get(rel):
            res.blocked.append(Blocked(rel, n.pop(rel), reason))

    # Sibling count for the mother's 1/6 restriction counts siblings even
    # if they are themselves excluded by hajb (majority position).
    sib_count_for_mother = sum(c(r) for r in SIBLING_RELS)

    # ---------------- hajb (exclusion) ----------------
    if c(Rel.SON):
        block(Rel.SONS_SON, "Blocked by the son (nearer male descendant).")
        block(Rel.SONS_DAUGHTER, "Blocked by the son.")
    if c(Rel.FATHER):
        block(Rel.GRANDFATHER, "Blocked by the father.")
        block(Rel.PATERNAL_GRANDMOTHER, "Blocked by the father (her son).")
    if c(Rel.MOTHER):
        block(Rel.MATERNAL_GRANDMOTHER, "Blocked by the mother.")
        block(Rel.PATERNAL_GRANDMOTHER, "Blocked by the mother.")
    if c(Rel.SONS_DAUGHTER) and c(Rel.DAUGHTER) >= 2 and not c(Rel.SONS_SON):
        block(Rel.SONS_DAUGHTER,
              "Two or more daughters exhaust the two-thirds and there is "
              "no son's son to make her residuary.")
    if any(c(r) for r in DESCENDANTS) or c(Rel.FATHER) or c(Rel.GRANDFATHER):
        reason = ("Blocked: uterine siblings inherit only when the deceased "
                  "leaves no descendant, father or paternal grandfather.")
        block(Rel.MATERNAL_BROTHER, reason)
        block(Rel.MATERNAL_SISTER, reason)

    core_sib_block = c(Rel.SON) or c(Rel.SONS_SON) or c(Rel.FATHER)
    if core_sib_block:
        why = "Blocked by the son / son's son / father."
        for r in (Rel.FULL_BROTHER, Rel.FULL_SISTER,
                  Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER):
            block(r, why)
    elif madhhab == Madhhab.HANAFI and c(Rel.GRANDFATHER):
        why = ("Blocked by the paternal grandfather (Hanafi: the grandfather "
               "stands in the father's place and excludes siblings).")
        for r in (Rel.FULL_BROTHER, Rel.FULL_SISTER,
                  Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER):
            block(r, why)

    has_male_desc = any(c(r) for r in MALE_DESCENDANTS)
    has_female_desc = any(c(r) for r in FEMALE_DESCENDANTS)
    has_desc = has_male_desc or has_female_desc

    gf_sib_branch = (
        madhhab != Madhhab.HANAFI and c(Rel.GRANDFATHER)
        and not c(Rel.FATHER)
        and (c(Rel.FULL_BROTHER) + c(Rel.FULL_SISTER)
             + c(Rel.PATERNAL_BROTHER) + c(Rel.PATERNAL_SISTER)) > 0)

    # Full sister(s) as residuary "with" daughters (ma'a al-ghayr).
    full_sis_mag = (c(Rel.FULL_SISTER) and not c(Rel.FULL_BROTHER)
                    and has_female_desc and not has_male_desc
                    and not gf_sib_branch)
    if (c(Rel.FULL_BROTHER) or full_sis_mag) and not gf_sib_branch:
        why = ("Blocked by the full brother." if c(Rel.FULL_BROTHER) else
               "Blocked by the full sister who takes as residuary with the "
               "daughter(s) (ma'a al-ghayr).")
        block(Rel.PATERNAL_BROTHER, why)
        block(Rel.PATERNAL_SISTER, why)
    elif (c(Rel.FULL_SISTER) >= 2 and c(Rel.PATERNAL_SISTER)
          and not c(Rel.PATERNAL_BROTHER) and not gf_sib_branch
          and not has_desc):
        block(Rel.PATERNAL_SISTER,
              "Two or more full sisters exhaust the two-thirds and there is "
              "no consanguine brother to make her residuary.")
    pat_sis_mag = (c(Rel.PATERNAL_SISTER) and not c(Rel.PATERNAL_BROTHER)
                   and not c(Rel.FULL_SISTER) and not c(Rel.FULL_BROTHER)
                   and has_female_desc and not has_male_desc
                   and not gf_sib_branch)

    # Distant residuary chain blocked by any nearer residuary.
    chain = [Rel.FULL_NEPHEW, Rel.PATERNAL_NEPHEW, Rel.FULL_UNCLE,
             Rel.PATERNAL_UNCLE, Rel.FULL_COUSIN, Rel.PATERNAL_COUSIN]
    nearer = (has_male_desc or c(Rel.FATHER) or c(Rel.GRANDFATHER)
              or c(Rel.FULL_BROTHER) or c(Rel.PATERNAL_BROTHER)
              or full_sis_mag or pat_sis_mag)
    if nearer:
        for r in chain:
            block(r, "Blocked by a nearer residuary heir (hajb).")
    else:
        seen = False
        for r in chain:
            if seen:
                block(r, "Blocked by a nearer residuary heir (hajb).")
            elif c(r):
                seen = True

    alloc = _Alloc()
    present = set(r for r in n if n[r])

    # ---------------- umariyyatan ----------------
    if present in ({Rel.HUSBAND, Rel.MOTHER, Rel.FATHER},
                   {Rel.WIFE, Rel.MOTHER, Rel.FATHER}):
        sp = Rel.HUSBAND if Rel.HUSBAND in present else Rel.WIFE
        sp_share = F(1, 2) if sp == Rel.HUSBAND else F(1, 4)
        alloc.add(sp, sp_share, "Spouse's fixed share (no descendants) - "
                                "Qur'an 4:12.")
        mother = (1 - sp_share) / 3
        alloc.add(Rel.MOTHER, mother,
                  "Umariyyatan: with only spouse and parents, the mother "
                  "takes one-third of the remainder after the spouse "
                  "(ruling of 'Umar ibn al-Khattab, adopted by all four "
                  "Sunni schools).")
        alloc.add(Rel.FATHER, 1 - sp_share - mother,
                  "Residue as residuary ('asaba).", residuary=True)
        res.notes.append("Umariyyatan (al-Gharrawayn) rule applied.")
        res.shares = alloc.to_shares(n)
        return res

    # ---------------- al-akdariyya (non-Hanafi) ----------------
    if (madhhab != Madhhab.HANAFI
            and present in ({Rel.HUSBAND, Rel.MOTHER, Rel.GRANDFATHER,
                             Rel.FULL_SISTER},
                            {Rel.HUSBAND, Rel.MOTHER, Rel.GRANDFATHER,
                             Rel.PATERNAL_SISTER})
            and (c(Rel.FULL_SISTER) == 1 or c(Rel.PATERNAL_SISTER) == 1)):
        sis = Rel.FULL_SISTER if Rel.FULL_SISTER in present \
            else Rel.PATERNAL_SISTER
        alloc.add(Rel.HUSBAND, F(9, 27), "Half, reduced by awl (base 6 -> 9).")
        alloc.add(Rel.MOTHER, F(6, 27), "Third, reduced by awl.")
        alloc.add(Rel.GRANDFATHER, F(8, 27),
                  "Al-akdariyya: grandfather and sister pool their shares "
                  "after awl and divide 2:1.", residuary=True)
        alloc.add(sis, F(4, 27), "Al-akdariyya: sister's portion after "
                                 "pooling with the grandfather.", True)
        res.awl_applied = True
        res.notes.append(
            "Al-akdariyya case (husband, mother, grandfather, one sister) - "
            "resolved per Zayd ibn Thabit as followed by the Maliki, "
            "Shafi'i and Hanbali schools.")
        res.shares = alloc.to_shares(n)
        return res

    # ---------------- fard (fixed) shares ----------------
    if c(Rel.HUSBAND):
        alloc.add(Rel.HUSBAND, F(1, 4) if has_desc else F(1, 2),
                  "Husband: 1/4 with descendants, else 1/2 - Qur'an 4:12.")
    if c(Rel.WIFE):
        alloc.add(Rel.WIFE, F(1, 8) if has_desc else F(1, 4),
                  "Wife/wives: 1/8 with descendants, else 1/4, shared "
                  "equally - Qur'an 4:12.")
    if c(Rel.MOTHER):
        if has_desc or sib_count_for_mother >= 2:
            alloc.add(Rel.MOTHER, F(1, 6),
                      "Mother: 1/6 because of descendants or two or more "
                      "siblings - Qur'an 4:11.")
        else:
            alloc.add(Rel.MOTHER, F(1, 3), "Mother: 1/3 - Qur'an 4:11.")
    gms = [r for r in (Rel.PATERNAL_GRANDMOTHER, Rel.MATERNAL_GRANDMOTHER)
           if c(r)]
    for r in gms:
        alloc.add(r, F(1, 6) / len(gms),
                  "Grandmother(s): one-sixth shared (Sunnah).")

    gf_acting = (c(Rel.GRANDFATHER) and not c(Rel.FATHER)
                 and not gf_sib_branch)
    father_like = Rel.FATHER if c(Rel.FATHER) else (
        Rel.GRANDFATHER if gf_acting else None)
    if father_like and has_desc:
        alloc.add(father_like, F(1, 6),
                  ("Father" if father_like == Rel.FATHER else
                   "Paternal grandfather (in the father's place)")
                  + ": 1/6 with descendants - Qur'an 4:11.")

    if c(Rel.DAUGHTER) and not c(Rel.SON):
        alloc.add(Rel.DAUGHTER,
                  F(1, 2) if c(Rel.DAUGHTER) == 1 else F(2, 3),
                  "Daughter(s): 1/2 for one, 2/3 for two or more - "
                  "Qur'an 4:11.")
    if c(Rel.SONS_DAUGHTER) and not c(Rel.SON) and not c(Rel.SONS_SON):
        if not c(Rel.DAUGHTER):
            alloc.add(Rel.SONS_DAUGHTER,
                      F(1, 2) if c(Rel.SONS_DAUGHTER) == 1 else F(2, 3),
                      "Son's daughter(s) take the daughters' share in "
                      "their absence.")
        elif c(Rel.DAUGHTER) == 1:
            alloc.add(Rel.SONS_DAUGHTER, F(1, 6),
                      "Son's daughter(s): 1/6 completing the two-thirds "
                      "with one daughter.")

    sisters_fard_ok = (not has_desc and not c(Rel.FATHER)
                       and not c(Rel.GRANDFATHER))
    if (c(Rel.FULL_SISTER) and not c(Rel.FULL_BROTHER) and not full_sis_mag
            and sisters_fard_ok):
        alloc.add(Rel.FULL_SISTER,
                  F(1, 2) if c(Rel.FULL_SISTER) == 1 else F(2, 3),
                  "Full sister(s): 1/2 for one, 2/3 for two or more - "
                  "Qur'an 4:176.")
    if (c(Rel.PATERNAL_SISTER) and not c(Rel.PATERNAL_BROTHER)
            and not pat_sis_mag and sisters_fard_ok
            and not c(Rel.FULL_BROTHER)):
        if not c(Rel.FULL_SISTER):
            alloc.add(Rel.PATERNAL_SISTER,
                      F(1, 2) if c(Rel.PATERNAL_SISTER) == 1 else F(2, 3),
                      "Consanguine sister(s) take the sisters' share in the "
                      "absence of full siblings - Qur'an 4:176.")
        elif c(Rel.FULL_SISTER) == 1:
            alloc.add(Rel.PATERNAL_SISTER, F(1, 6),
                      "Consanguine sister(s): 1/6 completing the two-thirds "
                      "with one full sister.")
    m_uterine = c(Rel.MATERNAL_BROTHER) + c(Rel.MATERNAL_SISTER)
    if m_uterine:
        ut_share = F(1, 6) if m_uterine == 1 else F(1, 3)
        for r in UTERINE:
            if c(r):
                alloc.add(r, ut_share * c(r) / m_uterine,
                          "Uterine sibling(s): 1/6 for one, 1/3 shared "
                          "equally (male and female alike) for two or "
                          "more - Qur'an 4:12.")

    # ---------------- grandfather with siblings (non-Hanafi) -------------
    if gf_sib_branch:
        _grandfather_with_siblings(res, alloc, n, c, settings)
        _close(res, alloc, n, settings, spouse_present=present)
        return res

    # ---------------- al-mushtaraka (Maliki / Shafi'i) ----------------
    residue = 1 - alloc.total()
    if (madhhab in (Madhhab.MALIKI, Madhhab.SHAFII)
            and c(Rel.HUSBAND) and m_uterine >= 2 and c(Rel.FULL_BROTHER)
            and residue <= 0):
        heads = (m_uterine + c(Rel.FULL_BROTHER) + c(Rel.FULL_SISTER))
        for r in UTERINE:
            if r in alloc.data:
                del alloc.data[r]
        for r in (Rel.MATERNAL_BROTHER, Rel.MATERNAL_SISTER,
                  Rel.FULL_BROTHER, Rel.FULL_SISTER):
            if c(r):
                alloc.add(r, F(1, 3) * c(r) / heads,
                          "Al-mushtaraka: full siblings share the uterine "
                          "third per head (Maliki/Shafi'i).")
        res.notes.append(
            "Al-mushtaraka (al-himariyya) applied: full siblings share the "
            "one-third with the uterine siblings (Maliki/Shafi'i). The "
            "Hanafi and Hanbali schools instead leave the full siblings "
            "with nothing in this case.")
        _close(res, alloc, n, settings, spouse_present=present)
        return res
    if (madhhab in (Madhhab.HANAFI, Madhhab.HANBALI)
            and c(Rel.HUSBAND) and m_uterine >= 2 and c(Rel.FULL_BROTHER)
            and residue <= 0):
        res.notes.append(
            "Al-mushtaraka situation: under the Hanafi/Hanbali view the "
            "full sibling(s) receive nothing here; the Maliki/Shafi'i "
            "schools would let them share the uterine third.")

    # ---------------- residue (ta'sib) ----------------
    residue = 1 - alloc.total()
    if residue > 0:
        distributed = _distribute_residue(
            res, alloc, n, c, residue, father_like, full_sis_mag,
            pat_sis_mag, chain)
        if not distributed:
            _apply_radd(res, alloc, n, residue, settings)
    _close(res, alloc, n, settings, spouse_present=present)
    return res


def _distribute_residue(res, alloc, n, c, residue, father_like,
                        full_sis_mag, pat_sis_mag, chain):
    def two_to_one(male_rel, female_rel, note):
        units = 2 * c(male_rel) + c(female_rel)
        if c(male_rel):
            alloc.add(male_rel, residue * F(2 * c(male_rel), units),
                      note + " (male share, 2:1 - Qur'an 4:11).", True)
        if c(female_rel):
            alloc.add(female_rel, residue * F(c(female_rel), units),
                      note + " (female share, 2:1).", True)
        return True

    if c(Rel.SON):
        return two_to_one(Rel.SON, Rel.DAUGHTER,
                          "Residue to sons and daughters")
    if c(Rel.SONS_SON):
        return two_to_one(Rel.SONS_SON, Rel.SONS_DAUGHTER,
                          "Residue to son's sons and son's daughters")
    if father_like:
        alloc.add(father_like, residue,
                  "Residue as residuary ('asaba).", True)
        return True
    if c(Rel.FULL_BROTHER):
        return two_to_one(Rel.FULL_BROTHER, Rel.FULL_SISTER,
                          "Residue to full siblings")
    if full_sis_mag:
        alloc.add(Rel.FULL_SISTER, residue,
                  "Full sister(s) take the residue as residuary with the "
                  "daughter(s) (ma'a al-ghayr).", True)
        return True
    if c(Rel.PATERNAL_BROTHER):
        return two_to_one(Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER,
                          "Residue to consanguine siblings")
    if pat_sis_mag:
        alloc.add(Rel.PATERNAL_SISTER, residue,
                  "Consanguine sister(s) take the residue as residuary "
                  "with the daughter(s).", True)
        return True
    for r in chain:
        if c(r):
            alloc.add(r, residue,
                      "Residue to the nearest agnatic (male-line) "
                      "residuary; equal per head.", True)
            return True
    return False


def _apply_radd(res, alloc, n, residue, settings):
    spouse_rels = {Rel.HUSBAND, Rel.WIFE}
    eligible = {r: v for r, v in alloc.data.items()
                if settings.radd_includes_spouse or r not in spouse_rels}
    if eligible:
        base = sum((v[0] for v in eligible.values()), F(0))
        for r in eligible:
            extra = residue * eligible[r][0] / base
            alloc.add(r, extra, "Radd: proportional return of the surplus "
                                "to the fixed-share heirs (spouse "
                                "excluded).")
        res.radd_applied = True
        res.notes.append(
            "Radd applied: the surplus returns to the fixed-share heirs "
            "in proportion to their shares, excluding the spouse "
            "(classical majority; setting radd_includes_spouse=False).")
    elif any(r in alloc.data for r in spouse_rels):
        if settings.radd_to_sole_spouse:
            for r in spouse_rels:
                if r in alloc.data:
                    alloc.add(r, residue,
                              "Radd to the sole surviving heir (spouse) - "
                              "contemporary practice; classically the "
                              "surplus went to the public treasury.")
            res.radd_applied = True
            res.notes.append("Sole-spouse radd applied (configurable).")
        else:
            res.warnings.append(
                "Surplus of {} remains; classically it passes to the "
                "public treasury (bayt al-mal). Consider a wasiyya or "
                "scholar guidance.".format(residue))
    else:
        res.warnings.append(
            "No faraid heirs found. The estate should be dealt with by "
            "wasiyya and scholar guidance (classically: bayt al-mal).")


def _grandfather_with_siblings(res, alloc, n, c, settings):
    """Maliki/Shafi'i/Hanbali: grandfather shares with full/consanguine
    siblings; he takes the best of muqasama, one-third of the residue
    (one-third of the whole when there are no other fard heirs), or
    one-sixth of the estate (when there are other fard heirs)."""
    bf, sf = c(Rel.FULL_BROTHER), c(Rel.FULL_SISTER)
    bp, sp = c(Rel.PATERNAL_BROTHER), c(Rel.PATERNAL_SISTER)
    fard_total = alloc.total()
    residue = 1 - fard_total
    units_sibs = 2 * (bf + bp) + sf + sp
    muqasama = residue * F(2, 2 + units_sibs)
    options = [muqasama, residue / 3]
    if fard_total > 0:
        options.append(F(1, 6))
    gf = max(options)
    if gf >= residue:
        alloc.add(Rel.GRANDFATHER, F(1, 6),
                  "Grandfather: guaranteed minimum of one-sixth even when "
                  "the residue is smaller.", True)
        res.warnings.append(
            "Residue insufficient for the siblings alongside the "
            "grandfather's guaranteed sixth; confirm this family "
            "situation with a scholar.")
        return
    alloc.add(Rel.GRANDFATHER, gf,
              "Grandfather with siblings (Maliki/Shafi'i/Hanbali): best of "
              "muqasama (sharing as a brother), one-third of the residue, "
              "or one-sixth of the estate. The Hanafi school would instead "
              "exclude the siblings entirely.", True)
    res.notes.append(
        "Grandfather-with-siblings rules applied (muqasama best-of). "
        "Hanafi position differs: the grandfather excludes siblings.")
    rem = residue - gf
    if bf:
        units = 2 * bf + sf
        if bf:
            alloc.add(Rel.FULL_BROTHER, rem * F(2 * bf, units),
                      "Residue shared with the grandfather (2:1).", True)
        if sf:
            alloc.add(Rel.FULL_SISTER, rem * F(sf, units),
                      "Residue shared with the grandfather (2:1).", True)
        if bp or sp:
            res.notes.append(
                "Consanguine siblings were counted against the grandfather "
                "('add) but are excluded by the full brother.")
    elif sf and (bp or sp):
        cap = F(1, 2) if sf == 1 else F(2, 3)
        sis = min(rem, cap)
        alloc.add(Rel.FULL_SISTER, sis,
                  "Counting rule: full sister completes her portion; "
                  "consanguine siblings take any remainder.", True)
        left = rem - sis
        if left > 0:
            units = 2 * bp + sp
            if bp:
                alloc.add(Rel.PATERNAL_BROTHER, left * F(2 * bp, units),
                          "Remainder after the full sister (2:1).", True)
            if sp:
                alloc.add(Rel.PATERNAL_SISTER, left * F(sp, units),
                          "Remainder after the full sister (2:1).", True)
        res.warnings.append(
            "Grandfather with a mix of full and consanguine siblings is an "
            "intricate chapter; this uses the standard counting ('add) "
            "rule - confirm with a scholar.")
    elif sf:
        alloc.add(Rel.FULL_SISTER, rem,
                  "Full sister(s) share the residue with the grandfather.",
                  True)
    else:
        units = 2 * bp + sp
        if bp:
            alloc.add(Rel.PATERNAL_BROTHER, rem * F(2 * bp, units),
                      "Residue shared with the grandfather (2:1).", True)
        if sp:
            alloc.add(Rel.PATERNAL_SISTER, rem * F(sp, units),
                      "Residue shared with the grandfather (2:1).", True)


def _close(res, alloc, n, settings, spouse_present):
    total = alloc.total()
    if total > 1:
        alloc.scale(F(1, 1) / total)
        res.awl_applied = True
        res.notes.append(
            "Awl applied: the fixed shares exceeded the estate, so every "
            "share is reduced proportionally (doctrine attributed to "
            "'Umar ibn al-Khattab, accepted by the four Sunni schools).")
    elif total < 1 and alloc.data:
        _apply_radd(res, alloc, n, 1 - total, settings)
    elif not alloc.data:
        res.warnings.append(
            "No faraid heirs found. The estate should be dealt with by "
            "wasiyya and scholar guidance (classically: bayt al-mal).")
    res.shares = alloc.to_shares(n)
