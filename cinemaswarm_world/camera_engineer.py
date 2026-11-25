"""Camera Engineer stack: deterministic previsualization geometry and shot continuity.

No optical calibration, filming, cinema rendering, or physical set measurement is
performed. Positions are proposed meter coordinates and lens equivalents.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from .contact_proof import validate_contact

SIZES=frozenset({"medium_close_up","wide","two_shot","reaction_close_up","close_up"})
MOVES=frozenset({"locked","dolly_in"})
VIEWS=frozenset({"objective","subjective"})
DEPARTMENTS={"director","camera_engineer","director_of_photography",
             "camera_operator","first_ac","gaffer","vfx_supervisor",
             "script_supervisor","sound_recordist","editor"}
POSITIONS={"S03","S04","S10-A","S10-B","S10-C","S11"}
EXPECTED_ORDER=["S03","S04","S10-A","S10-B","S10-C","S11"]

def _exact(x,fields,name):
    if not isinstance(x,dict) or set(x)!=set(fields):
        raise ValueError("invalid "+name)

def _xyz(v):
    if not isinstance(v,list) or len(v)!=3 or any(
        type(x) not in (int,float) or not math.isfinite(x) for x in v
    ):
        raise ValueError("invalid camera or target coordinates")

def _cross(a,b,p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])

def _distance(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def validate_camera_engineer(doc,identity,proof,scenes,roles,season):
    validate_contact(identity,proof,scenes,roles,season)
    _exact(doc,("version","season_id","episode_id","proof_sequence_id","status",
                "coordinate_system","action_axis","anchors","departments",
                "cameras","continuity","approval"),"camera engineer")
    if (doc["version"]!=1 or doc["season_id"]!=season["season_id"]
        or doc["episode_id"]!=proof["episode_id"]
        or doc["proof_sequence_id"]!=proof["sequence_id"]
        or doc["status"]!="engineering_draft"):
        raise ValueError("camera engineer dependency mismatch")
    cs=doc["coordinate_system"]
    _exact(cs,("units","origin","x","y","z","room","surveyed"),"coordinate system")
    if (cs["units"]!="meters" or cs["origin"]!="southwest_studio_corner"
        or (cs["x"],cs["y"],cs["z"])!=("east","north","up")
        or cs["surveyed"] is not False or cs["room"]!=[6,5,3]):
        raise ValueError("camera coordinates not canonical")
    anchor_items=doc["anchors"]
    if not isinstance(anchor_items,list) or len(anchor_items)!=4:
        raise ValueError("anchor count")
    anchors={}
    for item in anchor_items:
        _exact(item,("id","xyz","physical"),"set anchor")
        if item["id"] in anchors:
            raise ValueError("duplicate set anchor")
        _xyz(item["xyz"])
        if not (0<=item["xyz"][0]<=6 and 0<=item["xyz"][1]<=5
                and 0<=item["xyz"][2]<=3) or type(item["physical"]) is not bool:
            raise ValueError("set anchor outside stage")
        anchors[item["id"]]=item
    if set(anchors)!={"nia","vesper_mark","desk","cassette"}:
        raise ValueError("missing subject or target anchor")
    if anchors["vesper_mark"]["physical"] is not False:
        raise ValueError("Vesper mark is not a physical entity")
    axis=doc["action_axis"]
    _exact(axis,("from","to","allowed_side","tolerance_m2","eyeline_rule"),"action axis")
    if (axis["from"]!="nia" or axis["to"]!="vesper_mark"
        or axis["allowed_side"]!="negative"
        or type(axis["tolerance_m2"]) not in (int,float)
        or not 0<axis["tolerance_m2"]<0.1
        or not isinstance(axis["eyeline_rule"],str)
        or not axis["eyeline_rule"].strip()):
        raise ValueError("unsupported action axis")
    team=doc["departments"]
    if not isinstance(team,list) or {x.get("id") for x in team if isinstance(x,dict)} != DEPARTMENTS:
        raise ValueError("incomplete cinematography crew")
    for member in team:
        _exact(member,("id","responsibility","handoff"),"camera department")
        if not member["responsibility"] or not member["handoff"]:
            raise ValueError("camera crew responsibility missing")
    cameras=doc["cameras"]
    if not isinstance(cameras,list) or [x.get("id") for x in cameras]!=EXPECTED_ORDER:
        raise ValueError("camera coverage order")
    shot_duration={}
    observed=[]
    for camera in cameras:
        _exact(camera,("id","parent_shot","at","aim","lens_mm","shot_size","move",
                       "travel_m","seconds","view","sees","focus",
                       "lighting","audio","notes"),"camera setup")
        _xyz(camera["at"])
        if (not 0<=camera["at"][0]<=6 or not 0<=camera["at"][1]<=5
            or not 0<=camera["at"][2]<=3):
            raise ValueError("camera outside room")
        if camera["aim"] not in anchors or camera["aim"]=="desk":
            raise ValueError("invalid camera aim")
        if (type(camera["lens_mm"]) not in (int,float)
            or camera["lens_mm"] not in (28,35,50,65)
            or camera["shot_size"] not in SIZES
            or camera["move"] not in MOVES
            or type(camera["seconds"]) is not int or camera["seconds"]<=0
            or type(camera["travel_m"]) not in (int,float)
            or not math.isfinite(camera["travel_m"])
            or not 0<=camera["travel_m"]<=0.8):
            raise ValueError("invalid camera optics or timing")
        if (camera["move"]=="locked" and camera["travel_m"]!=0
            or camera["move"]=="dolly_in" and camera["travel_m"]<=0):
            raise ValueError("impossible camera movement")
        if (not isinstance(camera["focus"],list) or not camera["focus"]
            or not set(camera["focus"])<=anchors.keys()):
            raise ValueError("invalid focus targets")
        if (not isinstance(camera["sees"],list) or not camera["sees"]
            or not set(camera["sees"])<= {"nia","vesper"}
            or camera["view"] not in VIEWS):
            raise ValueError("invalid camera subjects")
        if camera["view"]=="objective" and "vesper" in camera["sees"]:
            raise ValueError("Vesper leaked into objective camera")
        if camera["view"]=="subjective" and camera["id"] in ("S10-A","S10-B") and "vesper" not in camera["sees"]:
            raise ValueError("audience cannot see Vesper")
        if camera["view"] != ("subjective" if camera["parent_shot"]=="S10" else "objective"):
            raise ValueError("shot POV mismatch")
        parent=next((p for p in proof["shots"] if p["id"]==camera["parent_shot"]),None)
        if parent is None:
            raise ValueError("unrecognized parent proof shot")
        if camera["id"].split("-")[0] != camera["parent_shot"]:
            raise ValueError("camera take/shot mismatch")
        signed=_cross(anchors["nia"]["xyz"],anchors["vesper_mark"]["xyz"],camera["at"])
        if signed>=-axis["tolerance_m2"]:
            raise ValueError("camera crosses 180-degree action axis")
        # Start and endpoint of any dolly both must stay on the same side.
        target=anchors[camera["aim"]]["xyz"]
        distance=_distance(camera["at"],target)
        if distance<=camera["travel_m"]+0.25:
            raise ValueError("dolly runs through subject")
        if camera["travel_m"]:
            dx=(target[0]-camera["at"][0])*camera["travel_m"]/distance
            dy=(target[1]-camera["at"][1])*camera["travel_m"]/distance
            end=[camera["at"][0]+dx,camera["at"][1]+dy,camera["at"][2]]
            if _cross(anchors["nia"]["xyz"],anchors["vesper_mark"]["xyz"],end)>=-axis["tolerance_m2"]:
                raise ValueError("camera movement crosses 180-degree line")
        shot_duration[camera["parent_shot"]]=shot_duration.get(camera["parent_shot"],0)+camera["seconds"]
        observed.append({"id":camera["id"],"parent_shot":camera["parent_shot"],
                         "axis_signed_area":round(signed,3),
                         "focus_distance_m":round(distance,2),
                         "lens_full_frame_equivalent_mm":camera["lens_mm"],
                         "subjective":camera["view"]=="subjective",
                         "framing":camera["shot_size"]})
    if [(k,shot_duration[k]) for k in proof["shot_ids"]] != [
        (s["id"],s["seconds"]) for s in proof["shots"]
    ]:
        raise ValueError("coverage timing does not match proof shots")
    con=doc["continuity"]
    _exact(con,("eye_match","visibility_rule","same_room_geometry",
                "no_physical_nexus_spill","cutting_order"),"camera continuity")
    if (con["cutting_order"]!=EXPECTED_ORDER or con["same_room_geometry"] is not True
        or con["no_physical_nexus_spill"] is not True):
        raise ValueError("camera continuity mismatch")
    eye=con["eye_match"]
    _exact(eye,("host","target","subjective_shot","objective_shot"),"eyeline match")
    if eye != {"host":"nia","target":"vesper_mark",
               "subjective_shot":"S10-C","objective_shot":"S11"}:
        raise ValueError("unmatched Nexus eyeline")
    if not isinstance(con["visibility_rule"],str) or "subjective" not in con["visibility_rule"]:
        raise ValueError("viewer visibility rules missing")
    approval=doc["approval"]
    _exact(approval,("engineer_reviewed","dp_reviewed","visual_assets_verified",
                     "blocking_rehearsed","physical_measurements_verified","evidence"),"engineering review")
    if any(approval[k] is not False for k in (
        "engineer_reviewed","dp_reviewed","visual_assets_verified",
        "blocking_rehearsed","physical_measurements_verified")):
        raise ValueError("unverified cinematography readiness")
    if not isinstance(approval["evidence"],str) or not approval["evidence"].strip():
        raise ValueError("engineering evidence missing")
    return {"version":1,"episode_id":doc["episode_id"],"sequence_id":doc["proof_sequence_id"],
            "status":"geometry_checks_passed_not_filmed","camera_setups":observed,
            "total_seconds":sum(x["seconds"] for x in cameras),
            "reviewed":False,"surveyed":False,"camera_ready_for_filming":False}

def load_camera_engineer(path,identity,proof,scenes,roles,season):
    return validate_camera_engineer(
        json.loads(Path(path).read_text(encoding="utf-8")),
        identity,proof,scenes,roles,season)
