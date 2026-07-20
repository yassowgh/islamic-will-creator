/* Wizard logic, validation, auth, persistence. Engine: engine.js */
"use strict";
const $ = (id) => document.getElementById(id);
const STEPS = ["step-you","step-estate","step-wasiyya","step-family",
  "step-executor","step-results","step-will","step-download"];
const NAMES = ["About you","Estate","Wasiyya","Family","Executor","Shares","Will","Download"];
const HINTS = {hanafi:"Largest school in the UK; grandfather excludes siblings.",
 maliki:"Grandfather shares with siblings (best-of rule).",
 shafii:"Grandfather shares with siblings; mushtaraka applied.",
 hanbali:"Close to Shafi'i on grandfather; no mushtaraka.",
 jafari:"Class system; no awl; spouse always inherits."};
const NAMEABLE = ["husband","wife","son","daughter","father","mother",
  "full_brother","full_sister","paternal_brother","paternal_sister",
  "maternal_brother","maternal_sister"];
let cur = 0, pie = null, lastResult = null, lastEstate = null;
let user = null, db = null, status = "created", pcValid = false, pcChecked = "";

/* ---------- auth ---------- */
const fbReady = !!(window.FIREBASE_CONFIG && window.firebase);
if (fbReady) {
  firebase.initializeApp(window.FIREBASE_CONFIG);
  db = firebase.firestore();
  firebase.auth().onAuthStateChanged(async (u) => {
    user = u;
    renderUserbox();
    if (u) { await loadWill(); showWizard(); }
    else showGate();
  });
} else {
  showWizard();
  renderUserbox();
}
function showGate(){ $("authgate").hidden = false; $("wizard").hidden = true; }
function showWizard(){ $("authgate").hidden = true; $("wizard").hidden = false; renderSteps(); }
function renderUserbox(){
  const b = $("userbox");
  if (!fbReady) { b.innerHTML = '<span class="hint" style="color:#fff">Guest mode — sign-in not yet enabled</span>'; return; }
  b.innerHTML = user
    ? `${user.email} <button class="btn sec" id="outBtn">Sign out</button>`
    : "";
  if (user) $("outBtn").onclick = () => firebase.auth().signOut();
}
if (fbReady) {
  $("loginBtn").onclick = () => authAct("signInWithEmailAndPassword");
  $("signupBtn").onclick = () => authAct("createUserWithEmailAndPassword");
}
async function authAct(method){
  $("authErr").innerHTML = "";
  try { await firebase.auth()[method]($("authEmail").value.trim(), $("authPass").value); }
  catch (e) { $("authErr").innerHTML = `<div class="errbox">${e.message}</div>`; }
}

/* ---------- persistence ---------- */
function collectState(){
  const s = { fields: {}, status, savedAt: new Date().toISOString() };
  document.querySelectorAll("#wizard input, #wizard select, #wizard textarea").forEach((el) => {
    if (el.type === "file") return;
    s.fields[el.id] = el.type === "checkbox" ? el.checked : el.value;
  });
  return s;
}
function applyState(s){
  if (!s || !s.fields) return;
  for (const [id, v] of Object.entries(s.fields)) {
    const el = $(id); if (!el) continue;
    if (el.type === "checkbox") el.checked = !!v; else el.value = v;
  }
  status = s.status || "created";
  ["gender","spouseKind"].forEach(()=>{});
  onGender(); onWasiyya(); onMinorsInputs(); onOutside(); renderHeirNames();
}
async function saveWill(){
  if (!user || !db) return;
  try { await db.collection("users").doc(user.uid).collection("wills")
      .doc("current").set(collectState(), { merge: true }); }
  catch (e) { console.warn("save failed", e); }
}
async function loadWill(){
  if (!user || !db) return;
  try {
    const d = await db.collection("users").doc(user.uid).collection("wills").doc("current").get();
    if (d.exists) applyState(d.data());
  } catch (e) { console.warn("load failed", e); }
}

