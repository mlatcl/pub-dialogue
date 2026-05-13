# Public Dialogue Analyser

## What this project does

This project applies large language model (LLM) text extraction and unsupervised
clustering to a corpus of 66 UK public dialogue reports, spanning 2004–2025 and
covering technologies including AI, gene editing, nanotechnology, nuclear energy,
geoengineering, drones, and quantum technologies.

The goal is to ask: **what do members of the public consistently say they are
concerned about, or see as beneficial, when asked about new and emerging technologies —
and how cross-cutting are those themes?**

The analysis pipeline:

1. **Extracts** concern and benefit phrases from each paragraph using a structured LLM prompt (GPT-4o-mini).
2. **Embeds** the extracted phrases using the OpenAI embeddings API.
3. **Clusters** the embeddings (k-means, 75 clusters) to identify recurring themes.
4. **Labels** each cluster using the LLM, producing human-readable summaries.
5. **Characterises** clusters as either cross-cutting (appearing across many technologies)
   or technology-specific (concentrated in one or two domains), using Shannon entropy.
6. **Tracks** how concern and benefit themes vary over time (by dialogue year) and
   across technology domains using document-level binary weighting (CIP-0009).

The work contributes to a research paper on the structure of public attitudes towards
science and technology in the UK.

## Data

The corpus consists of 66 publicly available UK public dialogue reports:

