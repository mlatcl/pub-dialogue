# Public Dialogue Analyser

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mlatcl/pub-dialogue/blob/main/public_dialogue_analyser_v12b_4.ipynb)

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

You will need to provide an **OpenAI API key** (stored as a Colab secret named
`OPENAI_API_KEY`, or pasted when prompted).

## Repository structure

| Path | Contents |
|------|----------|
| `public_dialogue_analyser_v12b_4.ipynb` | Main analysis notebook |
| `dialogue_utils.py` | Shared utility functions (imported by the notebook) |
| `tests/` | pytest suite for `dialogue_utils.py` (103 tests) |
| `validation_playbook.md` | Researcher guide for reviewing and validating outputs |
| `cip/` | Code Improvement Plans — design decisions and implementation tracking |
| `backlog/` | Task tracking — bugs and features |
| `requirements/` | Project requirements |

## Running locally

```bash
git clone https://github.com/mlatcl/pub-dialogue.git
cd pub-dialogue
pip install PyMuPDF openai scikit-learn umap-learn plotly kaleido openpyxl tqdm scipy
jupyter notebook public_dialogue_analyser_v12b_4.ipynb
```

## Running tests

```bash
pip install pytest
pytest tests/
```

## Analysis outputs

Running the full notebook produces a ZIP export containing:

| File | Description |
|------|-------------|
| `concern_phrases.csv` | All extracted concern phrases with source chunk and document |
| `benefit_phrases.csv` | All extracted benefit phrases |
| `concern_clusters_k*.csv` | Cluster assignments at each k |
| `benefit_clusters_k*.csv` | Cluster assignments at each k |
| `concern_labels_k*.json` | LLM-generated cluster labels |
| `benefit_labels_k*.json` | LLM-generated cluster labels |
| `extraction_yield_summary.csv` | Per-document extraction yield statistics |
| `tech_filter_drops_*.csv` | Phrases dropped by the technology-word filter |
| `extraction_errors_*.csv` | Chunks where the LLM returned an error |
| `concern_vocab_frequency.csv` | Top unigram/bigram vocabulary in concern phrases |
| `benefit_vocab_frequency.csv` | Top unigram/bigram vocabulary in benefit phrases |
| `validation_summary.txt` | Key counts and file checklist for result validation |
| `validation_playbook.md` | Researcher guide (copy of repository file) |

## Project management

This project uses [VibeSafe](https://github.com/lawrennd/vibesafe) for
structured project management. The development workflow is:

- **Tenets** — guiding principles
- **Requirements** (`requirements/`) — what the system should do
- **CIPs** (`cip/`) — how we are going to do it (design plans)
- **Backlog** (`backlog/`) — concrete tasks in progress or queued

Current open CIPs address: chunk extraction filter correctness, technology
metadata leak in cluster labelling, prompt sensitivity analysis, and temporal
analysis normalisation. See `cip/README.md` for the full list.
