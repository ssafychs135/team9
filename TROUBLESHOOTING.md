# 트러블슈팅 기록

이 프로젝트에서 만난 침묵하는 버그들과 디버깅 narrative. 결론(invariant) 은 `.serena/memories/` 에 박혀 있고, 여기엔 **어떻게 거기까지 왔는가** 와 **다음에 빠르게 잡는 방법**을 남깁니다.

---

## 2026-05-23 — crawled_data 의 NBSP 오염으로 인한 retrieval 메타데이터 매칭 침묵 실패

### 증상
- 챗봇이 "아이폰 17 Pro Max 카메라 스펙" 질문에 iPhone 15/16 시리즈 정보만 응답.
- ChromaDB 컬렉션에는 iPhone 17 Pro Max 데이터가 분명히 있음 (51개 파일 모두 임베딩 성공, 678 청크 저장 확인).
- `SelfQueryRetriever` 의 메타데이터 필터 결과가 0건 → fallback similarity 로 빠져서 다른 모델 잡힘.
- 사람 눈으로 파일명·메타데이터를 봐서는 어디가 깨졌는지 안 보임.

### 진단 과정
1. 직접 검색 — `coll.get(where={"model_name": "iPhone 17 Pro Max"}, limit=100)` → **0건**. 분명히 데이터는 있는데 키 매칭이 안 됨.
2. 전체 메타데이터 분포 가시화 — `Counter(m['model_name'] for m in all_meta['metadatas'])` 의 `repr()` 출력을 보고 발견:
   ```
   19건  'iPhone 15 Plus'                  ← 정상 공백
   19건  'iPhone\xa016\xa0Pro\xa0Max'      ← NBSP!
   10건  'iPhone 17\xa0Pro\xa0Max'         ← 부분 오염
   ```
3. `print()` 또는 `ls` 출력에선 일반 공백과 픽셀 단위로 동일해서 절대 안 보임. `repr()` 가 처음으로 `\xa0` 을 가시화.
4. 원본 파일 확인 — `crawled_data/` 의 51개 JSON 중 6개 파일명, 15개 파일 본문에 NBSP 박힘 (`True\xa0Tone` 같은 케이스).

### 원인
Apple 공식 페이지의 HTML 마크업이 제품명·기능명에 `&nbsp;` (U+00A0) 를 의도적으로 사용합니다 — 카탈로그 디자인에서 "iPhone 17 Pro Max" 같은 모델명이 줄바꿈으로 분리되지 않게 하기 위함. Selenium 크롤러의 `get_text(strip=True)` 가 NBSP 를 그대로 가져와 파일명 + JSON 본문에 침투. `embed_iphone_data` 가 파일명을 `os.path.splitext()` 로 그대로 model_name 메타데이터로 사용 → 컬렉션 키 = NBSP 박힌 문자열.

흥미로운 패턴: 모든 파일이 오염된 게 아니라 일부만 (iPhone 16 시리즈는 전체 NBSP, iPhone 17 시리즈는 부분 NBSP, iPhone 15 이하는 깨끗). Apple 페이지의 시기별 마크업 차이.

### 해결
- `AI/management/commands/webcrawler.py` — `import unicodedata` + 재귀 `_normalize()` 헬퍼 추가. model_name 추출 직후 + JSON 저장 직전 `page_data` 전체 정규화.
- `AI/management/commands/embed_iphone_data.py` — `_nfkc()` 헬퍼 추가. 파일명에서 추출한 `model_name` + 청크 분할 직전 `text_content` + 메타데이터의 `filename` 모두 `unicodedata.normalize('NFKC', text)` 적용.
- 컬렉션 재인덱싱: `python manage.py reset_chroma_collections --purge-all` → `python manage.py embed_iphone_data`.

### 교훈
- **외부 텍스트(HTML 스크래핑, PDF, 복붙) 가 들어오는 경계에서 항상 `unicodedata.normalize('NFKC', text)`**. NBSP 외에 전각/반각, 합자, 호환 문자까지 한 번에 정상화.
- 메타데이터 매칭이 침묵 실패할 때 **`repr()` 또는 `Counter` 로 byte 수준 키 분포를 가시화**. `print()` / `ls` / Finder 로는 NBSP·zero-width-space 같은 비표시 공백을 절대 못 잡음.
- "사람 눈에는 같아 보이는데 코드가 다르다고 한다" → 1순위 의심은 유니코드 비표시 문자.

### 관련
- `mem:conventions` 의 "외부 텍스트 정규화 (NBSP / 호환 문자)" 섹션
- `AI/management/commands/webcrawler.py` 의 `_normalize()`
- `AI/management/commands/embed_iphone_data.py` 의 `_nfkc()`

---

## 2026-05-23 — SelfQueryRetriever 의 비결정성 (작은 LLM 으로 옮긴 후 노출됨)

### 증상
- 같은 query "아이폰 17 Pro Max 카메라 스펙" 을 chain 으로 호출할 때 **호출마다 retrieve 결과가 다름**:
  - 1차: iPhone 17 Pro Max top-1 + iPhone 16/15 4건
  - 2차: iPhone 15 Pro / 15 Pro Max / 16 / 16 Plus / 16 Pro (iPhone 17 0건)
  - 3차: iPhone 17 Pro Max 5건 (모두)
