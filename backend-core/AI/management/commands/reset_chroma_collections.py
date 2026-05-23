"""ChromaDB 컬렉션 검사 및 정리.

기본 동작: 컬렉션 목록과 임베딩 개수만 출력.

옵션:
- ``--purge-legacy`` : 챗봇이 사용하지 않는 컬렉션만 삭제.
- ``--purge-all``    : 활성 컬렉션 포함 모두 삭제. 차원 마이그레이션
                       (Upstage 4096 → EmbeddingGemma 768) 직전에 사용.

차원이 다른 임베딩 모델로 교체하면 ChromaDB 컬렉션은 호환되지 않으므로
이 명령으로 컬렉션을 비운 뒤 ``embed_iphone_data`` 를 재실행해야 한다.
"""

import os

import chromadb
from django.core.management.base import BaseCommand


ACTIVE_COLLECTION = "iphone_specs_collection"
LEGACY_COLLECTIONS = {"iphone_collection", "crawled_specs_collection"}


class Command(BaseCommand):
    help = "ChromaDB 컬렉션 검사 및 정리 (임베딩 모델 교체 시 사용)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--chroma_path",
            type=str,
            default=os.getenv("CHROMA_DB_PATH_CRAWLED", "./chroma_db_crawled"),
            help="ChromaDB 저장 경로",
        )
        parser.add_argument(
            "--purge-legacy",
            action="store_true",
            help=f"빈/legacy 컬렉션({sorted(LEGACY_COLLECTIONS)}) 만 삭제",
        )
        parser.add_argument(
            "--purge-all",
            action="store_true",
            help="활성 컬렉션 포함 모두 삭제 (재인덱싱 전 사용)",
        )

    def handle(self, *args, **opts):
        path = opts["chroma_path"]
        client = chromadb.PersistentClient(path=path)
        collections = client.list_collections()

        self.stdout.write(self.style.SUCCESS(f"\n=== ChromaDB at {path} ==="))
        if not collections:
            self.stdout.write("  (컬렉션 없음 — 깨끗한 상태)")
        for c in collections:
            count = c.count()
            if c.name == ACTIVE_COLLECTION:
                tag = "ACTIVE"
            elif c.name in LEGACY_COLLECTIONS:
                tag = "LEGACY"
            else:
                tag = "OTHER"
            self.stdout.write(f"  [{tag}] {c.name} — {count}건")

        targets = []
        if opts["purge_all"]:
            targets = [c.name for c in collections]
        elif opts["purge_legacy"]:
            targets = [c.name for c in collections if c.name in LEGACY_COLLECTIONS]

        if not targets:
            self.stdout.write(
                "\n(삭제 옵션 미지정 — 위 목록만 표시. "
                "정리하려면 --purge-legacy 또는 --purge-all 옵션을 추가하세요.)"
            )
            return

        self.stdout.write(
            self.style.WARNING(f"\n다음 컬렉션을 삭제합니다: {targets}")
        )
        for name in targets:
            client.delete_collection(name=name)
            self.stdout.write(self.style.SUCCESS(f"  삭제됨: {name}"))

        if opts["purge_all"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "\n다음 단계: `python manage.py embed_iphone_data` 로 "
                    "EmbeddingGemma 임베딩 재생성"
                )
            )