/* ---------- steps ---------- */
function renderSteps(){
  const bar = $("stepsbar"); bar.innerHTML = "";
  STEPS.forEach((s,i)=>{const b=document.createElement("button");
    b.textContent=(i+1)+". "+NAMES[i];
    b.className=i===cur?"active":i<cur?"done":"";
    b.onclick=()=>{ if (i<cur || validateUpTo(i)) go(i); };
    bar.appendChild(b);});
  STEPS.forEach((s,i)=>$(s).hidden=i!==cur);
  $("prevBtn").style.visibility=cur===0?"hidden":"visible";
  $("nextBtn").textContent=cur===STEPS.length-1?"Finish":"Next";
}
function go(i){
  cur=Math.max(0,Math.min(STEPS.length-1,i));
  $("stepErr").innerHTML="";
  if(STEPS[cur]==="step-family")renderSpouseBlock();
  if(STEPS[cur]==="step-results")runCalc();
  if(STEPS[cur]==="step-will")renderWill();
  if(STEPS[cur]==="step-download")renderDownload();
  renderSteps();window.scrollTo(0,0);
  saveWill();
}
window.go = go;
$("prevBtn").onclick=()=>go(cur-1);
$("nextBtn").onclick=()=>{
  if(cur===STEPS.length-1){ alert("Your will is saved" + (user?" to your account.":" in this browser.")); return; }
  const errs = validateStep(STEPS[cur]);
  if (errs.length){ $("stepErr").innerHTML = `<div class="errbox">${errs.join("<br>")}</div>`; window.scrollTo(0,0); return; }
  go(cur+1);
};
function validateUpTo(target){
  for (let i=0;i<target;i++){
    const errs = validateStep(STEPS[i]);
    if (errs.length){ cur=i; renderSteps(); $("stepErr").innerHTML=`<div class="errbox">${errs.join("<br>")}</div>`; return false; }
  }
  return true;
}

/* ---------- validation ---------- */
const emailOk = (v) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v);
function mark(id, bad){ $(id).classList.toggle("invalid", !!bad); }
function age(dobStr){
  const d = new Date(dobStr), now = new Date();
  let a = now.getFullYear()-d.getFullYear();
  if (now.getMonth()<d.getMonth() || (now.getMonth()===d.getMonth() && now.getDate()<d.getDate())) a--;
  return a;
}
function validateStep(step){
  const errs = [];
  if (step==="step-you"){
    mark("fullName", !$("fullName").value.trim());
    if (!$("fullName").value.trim()) errs.push("Full legal name is required.");
    mark("gender", !$("gender").value);
    if (!$("gender").value) errs.push("Please select your gender — it determines the spouse questions and some shares.");
    mark("dob", !$("dob").value);
    if (!$("dob").value) errs.push("Date of birth is required.");
    else if (age($("dob").value) < 18){ mark("dob",1); errs.push("You must be 18 or over to make a will in England & Wales."); }
    mark("address", !$("address").value.trim());
    if (!$("address").value.trim()) errs.push("Address is required.");
    if (!$("outsideUK").checked){
      const pc = $("postcode").value.trim().toUpperCase();
      mark("postcode", !pc || !pcValid || pcChecked!==pc);
      if (!pc) errs.push("Postcode is required for UK addresses.");
      else if (pcChecked!==pc || !pcValid) errs.push("Postcode not recognised — pick one from the suggestions or check it.");
    }
  }
  if (step==="step-estate"){
    if (!(+$("gross").value > 0)){ mark("gross",1); errs.push("Please give an estimated gross estate value."); }
    else mark("gross",0);
  }
  if (step==="step-wasiyya"){
    if (+$("wasiyya").value > 0 && !$("wasiyyaTo").value.trim())
      errs.push("Please name the recipient(s) of your bequest (or set it back to 0%).");
  }
  if (step==="step-family"){
    const kids = (+$("son").value||0)+(+$("daughter").value||0);
    if (kids>0 && $("minors").value===""){ errs.push("Please say how many of your children are under 18 (0 if none)."); }
    if (+$("minors").value > kids) errs.push("Under-18 count cannot exceed the number of children.");
    const total = heirsFromForm().length;
    if (!total) errs.push("Add at least one heir (or your estate would have no faraid heirs — speak to a scholar).");
  }
  if (step==="step-executor"){
    if (!$("execName").value.trim()){ mark("execName",1); errs.push("An executor is required."); } else mark("execName",0);
    if (minorsCount()>0 && !$("guardian").value.trim()){ mark("guardian",1); errs.push("You have children under 18 — please appoint a guardian."); } else mark("guardian",0);
    if (!$("w1").value.trim() || !$("w2").value.trim()) errs.push("Two witnesses are required.");
    for (const [id,label] of [["execEmail","Executor"],["exec2Email","Backup executor"],["guardianEmail","Guardian"],["w1Email","Witness 1"],["w2Email","Witness 2"]]){
      if (!emailOk($(id).value)){ mark(id,1); errs.push(label+" email looks invalid."); } else mark(id,0);
    }
    const conflicts = witnessConflicts();
    if (conflicts.length) errs.push("Witness problem (Wills Act 1837 s.15): "+conflicts.join("; "));
  }
  return errs;
}
function witnessConflicts(){
  const heirNames = [];
  NAMEABLE.forEach((r)=>{ const el=$("names_"+r); if (el && el.value.trim())
    el.value.split(",").forEach((n)=>heirNames.push(n.trim().toLowerCase())); });
  const out=[];
  [["w1","Witness 1"],["w2","Witness 2"]].forEach(([id,label])=>{
    const v=$(id).value.trim().toLowerCase();
    if (v && heirNames.includes(v)) out.push(label+" ("+$(id).value+") appears to be a beneficiary — their gift would fail");
  });
  if ($("w1").value.trim() && $("w1").value.trim().toLowerCase()===$("w2").value.trim().toLowerCase())
    out.push("the two witnesses must be different people");
  return out;
}

