---
author: "Neil Lawrence"
created: "2026-05-12"
id: "000C"
last_updated: "2026-05-12"
status: "Proposed"
compressed: false
related_requirements: []
related_cips: ["000B"]
tags:
- cip
- llm
- multi-provider
title: "Multi-LLM provider support via litellm"
---

# CIP-000C: Multi-LLM provider support via litellm

## Status

- [x] Proposed - Initial idea documented
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete

## Summary

Replace the hard-coded `openai.OpenAI` client throughout the pipeline with
[litellm](https://docs.litellm.ai/), a thin wrapper that exposes an
OpenAI-compatible interface for virtually every major LLM provider (Anthropic,
Google Gemini, Mistral, Cohere, Azure, etc.).  With this change, switching
from `gpt-4o-mini` to `claude-3-5-haiku-latest` or
`gemini/gemini-2.0-flash` becomes a one-line config change.  Embeddings
remain on OpenAI by default (they are corpus-wide and cannot be changed
mid-project without re-embedding), but the embedding provider is also
made configurable.

## Motivation

CIP-000B introduced `pub_dialogue` as an installable package and added
`.env`-based key management for `OPENAI_API_KEY`.  The pipeline now has a
clean boundary between LLM calls (extraction, labelling, embedding) and
pure-Python analysis.

However, every LLM call is still tightly coupled to the `openai` SDK:

```python
from openai import OpenAI
client = OpenAI(api_key=api_key)
client.chat.completions.create(model="gpt-4o-mini", ...)
client.embeddings.create(model="text-embedding-3-large", ...)
```

Using Anthropic's Claude or Google's Gemini requires a completely different
SDK and call signature.  `litellm` removes this friction: it re-exports
`openai.chat.completions.create` and `openai.embeddings.create` semantics
but routes the call to any supported backend based on the model name prefix.

## Detailed Description

### Design decisions

**Why litellm, not provider SDKs directly?**
- Single import, single call signature — no branching code per provider.
- Model name is the only change needed: `"gpt-4o-mini"` →
  `"claude-3-5-haiku-latest"` → `"gemini/gemini-2.0-flash"`.
- Handles retries, rate limiting, and cost tracking across providers.
- Actively maintained; supports 100+ models.

**Embeddings**
Embeddings are intentionally more conservative.  The `concern_embeddings.npy`
and `benefit_embeddings.npy` artifacts are corpus-wide — changing the
embedding model invalidates all downstream cluster assignments.  Therefore:
- Default embedding provider stays `text-embedding-3-large` (OpenAI).
- A separate `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` config pair is added.
- Changing embedding model requires re-running `01_processing.ipynb` from
  scratch and is explicitly warned in the notebook.
- litellm supports embeddings from Cohere, VoyageAI, etc. if needed.

**Authentication**
litellm reads provider keys from environment variables automatically:
- `OPENAI_API_KEY` → OpenAI
- `ANTHROPIC_API_KEY` → Anthropic
- `GOOGLE_API_KEY` → Gemini
No extra wiring needed beyond what `.env` already provides (CIP-000B).

### `LLMClient` wrapper (`pub_dialogue/client.py`)

Rather than calling `litellm` directly inside utility functions (which just
swaps one tight coupling for another), a thin `LLMClient` class is introduced
as the single integration point.  Functions continue to receive a `client`
argument — dependency injection is preserved, and litellm is an implementation
detail hidden behind the wrapper.

```python
# pub_dialogue/client.py

class LLMClient:
    """Thin wrapper around litellm providing a stable, mockable interface.

    All LLM calls in pub_dialogue.utils go through this class.  litellm is
    imported lazily inside each method so the package loads without it if
    no API calls are needed (e.g. pure-analysis notebooks).
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-large",
    ):
        self.model = model
        self.embedding_model = embedding_model

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Return the text of the first completion choice."""
        import litellm
        resp = litellm.completion(model=self.model, messages=messages, **kwargs)
        return resp.choices[0].message.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors, one per input text."""
        import litellm
        resp = litellm.embedding(model=self.embedding_model, input=texts)
        return [d.embedding for d in resp.data]
```

**Why a wrapper rather than calling litellm directly?**

- **Testability**: `mock_client = MagicMock(spec=LLMClient)` — no
  module-level patching of `litellm.*` in every test.
- **Single integration point**: if litellm's API ever changes, only
  `client.py` needs updating.
- **Lazy import**: `import litellm` inside each method means analysis
  notebooks that never call the API don't pay the import cost and don't
  need litellm installed.
- **Type-safe signatures**: functions annotated `client: LLMClient` instead
  of `client: Any`.
- **Swappable**: a `MockLLMClient` with identical interface can be used
  in tests or dry-run modes without patching anything.

### Changes to `pub_dialogue/utils.py`

1. Remove `from openai import OpenAI`.
2. Import `LLMClient` from `pub_dialogue.client`.
3. `extract_phrases(chunk_text, kind, client: LLMClient)` — replace
   `client.chat.completions.create(...)` with `client.complete(messages)`.
4. `label_cluster(phrases, client: LLMClient)` — same.
5. `embed_texts(texts, client: LLMClient)` — replace
   `client.embeddings.create(...)` with `client.embed(texts)`.
6. The `model` parameter is removed from each function signature (it now
   lives on the `LLMClient` instance).

### Changes to notebooks

**`01_processing.ipynb` config cell** (cell 3):
```python
LLM_MODEL       = "gpt-4o-mini"             # any litellm model string
EMBEDDING_MODEL = "text-embedding-3-large"  # change only with full re-run
```

**API access cell** (cell 6) — simplified, constructs an `LLMClient`:
```python
import os
from dotenv import load_dotenv
from pub_dialogue.client import LLMClient

load_dotenv()

# Infer which env-var key to prompt for from the model name prefix
_key_map = {"claude": "ANTHROPIC_API_KEY", "gemini": "GOOGLE_API_KEY"}
_key_var = next(
    (v for k, v in _key_map.items() if LLM_MODEL.startswith(k)),
    "OPENAI_API_KEY",
)
if not os.environ.get(_key_var):
    from getpass import getpass
    os.environ[_key_var] = getpass(f"Enter {_key_var}: ")

client = LLMClient(model=LLM_MODEL, embedding_model=EMBEDDING_MODEL)
print(f"LLMClient ready — model: {LLM_MODEL}, embeddings: {EMBEDDING_MODEL}")
```

`LLM_PROVIDER` is dropped; the provider is inferred from the model name
(litellm convention), so `"claude-..."` routes to Anthropic automatically.

### `pyproject.toml` changes

```toml
dependencies = [
    ...
    "litellm>=1.40",   # replaces direct openai calls
    "openai>=1.10",    # still needed for embeddings fallback and type stubs
]
```

`anthropic` and `google-generativeai` are NOT added as hard dependencies —
litellm installs lightweight shims and only uses the provider SDK if the
user has it installed.  This keeps the package lean.

### Backward compatibility

- `pub_dialogue.utils` function signatures are unchanged (`client` is still
  the first positional argument); callers pass an `LLMClient` instead of an
  `openai.OpenAI`.  The `model` kwarg is removed from function signatures
  (it now lives on the client); existing call sites that passed `model=`
  explicitly will raise `TypeError` and need updating.
- Notebooks that pin `LLM_MODEL = "gpt-4o-mini"` and have `OPENAI_API_KEY`
  set continue to work by constructing `LLMClient(model=LLM_MODEL)`.
- Tests are updated to `MagicMock(spec=LLMClient)` — no litellm patching.

## Implementation Plan

1. **Add litellm to `pyproject.toml`** as a core dependency.

2. **Create `pub_dialogue/client.py`** with the `LLMClient` wrapper class.
   Export it from `pub_dialogue/__init__.py`.

3. **Update `pub_dialogue/utils.py`**:
   - Remove `from openai import OpenAI`.
   - Annotate `client: LLMClient` parameters.
   - Replace `client.chat.completions.create(...)` → `client.complete(messages)`.
   - Replace `client.embeddings.create(...)` → `client.embed(texts)`.
   - Remove `model` parameter from function signatures.

4. **Update `tests/test_dialogue_utils.py`**:
   - Replace `MagicMock` `openai.OpenAI` constructions with
     `MagicMock(spec=LLMClient)`.
   - Add a `TestLLMClient` class with mocked litellm; verify `complete` and
     `embed` return correctly shaped outputs.
   - Add parametrised provider smoke test.

5. **Update `01_processing.ipynb`** and **`01a_clustering.ipynb`**:
   - Drop `LLM_PROVIDER`; keep `LLM_MODEL` and `EMBEDDING_MODEL`.
   - Replace API access cell with `LLMClient(...)` construction.

6. **Update `.env.example`** with provider key comments (done in Level 1).

7. **Update `README.md`** with supported providers table.

8. **Run full test suite**; confirm 171+ tests pass.

9. **Commit** and mark CIP Implemented.

## Backward Compatibility

Existing notebooks using OpenAI continue to work unchanged as long as
`OPENAI_API_KEY` is set.  The `client` argument to utility functions is
preserved but ignored — a `DeprecationWarning` will be emitted.

## Testing Strategy

- **Unit tests for `LLMClient`**: mock `litellm.completion` and
  `litellm.embedding` at the litellm module level; verify `complete` returns
  a string and `embed` returns a list of float lists.
- **Unit tests for utils functions**: use `MagicMock(spec=LLMClient)` —
  no litellm patching needed.  Verify functions call `client.complete` /
  `client.embed` with correct arguments.
- **Parametrised provider smoke test**: construct `LLMClient` with model
  strings `"gpt-4o-mini"`, `"claude-3-5-haiku-latest"`,
  `"gemini/gemini-2.0-flash"`; verify no import errors and correct routing
  (mocked litellm).
- Full suite must stay at 171+ tests passing.

## Related Requirements

None formally defined yet; this improves developer flexibility and
reproducibility.

## Implementation Status

- [ ] Add litellm to `pyproject.toml`
- [ ] Create `pub_dialogue/client.py` with `LLMClient`
- [ ] Export `LLMClient` from `pub_dialogue/__init__.py`
- [ ] Update `pub_dialogue/utils.py` — swap openai calls, annotate client type
- [ ] Update `tests/test_dialogue_utils.py` — spec mocks + `TestLLMClient`
- [ ] Update `01_processing.ipynb` config + API access cells
- [ ] Update `01a_clustering.ipynb` if needed
- [ ] Update `README.md`
- [ ] Full test suite green
- [ ] Commit

## References

- [litellm documentation](https://docs.litellm.ai/)
- [litellm supported providers](https://docs.litellm.ai/docs/providers)
- [CIP-000B: pub_dialogue package](cip000B.md)
- [Dependency injection pattern](https://en.wikipedia.org/wiki/Dependency_injection)
