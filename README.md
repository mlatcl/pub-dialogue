# Public Dialogue Analyser

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mlatcl/pub-dialogue/blob/main/public_dialogue_analyser_v12b_4.ipynb)

Analysis of UK public dialogue documents on science and technology, identifying shared concerns and benefits across technologies and tracking how public dialogue about AI changes over time.

## Quick start

Click the badge above to open the notebook directly in Google Colab. The first cell installs dependencies and fetches `dialogue_utils.py` automatically.

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
