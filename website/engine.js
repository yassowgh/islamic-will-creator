/* Faraid engine - JavaScript port of the validated Python engine
 * (functions/faraid_engine, v1.0.0). Exact arithmetic via BigInt
 * fractions. Parity-tested against 1,235 fixtures generated from the
 * Python engine (see website/parity_test.js).
 * Not legal or religious advice. */
"use strict";

/* ---------- exact fractions ---------- */
function bgcd(a, b) { a = a < 0n ? -a : a; b = b < 0n ? -b : b;
  while (b) { [a, b] = [b, a % b]; } return a; }
class Frac {
  constructor(n, d = 1n) {
    n = BigInt(n); d = BigInt(d);
    if (d === 0n) throw new Error("division by zero");
    if (d < 0n) { n = -n; d = -d; }
    const g = bgcd(n, d) || 1n;
    this.n = n / g; this.d = d / g;
  }
  add(o) { return new Frac(this.n * o.d + o.n * this.d, this.d * o.d); }
  sub(o) { return new Frac(this.n * o.d - o.n * this.d, this.d * o.d); }
  mul(o) { return new Frac(this.n * o.n, this.d * o.d); }
  div(o) { return new Frac(this.n * o.d, this.d * o.n); }
  cmp(o) { const l = this.n * o.d, r = o.n * this.d;
    return l < r ? -1 : l > r ? 1 : 0; }
  eq(o) { return this.cmp(o) === 0; }
  lt(o) { return this.cmp(o) < 0; }
  gt(o) { return this.cmp(o) > 0; }
  le(o) { return this.cmp(o) <= 0; }
  ge(o) { return this.cmp(o) >= 0; }
  isZero() { return this.n === 0n; }
  neg() { return new Frac(-this.n, this.d); }
  toString() { return this.d === 1n ? `${this.n}` : `${this.n}/${this.d}`; }
  toNumber() { return Number(this.n) / Number(this.d); }
}
const F = (n, d = 1) => new Frac(BigInt(n), BigInt(d));
const ZERO = F(0), ONE = F(1);
const fmax = (...xs) => xs.reduce((a, b) => (b.gt(a) ? b : a));
const fsum = (xs) => xs.reduce((a, b) => a.add(b), ZERO);

/* ---------- model ---------- */
const REL = {
  HUSBAND: "husband", WIFE: "wife", SON: "son", DAUGHTER: "daughter",
  SONS_SON: "sons_son", SONS_DAUGHTER: "sons_daughter", FATHER: "father",
  MOTHER: "mother", GRANDFATHER: "paternal_grandfather",
  PGM: "paternal_grandmother", MGM: "maternal_grandmother",
  FB: "full_brother", FS: "full_sister", PB: "paternal_brother",
  PS: "paternal_sister", MB: "maternal_brother", MS: "maternal_sister",
  FNEPHEW: "full_brothers_son", PNEPHEW: "paternal_brothers_son",
  FUNCLE: "full_paternal_uncle", PUNCLE: "paternal_paternal_uncle",
  FCOUSIN: "full_uncles_son", PCOUSIN: "paternal_uncles_son",
};
const ALL_RELS = Object.values(REL);
const MALE_DESC = [REL.SON, REL.SONS_SON];
const FEMALE_DESC = [REL.DAUGHTER, REL.SONS_DAUGHTER];
const DESCENDANTS = MALE_DESC.concat(FEMALE_DESC);
const SIBLING_RELS = [REL.FB, REL.FS, REL.PB, REL.PS, REL.MB, REL.MS];
const UTERINE = [REL.MB, REL.MS];
const ORDER = [REL.HUSBAND, REL.WIFE, REL.FATHER, REL.MOTHER,
  REL.GRANDFATHER, REL.PGM, REL.MGM, REL.SON, REL.DAUGHTER, REL.SONS_SON,
  REL.SONS_DAUGHTER, REL.FB, REL.FS, REL.PB, REL.PS, REL.MB, REL.MS,
  REL.FNEPHEW, REL.PNEPHEW, REL.FUNCLE, REL.PUNCLE, REL.FCOUSIN,
  REL.PCOUSIN];

class FaraidError extends Error {}

const DEFAULT_SETTINGS = {
  raddIncludesSpouse: false, raddToSoleSpouse: true, jafariWifeLandNote: true,
};

function validateHeirs(heirs) {
  const counts = {};
  for (const h of heirs) {
    if (!ALL_RELS.includes(h.relationship))
      throw new FaraidError("Unknown relationship: " + h.relationship);
    const cnt = h.count == null ? 1 : h.count;
    if (cnt < 1) throw new FaraidError("count must be >= 1");
    counts[h.relationship] = (counts[h.relationship] || 0) + cnt;
  }
  if (counts[REL.HUSBAND] && counts[REL.WIFE])
    throw new FaraidError("A deceased cannot leave both a husband and a wife.");
  if ((counts[REL.HUSBAND] || 0) > 1) throw new FaraidError("At most one husband.");
  if ((counts[REL.WIFE] || 0) > 4) throw new FaraidError("At most four wives.");
  for (const r of [REL.FATHER, REL.MOTHER, REL.GRANDFATHER, REL.PGM, REL.MGM])
    if ((counts[r] || 0) > 1) throw new FaraidError("At most one " + r + ".");
}

