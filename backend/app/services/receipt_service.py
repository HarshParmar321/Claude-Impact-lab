"""Public Repair Receipt and citizen durability feedback (spec §11)."""

from __future__ import annotations

from sqlmodel import Session, select

from app.calculations import audit as audit_calc
from app.models import DurabilityFeedback, OfficerDecision
from app.services import claude_service
from app.services.data_store import DataStore

LANGS = ("en", "mr", "hi", "hinglish")

ISSUE = {
    "pothole": {"en": "pothole", "mr": "खड्डा", "hi": "गड्ढे", "hinglish": "khadde"},
    "drain_cover": {"en": "missing or open drain cover", "mr": "गटाराचे उघडे झाकण", "hi": "नाले के खुले ढक्कन", "hinglish": "gutter ke khule dhakkan"},
    "waterlogging": {"en": "waterlogging", "mr": "पाणी साचणे", "hi": "जलभराव", "hinglish": "paani bharne"},
    "road_surface": {"en": "damaged road surface", "mr": "खराब रस्ता", "hi": "टूटी सड़क", "hinglish": "tooti sadak"},
}

SUMMARY = {
    "en": "A citizen reported a {issue} on {road} on {date}.",
    "mr": "{date} रोजी एका नागरिकाने {road} वर {issue} बद्दल तक्रार केली.",
    "hi": "{date} को एक नागरिक ने {road} पर {issue} की शिकायत की।",
    "hinglish": "{date} ko ek citizen ne {road} pe {issue} ki complaint ki.",
}
NO_COMPLAINT = {
    "en": "No citizen complaint is linked to this work order.",
    "mr": "या कामाच्या आदेशाशी कोणतीही नागरिक तक्रार जोडलेली नाही.",
    "hi": "इस कार्य आदेश से कोई नागरिक शिकायत जुड़ी नहीं है।",
    "hinglish": "Is work order se koi citizen complaint linked nahi hai.",
}

STATUS = {
    "RELEASE_PAYMENT": {
        "en": "Payment can be released — no open review issues",
        "mr": "देयक दिले जाऊ शकते — कोणतीही प्रलंबित तपासणी नाही",
        "hi": "भुगतान जारी किया जा सकता है — कोई लंबित जाँच नहीं",
        "hinglish": "Payment release ho sakta hai — koi pending review nahi",
    },
    "HOLD_FOR_EVIDENCE": {
        "en": "Payment on hold until supporting documents are checked",
        "mr": "सहाय्यक कागदपत्रे तपासेपर्यंत देयक थांबवले आहे",
        "hi": "सहायक दस्तावेज़ों की जाँच तक भुगतान रोका गया है",
        "hinglish": "Documents check hone tak payment hold pe hai",
    },
    "WARRANTY_REVIEW": {
        "en": "Sent to the Ward Warranty Desk — the road is still under a repair guarantee (DLP)",
        "mr": "वॉर्ड वॉरंटी कक्षाकडे पाठवले — रस्ता अजून दुरुस्ती हमी कालावधीत (DLP) आहे",
        "hi": "वार्ड वारंटी डेस्क को भेजा गया — सड़क अभी मरम्मत गारंटी अवधि (DLP) में है",
        "hinglish": "Ward Warranty Desk ko bheja gaya — road abhi repair guarantee (DLP) mein hai",
    },
}
STATUS_SOURCE = {
    "recommended": {"en": "Recommended; awaiting ward officer decision", "mr": "शिफारस; वॉर्ड अधिकाऱ्याच्या निर्णयाची प्रतीक्षा",
                    "hi": "सिफारिश; वार्ड अधिकारी के निर्णय की प्रतीक्षा", "hinglish": "Recommendation; ward officer ke decision ka intezaar"},
    "decided": {"en": "Ward officer decision", "mr": "वॉर्ड अधिकाऱ्याचा निर्णय", "hi": "वार्ड अधिकारी का निर्णय", "hinglish": "Ward officer ka decision"},
}

