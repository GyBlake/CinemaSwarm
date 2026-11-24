"""Cross-episode symbolic obligations and narrative state convergence.

This is a deterministic bookkeeping and causality gate. It does not infer
symbolic intent from raw video. Approved manifests must supply the semantics.
"""
from __future__ import annotations
from .collaboration import digest, text

def validate_season_ledger(doc):
    if not isinstance(doc,dict) or set(doc) != {"version","season_id","episodes","obligations"} or doc["version"] != 1:
        raise ValueError("invalid season continuity ledger")
    text(doc["season_id"], "season")
    eps = doc["episodes"]
    if not isinstance(eps,list) or not eps or len(eps)>200:
        raise ValueError("ordered episodes required")
    ids = []
    for ep in eps:
        if not isinstance(ep,dict) or set(ep) != {"number","id","canon_sha256","approved"}:
            raise ValueError("invalid episode state")
        if type(ep["number"]) is not int or ep["number"] != len(ids)+1:
            raise ValueError("episodes must be contiguous and ordered")
        text(ep["id"],"episode id")
        if ep["id"] in ids or not isinstance(ep["canon_sha256"],str) or len(ep["canon_sha256"]) !=64:
            raise ValueError("duplicate episode or missing digest")
        if ep["approved"] is not True:
            raise ValueError("unapproved season episode")
        ids.append(ep["id"])
    obligations = doc["obligations"]
    if not isinstance(obligations,list) or len(obligations)>500:
        raise ValueError("invalid season obligations")
    names = set()
    for item in obligations:
        if not isinstance(item,dict) or set(item) != {"id","concept_id","introduced_in",
                                                       "due_by","resolved_in",
                                                       "seed_evidence","payoff_evidence",
                                                       "approved"}:
            raise ValueError("invalid payoff obligation")
        oid=text(item["id"],"obligation")
        if oid in names:
            raise ValueError("duplicate obligation")
        names.add(oid)
        text(item["concept_id"],"concept")
        start=item["introduced_in"]
        due=item["due_by"]
        resolved=item["resolved_in"]
        if (type(start) is not int or type(due) is not int or not 1<=start<=due
            or due>len(ids)):
            raise ValueError("obligation timeline invalid")
        text(item["seed_evidence"],"seed evidence")
        if resolved is None:
            if item["payoff_evidence"] is not None or item["approved"] is True:
                raise ValueError("unresolved obligation falsely approved")
        else:
            if type(resolved) is not int or not start<=resolved<=due:
                raise ValueError("payoff outside permitted timeline")
            text(item["payoff_evidence"],"payoff evidence")
            if item["approved"] is not True:
                raise ValueError("payoff review required")
    return doc

def audit_season_ledger(doc, through_episode=None):
    validate_season_ledger(doc)
    through = len(doc["episodes"]) if through_episode is None else through_episode
    if type(through) is not int or not 1<=through<=len(doc["episodes"]):
        raise ValueError("invalid audit horizon")
    overdue = [item["id"] for item in doc["obligations"]
               if item["introduced_in"] <= through
               and item["due_by"] <= through
               and item["resolved_in"] is None]
    upcoming = [item["id"] for item in doc["obligations"]
                if item["introduced_in"]<=through
                and item["resolved_in"] is None and item["due_by"]>through]
    resolved=[item["id"] for item in doc["obligations"]
              if item["resolved_in"] is not None and item["resolved_in"]<=through]
    return {"version":1,"season_id":doc["season_id"],"through_episode":through,
            "ledger_sha256":digest(doc),"status":"blocked" if overdue else "checks_passed",
            "error_count":len(overdue),"overdue":overdue,"pending":upcoming,
            "resolved":resolved,
            "scope":"authored and reviewer-approved payoff chronology; not automatic video semantic recognition"}
