# AI/chatbot_service.py

import os
import sys
import chromadb
from dotenv import load_dotenv
import datetime
import re
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field

# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from AI.lm_studio import get_chat_llm, EmbeddingGemmaEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema.runnable import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
    Runnable,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun

# .env 파일에서 환경 변수 로드
load_dotenv()

# 전역 변수로 llm과 retriever 저장 (서버 시작 시 한 번만 초기화)
llm = None
retriever = None


# === Structured retriever 구현 ===
# SelfQueryRetriever 를 대체. with_structured_output 으로 model_name 추출을 grammar-constrained
# decoding 으로 강제하여 LLM 비결정성과 한국어 음역 매칭 약점을 한 번에 해결.

_STRUCTURED_SYSTEM_PROMPT = (
    "당신은 iPhone 질문에서 검색 메타데이터를 추출하는 분석기입니다.\n\n"
    "엄격한 규칙:\n"
    "1. 질문에 직접 등장한 모델만 model_names 에 포함. 등장 없으면 빈 리스트 [].\n"
    "2. 비교/대조 질문(예: 'A와 B 비교', 'A vs B', 'A랑 B 차이')은 언급된 모든 모델을 포함.\n"
    "3. 모델 번호(예: '17')가 질문에 없는데 다른 번호로 추측 금지.\n"
    "4. 일반 추천('카메라 좋은 폰'), 오프토픽('맥북'), 인사말은 model_names=[].\n"
    "5. semantic_query 는 ChromaDB 검색용 짧은 키워드. 답변/완전한 문장 금지.\n"
    "   예: '카메라 스펙', '배터리 용량'. NOT '카메라가 뛰어난...'.\n"
    "6. 한국어 음역은 정확히 매핑: '프로'→Pro, '맥스'→Max, '에어'→Air, '미니'→mini."
)


def _validate_models_in_query(model_names: List[str], query: str) -> List[str]:
    """추출된 모델들 중 query 의 숫자 토큰과 매칭되는 것만 반환.

    Gemma 4 E4B 가 query 의 숫자(예: 17)와 다른 모델 번호(예: 16)로
    환각 매핑하는 케이스를 차단. 중복 제거 + 입력 순서 보존.
    """
    if not model_names:
        return []
    nums_in_query = re.findall(r'\d+', query)
    validated: List[str] = []
    for m in model_names:
        nums_in_model = re.findall(r'\d+', m)
        # 모델에 숫자가 없으면(예: 'iPhone Air') 통과; 있으면 query 와 교집합 필요
        if not nums_in_model or any(n in nums_in_query for n in nums_in_model):
            validated.append(m)
    return list(dict.fromkeys(validated))