- 동일 chain, 동일 입력, 동일 retrieve config 인데 매번 다름.
- `verbose=True` 옵션이 켜져 있는데도 SelfQueryRetriever 의 내부 필터 생성 로그가 stderr 에 안 보임.

### 진단 과정
1. chain 의 각 layer 를 분리해서 직접 호출 — retrieve 단의 비결정성 확인.
2. `SelfQueryRetriever` 가 내부적으로 **LLM 으로 메타데이터 필터 JSON 을 생성**한다는 점에 주목 — prompt-based parsing 의 다단계 호출 구조.
3. 같은 query 를 N회 반복 호출해서 결과 분포 확인 → 매번 다른 출력.

### 원인
LangChain `SelfQueryRetriever` 는 사용자 query 를 LLM 에 넘겨 "이 query 에 해당하는 메타데이터 필터 JSON 을 만들어라" 라고 prompt 함. 이 단계가 prompt-based parsing 이라 **작은 LLM (Gemma 4 E4B, 4.5B 유효 파라미터) 에선 비결정적**. 같은 입력에 매번 다른 JSON, 또는 다른 필터, 또는 필터 자체를 안 만듦.

큰 모델 (Solar-pro2, GPT-4 등) 은 instruction-following 안정성이 높아 같은 출력이 일관되지만, 작은 모델은 prompted-tool-use 의 흔들림이 크게 나타남. LangChain 기성 LLM-driven retriever 들의 공통 약점.

### 해결
- `SelfQueryRetriever` 제거.
- `AI/chatbot_service.py` 에 **`IPhoneQueryRetriever`** 신규 작성 (`BaseRetriever` 상속):
  - Pydantic 모델 `IPhoneQuery` 에 `model_name: Optional[Literal[*valid_models]]` 정의 → LLM 출력 공간을 **grammar-constrained decoding** 으로 강제 (51개 enum 중 하나 또는 None).
  - `valid_models` 는 ChromaDB 컬렉션에서 동적 추출 (새 iPhone 추가 시 코드 변경 불필요).
  - `llm.with_structured_output(IPhoneQuery)` 로 schema 강제.
  - structured output 전용 LLM 인스턴스를 답변용 LLM 과 격리 — `with_structured_output` 의 잔향이 답변 chain 으로 전파되지 않게.
- 검증: 동일 query 3회 호출 → 3회 모두 같은 결과 (100% 결정성).

### 교훈
- **작은 LLM 에선 prompted parsing 대신 schema constrained decoding**. "권유" 가 아니라 "강제". LangChain 의 `with_structured_output` + Pydantic Literal 이 표준 패턴.
- **LangChain 기성 LLM-driven retriever 들은 큰 모델 가정**. 작은 모델로 옮길 때 회귀 점검 필수 — 모델 교체가 retrieval 단의 흔들림을 노출시킬 수 있음.
- **같은 query 를 N회 반복 호출해서 결과 분포 보는 것**이 비결정성 진단의 1순위. 한 번 실패한 케이스가 가끔 성공한다면 LLM-driven 단계의 흔들림 강하게 의심.
- `with_structured_output` 같은 메서드는 immutable 보장이 있지만, 운영상 **structured 전용 LLM 과 답변용 LLM 인스턴스를 분리**하는 게 안전.

### 관련
- `mem:backend-core/core` 의 "RAG 챗봇 invariants" — Retriever 섹션
- `mem:conventions` 의 "RAG / ChromaDB" 섹션
- `AI/chatbot_service.py` 의 `IPhoneQueryRetriever` 클래스

---

## 2026-05-23 — Gemma 4 E4B 의 한국어 음역·숫자 매칭 false positive

### 증상
`SelfQueryRetriever` 를 structured output 기반 `IPhoneQueryRetriever` 로 교체한 후에도 일부 query 에서 잘못된 model_name 추출:

| Query | LLM 출력 (잘못) | 기대값 |
|---|---|---|
| `"17 프로 맥스 카메라"` | `iPhone 15 Pro Max` | `iPhone 17 Pro Max` |
| `"그냥 카메라 좋은 폰 추천"` | `iPhone 15 Pro Max` | `None` (모델 미지정) |
| `"맥북 m4 어때?"` | `iPhone 15 Pro` | `None` (오프토픽) |
| `"안녕하세요"` | `iPhone` | `None` (인사말) |

Pydantic Literal enum 제약 덕분에 출력은 항상 51개 중 하나였지만, **의미적으로 틀린 선택**.

### 진단 과정
1. `valid_values` 를 description 에 명시 — 효과 일부, false positive 여전.
2. Description 강화 (예: "추측 금지", "17 ≠ 15") — 효과 미미. Gemma 4 가 description 안의 negative example 을 무시하는 패턴.
3. System message 강화 — 효과 컸지만 여전히 일부 케이스 (특히 "17 프로 맥스" 같이 "아이폰" prefix 없는 경우) 에서 false positive.
4. 후처리 검증 추가 — LLM 이 출력한 model_name 의 숫자가 query 에 정말 등장하는지 정규식 검증.

