# Camera Engineer Stack v1 · CinemaSwarm

## Production department
CinemaSwarm's camera engineering layer translates an approved directorial scene objective into measurable **previsualization** geometry, camera placement, full-frame-equivalent lens choices, film grammar and technical checks. Unlike a text-only assistant, it checks the action axis, bounded stage dimensions, focus distances, lens and camera-motion constraints, the parent-shot runtime, matching eyelines and cross-shot companion visibility.

**Director → Cinematographer/DP → Camera Engineer → Camera Operator / First AC → Lighting / VFX / Sound / Script Supervisor → Editor / Technical QC.**

These are *responsibilities of a virtual production team*, not claims of certified professional crew or independent AI agents.

### Responsibilities
- Director: dramatic motivation, character meaning and intended audience perception.
- Director of photography: tone, exposure, light and visual consistency.
- Camera engineer: coordinate frame, rig constraints, lenses, camera placement, 180° line, targeting, coverage.
- Camera operator: executes movement and framing.
- First assistant camera: subject focus distances, rack focus and lens marks.
- Gaffer: physical lighting; do not let Nexus effects leave unexplained spill on objective plates.
- VFX supervisor: visible subjective Vesper, performer reference/tracking/eyeline plates, contrast to clean objective room.
- Script supervisor: eyeline and hand match, props, costume, body continuity.
- Production sound: isolated Nia and Vesper dialogue, in-world ambience.
- Editor: screen direction and audience legibility, no objective Vesper sightings.

### Inputs and outputs
**Inputs:** season handoff, dramatic-role registry, Episode 01 scene-role map, companion identity plan, timed contact sequence, proposed stage dimensions.

**Output:** `e01-camera-engineer.json`, a strictly checked data contract with six camera setups nested under **four** parent proof shots. The observer returns setup geometry, signed 180° side, focus distance, timing and evidence-based status. For safety, the observer reports *not filmed* and requires actual set survey and creative approvals before cinema production.

**Shot positions:** 6×5 m example room, x=east/y=north/z=up, Nia=(2.50,2.10,1.55), Vesper's **nonphysical** staging mark=(3.70,3.20,1.58). S03: 50mm close-up, S04: 28mm objective wide, S10-A: 35mm two-shot slow dolly, S10-B: 65mm Vesper reaction close-up, S10-C: 65mm Nia close-up, S11: 28mm objective wide. All six positions are on the same permitted side of the 180° axis, including the S10 dolly end.

**Critical visual invariant:** Audience sees Vesper as a full, expressive, identifiable character in S10-A/B. An objective camera sees ordinary empty space at that mark. No character besides the host gains a Nexus System merely because the audience can see the host's internal companion.

## Engineering limits
The checker validates **authored geometry**, not optics from a real camera, actor blocking from footage, lens distortion, focus-pulling accuracy, photometric lighting, dynamic collision with props, real physical stage access, artistic quality or performer identity. Its proposed meter measurements are not surveyed. An eventual renderer or video-provider adapter may consume this contract **only after explicit review**; passing this validator never authorizes video generation or costs.
