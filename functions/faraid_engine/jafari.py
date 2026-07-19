"""Ja'fari (Imami/Shia) inheritance engine.

Class system: Class I (parents + children/descendants), Class II
(grandparents + siblings/their children), Class III (uncles/aunts).
A nearer class fully excludes a further one. No ta'sib to distant
agnates; surplus returns (radd) to class members. Awl is rejected -
any deficiency falls on the daughters/sisters. Spouse always inherits.

References: al-Sistani, "Islamic Laws", ch. 38 (Inheritance),
sistani.org/english/book/48/8236 ff.; Mughniyya, "The Five Schools",
al-islam.org. Cited per-rule below and in docs/VALIDATION.md.
"""
from __future__ import annotations

from fractions import Fraction

from .model import (
    Blocked, CalculationResult, FaraidError, Madhhab, Rel, Settings, Share,
    validate_heirs,
)

F = Fraction

_CLASS1 = {Rel.FATHER, Rel.MOTHER, Rel.SON, Rel.DAUGHTER,
           Rel.SONS_SON, Rel.SONS_DAUGHTER}
_CLASS2 = {Rel.GRANDFATHER, Rel.PATERNAL_GRANDMOTHER,
           Rel.MATERNAL_GRANDMOTHER, Rel.FULL_BROTHER, Rel.FULL_SISTER,
           Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER, Rel.MATERNAL_BROTHER,
           Rel.MATERNAL_SISTER, Rel.FULL_NEPHEW, Rel.PATERNAL_NEPHEW}
_CLASS3 = {Rel.FULL_UNCLE, Rel.PATERNAL_UNCLE, Rel.FULL_COUSIN,
           Rel.PATERNAL_COUSIN}


def calculate_jafari(heirs, settings: Settings = None) -> CalculationResult:
    settings = settings or Settings()
    validate_heirs(heirs)
    res = CalculationResult(madhhab=Madhhab.JAFARI)
    n = {}
    for h in heirs:
        if not h.is_muslim:
            res.blocked.append(Blocked(
                h.relationship, h.count,
                "Barrier: difference of religion (consider a wasiyya)."))
        elif h.caused_death:
            res.blocked.append(Blocked(
                h.relationship, h.count, "Barrier: homicide."))
        else:
            n[h.relationship] = n.get(h.relationship, 0) + h.count

    def c(rel):
        return n.get(rel, 0)

    shares = {}   # rel -> [Fraction, reason]

    def put(rel, frac, reason):
        if rel in shares:
            shares[rel][0] += frac
            shares[rel][1] += "; " + reason
        else:
            shares[rel] = [frac, reason]

    # Substitution: grandchildren stand in for children when there are
    # no immediate children (per-stirpes in classical law; approximated
    # per-capita here with a warning).
    kids_m = c(Rel.SON)
    kids_f = c(Rel.DAUGHTER)
    if not (kids_m or kids_f) and (c(Rel.SONS_SON) or c(Rel.SONS_DAUGHTER)):
        kids_m, kids_f = c(Rel.SONS_SON), c(Rel.SONS_DAUGHTER)
        res.warnings.append(
            "Grandchildren inherit in place of their (predeceased) parent "
            "per stirpes in Ja'fari law; this calculation approximates "
            "per capita - confirm exact stirpes with a scholar.")
    has_kids = bool(kids_m or kids_f)
    class1 = has_kids or c(Rel.FATHER) or c(Rel.MOTHER)
    class2 = any(c(r) for r in _CLASS2)
    class3 = any(c(r) for r in _CLASS3)

    # Spouse fixed share - never excluded (Sistani, Islamic Laws, "the
    # husband and wife inherit in all cases").
    sp_share = F(0)
    if c(Rel.HUSBAND):
        sp_share = F(1, 4) if has_kids else F(1, 2)
        put(Rel.HUSBAND, sp_share,
            "Husband: 1/4 with children, else 1/2 - Qur'an 4:12.")
    elif c(Rel.WIFE):
        sp_share = F(1, 8) if has_kids else F(1, 4)
        put(Rel.WIFE, sp_share,
            "Wife/wives: 1/8 with children, else 1/4, shared equally - "
            "Qur'an 4:12.")
        if settings.jafari_wife_land_note:
            res.notes.append(
                "Ja'fari fiqh note: per the dominant opinion (e.g. "
                "al-Sistani), a wife does not inherit land itself but "
                "inherits the value of buildings and trees on it. Shown "
                "as a note; the percentage below applies to the movable "
                "estate and valuations.")

    def block_class(rels, why):
        for r in rels:
            if n.get(r):
                res.blocked.append(Blocked(r, n.pop(r), why))

    if class1:
        block_class(_CLASS2 | _CLASS3,
                    "Ja'fari: a nearer class (parents/children) excludes "
                    "further classes entirely.")
        _class_one(res, shares, put, n, c, kids_m, kids_f, has_kids,
                   sp_share, heirs)
    elif class2:
        block_class(_CLASS3,
                    "Ja'fari: Class II (grandparents/siblings) excludes "
                    "Class III (uncles/aunts).")
        _class_two(res, shares, put, n, c, sp_share)
    elif class3:
        _class_three(res, shares, put, n, c, sp_share)
    else:
        _spouse_only(res, shares, put, n, c, settings)

    out = []
    for rel, (frac, reason) in shares.items():
        out.append(Share(rel, n.get(rel, 1), frac, reason))
    order = {r: i for i, r in enumerate(Rel)}
    out.sort(key=lambda s: order[s.relationship])
    res.shares = out
    return res


