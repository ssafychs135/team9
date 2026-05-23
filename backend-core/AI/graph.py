"""LangGraph 기반 RAG 챗봇 워크플로우.

기존 ``chatbot_service.get_conversational_rag_chain()`` 의 ``RunnableBranch`` 단일
chain 을 명시 노드 그래프로 분해. 각 단계가 검사·재시도·확장 가능한 단위로 분리됨.

노드 구성:

- ``router``         — '아이폰 질문' vs '일반 대화' 분류
- ``contextualize``  — chat_history + input → 독립 질문 (멀티턴 query 재구성)
- ``extract_models`` — structured output (Pydantic Literal) 로 model_names 추출
- ``retrieve``       — model 별 분리 retrieval + merge (옵션 B)
- ``rerank``         — released_date 내림차순 정렬
- ``compose_answer`` — RAG 답변 생성 (token streaming 대상)
- ``verify``         — 회피 표현 / expected 모델 누락 검사 (log-only)
- ``general_chat``   — 일반 대화 (RAG 우회)

스트리밍은 ``graph.stream(..., stream_mode="messages")`` 로 token chunk + metadata
받아서 ``compose_answer`` 노드의 chunk 만 SSE 로 forward.

verify retry loop 는 현재 미도입 (log-only). 후속 PR 에서 ``compose_answer`` →
``verify`` → 조건부 retry 또는 END 로 확장 예정.
"""

import datetime
import sys
from typing import Any, TypedDict

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

from .chatbot_service import _validate_models_in_query, initialize_chatbot
from .lm_studio import get_chat_llm


# ============================================================================
# State
# ============================================================================

class ChatState(TypedDict, total=False):
    """노드 간 흐르는 상태. ``total=False`` 라 노드는 일부 키만 update 해도 됨."""
    input: str
    chat_history: list[BaseMessage]
    topic: str                  # "iphone" | "general"
    rewritten_query: str        # contextualize 결과
    model_names: list[str]      # extract_models 결과 (검증 후)
    semantic_query: str         # extract_models 의 semantic_query (retrieve 용)
    docs: list[Document]        # retrieve + rerank 결과
    answer: str                 # compose_answer 결과
    issues: list[str]           # verify 결과


# ============================================================================
# Prompts (chatbot_service.py 와 동일 — 같은 시점에 변경 시 양쪽 동기 필요)
# ============================================================================

_CONTEXTUALIZE_SYSTEM = (
    "주어진 대화 기록과 최신 사용자 질문을 바탕으로, 대화 기록 없이도 이해할 수 있는 "
    "독립적인 질문으로 다시 작성하세요. 질문에 답하지 마세요.\n\n"
    "특히 다음 패턴을 정확히 처리하세요:\n"
    "- 사용자가 새 iPhone 모델을 '추가로' 비교 요청하면, 직전 대화의 비교 대상 모델 + "
    "새 모델을 **모두 명시적으로** 포함한 query 로 재작성. "
    "예: 직전이 'iPhone 15 Pro vs Pro Max 비교' + 새 질문 'iPhone 17 Pro Max 와도 비교해줘' "
    "→ 'iPhone 15 Pro, iPhone 15 Pro Max, iPhone 17 Pro Max 스펙 비교'.\n"
    "- 직전 답변의 특정 모델에 대한 후속 질문이면 그 모델명을 query 에 명시.\n"
    "- 일반 인사/오프토픽이면 원본 그대로 둡니다."
)

_ROUTER_TEMPLATE = (
    "당신은 사용자의 질문을 '아이폰 질문'과 '일반 대화' 두 가지로 분류하는 라우터입니다.\n"
    "'아이폰 질문'은 아이폰 모델, 스펙, 색상, 기능, 출시일 등 아이폰과 관련된 구체적인 정보를 묻는 질문입니다.\n"
    "'일반 대화'는 인사, 안부, 농담, 아이폰과 관련 없는 일반적인 지식에 대한 질문입니다.\n\n"
    "오직 '아이폰 질문' 또는 '일반 대화' 둘 중 하나로만 답변해야 합니다.\n\n"
    "<질문>\n{input}\n</질문>\n\n분류:"
)

_COMPARE_FEWSHOT_HUMAN = "iPhone 14 Pro와 iPhone 15 Pro의 카메라 차이 알려줘"
_COMPARE_FEWSHOT_AI = (
    "두 모델의 카메라 사양을 정리해 드릴게요.\n\n"
    "**iPhone 14 Pro**\n"
    "- 메인: 48MP ƒ/1.78, 1세대 센서 시프트 OIS\n"
    "- 망원: 77mm 3배 광학\n\n"
    "**iPhone 15 Pro**\n"
    "- 메인: 48MP ƒ/1.78, 2세대 센서 시프트 OIS\n"
    "- 망원: 77mm 3배 광학\n\n"
    "핵심 차이: iPhone 15 Pro 가 2세대 센서 시프트 OIS 로 손떨림 보정이 한 단계 개선되었습니다."
)