/* ---------- allocation helper ---------- */
class Alloc {
  constructor() { this.data = new Map(); }
  add(rel, frac, reason, residuary = false) {
    if (!this.data.has(rel)) this.data.set(rel, { f: ZERO, reasons: [], residuary: false });
    const e = this.data.get(rel);
    e.f = e.f.add(frac);
    if (reason) e.reasons.push(reason);
    e.residuary = e.residuary || residuary;
  }
  del(rel) { this.data.delete(rel); }
  total() { return fsum([...this.data.values()].map((e) => e.f)); }
  scale(k) { for (const e of this.data.values()) e.f = e.f.mul(k); }
  toShares(n) {
    const out = [];
    for (const rel of ORDER)
      if (this.data.has(rel)) {
        const e = this.data.get(rel);
        out.push({ relationship: rel, count: n[rel] || 1, total: e.f,
          reason: e.reasons.join("; "), residuary: e.residuary });
      }
    return out;
  }
}

/* ---------- Sunni engine ---------- */
function calculateSunni(madhhab, heirs, settings) {
  const st = Object.assign({}, DEFAULT_SETTINGS, settings || {});
  validateHeirs(heirs);
  const res = { madhhab, shares: [], blocked: [], awl: false, radd: false,
    notes: [], warnings: [] };
  const n = {};
  let religionFlag = false;
  for (const h of heirs) {
    const cnt = h.count == null ? 1 : h.count;
    if (h.isMuslim === false) {
      res.blocked.push({ relationship: h.relationship, count: cnt,
        reason: "Barrier: difference of religion - a non-Muslim relative does not inherit by faraid (consider a wasiyya provision)." });
      religionFlag = true;
    } else if (h.causedDeath) {
      res.blocked.push({ relationship: h.relationship, count: cnt,
        reason: "Barrier: homicide - one who caused the death of the deceased is barred from inheriting." });
    } else n[h.relationship] = (n[h.relationship] || 0) + cnt;
  }
  if (religionFlag)
    res.warnings.push("One or more relatives are barred by difference of religion. You may provide for them through the wasiyya (up to 1/3).");

  const c = (r) => n[r] || 0;
  const block = (r, reason) => {
    if (n[r]) { res.blocked.push({ relationship: r, count: n[r], reason }); delete n[r]; }
  };
  const sibCountForMother = SIBLING_RELS.reduce((a, r) => a + c(r), 0);

  /* hajb */
  if (c(REL.SON)) {
    block(REL.SONS_SON, "Blocked by the son (nearer male descendant).");
    block(REL.SONS_DAUGHTER, "Blocked by the son.");
  }
  if (c(REL.FATHER)) {
    block(REL.GRANDFATHER, "Blocked by the father.");
    block(REL.PGM, "Blocked by the father (her son).");
  }
  if (c(REL.MOTHER)) {
    block(REL.MGM, "Blocked by the mother.");
    block(REL.PGM, "Blocked by the mother.");
  }
  if (c(REL.SONS_DAUGHTER) && c(REL.DAUGHTER) >= 2 && !c(REL.SONS_SON))
    block(REL.SONS_DAUGHTER, "Two or more daughters exhaust the two-thirds and there is no son's son to make her residuary.");
  if (DESCENDANTS.some((r) => c(r)) || c(REL.FATHER) || c(REL.GRANDFATHER)) {
    const why = "Blocked: uterine siblings inherit only when the deceased leaves no descendant, father or paternal grandfather.";
    block(REL.MB, why); block(REL.MS, why);
  }
  const coreSibBlock = c(REL.SON) || c(REL.SONS_SON) || c(REL.FATHER);
  if (coreSibBlock) {
    const why = "Blocked by the son / son's son / father.";
    [REL.FB, REL.FS, REL.PB, REL.PS].forEach((r) => block(r, why));
  } else if (madhhab === "hanafi" && c(REL.GRANDFATHER)) {
    const why = "Blocked by the paternal grandfather (Hanafi: the grandfather stands in the father's place and excludes siblings).";
    [REL.FB, REL.FS, REL.PB, REL.PS].forEach((r) => block(r, why));
  }
  const hasMaleDesc = MALE_DESC.some((r) => c(r));
  const hasFemaleDesc = FEMALE_DESC.some((r) => c(r));
  const hasDesc = hasMaleDesc || hasFemaleDesc;

  const gfSibBranch = madhhab !== "hanafi" && c(REL.GRANDFATHER) &&
    !c(REL.FATHER) && (c(REL.FB) + c(REL.FS) + c(REL.PB) + c(REL.PS)) > 0;

  const fullSisMag = c(REL.FS) && !c(REL.FB) && hasFemaleDesc &&
    !hasMaleDesc && !gfSibBranch;
  if ((c(REL.FB) || fullSisMag) && !gfSibBranch) {
    const why = c(REL.FB) ? "Blocked by the full brother."
      : "Blocked by the full sister who takes as residuary with the daughter(s) (ma'a al-ghayr).";
    block(REL.PB, why); block(REL.PS, why);
  } else if (c(REL.FS) >= 2 && c(REL.PS) && !c(REL.PB) && !gfSibBranch && !hasDesc) {
    block(REL.PS, "Two or more full sisters exhaust the two-thirds and there is no consanguine brother to make her residuary.");
  }
  const patSisMag = c(REL.PS) && !c(REL.PB) && !c(REL.FS) && !c(REL.FB) &&
    hasFemaleDesc && !hasMaleDesc && !gfSibBranch;

  const chain = [REL.FNEPHEW, REL.PNEPHEW, REL.FUNCLE, REL.PUNCLE,
    REL.FCOUSIN, REL.PCOUSIN];
  const nearer = hasMaleDesc || c(REL.FATHER) || c(REL.GRANDFATHER) ||
    c(REL.FB) || c(REL.PB) || fullSisMag || patSisMag;
  if (nearer) chain.forEach((r) => block(r, "Blocked by a nearer residuary heir (hajb)."));
  else {
    let seen = false;
    for (const r of chain) {
      if (seen) block(r, "Blocked by a nearer residuary heir (hajb).");
      else if (c(r)) seen = true;
    }
  }

  const alloc = new Alloc();
  const present = Object.keys(n).filter((r) => n[r]).sort().join(",");
  const setEq = (rels) => present === rels.slice().sort().join(",");

  /* umariyyatan */
  if (setEq([REL.HUSBAND, REL.MOTHER, REL.FATHER]) ||
      setEq([REL.WIFE, REL.MOTHER, REL.FATHER])) {
    const sp = c(REL.HUSBAND) ? REL.HUSBAND : REL.WIFE;
    const spShare = sp === REL.HUSBAND ? F(1, 2) : F(1, 4);
    alloc.add(sp, spShare, "Spouse's fixed share (no descendants) - Qur'an 4:12.");
    const mother = ONE.sub(spShare).div(F(3));
    alloc.add(REL.MOTHER, mother, "Umariyyatan: with only spouse and parents, the mother takes one-third of the remainder after the spouse.");
    alloc.add(REL.FATHER, ONE.sub(spShare).sub(mother), "Residue as residuary ('asaba).", true);
    res.notes.push("Umariyyatan (al-Gharrawayn) rule applied.");
    res.shares = alloc.toShares(n);
    return res;
  }
  /* akdariyya */
  if (madhhab !== "hanafi" &&
      (setEq([REL.HUSBAND, REL.MOTHER, REL.GRANDFATHER, REL.FS]) ||
       setEq([REL.HUSBAND, REL.MOTHER, REL.GRANDFATHER, REL.PS])) &&
      (c(REL.FS) === 1 || c(REL.PS) === 1)) {
    const sis = c(REL.FS) ? REL.FS : REL.PS;
    alloc.add(REL.HUSBAND, F(9, 27), "Half, reduced by awl (base 6 -> 9).");
    alloc.add(REL.MOTHER, F(6, 27), "Third, reduced by awl.");
    alloc.add(REL.GRANDFATHER, F(8, 27), "Al-akdariyya: grandfather and sister pool their shares after awl and divide 2:1.", true);
    alloc.add(sis, F(4, 27), "Al-akdariyya: sister's portion after pooling with the grandfather.", true);
    res.awl = true;
    res.notes.push("Al-akdariyya case resolved per Zayd ibn Thabit (Maliki/Shafi'i/Hanbali).");
    res.shares = alloc.toShares(n);
    return res;
  }

  /* fard shares */
  if (c(REL.HUSBAND))
    alloc.add(REL.HUSBAND, hasDesc ? F(1, 4) : F(1, 2),
      "Husband: 1/4 with descendants, else 1/2 - Qur'an 4:12.");
  if (c(REL.WIFE))
    alloc.add(REL.WIFE, hasDesc ? F(1, 8) : F(1, 4),
      "Wife/wives: 1/8 with descendants, else 1/4, shared equally - Qur'an 4:12.");
  if (c(REL.MOTHER)) {
    if (hasDesc || sibCountForMother >= 2)
      alloc.add(REL.MOTHER, F(1, 6), "Mother: 1/6 because of descendants or two or more siblings - Qur'an 4:11.");
    else alloc.add(REL.MOTHER, F(1, 3), "Mother: 1/3 - Qur'an 4:11.");
  }
  const gms = [REL.PGM, REL.MGM].filter((r) => c(r));
  for (const r of gms)
    alloc.add(r, F(1, 6).div(F(gms.length)), "Grandmother(s): one-sixth shared (Sunnah).");

  const gfActing = c(REL.GRANDFATHER) && !c(REL.FATHER) && !gfSibBranch;
  const fatherLike = c(REL.FATHER) ? REL.FATHER : gfActing ? REL.GRANDFATHER : null;
  if (fatherLike && hasDesc)
    alloc.add(fatherLike, F(1, 6),
      (fatherLike === REL.FATHER ? "Father" : "Paternal grandfather (in the father's place)") +
      ": 1/6 with descendants - Qur'an 4:11.");

  if (c(REL.DAUGHTER) && !c(REL.SON))
    alloc.add(REL.DAUGHTER, c(REL.DAUGHTER) === 1 ? F(1, 2) : F(2, 3),
      "Daughter(s): 1/2 for one, 2/3 for two or more - Qur'an 4:11.");
  if (c(REL.SONS_DAUGHTER) && !c(REL.SON) && !c(REL.SONS_SON)) {
    if (!c(REL.DAUGHTER))
      alloc.add(REL.SONS_DAUGHTER, c(REL.SONS_DAUGHTER) === 1 ? F(1, 2) : F(2, 3),
        "Son's daughter(s) take the daughters' share in their absence.");
    else if (c(REL.DAUGHTER) === 1)
      alloc.add(REL.SONS_DAUGHTER, F(1, 6),
        "Son's daughter(s): 1/6 completing the two-thirds with one daughter.");
  }
  const sistersFardOk = !hasDesc && !c(REL.FATHER) && !c(REL.GRANDFATHER);
  if (c(REL.FS) && !c(REL.FB) && !fullSisMag && sistersFardOk)
    alloc.add(REL.FS, c(REL.FS) === 1 ? F(1, 2) : F(2, 3),
      "Full sister(s): 1/2 for one, 2/3 for two or more - Qur'an 4:176.");
  if (c(REL.PS) && !c(REL.PB) && !patSisMag && sistersFardOk && !c(REL.FB)) {
    if (!c(REL.FS))
      alloc.add(REL.PS, c(REL.PS) === 1 ? F(1, 2) : F(2, 3),
        "Consanguine sister(s) take the sisters' share in the absence of full siblings - Qur'an 4:176.");
    else if (c(REL.FS) === 1)
      alloc.add(REL.PS, F(1, 6),
        "Consanguine sister(s): 1/6 completing the two-thirds with one full sister.");
  }
  const mUterine = c(REL.MB) + c(REL.MS);
  if (mUterine) {
    const ut = mUterine === 1 ? F(1, 6) : F(1, 3);
    for (const r of UTERINE)
      if (c(r)) alloc.add(r, ut.mul(F(c(r))).div(F(mUterine)),
        "Uterine sibling(s): 1/6 for one, 1/3 shared equally - Qur'an 4:12.");
  }

  if (gfSibBranch) {
    grandfatherWithSiblings(res, alloc, c);
    close(res, alloc, n, st);
    return res;
  }

  /* mushtaraka */
  let residue = ONE.sub(alloc.total());
  if ((madhhab === "maliki" || madhhab === "shafii") && c(REL.HUSBAND) &&
      mUterine >= 2 && c(REL.FB) && residue.le(ZERO)) {
    const heads = mUterine + c(REL.FB) + c(REL.FS);
    for (const r of UTERINE) alloc.del(r);
    for (const r of [REL.MB, REL.MS, REL.FB, REL.FS])
      if (c(r)) alloc.add(r, F(1, 3).mul(F(c(r))).div(F(heads)),
        "Al-mushtaraka: full siblings share the uterine third per head (Maliki/Shafi'i).");
    res.notes.push("Al-mushtaraka (al-himariyya) applied: full siblings share the one-third with the uterine siblings (Maliki/Shafi'i). Hanafi/Hanbali differ.");
    close(res, alloc, n, st);
    return res;
  }
  if ((madhhab === "hanafi" || madhhab === "hanbali") && c(REL.HUSBAND) &&
      mUterine >= 2 && c(REL.FB) && residue.le(ZERO))
    res.notes.push("Al-mushtaraka situation: under the Hanafi/Hanbali view the full sibling(s) receive nothing here; Maliki/Shafi'i would let them share the uterine third.");

  residue = ONE.sub(alloc.total());
  if (residue.gt(ZERO)) {
    const distributed = distributeResidue(res, alloc, c, residue, fatherLike,
      fullSisMag, patSisMag, chain);
    if (!distributed) applyRadd(res, alloc, residue, st);
  }
  close(res, alloc, n, st);
  return res;
}

