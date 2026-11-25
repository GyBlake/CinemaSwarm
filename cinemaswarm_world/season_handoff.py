"""Validate season creative handoffs without misreporting cinematic fulfillment."""
import json

def validate_season_handoff(doc):
    if not isinstance(doc, dict) or set(doc) != {"version","season_id","title","status",
        "public_fiction","showrunner_approval","production_release_authorized","world_rules",
        "protagonist","cast","episodes","production"}:
        raise ValueError("season handoff schema")
    if doc["version"] != 1 or doc["status"] != "development_draft" or doc["public_fiction"] is not True:
        raise ValueError("unexpected season handoff state")
    if doc["showrunner_approval"] or doc["production_release_authorized"]:
        raise ValueError("draft cannot claim authorization")
    people=doc["cast"]
    if len(people)!=5 or any(set(x)!={"id","name","awakened","nexus","system","story_role"} for x in people):
        raise ValueError("cast contract")
    ids=[p["id"] for p in people]
    if len(set(ids))!=len(ids) or sum(x["nexus"] is True for x in people)!=1:
        raise ValueError("exactly one protagonist Nexus")
    protagonist=doc["protagonist"]
    if set(protagonist)!={"id","name","status","nexus_class","system_voice"} or (
        protagonist["id"] not in ids or protagonist["nexus_class"] is not True):
        raise ValueError("protagonist contract")
    host=next(p for p in people if p["id"]==protagonist["id"])
    if not host["nexus"] or host["system"]!=protagonist["system_voice"]:
        raise ValueError("Nexus companion mismatch")
    for p in people:
        if p["nexus"] is not True and p["system"] is not None:
            raise ValueError("non-bearer assigned a System")
    episodes=doc["episodes"]
    if len(episodes)!=8 or any(set(ep)!={"number","id","title","logline","focus",
        "final_hook","screenplay_state","video_state","voice_state","approved"} for ep in episodes):
        raise ValueError("eight episode handoff required")
    for i,ep in enumerate(episodes):
        if ep["number"]!=i+1 or ep["focus"] not in ids or ep["approved"] is not False:
            raise ValueError("episode order or false approval")
        if ep["screenplay_state"]!=("development_draft" if i==0 else "treatment_only"):
            raise ValueError("episode script state")
        if ep["video_state"]!="not_generated" or ep["voice_state"]!="not_recorded":
            raise ValueError("unverified completed media")
    if len(set(ep["id"] for ep in episodes))!=8:
        raise ValueError("duplicate episodes")
    p=doc["production"]
    if set(p)!={"pilot_shots","locked_scripts","voice_recordings","finished_episodes",
                "cinematic_video_masters","reviewed_performances","rights_clearances",
                "shot_assets_ready","paid_generation_authorized","subtitle_assets_ready",
                "production_gate"}:
        raise ValueError("production gate schema")
    if (p["pilot_shots"]!=15 or any(p[k]!=0 for k in ("locked_scripts","voice_recordings",
           "finished_episodes","cinematic_video_masters","reviewed_performances","rights_clearances"))
           or any(p[k] for k in ("shot_assets_ready","paid_generation_authorized","subtitle_assets_ready"))
           or p["production_gate"]!="blocked_missing_assets_and_approvals"):
        raise ValueError("release claim without evidence")
    if not isinstance(doc["world_rules"],list) or len(doc["world_rules"])<5:
        raise ValueError("world rules missing")
    return doc

def load_handoff(path):
    with open(path,encoding="utf-8") as f:
        return validate_season_handoff(json.load(f))
