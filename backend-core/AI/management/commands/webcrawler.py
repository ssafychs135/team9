# Django의 management command를 만들기 위한 기본 클래스를 가져옵니다.
from django.core.management.base import BaseCommand, CommandError
# 웹 크롤링을 위한 selenium 관련 라이브러리를 가져옵니다.
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# HTML 파싱을 위한 BeautifulSoup 라이브러리를 가져옵니다.
from bs4 import BeautifulSoup
# 정규 표현식 사용을 위한 re 모듈을 가져옵니다.
import re
# 상대 URL을 절대 URL로 변환하기 위한 urljoin과 URL 구문 분석을 위한 urlparse를 가져옵니다.
from urllib.parse import urljoin, urlparse
# JSON 파일 저장을 위한 json 모듈을 가져옵니다.
import json
# 파일 경로 및 디렉토리 관리를 위한 os 모듈을 가져옵니다.
import os
# HTML 엔티티(예: &nbsp;)를 문자로 변환하기 위한 html 모듈을 가져옵니다.
import html

# Django의 management command는 반드시 Command라는 이름의 클래스로 정의되어야 하고, BaseCommand를 상속받아야 합니다.
class Command(BaseCommand):
    help = '지정된 URL에서 Apple 제품 링크를 찾고, 각 링크의 기술 사양을 모델명.json 파일로 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='크롤링을 시작할 대상 URL')

    def handle(self, *args, **options):
        target_url = options['url']
        self.stdout.write(f'크롤링 시작점: "{target_url}"')

        output_dir = 'crawled_data'
        os.makedirs(output_dir, exist_ok=True)
        self.stdout.write(f'결과물은 "{output_dir}" 폴더에 저장됩니다.')

        driver = None
        try:
            # --- 1단계: 링크 목록 찾기 ---
            self.stdout.write("1단계: 상세 정보를 수집할 페이지 링크를 찾습니다...")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            driver.get(target_url)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            path_pattern = re.compile(r"^/(?:kb/SP\d+|[a-z]{2}-[a-z]{2}/\d+|\d+)")
            
            initial_links = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_url = urljoin(target_url, href)
                if absolute_url.startswith("https://support.apple.com"):
                    path = urlparse(absolute_url).path
                    if path_pattern.match(path):
                        clean_url = absolute_url.split('?')[0].split('#')[0]
                        initial_links.add(clean_url)

            if not initial_links:
                self.stdout.write(self.style.WARNING('수집할 링크를 찾지 못했습니다. 작업을 종료합니다.'))
                return

            self.stdout.write(self.style.SUCCESS(f'총 {len(initial_links)}개의 페이지에서 상세 정보를 수집합니다.'))

            # --- 2단계: 각 링크를 방문하여 상세 정보 추출 및 파일 저장 ---
            self.stdout.write("\n2단계: 각 페이지를 방문하여 스펙 정보를 추출하고 JSON 파일로 저장합니다...")
            
            successful_saves = 0

            for link in sorted(list(initial_links)):
                self.stdout.write(f'  -> "{link}" 페이지 방문 중...')
                driver.get(link)
                page_soup = BeautifulSoup(driver.page_source, 'html.parser')

                model_name_tag = page_soup.find('h1', class_='gb-header')
                if not model_name_tag:
                    self.stdout.write(self.style.WARNING(f'    └ 모델명을 찾을 수 없어 이 페이지를 건너뜁니다.'))
                    continue
                
                model_name = model_name_tag.get_text(strip=True).split('-')[0].strip()
                model_name = html.unescape(model_name)
                safe_model_name = re.sub(r'[\\/*?:\"<>|]', "", model_name)
                filename = f"{safe_model_name}.json"
                filepath = os.path.join(output_dir, filename)

                page_data = {}

                # --- 출시 연도 추출 ---
                release_year_tag = page_soup.find('div', class_='gb-callout')
                if release_year_tag and release_year_tag.p:
                    text = release_year_tag.p.get_text(strip=True)
                    if text.startswith('출시 연도:'):
                        year = text.split(':')[1].strip()
                        page_data['출시 연도'] = year

                # --- 나머지 스펙 섹션 추출 ---
                for section_div in page_soup.find_all('div', class_='gb-group group-wrap-layout wrap-right'):
                    h3_tag = section_div.find('h3')
                    if not h3_tag:
                        continue
                    
                    raw_title = h3_tag.get_text(strip=True)
                    section_title = re.sub(r'[\d⁰¹²³⁴⁵⁶⁷⁸⁹]+$', '', raw_title).strip()
                    
                    ul_tag = section_div.find('ul')
                    if ul_tag:
                        items = []
                        key_value_items = {}
                        is_kv_format = False
                        
                        for item in ul_tag.find_all('li', recursive=False):
                            text = item.get_text(strip=True)
                            if ':' in text:
                                is_kv_format = True
                                parts = text.split(':', 1)
                                if len(parts) == 2:
                                    key = parts[0].strip()
                                    value = parts[1].strip()
                                    key_value_items[key] = value
                            else:
                                items.append(text)
                        
                        if is_kv_format:
                            if items:
                                key_value_items['기타'] = items
                            page_data[section_title] = key_value_items
                        else:
                            page_data[section_title] = items
                    else:
                        p_tags = section_div.find_all('p')
                        full_text = ' '.join(p.get_text(strip=True) for p in p_tags)
                        if full_text:
                            page_data[section_title] = full_text

                if page_data:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(page_data, f, ensure_ascii=False, indent=4)
                    
                    successful_saves += 1
                    self.stdout.write(self.style.SUCCESS(f'    └ {len(page_data)}개 섹션 정보 추출! -> "{filepath}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'    └ 이 페이지에서 유효한 스펙 정보를 찾지 못했습니다.'))

            # --- 3단계: 최종 결과 요약 ---
            self.stdout.write("\n\n--- 작업 요약 ---")
            self.stdout.write(f"총 {len(initial_links)}개의 링크를 확인하여 {successful_saves}개의 JSON 파일을 생성했습니다.")

        except Exception as e:
            raise CommandError(f'크롤링 중 에러 발생: {e}')
        
        finally:
            if driver:
                driver.quit()
            
            self.stdout.write(self.style.SUCCESS('\n모든 웹 크롤러 작업을 성공적으로 마쳤습니다.'))