def _radd_within(res, shares, spouse_excluded=True, exclude=()):
    total = sum((v[0] for v in shares.values()), F(0))
    if total >= 1:
        return
    surplus = 1 - total
    skip = {Rel.HUSBAND, Rel.WIFE} if spouse_excluded else set()
    skip |= set(exclude)
    eligible = {r: v for r, v in shares.items() if r not in skip}
    if not eligible:
        return
    base = sum((v[0] for v in eligible.values()), F(0))
    for r in eligible:
        eligible[r][0] += surplus * eligible[r][0] / base
    res.radd_applied = True
    res.notes.append(
        "Radd: the surplus returns to the class members in proportion to "
        "their shares (spouse excluded) - Ja'fari rule.")


def _class_one(res, shares, put, n, c, kids_m, kids_f, has_kids, sp_share,
               heirs):
    # Hijab of the mother from more than 1/6-with-radd: father alive plus
    # two brothers (or 1 brother + 2 sisters, or 4 sisters), full or
    # consanguine, Muslim (Sistani, Islamic Laws - inheritance of the
    # first group).
    bros = sum(h.count for h in heirs if h.is_muslim and not h.caused_death
               and h.relationship in (Rel.FULL_BROTHER, Rel.PATERNAL_BROTHER))
    sis = sum(h.count for h in heirs if h.is_muslim and not h.caused_death
              and h.relationship in (Rel.FULL_SISTER, Rel.PATERNAL_SISTER))
    hajib = c(Rel.FATHER) and (bros >= 2 or (bros >= 1 and sis >= 2)
                               or sis >= 4)
    if hajib:
        res.notes.append(
            "Mother restricted to 1/6 (and excluded from radd) because of "
            "the father plus qualifying siblings (hajb al-umm).")
    if has_kids:
        if c(Rel.FATHER):
            put(Rel.FATHER, F(1, 6), "Father: 1/6 with children - "
                                     "Qur'an 4:11.")
        if c(Rel.MOTHER):
            put(Rel.MOTHER, F(1, 6), "Mother: 1/6 with children - "
                                     "Qur'an 4:11.")
        if kids_m:
            fixed = sum((v[0] for v in shares.values()), F(0))
            residue = 1 - fixed
            units = 2 * kids_m + kids_f
            male_rel = Rel.SON if c(Rel.SON) else Rel.SONS_SON
            fem_rel = Rel.DAUGHTER if c(Rel.SON) or c(Rel.DAUGHTER) \
                else Rel.SONS_DAUGHTER
            put(male_rel, residue * F(2 * kids_m, units),
                "Sons take the residue, 2:1 with daughters - Qur'an 4:11.")
            if kids_f:
                put(fem_rel, residue * F(kids_f, units),
                    "Daughters share the residue, 2:1 - Qur'an 4:11.")
        else:
            fem_rel = Rel.DAUGHTER if c(Rel.DAUGHTER) else Rel.SONS_DAUGHTER
            d_share = F(1, 2) if kids_f == 1 else F(2, 3)
            put(fem_rel, d_share,
                "Daughter(s): 1/2 for one, 2/3 for two or more - "
                "Qur'an 4:11.")
            total = sum((v[0] for v in shares.values()), F(0))
            if total > 1:
                put(fem_rel, (1 - total),  # negative adjustment
                    "Ja'fari rejects awl: the deficiency falls on the "
                    "daughter(s); parents and spouse keep full shares.")
                res.notes.append(
                    "Awl rejected (Ja'fari): deficiency borne by the "
                    "daughter(s). Sunni schools would reduce all shares "
                    "proportionally.")
            else:
                excl = (Rel.MOTHER,) if hajib else ()
                _radd_within(res, shares, exclude=excl)
    else:
        # Parents (one or both) +/- spouse. No umariyyatan in Ja'fari:
        # the mother takes a full third of the whole estate.
        if c(Rel.MOTHER) and c(Rel.FATHER):
            m = F(1, 6) if hajib else F(1, 3)
            put(Rel.MOTHER, m,
                "Mother: {} - Ja'fari law takes the third from the whole "
                "estate (no umariyyatan reduction, unlike the Sunni "
                "schools).".format("1/6 (restricted)" if hajib else "1/3"))
            put(Rel.FATHER, 1 - sp_share - m,
                "Father takes the remainder.")
        elif c(Rel.MOTHER):
            put(Rel.MOTHER, 1 - sp_share,
                "Mother as sole Class I heir: fixed third plus radd of "
                "the remainder.")
            res.radd_applied = True
        elif c(Rel.FATHER):
            put(Rel.FATHER, 1 - sp_share,
                "Father as sole Class I heir takes the remainder.")


