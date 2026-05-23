"""LM Studio 로 서빙되는 LLM/임베딩 공용 어댑터.

LM Studio 는 OpenAI 호환 ``/v1`` 엔드포인트를 노출하므로 LangChain 의
``ChatOpenAI`` / ``OpenAIEmbeddings`` 를 그대로 쓸 수 있다. 다만 EmbeddingGemma
는 task prefix 비대칭(query/document)을 학습 시점에 적용했으므로 검색 품질을
위해 ``embed_query`` 와 ``embed_documents`` 에서 다른 prefix 를 붙여야 한다.

이 모듈은 이전 Upstage Solar 의 ``embedding-query`` / ``embedding-passage``
비대칭을 EmbeddingGemma 의 task prefix 로 매핑한 어댑터를 제공한다.
"""

import os
from typing import List, Optional

from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


EMB_QUERY_PREFIX = "task: search result | query: "
EMB_PASSAGE_PREFIX = "title: none | text: "


def _lm_studio_kwargs() -> dict:
    base_url = os.getenv("LM_STUDIO_BASE_URL", "https://lmstudio.chs135.com/v1")
    api_key = os.getenv("LM_STUDIO_API_KEY")
    if not api_key:
        raise ValueError(
            "LM_STUDIO_API_KEY 환경 변수가 설정되지 않았습니다. "
            ".env 에 게이트웨이 Bearer 토큰을 지정해주세요."
        )
    return {"base_url": base_url, "api_key": api_key}


def get_chat_llm(temperature: float = 0.2, **kwargs) -> ChatOpenAI:
    """LM Studio 에 서빙된 챗 모델(Gemma 4 E4B 등)을 ChatOpenAI 로 래핑."""
    model = os.getenv("LM_STUDIO_CHAT_MODEL")
    if not model:
        raise ValueError(
            "LM_STUDIO_CHAT_MODEL 환경 변수가 설정되지 않았습니다. "
            ".env 에 LM Studio 에서 로드한 모델의 식별자를 지정해주세요."
        )
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        **_lm_studio_kwargs(),
        **kwargs,
    )


class EmbeddingGemmaEmbeddings(Embeddings):
    """EmbeddingGemma 의 task prefix 비대칭을 감싼 LangChain Embeddings 어댑터.

    - 문서 인덱싱:  ``title: none | text: {doc}``
    - 질의 검색:    ``task: search result | query: {query}``

    ``dimensions`` 가 지정되면 OpenAI 호환 dimensions 파라미터로 MRL 차원
    축소를 요청한다 (None 이면 풀 차원 768).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> None:
        model_name = model or os.getenv("LM_STUDIO_EMBED_MODEL")
        if not model_name:
            raise ValueError(
                "LM_STUDIO_EMBED_MODEL 환경 변수가 설정되지 않았습니다. "
                ".env 에 LM Studio 에서 로드한 임베딩 모델의 식별자를 지정해주세요."
            )
        self._client = OpenAIEmbeddings(
            model=model_name,
            dimensions=dimensions,
            check_embedding_ctx_length=False,
            **_lm_studio_kwargs(),
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        prefixed = [f"{EMB_PASSAGE_PREFIX}{t}" for t in texts]
        return self._client.embed_documents(prefixed)

    def embed_query(self, text: str) -> List[float]:
        return self._client.embed_query(f"{EMB_QUERY_PREFIX}{text}")
