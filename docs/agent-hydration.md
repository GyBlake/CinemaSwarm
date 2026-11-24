# External Agent Hydration and Performance Quality Gates

## Hard boundary

External video/image/voice providers do not automatically receive repository,
MCP access, hidden prompts, or Dreamcorp private data. **Only explicitly
approved, sanitized public packages** may cross the boundary.

A validated handoff proves local package integrity, not that a provider's
private LLM understood the project. Provider claims require human inspection.

## Three-stage release workflow

1. **Creative hydration:** prepare a bounded, versioned `public` package
   containing a world snapshot identifier/digest, scene intents, character
   visual/voice anchors, relationships, spoken dialogue and the provider's
   *declared* capabilities. Supply the prepared package to a provider only
   after authorized review.
2. **Interpretation gate:** after the provider proposes an interpretation,
   the editor records all acknowledged scene and identity IDs, unresolved
   issues, and explicit signed-off approval. A digest mismatch or unresolved
   ambiguity blocks production. This is a local manual acknowledgment, not
   proof of direct MCP hydration.
3. **Voice/performance gate:** review each dialogue take with stable
   `speaker_id`, `voice_id`, audio SHA-256, signed-off voice match, and
   approved lip-sync. Measured or manually inspected sync offsets above
   80ms block on-screen speech. Thought, crowd, offscreen and disembodied
   channels must NOT attach to an animated visible mouth. Character voices
   require an explicitly approved voice-preview digest before handoff.

All candidate-mode MP4 assembly **now requires these three evidence files**.
Season qualification also requires them for every episode. Missing files,
unreviewed lines, mismatched voices or declined review block release.

**Evidence honesty:** The current tool validates reviewer attestations and
audio file hashes. It DOES NOT automatically identify voices by their acoustics,
infer gender from speech, calculate phoneme-to-mouth alignment, verify C2PA
signatures or reach into third-party agents. A maliciously fabricated approval
cannot be defeated with JSON validation alone. For stronger production
integrity, store actual reviewer evidence, use independent speech/visual
aligners, and retain immutable receipts.

## CLI

```bash
python cinema_swarm.py --prepare-collaboration ./private/public-contract.json \
  --collaboration-output ./private/provider-handoff.json

python cinema_swarm.py --verify-collaboration ./private/public-contract.json \
  --collaboration-ack ./private/interpretation-approved.json \
  --collaboration-report ./private/ack-check.json

python cinema_swarm.py --audit-performance ./private/voice-takes.json \
  --performance-package ./private/public-contract.json \
  --performance-root ./private \
  --performance-output ./private/voice-gate.json
```

The project files should reference `collaboration_package`,
`collaboration_ack`, and `performance_report` in both candidate scene
assembly plans and season delivery manifests.

### Dialogue channel definitions

- `onscreen`: speaking identity MUST match animated character identity.
- `offscreen`: character audible while not visible speaking.
- `thought`: internal monologue without animated mouth.
- `crowd`: explicitly cast NPC conversation, offscreen until mapped to
  an on-screen speaker in a separate `onscreen` line.
- `disembodied`: intentionally unlocated speaker with no visible mouth.

Stable voice IDs prevent accidental voice swaps **only when external
providers actually honor the IDs**. For providers lacking voice binding, use
separate rendered audio tracks and external lip-sync processing; the
declared `provider.capabilities` fields must be truthful.