### 원인
- **작은 모델(Gemma 4 E4B, 4.5B 유효)** 은 `Optional` 의 null 옵션을 잘 활용 안 하고 **enum 안에서 가장 그럴듯한 항목을 강제로 고르려는 경향**.
- 특히 **한국어 음역 + 숫자 매칭** 에서 약함:
  - BPE 토크나이저가 "17" 같은 숫자를 잘게 쪼개는 경향.
  - 한국어 "프로 맥스" 가 영문 "Pro Max" 와 매핑되는 학습은 잘 됐지만, 숫자 매칭은 약함.
  - "17 프로 맥스" → LLM 이 valid_models 중 "Pro Max" 가 포함된 항목 중 학습 빈도가 높은 "iPhone 15 Pro Max" 로 빨려감.
- Description 의 미세 규칙 ("null 활용", "추측 금지") 은 작은 모델이 자주 무시.

### 해결
2단 방어:

**Layer 1 — System message 강화** (`_STRUCTURED_SYSTEM_PROMPT`):
```
1. 모델 이름이 질문에 직접 등장하지 않으면 model_name 은 반드시 null.
2. 모델 번호(예: '17')가 질문에 없는데 다른 번호로 추측 금지.
3. 일반 추천('카메라 좋은 폰'), 오프토픽('맥북'), 인사말은 model_name=null.
...
```
System message 가 description 보다 attention 우선순위 높음.

**Layer 2 — 후처리 숫자 검증** (`_validate_model_in_query`):
```python
def _validate_model_in_query(model_name, query):
    if not model_name: return None
    nums_in_model = re.findall(r'\d+', model_name)
    nums_in_query = re.findall(r'\d+', query)
    if nums_in_model and not any(n in nums_in_query for n in nums_in_model):
        return None  # 숫자가 query 에 없으면 무효화
    return model_name
```
LLM 출력 model_name 에 숫자가 있는데 query 에 그 숫자가 등장하지 않으면 **결정적으로 None 강제**. LLM 이 뭘 출력하든 코드가 차단.

검증 결과 — 4가지 케이스 모두 정상 매핑:
- "17 프로 맥스 카메라" → iPhone 17 Pro Max
- "그냥 카메라 좋은 폰 추천" → None
- "맥북 m4 어때?" → None
- "안녕하세요" → None

### 교훈
- **작은 LLM 의 약점은 system prompt + 후처리 검증의 2단 방어로 잡음**. Schema enum 만으론 부족 — enum 안에서 잘못된 선택 가능.
- **후처리 검증은 결정적**. LLM 이 뭘 출력하든 코드가 강제 → 가장 robust 한 가드레일. "trust but verify" 패턴.
- **한국어 RAG 의 숫자 매칭 약점은 일반적 패턴**. 모델 번호·버전 번호·날짜 등 숫자 매칭이 중요한 도메인에선 항상 후처리 검증을 가드레일로.
- Description 강화는 어느 정도 효과 있지만 한계 있음 — 작은 모델은 negative example ("추측 금지") 을 무시. 명시적 boolean 또는 후처리가 더 확실.

### 후속
2026-05-23 다중 모델 비교 케이스 (아래) 에서 `_validate_model_in_query` (단수) → `_validate_models_in_query` (복수) 로 rename. 후처리 숫자 검증 로직 자체는 동일, 입력/출력이 `List[str]` 로 바뀜. `_STRUCTURED_SYSTEM_PROMPT` 도 `model_name` → `model_names` 표기 변경 + 비교 질문 규칙 1줄 추가.

### 관련
- `mem:backend-core/core` 의 RAG invariants
- `AI/chatbot_service.py` 의 `_validate_models_in_query()` 함수 (구 `_validate_model_in_query`)
- `AI/chatbot_service.py` 의 `_STRUCTURED_SYSTEM_PROMPT`

---

## 2026-05-23 — 다중 모델 비교 query 의 retrieval 누락 + 답변 LLM 의 모델명 회피

### 증상
- "iPhone 17 Pro Max와 iPhone 16 Pro 카메라 차이 알려줘" 같은 비교 질문에 **한쪽 모델 정보만** 답변, 다른 모델은 "정보가 없습니다" 로 회피.
- 출시일 비교 등 일부 비교 질문에서는 양쪽 모델 모두 답변되는데 카메라·스펙 비교는 잘 안 됨 — 도메인별 비대칭.
- 단일 모델 query 와 일반 추천은 정상 → multi-model retrieval 패스 자체가 실패.