/* ---------- postcode (postcodes.io - free UK API) ---------- */
let pcTimer=null;
$("postcode").addEventListener("input", ()=>{
  const q=$("postcode").value.trim();
  pcValid=false; $("pcStatus").textContent="";
  clearTimeout(pcTimer);
  if (q.length<2) return;
  pcTimer=setTimeout(async ()=>{
    try{
      const r=await fetch("https://api.postcodes.io/postcodes/"+encodeURIComponent(q)+"/autocomplete");
      const j=await r.json();
      $("pcList").innerHTML=(j.result||[]).map((p)=>`<option value="${p}">`).join("");
      const v=await fetch("https://api.postcodes.io/postcodes/"+encodeURIComponent(q)+"/validate");
      const jv=await v.json();
      pcValid=!!jv.result; pcChecked=q.toUpperCase();
      if (pcValid){
        const info=await (await fetch("https://api.postcodes.io/postcodes/"+encodeURIComponent(q))).json();
        const rr=info.result||{};
        $("pcStatus").textContent="✓ "+[rr.admin_district,rr.region||rr.country].filter(Boolean).join(", ");
      } else $("pcStatus").textContent="Keep typing — pick a suggestion";
    }catch(e){ $("pcStatus").textContent="Could not check postcode (offline?)"; }
  }, 350);
});
$("outsideUK").onchange=onOutside;
function onOutside(){
  $("outsideWarn").hidden=!$("outsideUK").checked;
  $("pcDiv").style.display=$("outsideUK").checked?"none":"";
}