LABELS = {
    "en": dict(title="Public Repair Receipt", complaint="Complaint", work_order="Work order", road="Road", ward="Ward",
               contractor="Contractor named on work order", method="Repair method", completed="Completed", amount="Amount billed",
               sla="Completed within SLA", reopened="Reopened within 30 days", dlp="Repair guarantee (DLP)", status="Current status",
               evidence="Evidence completeness", sources="Source records", yes="Yes", no="No", active="Active until {d}", none="Not under DLP",
               survive_q="Did this repair survive?", survived="Yes, it is holding up", failed="No, the problem returned", unsure="Not sure",
               describe="Briefly describe what you see", photo="Photo reference (optional, demo only — not verified)", submit="Send report",
               disclaimer="A review is a routine check of records, not a finding of wrongdoing.", ask="Ask about this repair",
               original="Original complaint text"),
    "mr": dict(title="सार्वजनिक दुरुस्ती पावती", complaint="तक्रार", work_order="कामाचा आदेश", road="रस्ता", ward="वॉर्ड",
               contractor="कामाच्या आदेशावरील कंत्राटदार", method="दुरुस्ती पद्धत", completed="पूर्ण झाल्याची तारीख", amount="बिल केलेली रक्कम",
               sla="वेळेत (SLA) पूर्ण", reopened="३० दिवसांत पुन्हा उघडले", dlp="दुरुस्ती हमी (DLP)", status="सद्यस्थिती",
               evidence="पुराव्यांची पूर्णता", sources="स्रोत नोंदी", yes="होय", no="नाही", active="{d} पर्यंत लागू", none="DLP मध्ये नाही",
               survive_q="ही दुरुस्ती टिकली का?", survived="होय, व्यवस्थित आहे", failed="नाही, समस्या परत आली", unsure="खात्री नाही",
               describe="तुम्हाला काय दिसते ते थोडक्यात लिहा", photo="फोटो संदर्भ (ऐच्छिक, फक्त डेमो — पडताळलेला नाही)", submit="अहवाल पाठवा",
               disclaimer="तपासणी म्हणजे नोंदींची नियमित पडताळणी आहे, कोणावरही आरोप नाही.", ask="या दुरुस्तीबद्दल विचारा",
               original="मूळ तक्रार"),
    "hi": dict(title="सार्वजनिक मरम्मत रसीद", complaint="शिकायत", work_order="कार्य आदेश", road="सड़क", ward="वार्ड",
               contractor="कार्य आदेश पर ठेकेदार", method="मरम्मत विधि", completed="पूरा होने की तारीख", amount="बिल की गई राशि",
               sla="समय सीमा (SLA) में पूरा", reopened="30 दिनों में दोबारा खुला", dlp="मरम्मत गारंटी (DLP)", status="वर्तमान स्थिति",
               evidence="साक्ष्य की पूर्णता", sources="स्रोत रिकॉर्ड", yes="हाँ", no="नहीं", active="{d} तक लागू", none="DLP में नहीं",
               survive_q="क्या यह मरम्मत टिकी?", survived="हाँ, ठीक है", failed="नहीं, समस्या लौट आई", unsure="पता नहीं",
               describe="आप जो देख रहे हैं, संक्षेप में लिखें", photo="फोटो संदर्भ (वैकल्पिक, केवल डेमो — सत्यापित नहीं)", submit="रिपोर्ट भेजें",
               disclaimer="जाँच रिकॉर्ड की सामान्य पड़ताल है, किसी पर आरोप नहीं।", ask="इस मरम्मत के बारे में पूछें",
               original="मूल शिकायत"),
    "hinglish": dict(title="Public Repair Receipt", complaint="Complaint", work_order="Work order", road="Road", ward="Ward",
                     contractor="Work order pe contractor", method="Repair ka tareeka", completed="Kaam poora hua", amount="Bill ki gayi rakam",
                     sla="SLA ke andar poora", reopened="30 din mein dobara khula", dlp="Repair guarantee (DLP)", status="Abhi ka status",
                     evidence="Saboot kitne poore", sources="Source records", yes="Haan", no="Nahi", active="{d} tak active", none="DLP mein nahi",
                     survive_q="Kya yeh repair tika?", survived="Haan, theek hai", failed="Nahi, problem wapas aa gayi", unsure="Pata nahi",
                     describe="Jo dikh raha hai thoda sa likhiye", photo="Photo reference (optional, sirf demo — verify nahi hua)", submit="Report bhejiye",
                     disclaimer="Review sirf records ki routine jaanch hai, kisi pe ilzaam nahi.", ask="Is repair ke baare mein poochiye",
                     original="Asli complaint"),
}

