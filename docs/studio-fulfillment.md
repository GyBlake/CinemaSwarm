# CinemaSwarm fulfillment: seven-stage operational audit

## Verified engineering additions

1. **Execution:** `heygen_adapter.py` implements a narrow, allowlisted
   HeyGen v3 Text-to-Video submission adapter, based on published v3 API
   documentation. It can produce an authorized provider request when
   `HEYGEN_API_KEY` is supplied locally; by default `make_provider_plan`
   is a dry run. Production callers must separately approve the spend,
   retain provider request IDs and reconcile the actual output.
2. **Memory:** `studio_runtime.py` maintains stable approved asset IDs,
   canonical references, SHA-256 hashes, ordered production inputs, provider
   jobs, and immutable output lineage. This is a local manifest, not cloud
   persistent agent memory.
3. **Inspection:** `media_qc.py` uses real FFmpeg/FFprobe operations to
   measure file integrity, resolution, duration, audio stream presence and
   temporal frame differences on local video. Frame motion is *not* proof of
   natural acting or facial consistency.
4. **Repair:** `plan_repair` creates a new, bounded and budget-aware retry
   only for rejected/failed jobs, preserving approved sources. It does not
   autonomously mutate a remote provider or guarantee a correct new take.
5. **Cross-episode continuity:** `series_ledger.py` validates the lifecycle
   of seeded symbols and obligated payoffs across a contiguous episode list.
   Overdue and unresolved symbolism blocks audit. It cannot recognize a
   foreshadowing motif in media without reviewed annotations.
6. **Orchestration:** offline run manifests provide dependency preflight,
   idempotency keys, reviewer authorization, budget checks and atomic output
   writes. They do not currently provide a distributed queue, cloud resume,
   signed reviewer identities, or a fully automatic provider lifecycle.
7. **Cinematic proof:** A 12-second symbolic angel doorway test was
   submitted via a connected HeyGen tool (external job id recorded in the
   session, not in public repository), but a full 15–30-second, multi-voice,
   independently audited series was **not** demonstrated at this commit.
   That stage remains incomplete pending returned real media, approved voice
   casting, phoneme-level sync assessment, and multi-episode continuity evidence.

## CLI examples

```bash
python cinema_swarm.py --audit-runtime private/runtime.json \
  --runtime-root private --runtime-report private/runtime-report.json
python cinema_swarm.py --plan-repair private/runtime.json \
  --repair-job failed-shot --repair-id failed-shot-retry1 \
  --repair-approved-by studio-supervisor \
  --repair-output private/repaired-runtime.json
python cinema_swarm.py --inspect-clips private/clips.json \
  --clips-root private --clips-report private/clips-report.json
python cinema_swarm.py --audit-series-ledger private/season-ledger.json \
  --through-episode 3 --series-report private/series-review.json
```

## Hard failure conditions and honest status

- Real video generation requires a provider-side API key and authorization;
  a dry-run plan, request receipt or synthetic MP4 is not a produced film.
- Generated media are stored outside Git by default; never upload private
  footage, cast likenesses, provider keys or private Nexus data to public
  branches.
- No model understands private canon automatically. Semantic projections
  and Rosetta reconciliation are public sanitized contracts.
- Technical audio/video metrics do not establish lip-sync, actor identity,
  aesthetic quality or story meaning. Those remain separately reviewed.
- Payment authorization in a JSON document is a validation criterion;
  account-side rate and budget limits require direct provider controls.
- CI tests can validate integrity, contracts, synthetic media and fail-closed
  behavior, not substitute for finished audiovisual filmmaking.

## Follow-through acceptance for final fulfillment

Mark all seven steps *operational* only after a provider-generated real asset
has been imported and hashed, the production job reconciled with actual
provider results, automatic measurements and independent human approvals
completed, at least one controlled defect repaired and revalidated, and
multiple final episodes cleared both technical and story-continuity audits.