- **PDFs**: [Public dialogue PDFs on Google Drive](https://drive.google.com/drive/folders/1WhTZE4kaNO5rBikDgNVsTe1INpdzNEJt?usp=sharing)
- **Metadata**: [tech_metadata Google Sheet](https://docs.google.com/spreadsheets/d/1fWE5Agm4LStCcZZQqvmgamIanhYyfrcb/edit?usp=share_link) — maps each PDF to its technology category and year

## Repository structure

### Analysis notebooks (run in order)

| Notebook | Stage | Description |
|---|---|---|
| `00_data_quality.ipynb` | Assess | Corpus quality assessment — chunk lengths, coverage by technology and year, missing-text diagnostics |
| `01_processing.ipynb` | Access → Address | PDF chunking, LLM concern/benefit extraction, embedding generation |
| `01a_clustering.ipynb` | Address | k-means clustering, LLM cluster labelling, framing-lens assignment |
| `02_shared_structure.ipynb` | Address | Cross-technology concern and benefit structure, cross-cutting cluster identification |
| `03_ai_distinctiveness.ipynb` | Address | AI-specific cluster salience compared to other technologies |
| `04_temporal_dynamics.ipynb` | Address | Year-by-year trend analysis using document-level binary weighting |
| `05_robustness.ipynb` | Address | Sensitivity analyses — alternative cluster counts, prompt wording, temporal stability |

The legacy monolith `public_dialogue_analyser_v19.ipynb` remains in the repository
for reference but is no longer the active pipeline.

### Python package

The `pub_dialogue/` package implements the [Fynesse](https://github.com/lawrennd/fynesse)
Access → Assess → Address pipeline:

| Module | Stage | Description |
|---|---|---|
| `pub_dialogue/access.py` | Access | PDF chunking, artifact loading, `AccessStage` config class |
| `pub_dialogue/assess.py` | Assess | Question-agnostic quality plots and diagnostics, `AssessStage` |
| `pub_dialogue/address.py` | Address | Extraction, clustering, labelling, temporal analysis, `AddressStage` |
| `pub_dialogue/client.py` | — | `LLMClient` abstraction over `litellm` (supports OpenAI, Anthropic, Gemini) |
| `pub_dialogue/utils.py` | — | Shared re-exports for notebook convenience |

### Other files

| Path | Description |
|---|---|
| `tests/` | 336-test pytest suite covering all three modules and stage classes |
| `outputs/` | Pipeline artefacts (CSVs, JSONs, figures) — not committed |
| `checkpoints/` | Embedding and soft-membership numpy arrays — not committed |
| `cip/` | Code Improvement Plans — design decisions (16 CIPs, all closed) |
| `backlog/` | Task tracking — bugs, features, documentation |
| `requirements/` | Project requirements (VibeSafe governance) |
| `validation_playbook.md` | Researcher guide for reviewing and validating LLM outputs |

## Quick start (local)

```bash
git clone https://github.com/mlatcl/pub-dialogue.git
cd pub-dialogue
pip install -e ".[dev]"
cp .env.example .env   # add your API key(s)
```

Run notebooks in order, starting with `01_processing.ipynb` to build the artefact
cache. Subsequent notebooks (`01a`, `02`–`05`) load pre-computed artefacts and do
not call the LLM.

## Running tests

```bash
pytest tests/ -v
# 336 tests across test_access.py, test_assess.py, test_address.py, test_dialogue_utils.py
```

## pub_dialogue package API

The package uses three stage-configuration dataclasses that centralise all path
and parameter constants (no more hard-coded values across notebooks).

### The three stages

```
Access → Assess → Address
```

| Stage | Owns | Question-agnostic? |
|---|---|---|
| **Access** | Obtaining raw data (PDFs → chunks → embeddings) | Yes |
| **Assess** | Characterising data quality without knowing the research question | Yes |
| **Address** | Answering the research question (extraction, clustering, labelling, analysis) | No |

### Stage classes

```python
from pub_dialogue.access import AccessStage
from pub_dialogue.assess import AssessStage
from pub_dialogue.address import AddressStage

# Instantiate (all parameters have sensible defaults)
access  = AccessStage()                   # output_folder="outputs", checkpoint_folder="checkpoints"
assess  = AssessStage(access=access)
address = AddressStage(access=access)     # n_concern_clusters=75, random_seed=42
```

**`AccessStage`** — paths and chunking parameters:

```python
artifacts = access.load_artifacts()       # load all pre-computed CSVs + numpy arrays
# Returns dict with: chunks_df, concerns_df, benefits_df,
#                    concern_embeddings, benefit_embeddings, concern_ids, benefit_ids
```

**`AssessStage`** — question-agnostic quality helpers:

```python
assess.plot_quality(chunks_df)            # write data_quality_overview.png to outputs/
assess.validate_cache(cache, kind)        # check extraction cache for partial-failure runs
assess.validation_summary()              # write validation_summary.txt to outputs/
```

**`AddressStage`** — analysis computations:

```python
# Year × cluster matrices (document-level binary weighting, CIP-0009)
ai_year       = address.concern_year_matrix(concerns_df, chunks_df)
benefit_ai_yr = address.benefit_year_matrix(benefits_df, chunks_df)

# PCA embedding trajectories
traj = address.concern_trajectory(concerns_df, embeddings, phrase_ids)

# Technology × cluster salience
salience = address.concern_salience(concerns_df)

# Pipeline methods (used in 01a_clustering.ipynb)
result = address.cluster_phrases(phrases_df, embeddings, kind='concern',
                                 output_folder=access.output_folder,
                                 checkpoint_folder=access.checkpoint_folder)
# result keys: phrases_df, assignments, embeddings_normalized, centroids_normalized, soft_membership

labels = address.label_clusters(exemplars, kind='concern',
                                output_folder=access.output_folder, client=client)

mappings = address.assign_framing_lenses(exemplars, labels, n_clusters=75,
                                         kind='concern',
                                         output_folder=access.output_folder, client=client)
```

### Notebook setup pattern

Every analysis notebook starts with:

```python
from pub_dialogue.utils import AccessStage, AddressStage, AssessStage, show_status

_access  = AccessStage()
_address = AddressStage(access=_access)
_assess  = AssessStage(access=_access)

OUTPUT_FOLDER     = _access.output_folder
CHECKPOINT_FOLDER = _access.checkpoint_folder
TECH_COL          = _address.tech_col

artifacts = _access.load_artifacts()
```

## Supported LLM providers

The pipeline uses [`litellm`](https://docs.litellm.ai/) — switch providers by
changing `LLM_MODEL` in `01_processing.ipynb` or `01a_clustering.ipynb`.

| Provider | Example `LLM_MODEL` | Required env-var |
|---|---|---|
| OpenAI (default) | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini/gemini-2.0-flash` | `GOOGLE_API_KEY` |

> **Note on embeddings**: `EMBEDDING_MODEL` (default `text-embedding-3-large`)
> is separate from `LLM_MODEL`. Changing it invalidates all saved `*.npy` embedding
> artefacts and requires a full re-run of `01_processing.ipynb`.

## Analysis outputs

Running the full pipeline produces outputs in `outputs/`:

| File | Description |
|---|---|
| `paragraph_chunks.csv` | All extracted text chunks with `chunking_method` and `was_truncated` |
| `extracted_concerns.csv` | Concern phrases with source chunk, cluster assignment, technology, year |
| `extracted_benefits.csv` | Benefit phrases with same fields |
| `cluster_labels.json` | LLM-generated concern cluster labels and descriptions |
| `benefit_cluster_labels.json` | LLM-generated benefit cluster labels |
| `cluster_summary.csv` | Concern cluster sizes, entropy, cross-cutting classification |
| `framing_lens_mappings.json` | Concern framing lens → cluster assignments |
| `benefit_framing_lens_mappings.json` | Benefit framing lens → cluster assignments |
| `ai_distinctive_concerns.csv` | Concern clusters most over/under-represented in AI dialogues |
| `ai_distinctive_benefits.csv` | Benefit clusters most distinctive to AI |
| `validation_summary.txt` | Key counts and file checklist for result validation |
| `sensitivity_*_k{60,75,90}.*` | Concern k-sensitivity outputs |
| `benefit_sensitivity_*_k{60,75,90}.*` | Benefit k-sensitivity outputs |

## Project management

This project uses [VibeSafe](https://github.com/lawrennd/vibesafe) for structured
project management. The development workflow is:

- **Tenets** — guiding principles (Fynesse AAA separation, Access/Assess/Address invariant)
- **Requirements** (`requirements/`) — what the system should do
- **CIPs** (`cip/`) — design plans and architectural decisions (16 CIPs, all closed — see `cip/README.md`)
- **Backlog** (`backlog/`) — concrete tasks in progress or queued