def _build_qa_prompt(today_str: str) -> ChatPromptTemplate:
    qa_system = (
        f"{today_str} 이는 가상의 시나리오나 가정이 아니고 실제 날짜입니다. 이 점을 명심하세요\n\n"
        "당신은 친절하고 전문적인 AI 비서입니다. 사용자의 질문에 대해 다음 지침을 엄격히 준수하여 답변하세요.\n\n"
        "1. 답변은 항상 자연스러운 한국어 문장으로 작성하고, 대화체로 응답하세요.\n"
        "2. 답변에 'CONTEXT'와 같은 기술적인 용어를 직접 언급하지 마세요.\n"
        "3. 정보가 명확하게 구분되도록 적절한 줄바꿈과 문단 구분을 사용하세요.\n"
        "4. 답변은 간결하고 핵심적이어야 합니다.\n\n"
        "5. 참고 같은 추가 정보를 제공 하지 말아야 함.\n\n"
        "6. 답변을 생성 하기 전에 제품 출시일과 주어진 실제 날짜를 확인하세요.\n\n"
        "7. 참고 정보에 여러 iPhone 모델의 스펙이 함께 들어 있다면, '정보가 없다'고 회피하지 말고 "
        "각 모델별로 정리해 비교 형식으로 답하세요. 모델 이름을 명시한 줄바꿈 또는 항목 구분을 사용하고, "
        "마지막에 핵심 차이점을 한두 줄로 요약하세요. "
        "**반드시 참고 정보에 등장한 정확한 모델명을 그대로 사용**하고 "
        "'첫 번째 모델', '두 번째 모델', '두 가지 모델' 같은 추상화/익명화 표현은 금지. "
        "또한 '공식 발표를 확인해 보세요', '정확한 차이는 알 수 없어요' 같은 회피 마무리도 금지.\n\n"
        "8. 참고 정보에 질문에서 언급된 iPhone 모델이 한 줄이라도 들어있으면 그 정보를 사용해 답하세요. "
        "'정보를 제공받지 못했습니다', '아직 출시되지 않았습니다', '구체적인 스펙이 없습니다' 같은 "
        "회피는 참고 정보가 정말로 비어있을 때만 사용하세요. "
        "각 모델의 출시일은 메타데이터의 released_date 로 확인 가능하며, 그 날짜가 "
        "오늘 이전이면 이미 출시된 모델입니다 (미출시로 단정하지 마세요).\n\n"
        "--- 정보 활용 지침 ---\n"
        "a. 먼저 제공된 '참고 정보'를 주의 깊게 확인하세요. 답변이 명확하게 존재한다면, 해당 정보를 사용하여 답변을 생성하세요.\n"
        "b. 만약 '참고 정보'가 질문과 관련은 있지만 직접적인 답변을 포함하고 있지 않다면, 당신의 자체 지식을 활용하여 정보를 보충할 수 있습니다. 이때, 답변이 검색된 정보와 당신의 일반 지식을 모두 기반으로 하고 있음을 언급해야 합니다. 예를 들어, '검색된 정보를 바탕으로 답변을 드리자면...'과 같이 문장을 시작하세요.\n"
        "c. 만약 '참고 정보'가 질문과 전혀 관련이 없다면, '참고 정보'를 무시하고 당신의 자체 지식으로 답변할 수 있습니다.\n\n"
        "--- 참고 정보 ---\n"
        "{context}\n"
        "--- 참고 정보 끝 ---"
    )
    return ChatPromptTemplate.from_messages([
        ("system", qa_system),
        ("human", _COMPARE_FEWSHOT_HUMAN),
        ("ai", _COMPARE_FEWSHOT_AI),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])


def _build_general_prompt(today_str: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            f"{today_str}\n\n당신은 친절하고 상냥한 AI 어시스턴트입니다. 사용자의 질문에 자유롭게 대화하세요.",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])


# ============================================================================
# 노드별로 chain 을 lazy build 하기 위한 module-level singletons
# get_chatbot_graph() 안에서 채워짐
# ============================================================================