/* ---------- family / gender ---------- */
$("gender").onchange=onGender;
function onGender(){ renderSpouseBlock(); }
function renderSpouseBlock(){
  const g=$("gender").value;
  const host=$("spouseBlock");
  const prev={kind:host.dataset.kind||"none",wives:host.dataset.wives||"1"};
  if (!g){ host.innerHTML='<div class="hint">Select your gender in step 1 to answer the spouse question.</div>'; return; }
  const q=g==="male"
    ? `<h3>Spouse</h3><div class="row"><div><label>Are you married?</label>
       <select id="spouseKind"><option value="none">Not married</option><option value="wife">Yes — I have a wife / wives</option></select></div>
       <div id="wivesN" hidden><label>Number of wives (1–4)</label><input id="wives" type="number" min="1" max="4" value="${prev.wives}"></div></div>`
    : `<h3>Spouse</h3><div class="row"><div><label>Are you married?</label>
       <select id="spouseKind"><option value="none">Not married</option><option value="husband">Yes — I have a husband</option></select></div></div>`;
  host.innerHTML=q;
  $("spouseKind").value=prev.kind==="none"?"none":(g==="male"?"wife":"husband");
  $("spouseKind").onchange=()=>{
    host.dataset.kind=$("spouseKind").value;
    if ($("wivesN")) $("wivesN").hidden=$("spouseKind").value!=="wife";
    renderHeirNames();
  };
  if ($("wives")) $("wives").oninput=()=>host.dataset.wives=$("wives").value;
  if ($("wivesN")) $("wivesN").hidden=$("spouseKind").value!=="wife";
}
["son","daughter"].forEach((id)=>$(id).addEventListener("input",onMinorsInputs));
function onMinorsInputs(){
  const kids=(+$("son").value||0)+(+$("daughter").value||0);
  $("minorsDiv").hidden=kids===0;
  $("minorsWarn").hidden=!(minorsCount()>0);
  renderHeirNames();
}
$("minors").addEventListener("input",()=>{ $("minorsWarn").hidden=!(minorsCount()>0); updateGuardianRequired(); });
function minorsCount(){ return +$("minors").value||0; }
function updateGuardianRequired(){
  $("guardianLabel").textContent="Guardian for minor children"+(minorsCount()>0?" *":" (none needed)");
}
document.querySelectorAll("#step-family input[type=number]").forEach((el)=>el.addEventListener("input",renderHeirNames));
function renderHeirNames(){
  const host=$("heirNames"); if (!host) return;
  let html="";
  for (const r of NAMEABLE){
    let count=0;
    if (r==="husband") count=($("spouseKind") && $("spouseKind").value==="husband")?1:0;
    else if (r==="wife") count=($("spouseKind") && $("spouseKind").value==="wife")?(+($("wives")&&$("wives").value)||1):0;
    else if (r==="father"||r==="mother") count=+$(r).value||0;
    else count=+$(r).value||0;
    if (count>0){
      const old=$("names_"+r); const oldV=old?old.value:"";
      html+=`<label>${count>1?count+" × ":""}${pretty(r)} name${count>1?"s (comma-separated)":""}</label>
             <input id="names_${r}" value="${oldV.replace(/"/g,"&quot;")}" placeholder="${count>1?"e.g. Ahmed, Sara":"full name"}">`;
    }
  }
  host.innerHTML=html||'<div class="hint">Add family members above and name fields appear here.</div>';
}