function distributeResidue(res, alloc, c, residue, fatherLike, fullSisMag,
                           patSisMag, chain) {
  const twoToOne = (m, f, note) => {
    const units = 2 * c(m) + c(f);
    if (c(m)) alloc.add(m, residue.mul(F(2 * c(m), units)),
      note + " (male share, 2:1 - Qur'an 4:11).", true);
    if (c(f)) alloc.add(f, residue.mul(F(c(f), units)),
      note + " (female share, 2:1).", true);
    return true;
  };
  if (c(REL.SON)) return twoToOne(REL.SON, REL.DAUGHTER, "Residue to sons and daughters");
  if (c(REL.SONS_SON)) return twoToOne(REL.SONS_SON, REL.SONS_DAUGHTER, "Residue to son's sons and son's daughters");
  if (fatherLike) { alloc.add(fatherLike, residue, "Residue as residuary ('asaba).", true); return true; }
  if (c(REL.FB)) return twoToOne(REL.FB, REL.FS, "Residue to full siblings");
  if (fullSisMag) { alloc.add(REL.FS, residue, "Full sister(s) take the residue as residuary with the daughter(s) (ma'a al-ghayr).", true); return true; }
  if (c(REL.PB)) return twoToOne(REL.PB, REL.PS, "Residue to consanguine siblings");
  if (patSisMag) { alloc.add(REL.PS, residue, "Consanguine sister(s) take the residue as residuary with the daughter(s).", true); return true; }
  for (const r of chain)
    if (c(r)) { alloc.add(r, residue, "Residue to the nearest agnatic residuary; equal per head.", true); return true; }
  return false;
}