_VECTORSTORE: Any = None
_STRUCTURED_CHAIN: Any = None
_ROUTER_CHAIN: Any = None
_CONTEXTUALIZE_CHAIN: Any = None
_GENERAL_CHAIN: Any = None
_GRAPH: Any = None


# ============================================================================
# Helper: 답변 chain 은 매 호출마다 build (today_str 동적). doc_prompt 로 metadata
# model_name 을 명시 prefix → 비교 질문에서 모델 매핑 회피 차단.
# ============================================================================

def _build_answer_chain(today_str: str):
    qa_prompt = _build_qa_prompt(today_str)
    answer_llm = get_chat_llm(temperature=0.0)
    doc_prompt = PromptTemplate.from_template("[{model_name}] {page_content}")
    return create_stuff_documents_chain(answer_llm, qa_prompt, document_prompt=doc_prompt)


# ============================================================================
# Nodes
# ============================================================================

def router_node(state: ChatState) -> dict:
    topic_raw = _ROUTER_CHAIN.invoke({"input": state["input"]})
    sys.stderr.write(f"[graph.router] '{topic_raw.strip()[:40]}'\n")
    return {"topic": "iphone" if "아이폰 질문" in topic_raw else "general"}


def contextualize_node(state: ChatState) -> dict:
    chat_history = state.get("chat_history") or []
    if not chat_history:
        # 첫 turn 은 재구성 불필요
        return {"rewritten_query": state["input"]}
    rewritten = _CONTEXTUALIZE_CHAIN.invoke({
        "input": state["input"],
        "chat_history": chat_history,
    })
    sys.stderr.write(f"[graph.contextualize] {state['input']!r} → {rewritten!r}\n")
    return {"rewritten_query": rewritten}


def extract_models_node(state: ChatState) -> dict:
    query = state.get("rewritten_query") or state["input"]
    try:
        parsed = _STRUCTURED_CHAIN.invoke({"query": query})
    except Exception as e:
        sys.stderr.write(f"[graph.extract_models] structured 추출 실패: {e} — fallback to raw query\n")
        return {"model_names": [], "semantic_query": query}

    validated = _validate_models_in_query(parsed.model_names, query)
    sys.stderr.write(
        f"[graph.extract_models] models={validated!r}, sq={parsed.semantic_query!r}\n"
    )
    return {"model_names": validated, "semantic_query": parsed.semantic_query}


