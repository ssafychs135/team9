import os
import json
import glob
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'crawled_data 폴더의 JSON 파일들에서 출시일자가 리스트인 경우, 가장 빠른 날짜 하나만 남깁니다.'

    def handle(self, *args, **options):
        target_dir = 'crawled_data'
        
        if not os.path.isdir(target_dir):
            raise CommandError(f'타겟 디렉토리 "{target_dir}"를 찾을 수 없습니다.')

        self.stdout.write(f'"{target_dir}" 폴더의 파일 정리를 시작합니다...')
        
        target_files = glob.glob(os.path.join(target_dir, '*.json'))
        updated_count = 0

        for target_path in target_files:
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # '출시 일자' 키가 있고, 그 값이 리스트인 경우에만 처리
                if '출시 일자' in data and isinstance(data['출시 일자'], list):
                    release_dates = data['출시 일자']
                    
                    # 리스트가 비어있지 않은 경우
                    if release_dates:
                        # YYYY-MM-DD 형식의 날짜 문자열은 일반적인 문자열 비교로 최소값을 찾을 수 있습니다.
                        earliest_date = min(release_dates)
                        
                        # 기존 값과 다른 경우에만 업데이트
                        if data['출시 일자'] != earliest_date:
                            data['출시 일자'] = earliest_date
                            
                            with open(target_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=4)
                            
                            self.stdout.write(self.style.SUCCESS(f'  -> "{os.path.basename(target_path)}" 파일 업데이트 완료: "{earliest_date}"'))
                            updated_count += 1
            
            except json.JSONDecodeError:
                self.stdout.write(self.style.ERROR(f'"{os.path.basename(target_path)}" 파일이 잘못된 JSON 형식입니다.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'"{os.path.basename(target_path)}" 파일 처리 중 에러 발생: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n정리 완료. 총 {updated_count}개 파일이 업데이트되었습니다.'))