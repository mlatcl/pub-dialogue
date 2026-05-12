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

### Changes to `pub_dialogue/utils.py`

1. Replace `from openai import OpenAI` with `import litellm`.
2. `extract_phrases(chunk_text, kind, client, model)` — `client` parameter
   becomes optional/deprecated; calls become `litellm.completion(model=model, ...)`.
3. `label_cluster(phrases, client, model)` — same pattern.
4. `embed_texts(texts, client, model)` — becomes
   `litellm.embedding(model=model, input=texts).data`.
5. A thin `get_client()` shim is kept for backward compatibility (returns a
   `litellm`-backed object that satisfies the existing call sites).

### Changes to notebooks

**`01_processing.ipynb` config cell** (cell 3):
```python
LLM_PROVIDER    = "openai"               # openai | anthropic | google
LLM_MODEL       = "gpt-4o-mini"          # any litellm model string
EMBEDDING_MODEL = "text-embedding-3-large"  # change only with full re-run
```

**API access cell** (cell 6) — simplified:
```python
import os, litellm
from dotenv import load_dotenv
load_dotenv()
# litellm picks up provider keys from env automatically.
# Verify at least one key is present:
provider_keys = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}
key_var = provider_keys.get(LLM_PROVIDER, "OPENAI_API_KEY")
if not os.environ.get(key_var):
    from getpass import getpass
    os.environ[key_var] = getpass(f"Enter {key_var}: ")
print(f"Provider: {LLM_PROVIDER}, model: {LLM_MODEL}")
```

The `client = OpenAI(...)` line and subsequent `client.models.list()` check
are removed; litellm is stateless.

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

- `pub_dialogue.utils` functions keep the same signatures; `client` arg
  is accepted but ignored (deprecated warning added).
- Notebooks that pin `LLM_MODEL = "gpt-4o-mini"` and have `OPENAI_API_KEY`
  set continue to work without any changes.
- Tests that mock `openai.OpenAI` are updated to mock `litellm.completion`
  and `litellm.embedding` instead.

## Implementation Plan

1. **Add litellm to `pyproject.toml`** as a core dependency.

2. **Update `pub_dialogue/utils.py`**:
   - Swap `openai.OpenAI` client calls for `litellm.completion` /
     `litellm.embedding`.
   - Keep function signatures; mark `client` arg as deprecated.

3. **Update `tests/test_dialogue_utils.py`**:
   - Replace `openai` mocks with `litellm` mocks.
   - Add provider-switching integration test (mocked).

4. **Update `01_processing.ipynb`**:
   - Add `LLM_PROVIDER` / `EMBEDDING_MODEL` config variables.
   - Simplify API access cell (remove `OpenAI` client init).

5. **Update remaining notebooks** (`01a_clustering.ipynb` and any that call
   LLM functions directly) for the same provider config pattern.

6. **Update `.env.example`** with provider key comments (done in Level 1).

7. **Update `README.md`** with supported providers table.

8. **Run full test suite**; confirm 171+ tests pass.

9. **Commit** and mark CIP Implemented.

## Backward Compatibility

Existing notebooks using OpenAI continue to work unchanged as long as
`OPENAI_API_KEY` is set.  The `client` argument to utility functions is
preserved but ignored — a `DeprecationWarning` will be emitted.

## Testing Strategy

- Unit tests: mock `litellm.completion` and `litellm.embedding`; verify
  extraction, labelling, and embedding functions produce correct output.
- Smoke test: parametrised test over provider strings `["openai",
  "anthropic", "google"]` using mocked responses.
- Full suite must stay at 171+ tests passing.

## Related Requirements

None formally defined yet; this improves developer flexibility and
reproducibility.

## Implementation Status

- [ ] Add litellm to `pyproject.toml`
- [ ] Update `pub_dialogue/utils.py` to use litellm
- [ ] Update test mocks
- [ ] Update `01_processing.ipynb` config + API access cells
- [ ] Update `01a_clustering.ipynb` if needed
- [ ] Update `README.md`
- [ ] Full test suite green
- [ ] Commit

## References

- [litellm documentation](https://docs.litellm.ai/)
- [litellm supported providers](https://docs.litellm.ai/docs/providers)
- [CIP-000B: pub_dialogue package](cip000B.md)
