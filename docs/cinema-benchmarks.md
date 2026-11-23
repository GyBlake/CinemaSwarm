# CinemaSwarm international-quality benchmark program

## Scope: qualification, not universal certification

No single authoritative worldwide "all AI cinema benchmarks" qualification
exists. Different distributors, broadcasters, festivals and jurisdictions have
different technical, editorial, accessibility and rights requirements.

CinemaSwarm supports **versioned internal studio profiles** inspired by public
delivery standards, while distinguishing genuine measurements, human reviews,
self-attestations and missing checks. Qualification is NOT an external Netflix,
YouTube, DCP, IMF, C2PA, EBU, WCAG or festival certification.

Source standards and references (consult their latest documents for each actual
distribution contract):
- YouTube upload guidance: https://support.google.com/youtube/answer/1722171
- Netflix Studio Delivery Knowledge Hub:
  https://studiopartner.netflix.net/studio/delivery-specifications-and-requirements-external
- EBU R128 loudness: https://tech.ebu.ch/publications/r128/
- WCAG 2.2 prerecorded captions: https://www.w3.org/TR/WCAG22/#captions-prerecorded
- C2PA: https://spec.c2pa.org/

## Benchmarks implemented

Profile `vertical-premium-v1` checks 1080x1920 minimum 9:16,
60–180 second runtime, 23–61 fps, 48 kHz audio, approved codecs, exact media
and caption hashes, basic caption presence, local media inspection via
`ffprobe`, linked media continuity report and provenance/rights approvals.
`cinematic-horizontal-v1` is a separate 4K 16:9 studio policy. Neither
purports to satisfy every deliverable of specific professional platforms.

Five human-scored dimensions are narrative 25%, performance 20%, visual
identity 25%, voice identity 20%, cinematography 10%. Internal studio target
is >=95/100 with no dimension below 85. All reviews require explicit
reviewer IDs and evidence provenance. Missing evaluations remain unknown.

Loudness measurements must eventually be validated against the appropriate
destination profile; supplying a number alone does **not** prove EBU/ITU
compliance. Caption presence alone does **not** prove WCAG conformance.
C2PA claims likewise require independent validation; a JSON claim is not a
signed credential. To protect integrity, these remain incomplete or review
required until trusted validation is integrated.

## CLI

```bash
python cinema_swarm.py --audit-season ./private/season.json \
  --benchmark-root ./private --benchmark-report ./private/benchmark-report.json
```

Manifest schema:

```json
{
  "version": 1,
  "season_id": "season-1",
  "profile": "vertical-premium-v1",
  "planned_episodes": 2,
  "episodes": [
    {
      "number": 1,
      "master": "master-01.mp4",
      "master_sha256": "64 lowercase hex digits",
      "captions": "captions-01.srt",
      "captions_sha256": "64 lowercase hex digits",
      "continuity_report": "qc-01.json",
      "provenance_record": "provenance-01.json",
      "reviews": {
        "narrative": {"score": 98, "reviewer": "editor", "evidence": "review-log", "approved": true},
        "performance": {"score": 98, "reviewer": "editor", "evidence": "review-log", "approved": true},
        "visual_identity": {"score": 98, "reviewer": "editor", "evidence": "review-log", "approved": true},
        "voice_identity": {"score": 98, "reviewer": "editor", "evidence": "review-log", "approved": true},
        "cinematography": {"score": 98, "reviewer": "editor", "evidence": "review-log", "approved": true}
      },
      "caption_review": {"approved": true},
      "rights_review": {"approved": true}
    }
  ]
}
```

The suite fails closed: missing episodes, incomplete evidence or failed
continuity checks cannot be labeled "qualified". Delivery-gate results
are about measurable technical specifications, not proof of artistic supremacy
or external certification. Existing scripts still create text production
packets, not finished videos or seasons.