function applyRadd(res, alloc, residue, st) {
  const spouseRels = [REL.HUSBAND, REL.WIFE];
  const eligible = [...alloc.data.keys()].filter(
    (r) => st.raddIncludesSpouse || !spouseRels.includes(r));
  if (eligible.length) {
    const base = fsum(eligible.map((r) => alloc.data.get(r).f));
    for (const r of eligible)
      alloc.add(r, residue.mul(alloc.data.get(r).f).div(base),
        "Radd: proportional return of the surplus to the fixed-share heirs (spouse excluded).");
    res.radd = true;
    res.notes.push("Radd applied: the surplus returns to the fixed-share heirs in proportion to their shares, excluding the spouse (classical majority).");
  } else if (spouseRels.some((r) => alloc.data.has(r))) {
    if (st.raddToSoleSpouse) {
      for (const r of spouseRels)
        if (alloc.data.has(r))
          alloc.add(r, residue, "Radd to the sole surviving heir (spouse) - contemporary practice.");
      res.radd = true;
      res.notes.push("Sole-spouse radd applied (configurable).");
    } else res.warnings.push("Surplus remains; classically it passes to the public treasury (bayt al-mal).");
  } else res.warnings.push("No faraid heirs found. The estate should be dealt with by wasiyya and scholar guidance (classically: bayt al-mal).");
}