### 진단 과정
1. `IPhoneQueryRetriever._get_relevant_documents` 의 stderr 로그 확인 — `model=iPhone 17 Pro Max` 한 모델만 추출, 비교 대상인 iPhone 16 Pro 는 아예 logged values 에서 누락.
2. Pydantic schema 점검 — `model_name: Optional[ModelLiteral]` **단수형**. grammar-constrained decoding 이 한 모델만 뽑게 강제하고 있었음.
3. schema 를 `model_names: List[ModelLiteral]` 로 바꾸고 retriever 도 모델별 분리 retrieval (옵션 B) 로 수정 → retrieval 단은 4 docs (각 모델 2개씩) 균등 분배 확인.
4. 그런데 답변 LLM 이 여전히 "정보가 없습니다" 회피. **컨텍스트에 두 모델 스펙이 다 들어있는데도 회피**. retrieval 문제는 아님.
5. `qa_system_prompt` 에 "비교 질문은 회피 말고 모델별로 정리" 지시 추가 → 부분 해결. 답변은 길어졌지만 LLM 이 모델명을 "첫 번째 사양", "두 번째 카메라 사양" 으로 익명화. 출시일 비교는 잘 되는데 카메라는 안 됨 — 도메인 의존적 회피.
6. 답변 LLM temperature 를 0.0 으로 낮추고 few-shot 예시 (`("human", "...비교..."), ("ai", "...모범 답변...")`) 추가 → 오히려 답변이 짧아지면서 회피. **prompt 강도 ≠ 답변 품질**.
7. 마지막으로 stuff 된 컨텍스트의 실제 모양을 확인 — `create_stuff_documents_chain` 의 default `document_prompt` 가 `page_content` 만 사용. 카메라 chunk 의 page_content 는 `"[카메라]\n- 48MP Fusion 메인..."` 으로 시작해서 **모델명이 본문 안에 없음**. 출시일 chunk 는 우연히 `"이 문서는 Apple iPhone 15 모델의..."` 첫 줄이 박혀있어서 LLM 이 모델 매핑을 알 수 있었음.
8. `document_prompt=PromptTemplate.from_template("[{model_name}] {page_content}")` 로 metadata prefix → 한 방에 해결.

### 원인
**두 개의 독립된 결함이 겹쳤음**:

1. **Retrieval shape 결함** — Pydantic schema 가 단수형 `Optional[Literal]` 이라 LLM 출력 공간이 비교 의도를 표현 불가. grammar-constrained decoding 이 정확히 "한 모델만" 강제. 비교 query 가 들어와도 schema 가 이미 한 슬롯이라 LLM 이 둘 중 하나 선택.

2. **Metadata propagation 결함** — retrieval 의 `model_name` 메타데이터가 답변 chain 까지 흘러가지 않음. LangChain `create_stuff_documents_chain` 의 default `document_prompt` 가 `"{page_content}"` 만 사용 → metadata 자체는 retrieve 단에 남아있고 LLM 은 못 봄. multi-model 컨텍스트가 들어와도 LLM 은 "이 spec 이 어느 모델 거냐" 라는 매핑을 잃어서 보수적으로 회피.

도메인 비대칭 (출시일 OK, 카메라 NG) 은 우연 — 출시일 chunk 는 `"이 문서는 Apple iPhone X 모델의..."` prefix 가 본문에 박혀있어서 metadata 없이도 LLM 이 매핑 가능. 카메라 chunk 는 split 결과 그 prefix 가 떨어져나간 fragment 라 그게 안 됨.

답변 LLM (Gemma 4 E4B) 의 보수성도 한몫 — context 모호하면 "정보 없다" 로 빠지는 안전 가드. 이게 retrieval 결함을 가시화시킴.

### 해결
3중 변경 모두 `backend-core/AI/chatbot_service.py` 단일 파일:

**1. Schema 복수형 + retriever 분리 호출** (옵션 B):
```python
class IPhoneQuery(BaseModel):
    model_names: List[ModelLiteral] = Field(default_factory=list, ...)
    semantic_query: str

# IPhoneQueryRetriever._get_relevant_documents 내부
if len(validated_models) == 1:
    return self.vectorstore.similarity_search(sq, k=self.k, filter={"model_name": validated_models[0]})
k_per_model = max(2, self.k // len(validated_models))
merged = []
for m in validated_models:
    merged.extend(self.vectorstore.similarity_search(sq, k=k_per_model, filter={"model_name": m}))
return merged
```
ChromaDB `$in` 필터(옵션 A) 보다 모델별 분리 호출이 균등 분배 보장 — 단일 query embedding 이 한 모델로 편향되는 것 방지.

**2. Metadata 명시 prefix** (회피 해소의 결정타):
```python
doc_prompt = PromptTemplate.from_template("[{model_name}] {page_content}")
question_answer_chain = create_stuff_documents_chain(answer_llm, qa_prompt, document_prompt=doc_prompt)
```
이걸 안 하면 stuff 된 context 가 모델명 없이 raw spec 만 보임. 모델명 prefix 가 들어가면 LLM 이 "[iPhone 17 Pro Max] 카메라..." 형태로 read 해서 매핑이 명확.

