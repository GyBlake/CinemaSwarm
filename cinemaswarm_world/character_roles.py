"""Public Season 01 cast-role taxonomy and relational continuity contract.

Roles are dramatic functions, not moral or power classes. Draft assignments
are reviewable, and hidden identities never silently resolve through this map.
"""
from __future__ import annotations
import json
from pathlib import Path
from .season_handoff import validate_season_handoff
from .collaboration import PRIVATE_PROJECT_MARKERS

TIERS = frozenset({"principal", "recurring", "support", "institution", "force"})

def validate_character_roles(doc, season):
    validate_season_handoff(season)
    if not isinstance(doc,dict) or set(doc) != {
        "version","season_id","status","taxonomy","characters","relationships","policies"
    } or doc["version"] != 1 or doc["season_id"] != season["season_id"]:
        raise ValueError("character role registry mismatch")
    if doc["status"] != "development_draft":
        raise ValueError("character roles must remain draft")
    if len(json.dumps(doc,ensure_ascii=False))>500_000:
        raise ValueError("role registry too large")
    if any(marker in json.dumps(doc,ensure_ascii=False).lower()
           for marker in PRIVATE_PROJECT_MARKERS):
        raise ValueError("private project content in role registry")
    terms=doc["taxonomy"]
    if not isinstance(terms,list) or not 25<=len(terms)<=90:
        raise ValueError("role taxonomy incomplete")
    term_ids=set()
    for x in terms:
        if not isinstance(x,dict) or set(x)!={"id","function"}:
            raise ValueError("role definition invalid")
        if (not isinstance(x["id"],str) or not isinstance(x["function"],str)
                or not x["function"].strip() or x["id"] in term_ids):
            raise ValueError("duplicate/empty role definition")
        term_ids.add(x["id"])
    required={"protagonist","deuteragonist","tritagonist","antagonist",
              "primary_antagonist","recurring_support","companion","mentor",
              "foil","confidant","catalyst","threshold_keeper","love_interest",
              "world_antagonism","mystery_figure","scholar","guest","cameo"}
    if not required <= term_ids:
        raise ValueError("missing canonical dramatic functions")
    cast=doc["characters"]
    if not isinstance(cast,list) or not 10<=len(cast)<=120:
        raise ValueError("character assignments incomplete")
    ids=set()
    rolemap={}
    for item in cast:
        if not isinstance(item,dict) or set(item)!={
            "id","name","tier","roles","canon","appearance","arc","approved"
        }:
            raise ValueError("character assignment schema")
        if (item["id"] in ids or not item["id"] or item["tier"] not in TIERS
                or item["approved"] is not False or any(
                not isinstance(item[k],str) or not item[k].strip()
                for k in ("id","name","canon","appearance","arc"))):
            raise ValueError("duplicate, unapproved, or malformed character")
        roles=item["roles"]
        if not isinstance(roles,list) or not roles or len(set(roles))!=len(roles) or not set(roles)<=term_ids:
            raise ValueError("unknown or duplicate role")
        if item["tier"] in ("institution","force") and any(role in roles for role in (
            "protagonist","deuteragonist","tritagonist","companion")):
            raise ValueError("non-person assigned individual protagonist role")
        ids.add(item["id"])
        rolemap[item["id"]]=set(roles)
    policies=doc["policies"]
    if not isinstance(policies,dict) or set(policies)!={
        "nexus_host_id","nexus_voice_id","sole_pov_anchor","allow_multiple_roles",
        "allow_antagonist_reversals","romance","hidden_identity","review_required"
    }:
        raise ValueError("role governance missing")
    if (policies["nexus_host_id"] != season["protagonist"]["id"]
            or policies["nexus_voice_id"] != season["protagonist"]["system_voice"]
            or policies["sole_pov_anchor"] != season["protagonist"]["id"]):
        raise ValueError("Nexus/protagonist conflict")
    if (policies["allow_multiple_roles"] is not True
            or policies["allow_antagonist_reversals"] is not True
            or policies["review_required"] is not True
            or policies["romance"]!="not_assigned"
            or policies["hidden_identity"] not in ids):
        raise ValueError("unapproved relationship or reveal policy")
    if [k for k,v in rolemap.items() if "protagonist" in v]!=[policies["sole_pov_anchor"]]:
        raise ValueError("sole protagonist invariant")
    if "companion" not in rolemap[policies["nexus_voice_id"]]:
        raise ValueError("Nexus companion has no dramatic role")
    if not {"primary_antagonist","antagonist"} & set.union(*(rolemap[x] for x in ids)):
        raise ValueError("no opposing dramatic force")
    for actor in season["cast"]:
        if actor["id"] not in ids:
            raise ValueError("season cast member missing role")
    rel=doc["relationships"]
    if not isinstance(rel,list) or not rel or len(rel)>300:
        raise ValueError("no character relationship network")
    ep_ids=[ep["id"] for ep in season["episodes"]]
    pairs=set()
    for relation in rel:
        if not isinstance(relation,dict) or set(relation)!={
            "from","to","type","initial","first_episode","last_episode","dynamic"}:
            raise ValueError("relationship schema")
        a,b=relation["from"],relation["to"]
        key=(a,b,relation["type"])
        if (a not in ids or b not in ids or a==b or key in pairs
                or relation["first_episode"] not in ep_ids
                or relation["last_episode"] not in ep_ids):
            raise ValueError("invalid relationship endpoint")
        if ep_ids.index(relation["first_episode"]) > ep_ids.index(relation["last_episode"]):
            raise ValueError("relationship timeline reversed")
        for k in ("type","initial","dynamic"):
            if not isinstance(relation[k],str) or not relation[k].strip():
                raise ValueError("empty relationship")
        pairs.add(key)
    return doc

def character_role_observer(doc,season):
    validate_character_roles(doc,season)
    return {
        "version":1,"season_id":doc["season_id"],
        "point_of_view":doc["policies"]["sole_pov_anchor"],
        "nexus_companion":doc["policies"]["nexus_voice_id"],
        "characters":[{"id":c["id"],"name":c["name"],
                       "dramatic_functions":c["roles"],"tier":c["tier"],
                       "arc":c["arc"]} for c in doc["characters"]],
        "relationships":doc["relationships"],
        "constraints":[
            "Multiple functions per character are allowed; no fixed moral alignment",
            "Only the approved protagonist receives a Nexus System",
            "Villains, antagonists, rivals, and foils are not interchangeable",
            "Undisclosed identities remain unresolved until author approval",
            "No undeclared romance; institutions and environmental forces are not individual characters",
            "No private source persona or proprietary character canon is public"
        ]
    }

def load_character_roles(path,season):
    with Path(path).open(encoding="utf-8") as stream:
        return validate_character_roles(json.load(stream),season)