function grandfatherWithSiblings(res, alloc, c) {
  const bf = c(REL.FB), sf = c(REL.FS), bp = c(REL.PB), sp = c(REL.PS);
  const fardTotal = alloc.total();
  const residue = ONE.sub(fardTotal);
  const unitsSibs = 2 * (bf + bp) + sf + sp;
  const muqasama = residue.mul(F(2, 2 + unitsSibs));
  const options = [muqasama, residue.div(F(3))];
  if (fardTotal.gt(ZERO)) options.push(F(1, 6));
  const gf = fmax(...options);
  if (gf.ge(residue)) {
    alloc.add(REL.GRANDFATHER, F(1, 6),
      "Grandfather: guaranteed minimum of one-sixth even when the residue is smaller.", true);
    res.warnings.push("Residue insufficient for the siblings alongside the grandfather's guaranteed sixth; confirm with a scholar.");
    return;
  }
  alloc.add(REL.GRANDFATHER, gf,
    "Grandfather with siblings (Maliki/Shafi'i/Hanbali): best of muqasama, one-third of the residue, or one-sixth of the estate. The Hanafi school would instead exclude the siblings.", true);
  res.notes.push("Grandfather-with-siblings rules applied (muqasama best-of). Hanafi position differs: the grandfather excludes siblings.");
  const rem = residue.sub(gf);
  if (bf) {
    const units = 2 * bf + sf;
    alloc.add(REL.FB, rem.mul(F(2 * bf, units)), "Residue shared with the grandfather (2:1).", true);
    if (sf) alloc.add(REL.FS, rem.mul(F(sf, units)), "Residue shared with the grandfather (2:1).", true);
    if (bp || sp) res.notes.push("Consanguine siblings were counted against the grandfather ('add) but are excluded by the full brother.");
  } else if (sf && (bp || sp)) {
    const cap = sf === 1 ? F(1, 2) : F(2, 3);
    const sis = rem.lt(cap) ? rem : cap;
    alloc.add(REL.FS, sis, "Counting rule: full sister completes her portion; consanguine siblings take any remainder.", true);
    const left = rem.sub(sis);
    if (left.gt(ZERO)) {
      const units = 2 * bp + sp;
      if (bp) alloc.add(REL.PB, left.mul(F(2 * bp, units)), "Remainder after the full sister (2:1).", true);
      if (sp) alloc.add(REL.PS, left.mul(F(sp, units)), "Remainder after the full sister (2:1).", true);
    }
    res.warnings.push("Grandfather with a mix of full and consanguine siblings uses the standard counting ('add) rule - confirm with a scholar.");
  } else if (sf) {
    alloc.add(REL.FS, rem, "Full sister(s) share the residue with the grandfather.", true);
  } else {
    const units = 2 * bp + sp;
    if (bp) alloc.add(REL.PB, rem.mul(F(2 * bp, units)), "Residue shared with the grandfather (2:1).", true);
    if (sp) alloc.add(REL.PS, rem.mul(F(sp, units)), "Residue shared with the grandfather (2:1).", true);
  }
}

