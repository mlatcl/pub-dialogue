"""
LLM client wrapper providing a stable, mockable interface over litellm.

All LLM calls in pub_dialogue.utils go through :class:`LLMClient`.
litellm is imported lazily inside each method so the package loads cleanly
in analysis notebooks that never make API calls.

Usage::

    from pub_dialogue.client import LLMClient

    client = LLMClient(model="gpt-4o-mini")
    text = client.complete([{"role": "user", "content": "Hello"}])
    vecs = client.embed(["phrase one", "phrase two"])

Provider selection is automatic based on the model name prefix (litellm
convention):

- ``gpt-*`` / ``o1-*`` → OpenAI  (``OPENAI_API_KEY``)
- ``claude-*``          → Anthropic (``ANTHROPIC_API_KEY``)
- ``gemini/*``          → Google Gemini (``GOOGLE_API_KEY``)

See https://docs.litellm.ai/docs/providers for the full list.
"""

from __future__ import annotations


class LLMClient:
    """Thin wrapper around litellm providing a stable, mockable interface.

    Parameters
    ----------
    model:
        Any litellm model string, e.g. ``"gpt-4o-mini"``,
        ``"claude-3-5-haiku-latest"``, ``"gemini/gemini-2.0-flash"``.
    embedding_model:
        Model used for :meth:`embed`.  Defaults to OpenAI
        ``"text-embedding-3-large"``.  Changing this mid-project invalidates
        all saved ``*.npy`` embedding artifacts — prefer keeping the default
        for the lifetime of a corpus.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-large",
    ) -> None:
        self.model = model
        self.embedding_model = embedding_model

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Return the text of the first completion choice.

        Parameters
        ----------
        messages:
            OpenAI-style message list,
            e.g. ``[{"role": "user", "content": "..."}]``.
        **kwargs:
            Passed through to ``litellm.completion`` (e.g. ``temperature``,
            ``max_tokens``).

        Returns
        -------
        str
            The assistant's reply text.
        """
        import litellm  # lazy: not needed in pure-analysis notebooks

        resp = litellm.completion(model=self.model, messages=messages, **kwargs)
        return resp.choices[0].message.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors, one per input text.

        Parameters
        ----------
        texts:
            Strings to embed.

        Returns
        -------
        list[list[float]]
            One float vector per input string.
        """
        import litellm  # lazy: not needed in pure-analysis notebooks

        resp = litellm.embedding(model=self.embedding_model, input=texts)
        # litellm returns data items as plain dicts, not attribute-access objects
        return [d["embedding"] if isinstance(d, dict) else d.embedding
                for d in resp.data]
