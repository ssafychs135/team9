import os
import json
import glob
import re
from django.core.management.base import BaseCommand, CommandError

# 이름 정규화를 위한 함수
def normalize_name(name):
    # (GSM), (3세대) 등 괄호 안의 내용 제거
    normalized = re.sub(r'\(.*\)', '', name)
    # iPhoneAir -> iPhone Air 처럼 특수 공백을 일반 공백으로 변경
    normalized = normalized.replace('\u00a0', ' ')
    # 양쪽 끝의 공백 제거
    return normalized.strip()

class Command(BaseCommand):
    help = '정규화된 모델 이름을 기준으로 crawled_data 폴더의 JSON 파일들에 출시일 정보를 업데이트합니다.'

    def handle(self, *args, **options):
        source_dir = 'AI/iPhone'
        target_dir = 'crawled_data'
        
        if not os.path.isdir(source_dir):
            raise CommandError(f'소스 디렉토리 "{source_dir}"를 찾을 수 없습니다.')
        if not os.path.isdir(target_dir):
            raise CommandError(f'타겟 디렉토리 "{target_dir}"를 찾을 수 없습니다.')

        self.stdout.write('1단계: AI/iPhone 폴더에서 정규화된 이름-출시일 맵을 생성합니다...')
        
        name_to_date_map = {}
        source_files = glob.glob(os.path.join(source_dir, '*.json'))

        for source_path in source_files:
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    source_data = json.load(f)
                
                model_name = source_data.get('name')
                release_date = source_data.get('released')

                if model_name and release_date:
                    # 맵을 만들 때부터 정규화된 이름을 키로 사용
                    normalized_model_name = normalize_name(model_name)
                    # 이미 같은 이름이 있다면 덮어쓰지 않음 (GSM/CDMA 등 여러 버전이 있을 경우 첫번째 것만 사용)
                    if normalized_model_name not in name_to_date_map:
                        name_to_date_map[normalized_model_name] = release_date
            except (json.JSONDecodeError, Exception) as e:
                self.stdout.write(self.style.WARNING(f'"{source_path}" 처리 중 오류 발생: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'총 {len(name_to_date_map)}개의 정규화된 모델 이름에 대한 출시일 정보를 확보했습니다.'))

        self.stdout.write(f'\n2단계: "{target_dir}" 폴더의 파일 업데이트를 시작합니다...')
        
        target_files = glob.glob(os.path.join(target_dir, '*.json'))
        updated_count = 0
        not_found_count = 0

        for target_path in target_files:
            try:
                filename = os.path.basename(target_path)
                model_name_from_filename = os.path.splitext(filename)[0]
                
                # 타겟 파일 이름도 정규화하여 맵에서 검색
                normalized_target_name = normalize_name(model_name_from_filename)
                release_date = name_to_date_map.get(normalized_target_name)

                if release_date:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        target_data = json.load(f)

                    if '출시 연도' in target_data:
                        del target_data['출시 연도']
                    
                    target_data['출시 일자'] = release_date

                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(target_data, f, ensure_ascii=False, indent=4)
                    
                    self.stdout.write(f'  -> "{filename}" 파일 업데이트 완료 (출시일: {release_date})')
                    updated_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  -> "{model_name_from_filename}"에 해당하는 출시일 정보가 없습니다.'))
                    not_found_count += 1

            except (json.JSONDecodeError, Exception) as e:
                self.stdout.write(self.style.ERROR(f'"{target_path}" 파일 처리 중 에러 발생: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n업데이트 완료. 총 {updated_count}개 파일 업데이트, {not_found_count}개 파일은 처리하지 못함.'))