**3. 답변 LLM temperature=0.0 + few-shot** (보조):
```python
answer_llm = get_chat_llm(temperature=0.0)
# qa_prompt 안에 ("human", "iPhone 14 Pro와 iPhone 15 Pro 카메라 차이"), ("ai", "**iPhone 14 Pro**\n- 메인: 48MP ƒ/1.78...") 페어
```
LLM 보수성 추가 억제. 다만 (2) 없이 (3) 만으로는 부족 — metadata propagation 이 핵심.

검증: 3개 query 모두 통과:
- 17 Pro Max vs 16 Pro 카메라: 두 모델 스펙 모두 항목별 정리 + 망원 4배/8배 vs 5배 핵심 차이 요약
- iPhone 15 vs 17 출시일: 양쪽 모델명 + 정확한 날짜 + 시간 비교 결론
- iPhone Air 무게 (단일 회귀): "iPhone Air의 무게는 165g입니다." 한 문장

### 교훈
- **Retrieval schema 의 cardinality 가 답변 품질의 상한선을 정함**. 단수형 schema 로는 비교 답변이 절대 만들어지지 않음 — LLM prompt 를 아무리 강화해도 retrieval 단에서 이미 한 모델만 들어왔으면 답변 LLM 이 다른 모델 정보를 만들어낼 수 없음 (만들면 hallucination).
- **"retrieval 잘 됐는데 답변이 회피한다" 는 패턴의 1순위 의심은 `document_prompt` default**. metadata 가 LLM 까지 안 흘러간 경우. `create_stuff_documents_chain` / `combine_documents` 류는 default 가 `page_content` 만 사용 — 거의 항상 custom `document_prompt` 가 필요.
- **답변 prompt 강화 (`temperature=0.0`, few-shot, anti-pattern 명시)** 는 metadata propagation 이 정상일 때만 효과. 컨텍스트가 모호한 상태에서 prompt 강화는 오히려 LLM 보수성을 누적시켜 답변을 더 짧게 만들 수 있음 — 이번 디버깅에서 step 6 → step 7 의 함정.
- **도메인별 답변 비대칭 (출시일 OK, 카메라 NG)** 이 보이면 chunk 구조 의심. split 으로 잘려나간 prefix 가 어떤 도메인에선 살아남고 다른 도메인에선 사라졌을 가능성 — chunk 구조가 답변 품질에 미치는 영향은 retrieval 단을 통과해도 나타남.
- **옵션 B (모델별 분리 retrieval) vs A (`$in` 단일 호출)** — 비교에서 균등 분배가 중요하면 B. ChromaDB 는 로컬이라 N배 호출 비용 거의 없음. 외부 vector DB (Pinecone, Weaviate) 라면 A 도 검토.

### 관련
- `mem:backend-core/core` 의 RAG 챗봇 invariants — Retriever, 답변 chain 섹션
- `mem:chatbot_enhancements` — 비교 답변 품질이 Phase 1 (Clarification) 의 trigger 케이스 중 하나
- `AI/chatbot_service.py` 의 `IPhoneQueryRetriever`, `_validate_models_in_query`, `doc_prompt`, few-shot 페어
- `langchain_core.prompts.PromptTemplate` + `create_stuff_documents_chain(document_prompt=...)` API

---

## 2026-05-23 — LangChain `RunnableBranch` chain → LangGraph 노드 그래프 마이그레이션

### 동기 (이전 구조의 한계)
- 회피 답변·모델명 누락이 발생해도 코드 레벨 검사가 불가능 — `qa_system_prompt` 에 지침 7-8 같은 micro-managing 누적으로만 통제. prompt 가 점점 두꺼워지면서 작은 LLM (Gemma 4 E4B) 의 instruction-following 한계에 부딪힘.
- `retrieve_documents_and_log` 안에 query 재구성 / structured extract / similarity / rerank 가 한 함수에 압축. 어느 단계가 실패했는지 stderr `print` 로만 추적 — 디버깅 비용 ↑.
- multi-turn 의 가장 흔들리는 contextualize 단계가 다른 chain 과 같은 LLM 인스턴스 공유 → temperature 분리 같은 fine-grained 제어 어려움.
- 향후 도입 예정 (`mem:chatbot_enhancements`) 인 clarification·HITL·verify retry 같은 패턴이 단일 chain 위에선 자연스럽게 안 붙음. RunnableBranch 의 분기 하나로 모든 의도 분기를 표현해야 하는 한계.

### 검토 — 왜 LangGraph 인가
- **Tool Use 위주 (LLM 자율 agent)** 는 Gemma 4 E4B 의 tool selection 흔들림으로 위험. SOTA 모델 도입 후 가능.
- **LangGraph + 명시 노드** 는 결정적 흐름 + 노드 단위 디버깅. 작은 모델로도 안전. `mem:chatbot_enhancements` Phase 3 와 일치.
- Tool Use 와 LangGraph 는 직교 차원 — 첫 마이그레이션은 LangGraph 만, Tool Use 는 모델 교체 후 후속.

### 구조 비교