METHOD = {
    "mastic_asphalt": {"en": "Mastic asphalt", "mr": "मॅस्टिक डांबर", "hi": "मैस्टिक डामर", "hinglish": "Mastic asphalt"},
    "hot_mix": {"en": "Hot mix asphalt", "mr": "हॉट मिक्स डांबर", "hi": "हॉट मिक्स डामर", "hinglish": "Hot mix"},
    "cold_mix": {"en": "Cold mix", "mr": "कोल्ड मिक्स", "hi": "कोल्ड मिक्स", "hinglish": "Cold mix"},
    "jet_patcher": {"en": "Jet patcher", "mr": "जेट पॅचर", "hi": "जेट पैचर", "hinglish": "Jet patcher"},
    "paver_block": {"en": "Paver blocks", "mr": "पेव्हर ब्लॉक", "hi": "पेवर ब्लॉक", "hinglish": "Paver block"},
    "precast_cover": {"en": "Precast drain cover", "mr": "प्रीकास्ट झाकण", "hi": "प्रीकास्ट ढक्कन", "hinglish": "Precast cover"},
    "ductile_iron_cover": {"en": "Ductile iron drain cover", "mr": "डक्टाइल लोखंडी झाकण", "hi": "डक्टाइल आयरन ढक्कन", "hinglish": "Ductile iron cover"},
}

RELATED = {
    "EARLIER": {"en": "Related earlier repair on the same road (duplicate-like record under review)",
                "mr": "याच रस्त्यावरील संबंधित आधीची दुरुस्ती (दुहेरी वाटणारी नोंद तपासणीत)",
                "hi": "इसी सड़क पर संबंधित पिछली मरम्मत (दोहराव जैसा रिकॉर्ड जाँच में)",
                "hinglish": "Isi road pe related pehle wali repair (duplicate jaisa record review mein)"},
    "LATER": {"en": "A later, similar repair record on the same road is under review",
              "mr": "याच रस्त्यावरील नंतरची, सारखी दुरुस्ती नोंद तपासणीत आहे",
              "hi": "इसी सड़क पर बाद का, मिलता-जुलता मरम्मत रिकॉर्ड जाँच में है",
              "hinglish": "Isi road pe baad ka, milta-julta repair record review mein hai"},
}

FEEDBACK_MSG = {
    "SURVIVED": {"en": "Thank you. Your confirmation has been recorded.", "mr": "धन्यवाद. तुमची पुष्टी नोंदवली आहे.",
                 "hi": "धन्यवाद। आपकी पुष्टि दर्ज कर ली गई है।", "hinglish": "Shukriya. Aapka confirmation record ho gaya hai."},
    "UNSURE": {"en": "Thank you. Your response has been recorded.", "mr": "धन्यवाद. तुमचा प्रतिसाद नोंदवला आहे.",
               "hi": "धन्यवाद। आपका जवाब दर्ज कर लिया गया है।", "hinglish": "Shukriya. Aapka jawab record ho gaya hai."},
    "FAILED_DLP": {"en": "Warranty review case {ref} created and routed to the Ward Warranty Desk to identify the original DLP owner. The contractor on this work order is not automatically held responsible.",
                   "mr": "वॉरंटी तपासणी प्रकरण {ref} तयार झाले असून मूळ DLP जबाबदार ओळखण्यासाठी वॉर्ड वॉरंटी कक्षाकडे पाठवले आहे. या आदेशावरील कंत्राटदाराला आपोआप जबाबदार धरले जात नाही.",
                   "hi": "वारंटी समीक्षा मामला {ref} बनाया गया और मूल DLP ज़िम्मेदार की पहचान के लिए वार्ड वारंटी डेस्क को भेजा गया। इस कार्य आदेश के ठेकेदार को अपने आप ज़िम्मेदार नहीं माना जाता।",
                   "hinglish": "Warranty review case {ref} ban gaya aur original DLP owner pata karne ke liye Ward Warranty Desk ko bheja gaya. Is work order ke contractor ko automatically zimmedaar nahi maana jaata."},
    "FAILED": {"en": "Repair-failure report {ref} sent to the ward engineer for physical inspection.",
               "mr": "दुरुस्ती अपयश अहवाल {ref} प्रत्यक्ष पाहणीसाठी वॉर्ड अभियंत्याकडे पाठवला आहे.",
               "hi": "मरम्मत विफलता रिपोर्ट {ref} भौतिक निरीक्षण के लिए वार्ड इंजीनियर को भेजी गई।",
               "hinglish": "Repair-failure report {ref} physical inspection ke liye ward engineer ko bheji gayi."},
}


