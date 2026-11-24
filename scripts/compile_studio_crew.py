"""Compile the authorized-input CinemaSwarm pilot crew planning packet.

No external calls, no assets, no provider authorization. Fails closed and
never overwrites an existing output unless explicitly requested.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from cinemaswarm_world.season_handoff import load_handoff
from cinemaswarm_world.character_roles import load_character_roles
from cinemaswarm_world.pilot_scene_roles import load_scene_roles
from cinemaswarm_world.studio_crew import compile_department_handoffs

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"docs"/"season-01"

def compile_default():
    season=load_handoff(BASE/"season-handoff.json")
    roles=load_character_roles(BASE/"character-roles.json",season)
    scenes=load_scene_roles(BASE/"e01-scene-roles.json",roles,season)
    def load(name):
        return json.loads((BASE/name).read_text(encoding="utf-8"))
    return compile_department_handoffs(
        load("studio-crew.json"),season,load("nia-vesper-identity.json"),
        load("nia-vesper-contact.json"),scenes,roles,load("e01-camera-engineer.json")
    )

def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline, no-provider crew planning packets")
    parser.add_argument("--output",required=True,type=Path,help="Destination JSON packet")
    parser.add_argument("--overwrite",action="store_true",help="Explicitly replace existing packet")
    args=parser.parse_args(argv)
    packet=compile_default()
    if args.output.is_dir():
        parser.error("output must be a file path")
    # No file is touched until all source contracts validate.
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w" if args.overwrite else "x",encoding="utf-8") as f:
        json.dump(packet,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print("Prepared",len(packet["departments"]),"department handoffs:",args.output)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