class IPhoneQueryRetriever(BaseRetriever):
    """structured output 으로 model_name 을 추출 후 ChromaDB 메타데이터 필터 + similarity.

    SelfQueryRetriever 대비 장점:
    - Pydantic Literal enum 으로 model_name 출력 공간을 grammar-constrained decoding 강제
    - 단일 LLM 호출 (SelfQuery 는 다단계)
    - 후처리 검증으로 false positive 차단
    """
    vectorstore: Any
    structured_chain: Any
    k: int = 5

    model_config = {"arbitrary_types_allowed": True}

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        try:
            parsed = self.structured_chain.invoke({"query": query})
        except Exception as e:
            sys.stderr.write(f"structured 추출 실패, 일반 similarity 폴백: {e}\n")
            return self.vectorstore.similarity_search(query, k=self.k)

        validated_models = _validate_models_in_query(parsed.model_names, query)
        sys.stderr.write(
            f"[IPhoneQuery] models={validated_models!r}, sq={parsed.semantic_query!r}\n"
        )

        if not validated_models:
            return self.vectorstore.similarity_search(parsed.semantic_query, k=self.k)

        if len(validated_models) == 1:
            return self.vectorstore.similarity_search(
                parsed.semantic_query,
                k=self.k,
                filter={"model_name": validated_models[0]},
            )

        # 옵션 B: 모델별 분리 retrieval + merge. 비교 질문에서 모든 모델이
        # 균등하게 컨텍스트에 들어가도록 모델당 최소 2개 청크 보장.
        k_per_model = max(2, self.k // len(validated_models))
        merged: List[Document] = []
        for m in validated_models:
            docs = self.vectorstore.similarity_search(
                parsed.semantic_query,
                k=k_per_model,
                filter={"model_name": m},
            )
            merged.extend(docs)
        sys.stderr.write(
            f"[IPhoneQuery] multi-model retrieve: {len(validated_models)}개 × {k_per_model} = {len(merged)} docs\n"
        )
        return merged


def initialize_chatbot():
    """
    챗봇에 필요한 LLM과 Retriever를 초기화합니다.
    이 함수는 서버 시작 시 한 번만 호출되어야 합니다.
    """
    global llm, retriever

    if llm is not None and retriever is not None:
        return

    # LM Studio 로 서빙된 챗 모델(Gemma 4 E4B 등)
    llm = get_chat_llm()

    # 크롤링된 데이터를 위한 ChromaDB 경로 및 컬렉션 이름 설정
    chroma_path = os.getenv("CHROMA_DB_PATH_CRAWLED", "./chroma_db_crawled")
    # embed_iphone_data.py 에서 생성한 컬렉션 이름으로 변경
    collection_name = "iphone_specs_collection"

    # 임베딩 모델 초기화 — LM Studio 의 EmbeddingGemma (task prefix 비대칭 자동 처리)
    embeddings = EmbeddingGemmaEmbeddings()

    # ChromaDB 클라이언트 및 벡터 스토어 초기화
    client = chromadb.PersistentClient(path=chroma_path)
    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=chroma_path,
    )

    # --- Structured Retriever 설정 (Pydantic Literal enum + 후처리 검증) ---
    # 컬렉션에서 valid model_name 을 동적으로 추출하여 LLM 출력 공간을 enum 으로 제약
    try:
        coll = client.get_collection(collection_name)
        all_meta = coll.get(limit=2000, include=["metadatas"])
        valid_models = tuple(sorted({m['model_name'] for m in all_meta['metadatas']}))
        if not valid_models:
            raise RuntimeError("컬렉션이 비어있어 valid_models 를 추출할 수 없습니다.")
        sys.stderr.write(f"valid_models {len(valid_models)}개 로드.\n")

        ModelLiteral = Literal[*valid_models]

        class IPhoneQuery(BaseModel):
            model_names: List[ModelLiteral] = Field(
                default_factory=list,
                description=(
                    "질문에 직접 언급된 정확한 iPhone 모델들. 비교 질문이면 "
                    "언급된 모든 모델을 포함. 명시 없거나 일반 추천/오프토픽이면 []."
                ),
            )
            semantic_query: str = Field(
                description="짧은 한국어 검색 키워드 (3-15자). 답변·추천 문장 아님."
            )

        structured_prompt = ChatPromptTemplate.from_messages([
            ("system", _STRUCTURED_SYSTEM_PROMPT),
            ("human", "{query}"),
        ])
        # 답변 생성용 llm 과 격리된 별도 인스턴스 — with_structured_output 의 잔향
        # (응답 JSON wrapping) 이 답변 chain 으로 전파되는 것을 차단.
        structured_llm = get_chat_llm(temperature=0.0)
        structured_chain = structured_prompt | structured_llm.with_structured_output(IPhoneQuery)

        retriever = IPhoneQueryRetriever(
            vectorstore=vectorstore,
            structured_chain=structured_chain,
            k=5,
        )
        sys.stderr.write("IPhoneQueryRetriever (structured output + 후처리 검증) 초기화 완료.\n")
    except Exception as e:
        sys.stderr.write(f"IPhoneQueryRetriever 초기화 실패 (일반 similarity 폴백): {e}\n")
        retriever = vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": 5}
        )

    sys.stderr.write("LLM 및 Retriever 초기화 완료.\n")