def _lang(language: str) -> str:
    return language if language in LANGS else "en"


def receipt(store: DataStore, session: Session, wo_id: str, language: str = "en") -> dict | None:
    rec = store.work_order(wo_id)
    if rec is None:
        return None
    lang = _lang(language)
    road = store.road(rec["road_id"])
    L = LABELS[lang]
    complaint = store.complaint(rec["complaint_id"]) if rec["complaint_id"] else None
    if complaint:
        summary = SUMMARY[lang].format(issue=ISSUE[complaint["category"]][lang], road=road["road_name"], date=complaint["created_at"][:10])
    else:
        summary = NO_COMPLAINT[lang]
    decision = session.exec(select(OfficerDecision).where(OfficerDecision.work_order_id == wo_id).order_by(OfficerDecision.created_at.desc())).first()
    verdict = decision.final_verdict if decision else rec["recommended_verdict"]
    status_source = "decided" if decision else "recommended"
    feedback = session.exec(select(DurabilityFeedback).where(DurabilityFeedback.work_order_id == wo_id)).all()
    ev = audit_calc.evidence_completeness(rec)
    under_dlp = road["under_dlp"] == "Y"
    related = None
    d = store.duplicates
    hit = d[(d.flagged_id == wo_id) | (d.partner_id == wo_id)]
    if len(hit):
        h = hit.iloc[0]
        other_id = h.partner_id if h.flagged_id == wo_id else h.flagged_id
        other = store.work_order(other_id)
        oc = store.complaint(other["complaint_id"]) if other["complaint_id"] else None
        related = dict(work_order_id=other_id, relation=RELATED["EARLIER" if h.flagged_id == wo_id else "LATER"][lang],
                       completed_date=other["completed_date"], amount_inr=int(other["cost_inr"]),
                       complaint_summary=SUMMARY[lang].format(issue=ISSUE[oc["category"]][lang], road=road["road_name"], date=oc["created_at"][:10]) if oc else NO_COMPLAINT[lang],
                       complaint_id=oc["complaint_id"] if oc else None)
    sources = [wo_id, rec["road_id"], rec["contractor_id"], rec["rate_card_id"]] + ([rec["complaint_id"]] if rec["complaint_id"] else [])
    return dict(
        language=lang,
        labels=L,
        work_order_id=wo_id,
        complaint=dict(complaint_id=complaint["complaint_id"], language=complaint["language"], text_original=complaint["text_original"],
                       upvotes=int(complaint["upvotes"]), created_at=complaint["created_at"]) if complaint else None,
        complaint_summary=summary,
        road_id=rec["road_id"], road_name=road["road_name"], ward_code=rec["ward_code"],
        contractor_name=rec["contractor_name"], contractor_id=rec["contractor_id"],
        repair_method=METHOD.get(rec["repair_method"], {}).get(lang, rec["repair_method"]),
        completed_date=rec["completed_date"], amount_inr=int(rec["cost_inr"]),
        sla_met=rec["sla_met"] == "Y", reopened_within_30d=rec["reopened_within_30d"] == "Y",
        dlp=dict(under_dlp=under_dlp, dlp_end_date=road["dlp_end_date"] or None,
                 text=L["active"].format(d=road["dlp_end_date"]) if under_dlp else L["none"]),
        verdict=verdict, status_text=STATUS[verdict][lang], status_source=STATUS_SOURCE[status_source][lang],
        is_review_lead=bool(rec["is_review_lead"]),
        evidence_completeness_pct=ev["score_pct"],
        source_ids=sources,
        related=related,
        feedback_counts={a: sum(1 for f in feedback if f.answer == a) for a in ("SURVIVED", "FAILED", "UNSURE")},
        warranty_cases=[dict(case_reference=f.case_reference, created_at=f.created_at.isoformat(), routed_to=f.routed_to)
                        for f in feedback if f.generated_warranty_review],
        qr_note="Demo: this QR code points to the local receipt URL. Physical QR codes are a proposed future workflow, not deployed across Mumbai.",
    )