/* ---------- calc ---------- */
$("madhhab").onchange=()=>$("madhhabHint").textContent=HINTS[$("madhhab").value];
$("madhhab").onchange();
$("wasiyya").oninput=onWasiyya;
function onWasiyya(){
  $("wasiyyaVal").textContent=Number($("wasiyya").value).toFixed(2)+"%";
  $("wasiyyaToDiv").hidden=!(+$("wasiyya").value>0);
}
function heirsFromForm(){
  const h=[];
  const kind=$("spouseKind")?$("spouseKind").value:"none";
  if(kind==="husband")h.push({relationship:"husband"});
  if(kind==="wife")h.push({relationship:"wife",count:Math.min(4,Math.max(1,+($("wives")&&$("wives").value)||1))});
  ["son","daughter","sons_son","sons_daughter","full_brother","full_sister",
   "paternal_brother","paternal_sister","maternal_brother","maternal_sister",
   "full_brothers_son","paternal_brothers_son","full_paternal_uncle",
   "paternal_paternal_uncle"].forEach((r)=>{const v=+$(r).value||0;if(v>0)h.push({relationship:r,count:v});});
  ["father","mother","paternal_grandfather","paternal_grandmother",
   "maternal_grandmother"].forEach((r)=>{if($(r).value==="1")h.push({relationship:r});});
  return h;
}
function namesFor(rel,count){
  const el=$("names_"+rel);
  if (!el || !el.value.trim()) return null;
  const parts=el.value.split(",").map((s)=>s.trim()).filter(Boolean);
  return parts.slice(0,count);
}
function runCalc(){
  const E=window.FaraidEngine;$("calcError").innerHTML="";
  try{
    lastEstate=E.settleEstate({grossEstate:+$("gross").value||0,funeralCosts:+$("funeral").value||0,
      debts:+$("debts").value||0,unpaidMahr:+$("mahr").value||0,unpaidZakat:+$("zakat").value||0,
      kaffarat:+$("kaffarat").value||0,wasiyyaFraction:(+$("wasiyya").value||0)/100});
    lastResult=E.calculate($("madhhab").value,heirsFromForm());
  }catch(e){$("calcError").innerHTML='<div class="errbox">'+e.message+'</div>';lastResult=null;return;}
  const r=lastResult,est=lastEstate,dist=est.distributable.toNumber();
  let rows="<table><tr><th>Heir</th><th>Share</th><th>%</th><th>£</th><th>Why</th></tr>";
  const labels=[],data=[];
  for(const s of r.shares){
    if(s.total.isZero())continue;
    const pct=s.total.toNumber()*100;
    const nm=namesFor(s.relationship,s.count);
    const disp=(nm?nm.join(", ")+" — ":"")+pretty(s.relationship)+(s.count>1?" ×"+s.count:"");
    labels.push(nm?nm.join(", "):pretty(s.relationship));data.push(pct);
    rows+=`<tr><td>${disp}</td><td>${s.total.toString()}</td><td>${pct.toFixed(2)}%</td><td>£${(dist*s.total.toNumber()).toLocaleString(undefined,{maximumFractionDigits:0})}</td><td style="font-size:.78rem">${s.reason}</td></tr>`;
  }
  rows+="</table>";
  rows=`<p style="font-size:.85rem">Net estate £${est.net.toNumber().toLocaleString()}${est.wasiyya.toNumber()>0?" − wasiyya £"+est.wasiyya.toNumber().toLocaleString(undefined,{maximumFractionDigits:0}):""} = <b>£${dist.toLocaleString(undefined,{maximumFractionDigits:0})} distributable</b>${r.awl?" · <b>awl applied</b>":""}${r.radd?" · <b>radd applied</b>":""}</p>`+rows;
  $("resultsTable").innerHTML=rows;
  $("blockedList").innerHTML=r.blocked.length?"<h3>Not inheriting (with reason)</h3><ul style='font-size:.82rem'>"+r.blocked.map((b)=>`<li><b>${pretty(b.relationship)}${b.count>1?" ×"+b.count:""}</b> — ${b.reason}</li>`).join("")+"</ul>":"";
  $("notesList").innerHTML=[...r.notes.map((x)=>`<div class="edu">${x}</div>`),...r.warnings.map((x)=>`<div class="warnbox">${x}</div>`)].join("");
  if(pie)pie.destroy();
  pie=new Chart($("pie"),{type:"pie",data:{labels,datasets:[{data}]},
    options:{plugins:{legend:{position:"bottom",labels:{font:{size:11}}}}}});
}
$("editSharesBtn").onclick=()=>{
  modal(`<h2 style="color:var(--err)">Shares cannot be edited by hand</h2>
  <p style="font-size:.9rem">These percentages are fixed by the Qur'an (4:11, 4:12, 4:176) and the rules of the
  <b>${$("madhhab").options[$("madhhab").selectedIndex].text}</b> school. Changing them manually would make the
  distribution un-Islamic.</p>
  <p style="font-size:.9rem">What you <i>can</i> do: change your <b>school (madhhab)</b> in step 1 — schools differ on some
  family situations — or provide for extra people through the <b>wasiyya</b> (up to one-third, step 3), or correct your
  family details (step 4). The shares recalculate automatically.</p>`);
};
function modal(html){
  $("modalHost").innerHTML=`<div class="modal-bg" onclick="this.remove()"><div class="modal" onclick="event.stopPropagation()">${html}<p style="text-align:right"><button class="btn" onclick="document.querySelector('.modal-bg').remove()">Close</button></p></div></div>`;
}
function pretty(r){return r.replace(/_/g," ").replace(/\b\w/g,(c)=>c.toUpperCase())
  .replace("Sons Son","Son's son").replace("Sons Daughter","Son's daughter")
  .replace("Brothers Son","brother's son").replace("Uncles Son","uncle's son");}