**Before — LangChain `RunnableBranch` chain (단일 흐름)**
```
              User Input + chat_history
                       │
                       ▼
       ┌─────────────────────────────────┐
       │  RunnablePassthrough.assign(    │
       │    topic=router_chain.invoke()  │
       │  )                              │
       └─────┬────────────────────┬──────┘
       iphone│                    │general
             ▼                    ▼
   ┌───────────────────┐   ┌──────────────────┐
   │   rag_chain       │   │   general_chain  │
   │  ───────────      │   │  ──────────      │
   │  retrieve_docs_   │   │  general_prompt  │
   │    and_log:       │   │     │            │
   │   ┌─────────────┐ │   │     ▼            │
   │   │history_aware│ │   │   llm            │
   │   │_retriever   │ │   │     │            │
   │   │ (재구성 +    │ │   │     ▼            │
   │   │  retrieve)  │ │   │   StrOutputParse │
   │   └──────┬──────┘ │   │     │            │
   │          ▼        │   │     ▼            │
   │   sort_by_date    │   │   format_general │
   │          │        │   │     │            │
   │          ▼        │   │     ▼            │
   │   stuff_documents │   │  {answer: ...}   │
   │     _chain (LLM)  │   └──────────┬───────┘
   │          │        │              │
   │          ▼        │              │
   │ {answer, context} │              │
   └─────────┬─────────┘              │
             └──────────┬─────────────┘
                        ▼
                   dict 반환
```

**한 함수 안에 압축됨**: `retrieve_documents_and_log` 가 (1) history 재구성 (2) structured 추출 (3) similarity search (4) 정렬 (5) logging 까지 다 수행. 단계별 추적은 stderr `print` 만.

**After — LangGraph 노드 그래프 (단계 분리)**
```
                      START
                        │
                        ▼
                   ┌─────────┐
                   │ router  │
                   └────┬────┘
              iphone    │    general
        ┌──────────────┘ └──────────────┐
        ▼                               ▼
 ┌─────────────┐                  ┌─────────────┐
 │contextualize│                  │general_chat │──► END
 └──────┬──────┘                  └─────────────┘
        ▼
 ┌──────────────┐
 │extract_models│  ← Pydantic Literal + _validate_models_in_query
 └──────┬───────┘
        ▼
 ┌──────────┐
 │ retrieve │     ← 모델별 분리 retrieval + merge (옵션 B)
 └────┬─────┘
      ▼
 ┌──────────┐
 │  rerank  │     ← released_date desc 정렬
 └────┬─────┘
      ▼
 ┌──────────────┐
 │compose_answer│ ← stream_mode="messages" forward 대상
 └──────┬───────┘
        ▼
 ┌──────────┐
 │  verify  │    ← 회피 표현 / 모델 누락 검사 (현재 log-only,
 └────┬─────┘       향후 conditional edge → compose_answer 재시도)
      ▼
     END
```

**State (TypedDict) 가 노드 간 흐름**:
```
ChatState = {
  input, chat_history,            ← 입력
  topic,                          ← router 결과
  rewritten_query,                ← contextualize 결과
  model_names, semantic_query,    ← extract_models 결과
  docs,                           ← retrieve/rerank 결과
  answer,                         ← compose_answer 결과
  issues,                         ← verify 결과
}
```

### 핵심 변화 매핑

| 차원 | Before (LangChain chain) | After (LangGraph graph) |
|---|---|---|
| 단계 분리 | 1개 함수에 다단계 압축 | 8개 노드 명시 분리 |
| 분기 | `RunnableBranch` 1군데 | `add_conditional_edges` — 라우터/검증 모두 |
| 디버깅 | stderr `print` 만 | 노드별 stderr + state snapshot + mermaid |
| 회피 검사 | prompt 의 지침 7-8 으로만 통제 | `verify_node` 가 코드로 detect + log (향후 retry) |
| stream 단위 | `chain.stream` 의 dict chunk 의 `answer` 키 | `graph.stream(stream_mode="messages")` + 노드 metadata 필터 |
| 확장 | 새 의도 추가 시 chain 재구성 | 노드 추가 + edge 추가 |
| temperature 분리 | 답변 LLM 만 0.0 (다른 단계 0.2) | contextualize/answer 둘 다 0.0, 일반 chain 0.2 |
| state 가시성 | chain 내부 변수 (외부 접근 불가) | `ChatState` TypedDict — 모든 단계 가시 |

### 마이그레이션 절차
1. `langgraph==0.6.11` 의존성 추가
2. `AI/graph.py` 신규 — `ChatState` + 8 노드 함수 + `get_chatbot_graph()` lazy singleton
3. `AI/chatbot_service.py` 그대로 유지 — `IPhoneQueryRetriever` 의 vectorstore/structured_chain 을 graph 가 attribute 로 import (재초기화 없음, 같은 ChromaDB connection)
4. `AI/views.py` 의 단발/스트림 view 둘 다 `get_chatbot_graph()` 사용. stream view 는 `stream_mode="messages"` + `_USER_FACING_NODES={"compose_answer", "general_chat"}` 필터
5. shell e2e 검증 — 3턴 시나리오 (15 Pro vs Max → 영상 콘텐츠 → 17 Pro Max 추가) + 일반 대화 분기 모두 통과
6. curl e2e — SSE 741 chunks + sessionid 발급 + multi-turn DB 누적 4 messages 확인