def retrieve_node(state: ChatState) -> dict:
    sq = state.get("semantic_query") or state.get("rewritten_query") or state["input"]
    models = state.get("model_names") or []

    if not models:
        docs = _VECTORSTORE.similarity_search(sq, k=5)
    elif len(models) == 1:
        docs = _VECTORSTORE.similarity_search(sq, k=5, filter={"model_name": models[0]})
    else:
        # 옵션 B: 모델별 분리 retrieval + merge. 모델당 최소 2개 청크 보장.
        k_per = max(2, 5 // len(models))
        docs = []
        for m in models:
            docs.extend(_VECTORSTORE.similarity_search(sq, k=k_per, filter={"model_name": m}))
        sys.stderr.write(
            f"[graph.retrieve] multi-model: {len(models)}개 × {k_per} = {len(docs)} docs\n"
        )
    return {"docs": docs}


def rerank_node(state: ChatState) -> dict:
    docs = state.get("docs") or []
    sorted_docs = sorted(
        docs,
        key=lambda d: d.metadata.get("released_date", "1900-01-01"),
        reverse=True,
    )
    sys.stderr.write(f"--- [graph.rerank] {len(sorted_docs)} docs (released_date desc) ---\n")
    for i, doc in enumerate(sorted_docs):
        r = doc.metadata.get("released_date", "Unknown")
        m = doc.metadata.get("model_name", "Unknown")
        sys.stderr.write(f"  Doc {i+1} [{r}] {m}: {doc.page_content[:50]}...\n")
    sys.stderr.write("---\n")
    return {"docs": sorted_docs}


def compose_answer_node(state: ChatState) -> dict:
    today_str = datetime.date.today().strftime(
        "오늘 날짜는 %Y년 %m월 %d일입니다. 이를 기준으로 답변하세요"
    )
    answer_chain = _build_answer_chain(today_str)
    answer = answer_chain.invoke({
        "input": state["input"],
        "chat_history": state.get("chat_history") or [],
        "context": state.get("docs") or [],
    })
    return {"answer": answer}


# verify 의 회피 표현 detection 패턴. 정확히 일치할 필요는 없고 substring 검색.
_AVOIDANCE_PATTERNS = [
    "정보를 제공받지 못",
    "정확한 차이는 알 수 없",
    "공식 발표를 확인",
    "구체적인 스펙이 없",
    "아직 출시되지 않",
    "정보가 포함되어 있지 않",
]


def verify_node(state: ChatState) -> dict:
    """답변 검증 — prompt 가 아닌 코드에서 회피·누락 catch.

    현재는 log-only (issues 만 기록, retry 안 함). 후속 PR 에서 issues 있을 때
    compose_answer 로 재시도하는 conditional edge 도입 예정.
    """
    issues: list[str] = []
    answer = state.get("answer") or ""
    expected = state.get("model_names") or []

    missing = [m for m in expected if m not in answer]
    if missing:
        issues.append(f"missing_models: {missing}")

    if any(p in answer for p in _AVOIDANCE_PATTERNS):
        issues.append("avoidance_phrase")

    if issues:
        sys.stderr.write(f"[graph.verify] ⚠️ issues={issues}\n")
    else:
        sys.stderr.write("[graph.verify] ✓ ok\n")
    return {"issues": issues}


def general_chat_node(state: ChatState) -> dict:
    answer = _GENERAL_CHAIN.invoke({
        "input": state["input"],
        "chat_history": state.get("chat_history") or [],
    })
    return {"answer": answer}


# ============================================================================
# Conditional edges
# ============================================================================

def _route_after_router(state: ChatState) -> str:
    return "contextualize" if state.get("topic") == "iphone" else "general_chat"


# ============================================================================
# Graph 빌드 — lazy singleton
# ============================================================================

def get_chatbot_graph():
    """컴파일된 graph 를 lazy 하게 생성·반환. 매 호출 시 같은 인스턴스."""
    global _GRAPH, _VECTORSTORE, _STRUCTURED_CHAIN
    global _ROUTER_CHAIN, _CONTEXTUALIZE_CHAIN, _GENERAL_CHAIN

    if _GRAPH is not None:
        return _GRAPH

    # chatbot_service 의 retriever/llm 초기화 (idempotent)
    initialize_chatbot()
    from . import chatbot_service as cs  # 순환 import 회피용 지연 import

    # retriever 가 IPhoneQueryRetriever 면 vectorstore + structured_chain 추출.
    # 폴백(일반 similarity retriever) 경로면 vectorstore 만 추출 후 structured 무력화.
    cs_retriever = cs.retriever
    if hasattr(cs_retriever, "structured_chain"):
        _VECTORSTORE = cs_retriever.vectorstore
        _STRUCTURED_CHAIN = cs_retriever.structured_chain
    else:
        # fallback: extract_models 가 항상 빈 리스트 반환하도록
        _VECTORSTORE = cs_retriever.vectorstore  # langchain_chroma.Chroma
        _STRUCTURED_CHAIN = None
        sys.stderr.write("⚠️ graph: structured_chain 없음 — extract_models 가 빈 결과 반환\n")

    llm = cs.llm

    # Router / Contextualize / General chain 은 graph build 시점에 한 번만 build
    router_prompt = ChatPromptTemplate.from_template(_ROUTER_TEMPLATE)
    _ROUTER_CHAIN = router_prompt | llm | StrOutputParser()

    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", _CONTEXTUALIZE_SYSTEM),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    contextualize_llm = get_chat_llm(temperature=0.0)
    _CONTEXTUALIZE_CHAIN = contextualize_prompt | contextualize_llm | StrOutputParser()

    # general_chain 의 today_str 은 build 시점 고정 (서버 부팅 시 today, 챗봇 init 후 변경 없음)
    today_str = datetime.date.today().strftime(
        "오늘 날짜는 %Y년 %m월 %d일입니다. 이를 기준으로 답변하세요"
    )
    _GENERAL_CHAIN = _build_general_prompt(today_str) | llm | StrOutputParser()

    # === Graph ===
    g = StateGraph(ChatState)
    g.add_node("router", router_node)
    g.add_node("contextualize", contextualize_node)
    g.add_node("extract_models", extract_models_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("rerank", rerank_node)
    g.add_node("compose_answer", compose_answer_node)
    g.add_node("verify", verify_node)
    g.add_node("general_chat", general_chat_node)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        _route_after_router,
        {"contextualize": "contextualize", "general_chat": "general_chat"},
    )
    g.add_edge("contextualize", "extract_models")
    g.add_edge("extract_models", "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "compose_answer")
    g.add_edge("compose_answer", "verify")
    g.add_edge("verify", END)
    g.add_edge("general_chat", END)

    _GRAPH = g.compile()
    sys.stderr.write("✓ LangGraph 챗봇 그래프 컴파일 완료.\n")
    return _GRAPH
