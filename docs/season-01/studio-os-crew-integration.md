# CinemaSwarm Studio OS Crew Integration v1

**Original production-control adaptation.** This public implementation follows general Studio OS organizational principles: founder scope → canon → director → departmental handoffs → reviewer gates → existing authorized runtime → QC → publishing → archive. No private crew identities or private repository contents are copied or loaded.

## Single crew, many functional lenses
The 18 roles in [studio-crew.json](studio-crew.json) are department **capabilities and responsibilities**, not eighteen autonomously alive AI personalities. Original CinemaSwarm's nine specialist agent tools remain intact in `cinema_swarm.py`; this adds an offline operational handoff bus without proliferating agents.

**Director / Showrunner** owns dramatic decisions. **Stage Manager / Art Department** owns shared stage and prop coordinates. **Thespian Director** owns actor eyeline and character choices. **Cinematographer / Camera Engineer / Camera Operator / First AC** own coverage geometry, lens/focus/movement and eventual camera execution. **Gaffer, VFX and Sound** receive the same shared scene state. **Editor, QC, Publishing and Archive** handle reviewed footage only. **Executive Producer** owns scope, authorizations and release.

## What actually runs
`cinemaswarm_world.studio_crew.compile_department_handoffs` takes the validated public Season 01 handoff, cast registry, pilot scene roles, Nia/Vesper identities and 40-second proof, and numeric camera manifest. It deterministically compiles **18 structured department packets** sharing identical camera setups, actor marks, shot durations, cast, props and stated scene objectives, with traceable hashes. Packets say either `prepared_plan`, `blocked_on_assets_and_approval`, or `approval_required`. This is executable *preproduction control*, not generated acting or video.

`studio_crew.validate_handoffs` rejects stale or rewritten packets against canonical inputs. `studio_crew.runtime_bridge` validates an actual existing `studio_runtime` document and returns only already-authorized and dependency-ready jobs. It **never** creates, authorizes or launches an external provider job.

## Missing before crew is capable of filmmaking
Real asset/likeness approvals, embodied animated performers, stage models, performance recording, calibrated optics, practical or generated lighting, video providers and render receipts, actor animation, voice/lip-sync, verified edited masters, licensing, approval decisions and publishing authorization. The engine never implies these steps occurred.

## General source-to-release process mapping
Source → Seal → Orient → Couple → Sync → Coordinate → Receipt → Release maps operationally to: collect canonical story; hash inputs; validate world and roles; bind crew; issue consistent scene-state handoffs; check dependencies and camera geometry; require provider and human review receipts; release only approved footage. This sequence documents neutral studio operations without importing private crew personnel or configurations.

## Offline CLI

`python -m scripts.compile_studio_crew --output build/aecluptic-crew-handoffs.json` compiles all 18 packets from versioned source documents. The command is offline, validates upstream dependencies, refuses to overwrite existing output by default, and does **not** create or authorize paid runtime jobs.
