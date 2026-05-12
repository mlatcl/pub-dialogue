# Public Dialogue Analyser

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mlatcl/pub-dialogue/blob/main/public_dialogue_analyser_v19.ipynb)

## What this project does

This project applies large language model (LLM) text extraction and unsupervised
clustering to a corpus of 66 UK public dialogue reports, spanning 2004–2025 and
covering technologies including AI, gene editing, nanotechnology, nuclear energy,
geoengineering, drones, and quantum technologies.

The goal is to ask: **what do members of the public consistently say they are
concerned about, or see as beneficial, when asked about new and emerging technologies —
and how cross-cutting are those themes?**

The analysis pipeline:

1. **Extracts** concern and benefit phrases from each paragraph in each report
   using a structured LLM prompt (GPT-4o).
2. **Embeds** the extracted phrases using the OpenAI embeddings API.
3. **Clusters** the embeddings (k-means) to identify recurring themes.
4. **Labels** each cluster using the LLM, producing human-readable summaries.
5. **Characterises** clusters as either cross-cutting (appearing across many
   technologies) or technology-specific (concentrated in one or two domains),
   using Shannon entropy over the technology distribution.
6. **Tracks** how concern and benefit themes vary over time (by dialogue year)
   and across technology domains.

The work contributes to a research paper on the structure of public attitudes
towards science and technology in the UK.

## Data

The corpus consists of 66 publicly available UK public dialogue reports, held in
a shared Google Drive folder:

- **PDFs**: [Public dialogue PDFs on Google Drive](https://drive.google.com/drive/folders/1WhTZE4kaNO5rBikDgNVsTe1INpdzNEJt?usp=sharing)
- **Metadata**: [tech_metadata Google Sheet](https://docs.google.com/spreadsheets/d/1fWE5Agm4LStCcZZQqvmgamIanhYyfrcb/edit?usp=share_link) — maps each PDF to its technology category and year

The notebook downloads both automatically when run in Colab. No manual upload is
needed.

## Quick start (Google Colab)

Click the badge above. The notebook will:

1. Install Python dependencies (`PyMuPDF`, `openai`, `scikit-learn`, etc.)
2. Fetch `dialogue_utils.py` from this repository
3. Download the PDF corpus and metadata from Google Drive

You will need to provide an API key for your chosen LLM provider (stored as a
Colab secret or in a local `.env` file — see [Supported LLM providers](#supported-llm-providers) below).

## Repository structure

| Path | Contents |
|------|----------|
| `public_dialogue_analyser_v19.ipynb` | Main analysis notebook (v19) |
| `prompt_sensitivity_v16.ipynb` | Prompt sensitivity analysis notebook |
| `dialogue_utils.py` | Shared utility functions (imported by the notebook) |
| `tests/` | pytest suite for `dialogue_utils.py` (153 tests) |
| `validation_playbook.md` | Researcher guide for reviewing and validating outputs |
| `cip/` | Code Improvement Plans — design decisions and implementation tracking |
| `backlog/` | Task tracking — bugs and features |
| `requirements/` | Project requirements |

## Supported LLM providers

The pipeline uses [`litellm`](https://docs.litellm.ai/) so you can switch
providers by changing a single config variable (`LLM_MODEL`) in the notebook.

| Provider | Example `LLM_MODEL` | Required env-var |
|---|---|---|
| OpenAI (default) | `gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini/gemini-2.0-flash` | `GOOGLE_API_KEY` |

For the full list of supported models see the
[litellm provider docs](https://docs.litellm.ai/docs/providers).

> **Note on embeddings**: `EMBEDDING_MODEL` (default `text-embedding-3-large`)
> is intentionally separate from `LLM_MODEL`.  Changing it invalidates all
> saved `*.npy` embedding artifacts and requires a full re-run of
> `01_processing.ipynb`.

## Running locally

```bash
git clone https://github.com/mlatcl/pub-dialogue.git
cd pub-dialogue
pip install -e ".[dev]"
cp .env.example .env   # then add your API key(s)
jupyter notebook 01_processing.ipynb
```

## Running tests

```bash
pip install pytest
pytest tests/
```

## Analysis outputs

Running the full notebook produces outputs in the `outputs/` directory, including:

| File | Description |
|------|-------------|
| `paragraph_chunks.csv` | All extracted text chunks with `chunking_method` and `was_truncated` columns |
| `paragraph_chunks_per_document.csv` | Per-document chunk counts and chunking method used |
| `extracted_concerns.csv` | All extracted concern phrases with source chunk and document |
| `extracted_benefits.csv` | All extracted benefit phrases |
| `cluster_summary.csv` | Concern cluster sizes, entropy, and cross-cutting classification |
| `benefit_cluster_summary.csv` | Benefit cluster summary |
| `cluster_labels.json` | LLM-generated concern cluster labels |
| `benefit_cluster_labels.json` | LLM-generated benefit cluster labels |
| `ai_distinctive_concerns.csv` | Concern clusters most over- or under-represented in AI dialogues |
| `ai_distinctive_framings.csv` | Framing lens distinctiveness for AI vs non-AI dialogues |
| `ai_distinctive_benefits.csv` | Benefit clusters most distinctive to AI dialogues |
| `extraction_yield_summary.csv` | Per-run extraction yield statistics (concern + benefit) |
| `tech_filter_drops_concern.csv` | Concern phrases dropped by the technology-word filter |
| `tech_filter_drops_benefit.csv` | Benefit phrases dropped by the technology-word filter |
| `validation_summary.txt` | Key counts and file checklist for result validation |
| `sensitivity_*_k{60,75,90}.*` | Concern k-sensitivity outputs |
| `benefit_sensitivity_*_k{60,75,90}.*` | Benefit k-sensitivity outputs |

## Project management

This project uses [VibeSafe](https://github.com/lawrennd/vibesafe) for
structured project management. The development workflow is:

- **Tenets** — guiding principles
- **Requirements** (`requirements/`) — what the system should do
- **CIPs** (`cip/`) — how we are going to do it (design plans)
- **Backlog** (`backlog/`) — concrete tasks in progress or queued

Current open CIPs address: prompt sensitivity analysis methodology (CIP-0008)
and temporal analysis normalisation (CIP-0009) — both pending research
discussion. See `cip/README.md` for the full list.