/* ---------- will document ---------- */
function renderWill(){
  if(!lastResult)runCalc();
  const r=lastResult,est=lastEstate;if(!r)return;
  const name=$("fullName").value||"[FULL LEGAL NAME]";
  const addr=$("address").value+($("outsideUK").checked?"":", "+$("postcode").value.toUpperCase());
  const dob=$("dob").value||"[DATE OF BIRTH]";
  const school=$("madhhab").options[$("madhhab").selectedIndex].text;
  const wasPct=Number($("wasiyya").value)||0;
  let sched="";
  for(const s of r.shares){ if(s.total.isZero())continue;
    const nm=namesFor(s.relationship,s.count);
    const label=nm?`${nm.join(", ")} (my ${pretty(s.relationship).toLowerCase()}${s.count>1?"s":""})`:`my ${pretty(s.relationship).toLowerCase()}${s.count>1?"s ("+s.count+", shared)":""}`;
    sched+=`   ${label}: ${s.total.toString()} (${(s.total.toNumber()*100).toFixed(2)}%)\n`;
  }
  const clauses=[];
  clauses.push(`1. DECLARATION OF FAITH. I declare that I am a Muslim. I direct that my estate be distributed in accordance with the Islamic law of inheritance of the ${school} school, as set out in this will.`);
  clauses.push(`2. REVOCATION. I revoke all former wills and codicils made by me.`);
  clauses.push(`3. EXECUTORS. I appoint ${$("execName").value||"[EXECUTOR]"}${$("execEmail").value?" ("+$("execEmail").value+")":""} as my executor and trustee${$("exec2Name").value?`; if unable or unwilling, I appoint ${$("exec2Name").value}${$("exec2Email").value?" ("+$("exec2Email").value+")":""} in substitution`:""}. My executors shall have the standard administrative powers of personal representatives, including the powers in the Trustee Act 2000.`);
  let n=4;
  if (minorsCount()>0)
    clauses.push(`${n++}. GUARDIANSHIP. ${minorsCount()} of my children are under 18. If at my death any of my children are under 18 and no other person has parental responsibility, I appoint ${$("guardian").value||"[GUARDIAN]"}${$("guardianEmail").value?" ("+$("guardianEmail").value+")":""} to be their guardian.`);
  clauses.push(`${n++}. FUNERAL WISHES. ${$("funeralWishes").value}`);
  clauses.push(`${n++}. PAYMENT OF DEBTS FIRST. My executors shall first pay my funeral and burial expenses and then all my debts, including any unpaid mahr, unpaid zakat, kaffarat and fidya, before any distribution.`);
  if (wasPct>0)
    clauses.push(`${n++}. WASIYYA (BEQUEST). I give ${wasPct.toFixed(2)}% of my net estate (not exceeding one-third) to: ${$("wasiyyaTo").value}. If any recipient is also an heir under the Schedule, that gift shall take effect only with the consent of my other heirs, per classical Islamic law.`);
  const estNotes=$("estateNotes").value.trim();
  clauses.push(`${n++}. RESIDUARY ESTATE. My executors shall distribute the residue of my estate${estNotes?` (including, without limitation: ${estNotes})`:""} in accordance with the Schedule of Faraid Shares below, calculated per the ${school} school${r.awl?" (awl applied)":""}${r.radd?" (radd applied)":""}. If the family circumstances at my death differ from the Schedule, or any named heir predeceases me, my residuary estate shall instead be distributed in accordance with the Islamic law of inheritance of the ${school} school as determined by a qualified Islamic scholar chosen by my executors.`);
  clauses.push(`${n++}. INHERITANCE ACT NOTE. I am aware that under the Inheritance (Provision for Family and Dependants) Act 1975 certain dependants may claim against my estate notwithstanding this will.`);
  clauses.push(`${n++}. ATTESTATION. Signed by me, ${name}, in the joint presence of the two witnesses named below, who each signed in my presence and in the presence of each other (Wills Act 1837, s.9).`);
  $("willdoc").textContent=
`LAST WILL AND TESTAMENT

of ${name}, of ${addr}, born ${dob}.

${clauses.join("\n\n")}

SCHEDULE OF FARAID SHARES (calculated ${new Date().toISOString().slice(0,10)}, engine v1.0.0)
${sched}

Signature of testator: _________________________    Date: ______________


WITNESS 1 (must not be a beneficiary or a beneficiary's spouse)
Name: ${$("w1").value||"____________________"}   Signature: __________________
Address: ______________________________   Occupation: ________________

WITNESS 2 (must not be a beneficiary or a beneficiary's spouse)
Name: ${$("w2").value||"____________________"}   Signature: __________________
Address: ______________________________   Occupation: ________________

------------------------------------------------------------------
Generated by a software tool - not legal or religious advice. Have it
reviewed by a qualified solicitor and a qualified scholar before signing.`;
}

