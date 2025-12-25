# AI/chatbot_service.py

import os
import chromadb
from dotenv import load_dotenv
import datetime
import re


# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain_upstage import UpstageEmbeddings, ChatUpstage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema.runnable import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser

# .env 파일에서 환경 변수 로드
load_dotenv()

# 전역 변수로 llm과 retriever 저장 (서버 시작 시 한 번만 초기화)
llm = None
retriever = None


def initialize_chatbot():
    """
    챗봇에 필요한 LLM과 Retriever를 초기화합니다.
    이 함수는 서버 시작 시 한 번만 호출되어야 합니다.
    """
    global llm, retriever

    if llm is not None and retriever is not None:
        return

    # Upstage API 키 환경 변수 확인
    upstage_api_key = os.getenv("UPSTAGE_API_KEY")
    if not upstage_api_key:
        raise ValueError(
            "UPSTAGE_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요."
        )

    # LLM 모델 정의
    llm = ChatUpstage(model="solar-pro2")

    # ChromaDB 경로 환경 변수에서 가져오기
    # 기존 코드 주석 처리
    # chroma_path = os.getenv('CHROMA_DB_PATH', './chroma_db_crawled')
    # collection_name = 'iphone_collection'

    # 크롤링된 데이터를 위한 ChromaDB 경로 및 컬렉션 이름 설정
    chroma_path = os.getenv("CHROMA_DB_PATH_CRAWLED", "./chroma_db_crawled")
    # embed_iphone_data.py 에서 생성한 컬렉션 이름으로 변경
    collection_name = "iphone_specs_collection"

    # 임베딩 모델 초기화
    embeddings = UpstageEmbeddings(model="embedding-query")

    # ChromaDB 클라이언트 및 벡터 스토어 초기화
    client = chromadb.PersistentClient(path=chroma_path)
    vectorstore = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=chroma_path,
    )

    # --- Self-Querying Retriever 설정 (메타데이터 필터링) ---
    from langchain.chains.query_constructor.base import AttributeInfo
    from langchain.retrievers.self_query.base import SelfQueryRetriever

    # 1. 메타데이터 필드 정보 정의 (LLM이 이해할 수 있도록 설명)
    metadata_field_info = [
        AttributeInfo(
            name="model_name",
            description="The name of the iPhone model, e.g., 'iPhone 13', 'iPhone 14 Pro', 'iPhone SE (3rd Gen)'.",
            type="string",
        ),
        AttributeInfo(
            name="released_date",
            description="The release date of the iPhone model in YYYY-MM-DD format.",
            type="string",
        ),
        AttributeInfo(
            name="source",
            description="The source type of the data, usually 'crawled_spec'.",
            type="string",
        ),
    ]

    # 2. 문서 콘텐츠 설명
    document_content_description = "Technical specifications and details of various iPhone models"

    # 3. SelfQueryRetriever 생성
    # LLM이 질문을 분석하여 자동으로 메타데이터 필터(예: model_name="iPhone 13")를 생성합니다.
    try:
        retriever = SelfQueryRetriever.from_llm(
            llm,
            vectorstore,
            document_content_description,
            metadata_field_info,
            verbose=True,  # 내부적으로 어떤 필터가 생성되었는지 콘솔에 출력
            search_kwargs={"k": 5} # 검색 결과 개수
        )
        print("SelfQueryRetriever (메타데이터 필터 포함) 초기화 완료.")
    except Exception as e:
        print(f"SelfQueryRetriever 초기화 실패 (기본 검색기 사용): {e}")
        # 실패 시 기본 리트리버로 폴백
        retriever = vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": 5}
        )
    
    print("LLM 및 Retriever 초기화 완료.")


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
    contextualize_q_system_prompt = (
        "주어진 대화 기록과 최신 사용자 질문을 바탕으로, 대화 기록 없이도 이해할 수 있는 독립적인 질문으로 다시 작성하세요. "
        "질문에 답하지 마세요. 필요한 경우에만 질문을 재구성하세요."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
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
        "--- 정보 활용 지침 ---\n"
        "a. 먼저 제공된 '참고 정보'를 주의 깊게 확인하세요. 답변이 명확하게 존재한다면, 해당 정보를 사용하여 답변을 생성하세요.\n"
        "b. 만약 '참고 정보'가 질문과 관련은 있지만 직접적인 답변을 포함하고 있지 않다면, 당신의 자체 지식을 활용하여 정보를 보충할 수 있습니다. 이때, 답변이 검색된 정보와 당신의 일반 지식을 모두 기반으로 하고 있음을 언급해야 합니다. 예를 들어, '검색된 정보를 바탕으로 답변을 드리자면...'과 같이 문장을 시작하세요.\n"
        "c. 만약 '참고 정보'가 질문과 전혀 관련이 없다면, '참고 정보'를 무시하고 당신의 자체 지식으로 답변할 수 있습니다.\n\n"
        "--- 참고 정보 ---\n"
        "{context}\n"
        "--- 참고 정보 끝 ---"
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            ("human", "{input}"),
        ]
    )

    # 1-3. RAG 답변 생성 체인
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

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
        print(f"--- Retrieved & Sorted Documents ({len(retrieved_documents)} docs) ---")
        for i, doc in enumerate(retrieved_documents):
            # 메타데이터의 날짜 정보 표시
            r_date = doc.metadata.get('released_date', 'Unknown Date')
            model_name = doc.metadata.get('model_name', 'Unknown Model')
            print(f"Doc {i+1} [{r_date}] {model_name}: {doc.page_content[:50]}...")
        print("------------------------------------")
        
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