function close(res, alloc, n, st) {
  const total = alloc.total();
  if (total.gt(ONE)) {
    alloc.scale(ONE.div(total));
    res.awl = true;
    res.notes.push("Awl applied: the fixed shares exceeded the estate, so every share is reduced proportionally.");
  } else if (total.lt(ONE) && alloc.data.size) {
    applyRadd(res, alloc, ONE.sub(total), st);
  } else if (!alloc.data.size) {
    res.warnings.push("No faraid heirs found. The estate should be dealt with by wasiyya and scholar guidance (classically: bayt al-mal).");
  }
  res.shares = alloc.toShares(n);
}

/* ---------- Ja'fari engine ---------- */
const CLASS1 = [REL.FATHER, REL.MOTHER, REL.SON, REL.DAUGHTER, REL.SONS_SON, REL.SONS_DAUGHTER];
const CLASS2 = [REL.GRANDFATHER, REL.PGM, REL.MGM, REL.FB, REL.FS, REL.PB, REL.PS, REL.MB, REL.MS, REL.FNEPHEW, REL.PNEPHEW];
const CLASS3 = [REL.FUNCLE, REL.PUNCLE, REL.FCOUSIN, REL.PCOUSIN];

function calculateJafari(heirs, settings) {
  const st = Object.assign({}, DEFAULT_SETTINGS, settings || {});
  validateHeirs(heirs);
  const res = { madhhab: "jafari", shares: [], blocked: [], awl: false,
    radd: false, notes: [], warnings: [] };
  const n = {};
  for (const h of heirs) {
    const cnt = h.count == null ? 1 : h.count;
    if (h.isMuslim === false)
      res.blocked.push({ relationship: h.relationship, count: cnt,
        reason: "Barrier: difference of religion (consider a wasiyya)." });
    else if (h.causedDeath)
      res.blocked.push({ relationship: h.relationship, count: cnt, reason: "Barrier: homicide." });
    else n[h.relationship] = (n[h.relationship] || 0) + cnt;
  }
  const c = (r) => n[r] || 0;
  const shares = new Map(); // rel -> {f, reason}
  const put = (rel, frac, reason) => {
    if (shares.has(rel)) { const e = shares.get(rel); e.f = e.f.add(frac); e.reason += "; " + reason; }
    else shares.set(rel, { f: frac, reason });
  };

  let kidsM = c(REL.SON), kidsF = c(REL.DAUGHTER);
  if (!(kidsM || kidsF) && (c(REL.SONS_SON) || c(REL.SONS_DAUGHTER))) {
    kidsM = c(REL.SONS_SON); kidsF = c(REL.SONS_DAUGHTER);
    res.warnings.push("Grandchildren inherit in place of their (predeceased) parent per stirpes in Ja'fari law; this calculation approximates per capita - confirm exact stirpes with a scholar.");
  }
  const hasKids = !!(kidsM || kidsF);
  const class1 = hasKids || c(REL.FATHER) || c(REL.MOTHER);
  const class2 = CLASS2.some((r) => c(r));
  const class3 = CLASS3.some((r) => c(r));

  let spShare = ZERO;
  if (c(REL.HUSBAND)) {
    spShare = hasKids ? F(1, 4) : F(1, 2);
    put(REL.HUSBAND, spShare, "Husband: 1/4 with children, else 1/2 - Qur'an 4:12.");
  } else if (c(REL.WIFE)) {
    spShare = hasKids ? F(1, 8) : F(1, 4);
    put(REL.WIFE, spShare, "Wife/wives: 1/8 with children, else 1/4, shared equally - Qur'an 4:12.");
    if (st.jafariWifeLandNote)
      res.notes.push("Ja'fari fiqh note: per the dominant opinion (e.g. al-Sistani), a wife does not inherit land itself but inherits the value of buildings and trees on it.");
  }
  const blockClass = (rels, why) => {
    for (const r of rels) if (n[r]) { res.blocked.push({ relationship: r, count: n[r], reason: why }); delete n[r]; }
  };

  const raddWithin = (exclude = []) => {
    const total = fsum([...shares.values()].map((e) => e.f));
    if (total.ge(ONE)) return;
    const surplus = ONE.sub(total);
    const skip = new Set([REL.HUSBAND, REL.WIFE, ...exclude]);
    const eligible = [...shares.keys()].filter((r) => !skip.has(r));
    if (!eligible.length) return;
    const base = fsum(eligible.map((r) => shares.get(r).f));
    for (const r of eligible) {
      const e = shares.get(r);
      e.f = e.f.add(surplus.mul(e.f).div(base));
    }
    res.radd = true;
    res.notes.push("Radd: the surplus returns to the class members in proportion to their shares (spouse excluded) - Ja'fari rule.");
  };

  if (class1) {
    blockClass(CLASS2.concat(CLASS3), "Ja'fari: a nearer class (parents/children) excludes further classes entirely.");
    // hajb of the mother
    let bros = 0, sis = 0;
    for (const h of heirs) {
      if (h.isMuslim === false || h.causedDeath) continue;
      const cnt = h.count == null ? 1 : h.count;
      if (h.relationship === REL.FB || h.relationship === REL.PB) bros += cnt;
      if (h.relationship === REL.FS || h.relationship === REL.PS) sis += cnt;
    }
    const hajib = c(REL.FATHER) && (bros >= 2 || (bros >= 1 && sis >= 2) || sis >= 4);
    if (hajib) res.notes.push("Mother restricted to 1/6 (and excluded from radd) because of the father plus qualifying siblings (hajb al-umm).");
    if (hasKids) {
      if (c(REL.FATHER)) put(REL.FATHER, F(1, 6), "Father: 1/6 with children - Qur'an 4:11.");
      if (c(REL.MOTHER)) put(REL.MOTHER, F(1, 6), "Mother: 1/6 with children - Qur'an 4:11.");
      if (kidsM) {
        const fixed = fsum([...shares.values()].map((e) => e.f));
        const residue = ONE.sub(fixed);
        const units = 2 * kidsM + kidsF;
        const maleRel = c(REL.SON) ? REL.SON : REL.SONS_SON;
        const femRel = c(REL.SON) || c(REL.DAUGHTER) ? REL.DAUGHTER : REL.SONS_DAUGHTER;
        put(maleRel, residue.mul(F(2 * kidsM, units)), "Sons take the residue, 2:1 with daughters - Qur'an 4:11.");
        if (kidsF) put(femRel, residue.mul(F(kidsF, units)), "Daughters share the residue, 2:1 - Qur'an 4:11.");
      } else {
        const femRel = c(REL.DAUGHTER) ? REL.DAUGHTER : REL.SONS_DAUGHTER;
        const dShare = kidsF === 1 ? F(1, 2) : F(2, 3);
        put(femRel, dShare, "Daughter(s): 1/2 for one, 2/3 for two or more - Qur'an 4:11.");
        const total = fsum([...shares.values()].map((e) => e.f));
        if (total.gt(ONE)) {
          put(femRel, ONE.sub(total), "Ja'fari rejects awl: the deficiency falls on the daughter(s); parents and spouse keep full shares.");
          res.notes.push("Awl rejected (Ja'fari): deficiency borne by the daughter(s). Sunni schools would reduce all shares proportionally.");
        } else raddWithin(hajib ? [REL.MOTHER] : []);
      }
    } else {
      if (c(REL.MOTHER) && c(REL.FATHER)) {
        const m = hajib ? F(1, 6) : F(1, 3);
        put(REL.MOTHER, m, (hajib ? "Mother: 1/6 (restricted)" : "Mother: 1/3") +
          " - Ja'fari law takes the third from the whole estate (no umariyyatan reduction, unlike the Sunni schools).");
        put(REL.FATHER, ONE.sub(spShare).sub(m), "Father takes the remainder.");
      } else if (c(REL.MOTHER)) {
        put(REL.MOTHER, ONE.sub(spShare), "Mother as sole Class I heir: fixed third plus radd of the remainder.");
        res.radd = true;
      } else if (c(REL.FATHER)) {
        put(REL.FATHER, ONE.sub(spShare), "Father as sole Class I heir takes the remainder.");
      }
    }
  } else if (class2) {
    blockClass(CLASS3, "Ja'fari: Class II (grandparents/siblings) excludes Class III (uncles/aunts).");
    const ut = c(REL.MB) + c(REL.MS);
    const matGp = c(REL.MGM);
    let patLineUnits = (c(REL.FB) || c(REL.FS))
      ? 2 * c(REL.FB) + c(REL.FS)
      : 2 * c(REL.PB) + c(REL.PS);
    if (c(REL.FB) || c(REL.FS)) {
      for (const r of [REL.PB, REL.PS])
        if (n[r]) { res.blocked.push({ relationship: r, count: n[r], reason: "Ja'fari: full siblings exclude consanguine siblings." }); delete n[r]; }
    }
    if (c(REL.FNEPHEW) || c(REL.PNEPHEW)) {
      if (patLineUnits || ut) {
        for (const r of [REL.FNEPHEW, REL.PNEPHEW])
          if (n[r]) { res.blocked.push({ relationship: r, count: n[r], reason: "Ja'fari: siblings exclude siblings' children." }); delete n[r]; }
      } else {
        res.warnings.push("Siblings' children substitute for siblings per stirpes; approximated per capita - confirm with a scholar.");
        patLineUnits = 2 * (c(REL.FNEPHEW) + c(REL.PNEPHEW));
      }
    }
    let maternalPot = ZERO;
    if (ut || matGp) {
      const heads = ut + matGp;
      maternalPot = heads === 1 ? F(1, 6) : F(1, 3);
      for (const r of [REL.MB, REL.MS, REL.MGM])
        if (c(r)) put(r, maternalPot.mul(F(c(r))).div(F(heads)),
          "Maternal line (uterine siblings / maternal grandparent): 1/6 for one, 1/3 shared equally - Qur'an 4:12; Sistani.");
    }
    const remainder = ONE.sub(spShare).sub(maternalPot);
    const patMembers = patLineUnits || c(REL.GRANDFATHER) || c(REL.PGM);
    if (patMembers) {
      const units = patLineUnits + (c(REL.GRANDFATHER) ? 2 : 0) + (c(REL.PGM) ? 1 : 0);
      const sistersOnly = units && !c(REL.FB) && !c(REL.PB) && !c(REL.GRANDFATHER) && !c(REL.PGM);
      if (sistersOnly) {
        const sf = c(REL.FS) || c(REL.PS);
        const rel = c(REL.FS) ? REL.FS : REL.PS;
        const fard = sf === 1 ? F(1, 2) : F(2, 3);
        const got = fard.lt(remainder) ? fard : remainder;
        put(rel, got, "Sister(s): fixed share; Ja'fari rejects awl, so any deficiency falls here, and any surplus returns by radd.");
        if (got.lt(fard)) res.notes.push("Awl rejected (Ja'fari): deficiency borne by the sister(s).");
      } else {
        const table = [[REL.FB, 2], [REL.FS, 1], [REL.PB, 2], [REL.PS, 1],
          [REL.GRANDFATHER, 2], [REL.PGM, 1], [REL.FNEPHEW, 2], [REL.PNEPHEW, 2]];
        for (const [r, u] of table)
          if (c(r)) put(r, remainder.mul(F(u * c(r), units)),
            "Paternal line of Class II shares the remainder, male:female 2:1 (Sistani).");
      }
      if ((c(REL.GRANDFATHER) && (ut || matGp)) || (matGp && patLineUnits))
        res.warnings.push("Mixed grandparents and siblings across maternal and paternal lines involve additional Ja'fari detail - confirm the result with a scholar.");
    }
    // radd within class (exclude maternal line if paternal-line sisters took fard)
    raddWithin();
  } else if (class3) {
    res.warnings.push("Class III (uncles/cousins) distribution is simplified here - confirm with a scholar.");
    const remainder = ONE.sub(spShare);
    const seq = [[REL.FUNCLE, "Full paternal uncles take; they exclude consanguine uncles (Ja'fari)."],
      [REL.PUNCLE, "Consanguine paternal uncles."],
      [REL.FCOUSIN, "Uncles' sons substitute for uncles."],
      [REL.PCOUSIN, "Uncles' sons substitute."]];
    let taken = false;
    for (const [r, why] of seq) {
      if (!taken && c(r)) { put(r, remainder, why); taken = true; }
      else if (taken && n[r]) {
        res.blocked.push({ relationship: r, count: n[r], reason: "Excluded by a nearer Class III heir." });
        delete n[r];
      }
    }
  } else {
    if (c(REL.HUSBAND)) {
      put(REL.HUSBAND, F(1, 2), "Radd: husband as sole heir takes the entire estate (fixed half plus return of the remainder) - Sistani.");
      res.radd = true;
    } else if (c(REL.WIFE)) {
      res.warnings.push("Wife as sole heir: the remaining three-quarters are, per the dominant opinion, handled under the ruling of the marja' - consult a scholar.");
    } else {
      res.warnings.push("No faraid heirs found. The estate should be dealt with by wasiyya and scholar guidance.");
    }
  }
  const out = [];
  for (const rel of ORDER)
    if (shares.has(rel)) {
      const e = shares.get(rel);
      out.push({ relationship: rel, count: n[rel] || 1, total: e.f, reason: e.reason, residuary: false });
    }
  res.shares = out;
  return res;
}

