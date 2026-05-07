# Public Dialogue Analyser

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mlatcl/pub-dialogue/blob/main/public_dialogue_analyser_v12b_4.ipynb)

Analysis of UK public dialogue documents on science and technology, identifying shared concerns and benefits across technologies and tracking how public dialogue about AI changes over time.

## Quick start

Click the badge above to open the notebook directly in Google Colab. The first cell installs dependencies and fetches `dialogue_utils.py` automatically.

### Loading the PDF corpus

The notebook supports two modes for loading the 66 source PDFs:

**Option A — Public Google Drive folder (recommended)**

1. Upload the PDF corpus and metadata Excel to a Google Drive folder
2. Share the folder: right-click → Share → **Anyone with the link → Viewer**
3. Copy the folder ID from the URL (`drive.google.com/drive/folders/`**`<ID>`**)
4. In cell "Load PDF corpus", set `CORPUS_FOLDER_ID = "<your folder ID>"`
5. Do the same for `METADATA_FILE_ID` (the file ID of the metadata Excel)

The notebook will then download everything automatically via `gdown` — no sign-in required.

**Option B — Manual upload**

Leave `CORPUS_FOLDER_ID = None`. The cell falls back to `files.upload()`, where you can select all PDFs at once.

## Repository structure

| Path | Contents |
|------|----------|
| `public_dialogue_analyser_v12b_4.ipynb` | Main analysis notebook |
| `dialogue_utils.py` | Shared utility functions (imported by the notebook) |
| `tests/` | pytest test suite for `dialogue_utils.py` (103 tests) |
| `validation_playbook.md` | Researcher guide for reviewing analysis outputs |
| `cip/` | Code Improvement Plans |
| `backlog/` | Task tracking |
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

## Project management

This project uses [VibeSafe](https://github.com/lawrennd/vibesafe) for structured project management (CIPs, backlog, requirements).
