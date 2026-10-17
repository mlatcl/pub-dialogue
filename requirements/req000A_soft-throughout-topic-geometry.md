---
id: "000A"
title: "Topic geometry stays soft through Address; hard labels are a late view"
status: "In Progress"
priority: "High"
created: "2026-10-17"
last_updated: "2026-10-17"
related_tenets: ["access-assess-address"]
stakeholders: ["Neil Lawrence"]
tags: ["soft-assignment", "ppca", "emd", "clustering", "address", "multilogue"]
---

# REQ-000A: Topic geometry stays soft through Address; hard labels are a late view

## Description

The Address pipeline already uses soft assignment and Earth Mover's Distance for framing lenses (cluster→lens PPCA mixture weights; σ²\* by cross-run EMD) and for document distance (EMD on topic-share histograms). Phrase→topic geometry, however, is still hardened at k-means: each phrase gets a single `cluster_id`, and those hard ids are the atoms for labelling, lens partition, soft lens lookup, and document histograms.

The required outcome is that **soft responsibilities are the primary topic-state** from embedding through transport and framing analyses. Discrete topic labels exist only where a consumer insists on them (LLM naming I/O, tables, prose) — obtained by hardening a soft state at that boundary, not by discarding softness at clustering time.

**Why this matters**: Hardening early forces a second, partial re-softening at the lens layer and makes sklearn vs member-mean centroid quirks load-bearing for σ²\*. Soft-throughout matches the pipeline's actual dependence on soft assignment and EMD, and keeps probabilistic geometry as the citable Address method.

**Who benefits**: Authors of pub-dialogue and other multilogue consumers; readers who need a coherent soft→hard story; anyone reproducing sensitivity / multiverse results under a single topic definition.

## Acceptance Criteria

- [ ] Phrase→topic membership used for document histograms, framing profiles, and checkpointed geometry is soft (responsibilities), not solely a hard k-means label
- [ ] Document EMD bins receive soft mass (sums of responsibilities), not only hard counts — unless a documented hard view is explicitly selected for a sensitivity arm
- [ ] LLM topic labelling and lens-partition prompts consume a **hardened view** of soft topics (or an equivalent discrete interface), without requiring hard assignment to be the stored primary state
- [ ] Soft lens (topic→lens) and document-distance layers consume the same soft topic geometry; no divergent centroid definition between fresh fit and freeze/replay
- [ ] Published or multiverse sensitivity language states when a hard view was taken and that it is a late discretisation of soft state

## Notes

This requirement does not mandate mixture-of-PPCA, a particular EM schedule, or where code lives (pub vs multilogue) — those are CIP decisions. It does require that hard topics are not the foundational Address state.

Related existing outcomes: REQ-0007 (lens stability / canonical mappings) still applies to whatever discrete lens interface the LLM sees; soft-throughout must not reintroduce stochastic lens drift as a side-effect of re-hardening.

## References

- Multilogue address pipeline (soft lenses + two EMD uses)
- Downstream of multilogue CIP-0005 (soft PPCA / document EMD in library)
- Interim bug: sklearn `cluster_centers_` vs member-mean centroids under flat EMD

## Progress Updates

### 2026-10-17

Requirement proposed after design discussion: hard topics are only required at LLM/report boundaries; soft can be sustained throughout and hardened at the end.

CIP-0017 Accepted; backlog tasks created. Status → In Progress.