### 교훈
- **prompt 의 micro-managing 은 단일 chain 의 한계 신호**. 회피·누락 같은 검사를 prompt 로만 통제하면 누적되어 LLM 이 무시. **노드 분리 + 코드 검사** 로 이전하면 prompt 가 얇아지면서 더 robust.
- **multi-step LLM 워크플로우의 디버깅 비용**은 step 수 × 비결정성. chain 안에 다단계 압축하면 비용 ↑. 그래프는 노드별 state snapshot 으로 디버깅을 step 수에 선형 분해.
- **graph 도입 = Tool Use 도입 아님**. 둘은 직교 차원 — graph 는 워크플로우 (개발자가 흐름 설계), Tool Use 는 LLM capability (LLM 이 흐름 결정). 작은 모델엔 graph 가 더 안전, SOTA 엔 Tool Use 도 자연스러움.
- **stream forwarding 의 핵심**은 graph 의 모든 LLM 호출 token chunk 가 한 stream 으로 통합되는 것. `metadata.langgraph_node` 로 user-facing 노드만 필터 — 다른 단계 (router/contextualize/extract_models) 의 token 은 내부 reasoning 이라 차단. 깔끔.
- LangGraph 의 진짜 부가가치는 **verify retry loop, checkpointer, conditional edges** 같은 패턴이 자연스럽게 도입 가능해진다는 것. 첫 마이그레이션 후 incremental 로 확장.

### 관련
- `mem:chatbot_enhancements` 의 Phase 3 (LangGraph 도입) 가 이번 작업으로 달성됨. Phase 1 (clarification), Phase 4 (verify retry) 등은 후속 PR
- `AI/graph.py` — 신규 모듈
- `AI/views.py` — `get_chatbot_graph()` 사용, `stream_mode="messages"` + 노드 metadata 필터
- `AI/chatbot_service.py` — `get_conversational_rag_chain()` 은 legacy 로 유지. 후속 PR 에서 제거 예정

---

## 2026-06-07 — verify → compose_answer 재시도 루프 구현 (단일 체인으로는 불가능했던 순환 제어)

### 증상 / 배경
- 2026-05-23 비교 답변 디버깅에서 회피 표현·모델명 누락을 `qa_system_prompt` 지침 7-8 + few-shot + `temperature=0.0` 으로 억눌렀지만, 작은 LLM (Gemma 4 E4B) 특성상 **확률적으로 가끔 다시 회피**. prompt 강화는 상한이 있음 (이미 그 함정을 비교 디버깅 step 6→7 에서 확인).
- 같은 날 LangGraph 마이그레이션에서 `verify_node` 를 넣었지만 **log-only** — 회피/누락을 *감지만* 하고 답변은 그대로 사용자에게 나감. "감지는 하는데 고치진 않는" 반쪽 상태로 남아 있었음.

### 진단 / 설계 판단
- 근본 해결 = 답변 생성 후 코드로 검증하고, 실패하면 **생성 단계로 되돌려 다시 생성하는 순환 루프**.
- 그런데 이전 단일 체인(LCEL DAG)은 처리가 한 방향으로만 흘러 "되돌리기" 를 표현 불가. `RunnableBranch` 는 순방향 분기일 뿐 back-edge 가 아님. 체인 밖 `while` 로 흉내내면 router/retrieve 까지 통째 재실행 + 오케스트레이션이 체인 밖으로 누출 → 선언적 체인의 의미 상실.
- LangGraph 의 conditional edge 는 노드로 되돌아가는 **사이클을 그래프 토폴로지로 직접 표현** → `compose_answer` 만 재실행. 이것이 마이그레이션의 실제 명분이자, 단일 체인 대비 유일한 본질적 차별점(검증이 아니라 **순환**).

### 해결
모두 `backend-core/` 내 3개 파일.

**1. `AI/graph.py` — 순환 루프 + 상한 + 피드백 주입**
```python
_MAX_COMPOSE_ATTEMPTS = 2   # 최초 1 + 재시도. 로컬 Gemma 지연 고려.

def _retry_pending(issues, attempts):          # 라우팅과 stream reset 이 공유하는 단일 기준
    return bool(issues) and attempts < _MAX_COMPOSE_ATTEMPTS

def _route_after_verify(state):
    if _retry_pending(state.get("issues"), state.get("attempts", 0)):
        return "compose_answer"                 # 검증 실패 → 생성 단계로 되돌림(사이클)
    return END

# 엣지 교체: 무조건 종료 → 조건부 백엣지
g.add_conditional_edges("verify", _route_after_verify,
                        {"compose_answer": "compose_answer", END: END})
```
`compose_answer_node` 는 재진입 시 직전 `issues` 를 `_build_retry_feedback()` 로 변환해 `[재작성 지침]` 으로 프롬프트에 주입 — **단순 재호출이 아니라 교정 신호 포함**. `attempts` 카운터는 `ChatState` 에 추가.