def submit_feedback(store: DataStore, session: Session, wo_id: str, answer: str, description: str, language: str,
                    photo_reference: str = "") -> dict:
    rec = store.work_order(wo_id)
    if rec is None:
        raise KeyError(wo_id)
    lang = _lang(language)
    road = store.road(rec["road_id"])
    fb = DurabilityFeedback(work_order_id=wo_id, answer=answer, description=description.strip(), language=lang,
                            photo_reference=photo_reference.strip())
    if answer == "FAILED" and road["under_dlp"] == "Y":
        fb.generated_warranty_review = True
        fb.routed_to = "Ward Warranty Desk (original DLP owner not established)"
    elif answer == "FAILED":
        fb.routed_to = "Ward engineer (physical inspection)"
    session.add(fb)
    session.commit()
    session.refresh(fb)
    if answer == "FAILED":
        fb.case_reference = f"{'WR' if fb.generated_warranty_review else 'RF'}-{wo_id[-5:]}-{fb.id:04d}"
        session.add(fb)
        session.commit()
        session.refresh(fb)
        key = "FAILED_DLP" if fb.generated_warranty_review else "FAILED"
        msg = FEEDBACK_MSG[key][lang].format(ref=fb.case_reference)
    else:
        msg = FEEDBACK_MSG[answer][lang]
    return dict(feedback=fb.model_dump(mode="json"), message=msg,
                case_type="WARRANTY_REVIEW" if fb.generated_warranty_review else ("REPAIR_FAILURE_REPORT" if answer == "FAILED" else None),
                photo_note="Photo references are stored as text only; no image verification is performed." if photo_reference else None)


ASK_TEMPLATE = {
    "en": "Work order {wo} on {road} was completed on {date} by {contractor}; ₹{amt} was billed. Status: {status}. {disclaimer}",
    "mr": "{road} वरील कामाचा आदेश {wo} {date} रोजी {contractor} यांनी पूर्ण केला; ₹{amt} बिल केले. स्थिती: {status}. {disclaimer}",
    "hi": "{road} पर कार्य आदेश {wo} {date} को {contractor} ने पूरा किया; ₹{amt} का बिल दिया गया। स्थिति: {status}। {disclaimer}",
    "hinglish": "{road} pe work order {wo} {date} ko {contractor} ne poora kiya; ₹{amt} ka bill bana. Status: {status}. {disclaimer}",
}


def ask(store: DataStore, session: Session, wo_id: str, question: str, language: str) -> dict:
    r = receipt(store, session, wo_id, language)
    if r is None:
        raise KeyError(wo_id)
    facts = {k: r[k] for k in ("work_order_id", "complaint_summary", "road_name", "ward_code", "contractor_name", "repair_method",
                               "completed_date", "amount_inr", "sla_met", "reopened_within_30d", "status_text", "status_source")}
    facts["dlp"] = r["dlp"]["text"]
    facts["disclaimer"] = r["labels"]["disclaimer"]
    try:
        answer = claude_service.answer_citizen(question, r["language"], facts)
        from app.schemas import contains_forbidden
        if not answer or contains_forbidden(answer):
            raise claude_service.ClaudeUnavailable("answer failed checks")
        mode = "live"
    except claude_service.ClaudeUnavailable:
        answer = ASK_TEMPLATE[r["language"]].format(wo=wo_id, road=r["road_name"], date=r["completed_date"], contractor=r["contractor_name"],
                                                    amt=f"{r['amount_inr']:,}", status=r["status_text"], disclaimer=r["labels"]["disclaimer"])
        mode = "template"
    return dict(answer=answer, language=r["language"], mode=mode, source_ids=r["source_ids"])