def _class_two(res, shares, put, n, c, sp_share):
    ut = c(Rel.MATERNAL_BROTHER) + c(Rel.MATERNAL_SISTER)
    mat_gp = c(Rel.MATERNAL_GRANDMOTHER)
    pat_line_units = (2 * c(Rel.FULL_BROTHER) + c(Rel.FULL_SISTER)
                     if (c(Rel.FULL_BROTHER) or c(Rel.FULL_SISTER))
                     else 2 * c(Rel.PATERNAL_BROTHER)
                     + c(Rel.PATERNAL_SISTER))
    if c(Rel.FULL_BROTHER) or c(Rel.FULL_SISTER):
        if c(Rel.PATERNAL_BROTHER) or c(Rel.PATERNAL_SISTER):
            for r in (Rel.PATERNAL_BROTHER, Rel.PATERNAL_SISTER):
                if n.get(r):
                    res.blocked.append(Blocked(
                        r, n.pop(r),
                        "Ja'fari: full siblings exclude consanguine "
                        "siblings."))
    if c(Rel.FULL_NEPHEW) or c(Rel.PATERNAL_NEPHEW):
        if pat_line_units or ut:
            for r in (Rel.FULL_NEPHEW, Rel.PATERNAL_NEPHEW):
                if n.get(r):
                    res.blocked.append(Blocked(
                        r, n.pop(r),
                        "Ja'fari: siblings exclude siblings' children."))
        else:
            res.warnings.append(
                "Siblings' children substitute for siblings per stirpes; "
                "approximated per capita - confirm with a scholar.")
            pat_line_units = 2 * (c(Rel.FULL_NEPHEW)
                                  + c(Rel.PATERNAL_NEPHEW))

    maternal_pot = F(0)
    if ut or mat_gp:
        heads = ut + mat_gp
        maternal_pot = (F(1, 6) if heads == 1 else F(1, 3))
        for r in (Rel.MATERNAL_BROTHER, Rel.MATERNAL_SISTER,
                  Rel.MATERNAL_GRANDMOTHER):
            if c(r):
                put(r, maternal_pot * c(r) / heads,
                    "Maternal line (uterine siblings / maternal "
                    "grandparent): 1/6 for one, 1/3 shared equally - "
                    "Qur'an 4:12; Sistani, Islamic Laws (second group).")
    remainder = 1 - sp_share - maternal_pot
    pat_members = (pat_line_units or c(Rel.GRANDFATHER)
                   or c(Rel.PATERNAL_GRANDMOTHER))
    if pat_members:
        units = pat_line_units + (2 if c(Rel.GRANDFATHER) else 0) \
            + (1 if c(Rel.PATERNAL_GRANDMOTHER) else 0)
        sisters_only = (units and not c(Rel.FULL_BROTHER)
                        and not c(Rel.PATERNAL_BROTHER)
                        and not c(Rel.GRANDFATHER)
                        and not c(Rel.PATERNAL_GRANDMOTHER))
        if sisters_only:
            sf = c(Rel.FULL_SISTER) or c(Rel.PATERNAL_SISTER)
            rel = Rel.FULL_SISTER if c(Rel.FULL_SISTER) \
                else Rel.PATERNAL_SISTER
            fard = F(1, 2) if sf == 1 else F(2, 3)
            got = min(fard, remainder)
            put(rel, got,
                "Sister(s): fixed share; Ja'fari rejects awl, so any "
                "deficiency falls here, and any surplus returns by radd.")
            if got < fard:
                res.notes.append("Awl rejected (Ja'fari): deficiency "
                                 "borne by the sister(s).")
        else:
            for r, u in ((Rel.FULL_BROTHER, 2), (Rel.FULL_SISTER, 1),
                         (Rel.PATERNAL_BROTHER, 2), (Rel.PATERNAL_SISTER, 1),
                         (Rel.GRANDFATHER, 2),
                         (Rel.PATERNAL_GRANDMOTHER, 1),
                         (Rel.FULL_NEPHEW, 2), (Rel.PATERNAL_NEPHEW, 2)):
                if c(r):
                    put(r, remainder * F(u * c(r), units),
                        "Paternal line of Class II shares the remainder, "
                        "male:female 2:1 (Sistani, Islamic Laws).")
        if c(Rel.GRANDFATHER) and (ut or mat_gp) \
                or (mat_gp and pat_line_units):
            res.warnings.append(
                "Mixed grandparents and siblings across maternal and "
                "paternal lines involve additional Ja'fari detail - "
                "confirm the result with a scholar.")
    _radd_within(res, shares)