**2. `AI/views.py` — 스트리밍 재시도 정합성**
```python
# stream_mode 를 리스트로 → (mode, payload) 튜플. updates 로 verify 판정 가로채기.
for mode, payload in graph.stream(inputs, stream_mode=["updates", "messages"]):
    if mode == "messages": ... # 토큰 forward
    else:
        if payload.get("compose_answer"): attempts = ...   # 노드 종료 시점 attempts 갱신
        elif _retry_pending(payload.get("verify", {}).get("issues"), attempts):
            parts.clear()                                  # 결함 답변 폐기
            yield 'data: {"reset": true}\n\n'              # 클라이언트도 비우라 신호
```

**3. `frontend/src/views/ChatbotPage.vue`** — `reset` 수신 시 봇 버블 `raw/text` 비우고 typing-dot 재표시 → 재생성분으로 자연 교체.

검증: 격리 토폴로지 테스트 (compose→verify→compose→verify→END, 정확히 1회 재시도 후 종료), `py_compile`, Django import + `_retry_pending`/`_build_retry_feedback` 단위 동작 모두 통과.

### 함정
- **스트리밍에서 재시도는 이미 보낸 토큰과 충돌**. `messages` 모드만으로는 attempt 경계를 못 잡음 — `verify` 는 LLM 토큰을 안 내보내 attempt1 마지막 토큰과 attempt2 첫 토큰이 연속으로 붙음. `updates` 모드를 병행해 노드 종료 이벤트로 경계를 감지해야 함.
- **reset 판정은 그래프 라우팅과 같은 기준이어야 함**. verify 가 issues 를 내도 상한 도달이면 재시도 안 하는데, 그때 reset 을 보내면 최종 답변이 지워짐. `_retry_pending()` 단일 함수로 graph 라우팅과 stream reset 이 같은 기준을 공유하게 분리.
- **재시도 = 단순 재호출이면 또 같은 회피**. 작은 LLM 은 같은 입력에 같은 실패를 반복할 확률이 높아, 직전 실패 사유(issues)를 프롬프트에 피드백으로 넣어야 교정 압력이 생김.

### 측정 (남은 칸)
- **구조는 완성**됐고 사이클 동작은 검증됨. 다만 "회피율이 실제로 줄었다" 는 **측정은 아직**. LM Studio e2e 로 회피 유발 비교 질문을 돌려 회피표현 발생률 before/after 를 세야 "구조 확보 → 결함 감소" 로 승격됨. `TROUBLESHOOTING.html` deck 의 P2(반복 실행 변동성) 패턴으로 시각화 예정.
- 따라서 현재 정확한 서술은 *"회피·누락을 잡는 재시도 루프를 구현했다"* 까지. *"답변 품질이 올랐다"* 는 측정 후에 쓸 카드.

### 교훈
- **단일 체인 vs 그래프의 본질 차이는 "검증" 이 아니라 "사이클"**. 검증 한 단계만이면 `RunnableLambda` 로 단일 체인에 넣어도 됨. 그래프가 본전을 뽑는 건 검증 실패 시 되돌아가는 back-edge 가 필요할 때.
- **log-only 검증은 절반**. 감지만 하고 교정 안 하면 사용자 답변 품질은 그대로 — 감지 → 재생성까지 루프를 닫아야 의미.
- **순환 도입 시 상한 카운터는 필수**. `attempts` 없으면 계속 실패하는 query 에서 무한 루프. LangGraph `recursion_limit` 도 있지만, 의미있는 종료(상한 도달 시 최선답 반환)를 위해 명시 카운터가 낫다.
- **스트리밍 + 재시도는 표면 기능 하나에 숨은 복잡도**. "되돌려 재생성" 한 줄이 클라이언트 버퍼 정합성(SSE reset)까지 끌고옴 — 백엔드 루프만 짜고 끝낼 수 없음.

### 관련
- `AI/graph.py` — `_route_after_verify`, `_retry_pending`, `_MAX_COMPOSE_ATTEMPTS`, `_build_retry_feedback`, `compose_answer_node`, conditional edge
- `AI/views.py` — `chatbot_stream_api` 의 `stream_mode=["updates","messages"]` + `reset` 이벤트
- `frontend/src/views/ChatbotPage.vue` — `reset` 핸들링
- 2026-05-23 LangGraph 마이그레이션 (위 섹션) 의 verify log-only 를 이 작업으로 닫음
- `mem:chatbot_enhancements` Phase 4 (verify retry) 달성

---

## 기록 추가 형식

새 사건 추가 시 다음 템플릿을 H2 section 으로 append:

```markdown
## YYYY-MM-DD — 한 줄 제목

### 증상
사용자/시스템 관점에서 무엇이 잘못 보였는가.

### 진단 과정
어떤 가설을 세웠고 어떻게 검증했는가 (시간순).

### 원인
진짜 root cause.

### 해결
무엇을 어디서 어떻게 고쳤는가 (파일 경로 + 핵심 코드).

### 교훈
비슷한 케이스를 빠르게 잡는 mental model 또는 체크리스트.

### 관련
`mem:xxx`, 관련 파일 경로, 커밋.
```
