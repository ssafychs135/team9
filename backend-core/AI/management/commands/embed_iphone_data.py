import os
import json
import glob
import unicodedata
from django.core.management.base import BaseCommand, CommandError
from dotenv import load_dotenv


def _nfkc(text):
    """문자열을 NFKC 정규화. NBSP·전각/반각 등 호환 문자를 표준 형태로 통일."""
    return unicodedata.normalize('NFKC', text)

# Langchain 임포트 — 임베딩은 LM Studio (EmbeddingGemma) 사용
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from AI.lm_studio import EmbeddingGemmaEmbeddings
from langchain_core.documents import Document

# ChromaDB 클라이언트 임포트
import chromadb
from tqdm import tqdm

# .env 파일에서 환경 변수 로드
load_dotenv()

class Command(BaseCommand):
    help = 'crawled_data 폴더의 iPhone JSON 파일에서 스펙 데이터를 로드하여 LM Studio 의 EmbeddingGemma 로 임베딩하고 ChromaDB에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--collection_name',
            type=str,
            default='iphone_specs_collection', # 새로운 컬렉션 이름
            help='Name of the ChromaDB collection for iPhone spec data.',
        )
        parser.add_argument(
            '--chroma_path',
            type=str,
            default=os.getenv('CHROMA_DB_PATH_CRAWLED', './chroma_db_crawled'), # 크롤링 데이터 전용 경로
            help='Path to store ChromaDB data for crawled spec files.',
        )

    def handle(self, *args, **options):
        collection_name = options['collection_name']
        chroma_path = options['chroma_path']

        self.stdout.write(self.style.SUCCESS('LM Studio 의 EmbeddingGemma 어댑터를 초기화합니다...'))
        try:
            # 문서 임베딩용 — title:none | text: prefix 자동 부착
            embeddings = EmbeddingGemmaEmbeddings()
        except ValueError as e:
            raise CommandError(str(e))
        except Exception as e:
            raise CommandError(f"임베딩 모델 초기화에 실패했습니다: {e}")

        self.stdout.write(self.style.SUCCESS('ChromaDB 클라이언트를 초기화합니다...'))
        try:
            client = chromadb.PersistentClient(path=chroma_path)
            # 기존 컬렉션이 있으면 삭제하고 새로 생성 (완전한 재임베딩을 위해)
            existing_collections = [col.name for col in client.list_collections()]
            if collection_name in existing_collections:
                self.stdout.write(self.style.WARNING(f"기존 컬렉션 '{collection_name}'을(를) 삭제합니다..."))
                client.delete_collection(name=collection_name)
            
            # 컬렉션 생성 (get_or_create 대신 create를 써도 되지만, 안전하게)
            collection = client.get_or_create_collection(name=collection_name)
            self.stdout.write(self.style.SUCCESS(f"ChromaDB 컬렉션 '{collection_name}'이(가) '{chroma_path}' 경로에 준비되었습니다."))
        except Exception as e:
            raise CommandError(f"ChromaDB 초기화에 실패했습니다: {e}")

        self.stdout.write(self.style.SUCCESS('crawled_data 폴더에서 JSON 데이터를 로드합니다...'))

        # manage.py가 있는 review_site 디렉토리 기준
        json_files_path = os.path.join('crawled_data', '*.json')
        json_file_paths = glob.glob(json_files_path)
        
        if not json_file_paths:
            raise CommandError(f"'{json_files_path}' 경로에서 JSON 파일을 찾을 수 없습니다. review_site/crawled_data 폴더를 확인해주세요.")

        documents = []
        total_files = len(json_file_paths)

        for i, json_file_path in enumerate(json_file_paths):
            self.stdout.write(self.style.MIGRATE_HEADING(f'  JSON 파일 처리 중 {i+1}/{total_files}: {os.path.basename(json_file_path)}'))
            
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    spec_data = json.load(f)

                # 파일명에서 확장자 제거하여 모델명 추출 — NBSP 가 박힌 기존 파일에도 대응
                model_name = os.path.splitext(os.path.basename(json_file_path))[0]
                model_name = _nfkc(model_name)
                
                # 텍스트 변환 시작
                text_parts = [f"이 문서는 Apple {model_name} 모델의 상세 스펙 정보를 담고 있습니다."]

                # 섹션별 처리
                for section, content in spec_data.items():
                    # 이미 처리했거나 메타데이터로 뺄 필드는 본문에서 제외할 수도 있지만, 
                    # 검색 정확도를 위해 본문에도 포함하는 것이 좋습니다.
                    if section == "출시 일자":
                        continue # 메타데이터로만 사용

                    text_parts.append(f"\n[{section}]")
                    
                    if isinstance(content, dict):
                        for key, value in content.items():
                            if isinstance(value, list):
                                value_str = ", ".join(value)
                                text_parts.append(f"- {key}: {value_str}")
                            else:
                                text_parts.append(f"- {key}: {value}")
                    
                    elif isinstance(content, list):
                        # 리스트인 경우 항목 나열
                        value_str = ", ".join(content)
                        text_parts.append(f": {value_str}")
                    
                    else:
                        # 문자열이나 기타 기본 타입
                        text_parts.append(f": {content}")

                # 본문 전체 NFKC — JSON 내부의 "True\xa0Tone" 같은 NBSP 들을 일괄 정리
                text_content = _nfkc("\n".join(text_parts))

                # 메타데이터 구성 (filename 도 정규화하여 메타데이터 일관성 확보)
                metadata = {
                    "source": "crawled_spec",
                    "model_name": model_name,
                    "filename": _nfkc(os.path.basename(json_file_path)),
                }
                
                # 출시 일자가 있으면 메타데이터에 추가
                if "출시 일자" in spec_data:
                    released = spec_data["출시 일자"]
                    if isinstance(released, list):
                        metadata["released_date"] = ', '.join(released)
                    else:
                        metadata["released_date"] = str(released)

                doc = Document(page_content=text_content, metadata=metadata)
                documents.append(doc)

            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(f"  '{os.path.basename(json_file_path)}' 파일이 잘못된 JSON 형식입니다. 건너뜀."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  '{os.path.basename(json_file_path)}' 처리 중 오류 발생: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f'총 {len(documents)}개의 Document 객체를 생성했습니다.'))

        self.stdout.write(self.style.SUCCESS('Document를 청크로 분할합니다...'))
        # 스펙 데이터는 구조가 중요하므로 청크 사이즈를 넉넉하게 잡습니다.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(documents)
        self.stdout.write(self.style.SUCCESS(f'{len(chunks)}개의 청크를 생성했습니다.'))

        self.stdout.write(self.style.SUCCESS('임베딩을 생성하고 ChromaDB에 저장합니다...'))
        
        try:
            # Langchain Wrapper를 사용하여 저장 (이 과정에서 임베딩이 수행됨)
            vectorstore = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=chroma_path
            )
            
            # 배치 처리를 위해 tqdm 사용 가능하지만, vectorstore.add_documents가 알아서 처리함
            # 여기서는 진행 상황을 보기 어려우므로 그냥 호출
            vectorstore.add_documents(chunks)
            
            self.stdout.write(self.style.SUCCESS(f'ChromaDB에 {len(chunks)}개의 청크를 성공적으로 저장했습니다.'))
            self.stdout.write(self.style.SUCCESS(f"컬렉션 이름: {collection_name}"))
            self.stdout.write(self.style.SUCCESS(f"저장 경로: {chroma_path}"))
            
        except Exception as e:
            raise CommandError(f"ChromaDB에 임베딩 저장 실패: {e}")

        self.stdout.write(self.style.SUCCESS('임베딩 프로세스가 성공적으로 완료되었습니다!'))
