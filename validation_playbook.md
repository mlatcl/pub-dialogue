# Validation Playbook: Public Dialogue Analyser

> **Who this is for:** Researchers reviewing the dialogue analyser outputs — no Python required.
> All steps use a spreadsheet app (Excel / Numbers / Google Sheets) and a web browser.
>
> **When to use it:** After any complete analysis run, before drawing conclusions or writing up results.

---

## Export pack contents

After running the notebook and downloading the ZIP, you will find:

| File | What it contains |
|------|-----------------|
| `extracted_concerns.csv` | Every retained concern phrase with `chunk_id` provenance |
| `extracted_benefits.csv` | Every retained benefit phrase with `chunk_id` provenance |
| `paragraph_chunks.csv` | Source paragraph text, document name, year, technology |
| `cluster_summary.csv` | One row per cluster: size, cross-cutting flag, document count |
| `cluster_exemplars.json` | Top phrases per cluster used to generate labels |
| `cluster_labels.json` | Human-readable cluster labels and framing lens assignments |
| `traceability_paragraphs.csv` | Links every phrase → cluster → source paragraph |
| `evidence_pack_paragraphs.html` | Browser-viewable: cluster label, exemplar phrases, source paragraphs |
| `extraction_yield_summary.csv` | Counts of retained phrases, sentinels, filter drops, errors (CIP-0001) |
| `tech_filter_drops_concern.csv` | Concern phrases removed by the tech-word filter |
| `tech_filter_drops_benefit.csv` | Benefit phrases removed by the tech-word filter |
| `concern_vocab_frequency.csv` | Top-100 words/bigrams in concern phrases; flags meta-vocabulary (CIP-0004) |
| `benefit_vocab_frequency.csv` | Top-100 words/bigrams in benefit phrases; flags meta-vocabulary (CIP-0004) |
| `validation_summary.txt` | Auto-generated counts to use in Activity 4 |
| `validation_playbook.md` | This document |

---

## Suspicious cluster criteria

Flag a cluster for further investigation if **any** of the following are true:

- The cluster label does not match its exemplar phrases
- More than 60 % of phrases come from a single document
- The cluster appears in only one technology's documents despite a "cross-cutting" flag
- Exemplar phrases contain primarily meta-vocabulary ("public dialogue", "engagement", "consultation", "participation")
- Fewer than 3 distinct source documents contribute phrases to the cluster

---

## Activity 1 — Cluster coherence spot-check

**Goal:** Confirm that the top clusters are semantically coherent.

**Files needed:** `cluster_summary.csv`, `evidence_pack_paragraphs.html`

**Steps:**

1. Open `cluster_summary.csv` in a spreadsheet. Sort by the `size` column, largest first.
2. Take the **top 10 clusters by size** and note their `cluster_id` values.
3. Open `evidence_pack_paragraphs.html` in your browser (File → Open).
4. For each of the 10 clusters, find the cluster section (use Ctrl+F to search for the cluster ID or label).
5. Read the **label**, the **exemplar phrases**, and **3–5 source paragraphs**.
6. Ask:
   - Does the label accurately describe the exemplar phrases?
   - Do the source paragraphs contain the concern or benefit described by the phrase?
   - Are any exemplar phrases generic process language (e.g. "ensuring public dialogue is inclusive")?
7. Also spot-check **5 randomly chosen clusters** — use the random sampling snippet below.
8. Record findings in a spreadsheet:

| cluster_id | label | coherent (Y/N/Partial) | notes |
|-----------|-------|----------------------|-------|
| 12 | unfair automated decisions | Y | |
| 7 | public dialogue process | N | Artefact — meta-vocabulary |

<details>
<summary>Optional Python: random sample of 5 clusters</summary>

```python
import pandas as pd, random
cluster_summary = pd.read_csv("cluster_summary.csv")
random.seed(42)
sample = cluster_summary.sample(5, random_state=42)
print(sample[["cluster_id", "label", "size", "cross_cutting"]].to_string(index=False))
```

</details>

---

## Activity 2 — Cross-cutting claim check

**Goal:** Verify that clusters marked as cross-cutting genuinely appear across multiple technologies.

**Files needed:** `cluster_summary.csv`, `traceability_paragraphs.csv`

**Steps:**

1. Open `cluster_summary.csv`. Filter rows where `cross_cutting` is `True` (or `1`).
2. Sort by size, largest first. Take the **top 10 cross-cutting clusters**.
3. Open `traceability_paragraphs.csv`. For each cluster:
   - Filter to rows where `cluster_id` equals the cluster ID.
   - Count how many distinct values appear in the `technology` column.
   - Count the share of phrases from the single most common technology.
4. Flag any cross-cutting cluster where **fewer than 3 technologies** are represented, or where **one technology contributes > 60 %** of phrases.

<details>
<summary>Optional Python: dominance check for all cross-cutting clusters</summary>