/* ---------- download & upload ---------- */
const STATUSES=["created","downloaded","signed_uploaded"];
const STATUS_LABELS={created:"Will created",downloaded:"Downloaded / printed",signed_uploaded:"Signed copy uploaded"};
function renderDownload(){
  const idx=STATUSES.indexOf(status);
  $("statusTrack").innerHTML=STATUSES.map((s,i)=>`<span class="${i<=idx?"on":""}">${STATUS_LABELS[s]}</span>`).join("");
  $("uploadBlock").style.display=fbReady&&user?"":"none";
  if (!(fbReady&&user)) $("uploadStatus").innerHTML='<div class="hint">Sign in to store the signed copy in your account.</div>';
}
$("downloadBtn").onclick=()=>{
  renderWill();
  if (STATUSES.indexOf(status)<1){ status="downloaded"; saveWill(); }
  renderDownload();
  go(6); setTimeout(()=>window.print(),300);
};
$("uploadBtn").onclick=async ()=>{
  if (!user||!db) return;
  const files=[...$("scanFiles").files];
  if (!files.length){ $("uploadStatus").innerHTML='<div class="errbox">Choose photo(s) of the signed will first.</div>'; return; }
  $("uploadStatus").innerHTML='<div class="hint">Uploading…</div>';
  try{
    const col=db.collection("users").doc(user.uid).collection("wills").doc("current").collection("signedPages");
    let page=0;
    for (const f of files){
      const dataUrl=await compressImage(f, 1400, 0.8);
      if (dataUrl.length>900000) throw new Error(f.name+" is too large even after compression - retake at lower resolution.");
      await col.doc("page"+(++page)+"_"+Date.now()).set({name:f.name,dataUrl,at:new Date().toISOString()});
    }
    status="signed_uploaded"; await saveWill(); renderDownload();
    $("uploadStatus").innerHTML=`<div class="edu">Uploaded ${files.length} page(s) to your account. Keep the paper original safe.</div>`;
  }catch(e){ $("uploadStatus").innerHTML=`<div class="errbox">Upload failed: ${e.message}</div>`; }
};
function compressImage(file, maxW, q){
  return new Promise((resolve,reject)=>{
    const img=new Image();
    img.onload=()=>{
      const scale=Math.min(1,maxW/img.width);
      const cv=document.createElement("canvas");
      cv.width=Math.round(img.width*scale); cv.height=Math.round(img.height*scale);
      cv.getContext("2d").drawImage(img,0,0,cv.width,cv.height);
      resolve(cv.toDataURL("image/jpeg",q));
    };
    img.onerror=reject;
    img.src=URL.createObjectURL(file);
  });
}

/* ---------- init ---------- */
onWasiyya(); onOutside(); onMinorsInputs(); updateGuardianRequired(); renderHeirNames(); renderSteps();
setInterval(saveWill, 30000);