/* ---------- estate ---------- */
const WASIYYA_CAP = F(1, 3);
function settleEstate(e) {
  const get = (k) => e[k] == null ? ZERO : (e[k] instanceof Frac ? e[k] : F(Math.round(Number(e[k]) * 100), 100));
  const gross = get("grossEstate"), wasF = e.wasiyyaFraction instanceof Frac ? e.wasiyyaFraction : (e.wasiyyaFraction ? F(Math.round(Number(e.wasiyyaFraction) * 10000), 10000) : ZERO);
  for (const k of ["grossEstate", "funeralCosts", "debts", "unpaidMahr", "unpaidZakat", "kaffarat", "fidya"])
    if (get(k).lt(ZERO)) throw new FaraidError(k + " cannot be negative");
  if (wasF.lt(ZERO) || wasF.gt(WASIYYA_CAP))
    throw new FaraidError("The wasiyya (bequest) may not exceed one-third of the net estate (hadith of Sa'd ibn Abi Waqqas - Bukhari 2742, Muslim 1628).");
  const deductions = fsum(["funeralCosts", "debts", "unpaidMahr", "unpaidZakat", "kaffarat", "fidya"].map(get));
  if (deductions.gt(gross))
    throw new FaraidError("Deductions (funeral costs and debts) exceed the gross estate; there is nothing to distribute.");
  const net = gross.sub(deductions);
  const wasiyya = net.mul(wasF);
  return { gross, deductions, net, wasiyya, distributable: net.sub(wasiyya) };
}

function calculate(madhhab, heirs, settings) {
  if (madhhab === "jafari") return calculateJafari(heirs, settings);
  if (!["hanafi", "maliki", "shafii", "hanbali"].includes(madhhab))
    throw new FaraidError("Unknown madhhab: " + madhhab);
  return calculateSunni(madhhab, heirs, settings);
}

const ENGINE = { calculate, settleEstate, Frac, F, REL, FaraidError,
  version: "1.0.0-js" };
if (typeof module !== "undefined") module.exports = ENGINE;
if (typeof window !== "undefined") window.FaraidEngine = ENGINE;