```python
import pandas as pd

summary = pd.read_csv("cluster_summary.csv")
trace = pd.read_csv("traceability_paragraphs.csv")

cross = summary[summary["cross_cutting"] == True]["cluster_id"].tolist()

rows = []
for cid in cross:
    sub = trace[trace["cluster_id"] == cid]
    if sub.empty:
        continue
    tech_counts = sub["technology"].value_counts()
    n_techs = len(tech_counts)
    top_share = tech_counts.iloc[0] / len(sub)
    rows.append({
        "cluster_id": cid,
        "n_technologies": n_techs,
        "dominant_tech": tech_counts.index[0],
        "dominant_share_pct": round(100 * top_share, 1),
        "flag": top_share > 0.6 or n_techs < 3,
    })

flags = pd.DataFrame(rows)
print(flags[flags["flag"]])
```

</details>

---

## Activity 3 — Source paragraph verification

**Goal:** Confirm extracted phrases are faithful representations of the source paragraph text.

**Files needed:** `extracted_concerns.csv` (or `extracted_benefits.csv`), `paragraph_chunks.csv`

**Steps:**

1. Open `extracted_concerns.csv`. Take a **random sample of 20 rows**.
2. For each row, find the `chunk_id` value.
3. Open `paragraph_chunks.csv` and filter to that `chunk_id` to get the source paragraph text.
4. Read the source paragraph and the extracted phrase **side by side**.
5. Ask:
   - Is the concern/benefit phrase a fair, decontextualised representation of what the paragraph actually says?
   - Does the phrase contain vocabulary from the extraction prompt (e.g. "public dialogue", "dialogue participants")?
   - Is the phrase so generic it could apply to any paragraph in any document?
6. Record flagged rows:

| chunk_id | extracted_phrase | source_paragraph (excerpt) | issue |
|---------|-----------------|---------------------------|-------|
| chunk_047 | "public dialogue concerns" | "The session was... " | Meta-vocabulary artefact |

<details>
<summary>Optional Python: random sample of 20 rows</summary>

```python
import pandas as pd

concerns = pd.read_csv("extracted_concerns.csv")
chunks = pd.read_csv("paragraph_chunks.csv")

sample = concerns.sample(20, random_state=99)
merged = sample.merge(chunks[["chunk_id", "text", "source_file", "technology"]], on="chunk_id", how="left")

for _, row in merged.iterrows():
    print(f"\n--- chunk_id: {row['chunk_id']} | tech: {row['technology']} ---")
    print(f"PHRASE : {row['concern']}")
    print(f"SOURCE : {str(row['text'])[:300]}")
    print()
```

</details>

---

## Activity 4 — Export pack completeness check

**Goal:** Confirm the export pack contains expected files and that record counts are consistent.

**Files needed:** `validation_summary.txt`, `extraction_yield_summary.csv`

**Steps:**

1. Open `validation_summary.txt` (auto-generated by the notebook). It shows key counts.
2. Verify the following files are present in the ZIP:
   - [ ] `paragraph_chunks.csv`
   - [ ] `extracted_concerns.csv`
   - [ ] `extracted_benefits.csv`
   - [ ] `cluster_summary.csv`
   - [ ] `cluster_exemplars.json`
   - [ ] `cluster_labels.json`
   - [ ] `traceability_paragraphs.csv`
   - [ ] `evidence_pack_paragraphs.html`
   - [ ] `extraction_yield_summary.csv`
3. Cross-check record counts from `extraction_yield_summary.csv`:
   - `total_chunks` (concern row) should equal row count of `paragraph_chunks.csv`
   - `retained_phrases` (concern row) should equal row count of `extracted_concerns.csv`
   - `retained_phrases` (benefit row) should equal row count of `extracted_benefits.csv`
4. Check that `cluster_summary.csv` has exactly `N_CONCERN_CLUSTERS` rows for the concern analysis and `N_BENEFIT_CLUSTERS` rows for the benefit analysis.
5. Flag any discrepancies.

---

## Recommended review order

For an efficient first pass, work through the activities in this order:

1. **Activity 4** first — confirm the export pack is complete before investing time in content review.
2. **Activity 1** — check that the largest clusters (which drive most conclusions) are coherent.
3. **Activity 3** — ground-truth a random sample of phrases against source paragraphs.
4. **Activity 2** — verify cross-cutting claims if they are used in the paper.

For a thorough review (e.g. before submission), repeat Activity 3 with a larger sample (50+ rows) and check all cross-cutting clusters in Activity 2.

---

## Recording your findings

Use a shared spreadsheet with four tabs (one per activity). Aim to document:

- Which clusters were flagged and why
- How many phrases in the random sample were faithful vs. problematic
- Whether any systematic pattern is visible (e.g. a particular document dominates a cluster)

Share findings with the other analyst and agree on whether flagged clusters should be:

- **Removed** from the analysis (if they are clear artefacts)
- **Relabelled** (if the cluster is real but the label is poor)
- **Noted** in the paper as a limitation

---

## Linking back to the notebook

If you find a problematic cluster and want to investigate further in the notebook:

```python
# Find all phrases in a specific cluster
SUSPECT_CLUSTER_ID = 7
suspect = traceability_df[traceability_df["cluster_id"] == SUSPECT_CLUSTER_ID]
print(suspect[["concern", "chunk_id", "source_file", "technology"]].to_string(index=False))
```

---

*This playbook was generated as part of CIP-0005. See `cip/cip0005.md` for the full design rationale.*