def _class_three(res, shares, put, n, c, sp_share):
    res.warnings.append(
        "Class III (uncles/cousins) distribution is simplified here "
        "(paternal uncles per head; cousins substitute). Ja'fari works "
        "have further detail - confirm with a scholar.")
    remainder = 1 - sp_share
    if c(Rel.FULL_UNCLE):
        put(Rel.FULL_UNCLE, remainder,
            "Full paternal uncles take; they exclude consanguine uncles "
            "(Ja'fari).")
        for r in (Rel.PATERNAL_UNCLE, Rel.FULL_COUSIN, Rel.PATERNAL_COUSIN):
            if n.get(r):
                res.blocked.append(Blocked(r, n.pop(r),
                                   "Excluded by a nearer Class III heir."))
    elif c(Rel.PATERNAL_UNCLE):
        put(Rel.PATERNAL_UNCLE, remainder, "Consanguine paternal uncles.")
        for r in (Rel.FULL_COUSIN, Rel.PATERNAL_COUSIN):
            if n.get(r):
                res.blocked.append(Blocked(r, n.pop(r),
                                   "Excluded by a nearer Class III heir."))
    elif c(Rel.FULL_COUSIN):
        put(Rel.FULL_COUSIN, remainder, "Uncles' sons substitute for "
                                        "uncles.")
        if n.get(Rel.PATERNAL_COUSIN):
            res.blocked.append(Blocked(
                Rel.PATERNAL_COUSIN, n.pop(Rel.PATERNAL_COUSIN),
                "Excluded by a nearer Class III heir."))
    elif c(Rel.PATERNAL_COUSIN):
        put(Rel.PATERNAL_COUSIN, remainder, "Uncles' sons substitute.")


def _spouse_only(res, shares, put, n, c, settings):
    if c(Rel.HUSBAND):
        put(Rel.HUSBAND, F(1, 2),
            "Radd: husband as sole heir takes the entire estate (fixed "
            "half plus return of the remainder) - Sistani, Islamic Laws.")
        res.radd_applied = True
    elif c(Rel.WIFE):
        res.warnings.append(
            "Wife as sole heir: the remaining three-quarters are, per the "
            "dominant opinion, handled under the ruling of the marja' "
            "(commonly to the Imam's share via the religious authority) - "
            "consult a scholar. Sunni schools and some contemporary "
            "positions differ.")
    else:
        res.warnings.append(
            "No faraid heirs found. The estate should be dealt with by "
            "wasiyya and scholar guidance.")