def get_conversational_rag_chain():
    """
    사용자 질문의 의도를 파악하여 RAG 또는 일반 대화 체인을 선택적으로 실행하는
    분기(branch) 로직을 포함한 대화형 체인을 생성하여 반환합니다.
    """
    if llm is None or retriever is None:
        initialize_chatbot()
    # 오늘 날짜 정보를 프롬프트에 추가
    today_str = datetime.date.today().strftime("오늘 날짜는 %Y년 %m월 %d일입니다. 이를 기준으로 답변하세요")

    # --- 1. RAG 전문가 체인 정의 (기존 로직) ---

    # 1-1. 질문 재구성 프롬프트 및 리트리버
    # 멀티턴의 가장 비결정적 단계 — 0.2 면 turn 3+ 에서 모델 누락 빈발.
    # temperature=0.0 으로 분리 + "추가 비교 요청" 패턴을 명시 가이드해 결정성 강화.
    contextualize_q_system_prompt = (
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
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    contextualize_llm = get_chat_llm(temperature=0.0)
    history_aware_retriever = create_history_aware_retriever(
        contextualize_llm, retriever, contextualize_q_prompt
    )

    # 1-2. 답변 생성 프롬프트 (RAG용 - 유연한 버전)
    qa_system_prompt = (
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
    # 비교 답변 few-shot — Gemma 4 E4B 의 모델명 익명화/회피 패턴 차단.
    # human/ai 페어로 dialogue pattern 을 학습시켜 single-shot system 지시보다 강하게 작동.
    _COMPARE_FEWSHOT_HUMAN = (
        "iPhone 14 Pro와 iPhone 15 Pro의 카메라 차이 알려줘"
    )
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

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            # Few-shot: 정확한 모델명 명시 + 핵심 차이 요약 + 회피 마무리 없음
            ("human", _COMPARE_FEWSHOT_HUMAN),
            ("ai", _COMPARE_FEWSHOT_AI),
            # 실제 대화 흐름 (멀티턴) — few-shot 다음에 위치시켜 LLM 이
            # 예시(14/15 Pro) 를 "직전 turn" 으로 오인하지 않게 함. 가장 최근 messages
            # 가 진짜 history 의 turn 들이 되도록 순서 고정.
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )

    # 1-3. RAG 답변 생성 체인 — 비교 응답의 결정성/사실성 강화를 위해 temperature=0.0 인스턴스 분리
    # document_prompt 로 metadata 의 model_name 을 명시 prefix → 비교 질문에서 모델 매핑 회피 차단
    answer_llm = get_chat_llm(temperature=0.0)
    doc_prompt = PromptTemplate.from_template("[{model_name}] {page_content}")
    question_answer_chain = create_stuff_documents_chain(
        answer_llm, qa_prompt, document_prompt=doc_prompt
    )

    # 1-4. 검색된 문서 로깅 및 RAG 체인 완성
    def retrieve_documents_and_log(x):
        retrieved_documents = history_aware_retriever.invoke(x)
        
        # 1. 날짜 정렬 로직 (메타데이터 활용)
        def get_date_value(doc):
            # 메타데이터에서 'released_date' 가져오기 (없으면 아주 옛날 날짜로 취급)
            date_str = doc.metadata.get('released_date', '1900-01-01')
            return date_str

        # 2. 최신순(내림차순) 정렬
        # 날짜 문자열(YYYY-MM-DD)은 사전순 정렬 시 최신 날짜가 뒤로 가므로,
        # reverse=True를 주면 최신 날짜가 앞으로 옵니다.
        retrieved_documents.sort(key=get_date_value, reverse=True)

        # 로그 출력
        sys.stderr.write(f"--- Retrieved & Sorted Documents ({len(retrieved_documents)} docs) ---\n")
        for i, doc in enumerate(retrieved_documents):
            # 메타데이터의 날짜 정보 표시
            r_date = doc.metadata.get('released_date', 'Unknown Date')
            model_name = doc.metadata.get('model_name', 'Unknown Model')
            sys.stderr.write(f"Doc {i+1} [{r_date}] {model_name}: {doc.page_content[:50]}...\n")
        sys.stderr.write("------------------------------------\n")
        
        return retrieved_documents

    rag_chain = RunnablePassthrough.assign(context=retrieve_documents_and_log).assign(
        answer=question_answer_chain
    )

    # --- 2. 라우터(교통정리) 체인 정의 ---

    router_prompt_text = """당신은 사용자의 질문을 '아이폰 질문'과 '일반 대화' 두 가지로 분류하는 라우터입니다.
'아이폰 질문'은 아이폰 모델, 스펙, 색상, 기능, 출시일 등 아이폰과 관련된 구체적인 정보를 묻는 질문입니다.
'일반 대화'는 인사, 안부, 농담, 아이폰과 관련 없는 일반적인 지식에 대한 질문입니다.

오직 '아이폰 질문' 또는 '일반 대화' 둘 중 하나로만 답변해야 합니다.

<질문>
{input}
</질문>

분류:"""
    router_prompt = ChatPromptTemplate.from_template(router_prompt_text)
    # The router chain classifies the input.
    router = router_prompt | llm | StrOutputParser()

    # --- 3. 일반 상담원 체인 정의 ---

    general_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"{today_str}\n\n당신은 친절하고 상냥한 AI 어시스턴트입니다. 사용자의 질문에 자유롭게 대화하세요.",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ]
    )

    # 일반 대화 체인의 출력을 RAG 체인과 동일한 딕셔너리 형태로 맞추기 위한 래퍼 함수
    def format_general_output(answer_str):
        return {"answer": answer_str, "context": []}

    general_chain = (
        general_prompt | llm | StrOutputParser() | RunnableLambda(format_general_output)
    )

    # --- 4. 최종 체인: 라우터와 각 담당자 연결 ---

    # RunnableBranch를 사용하여 라우터의 결과에 따라 실행할 체인을 결정
    branch = RunnableBranch(
        (
            lambda x: "아이폰 질문" in x["topic"],
            rag_chain,
        ),  # 'topic'에 '아이폰 질문'이 포함되어 있으면 rag_chain 실행
        general_chain,  # 그렇지 않으면 general_chain 실행
    )

    # 전체 워크플로우를 정의하는 최종 체인
    # 1. 사용자의 입력을 받아 라우터를 실행하여 'topic'을 결정
    # 2. 'topic'과 원래 입력을 함께 branch로 전달
    full_chain = (
        RunnablePassthrough.assign(topic=lambda x: router.invoke({"input": x["input"]}))
        | branch
    )

    return full_chain

