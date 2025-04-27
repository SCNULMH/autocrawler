# auto_crawler.py
# 오토크롤러 프로그램 (사용자 클릭 기록 + 재생 기능 추가)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import csv
import os
import json

# 1. 크롬드라이버 경로 설정
service = Service(executable_path="./chromedriver.exe")
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=service, options=chrome_options)

# 2. URL 입력 및 자동 보정
url = input("크롤링할 사이트 URL 입력: ")
if not url.startswith("http"):
    url = "https://" + url
print(f"✅ 접속할 URL: {url}")
driver.get(url)

time.sleep(2)

# 3. 클릭 기록 여부
record_clicks = input("💬 클릭하는 버튼을 기록할까요? (y/n): ").lower() == 'y'

click_history = []

if record_clicks:
    print("🖱️ 클릭하고 싶은 요소를 클릭하세요. (10초 동안 기록)")
    start_time = time.time()
    while time.time() - start_time < 10:
        elements = driver.find_elements(By.XPATH, "//*")
        for elem in elements:
            try:
                if elem.is_displayed():
                    driver.execute_script("""
                    arguments[0].addEventListener('click', function(){
                        console.log('CLICKED:', arguments[0]);
                    });
                    """, elem)
            except:
                pass
        time.sleep(1)
    print("🛑 클릭 기록 시간 종료")
else:
    # 기록된 클릭 히스토리가 있다면 재생
    if os.path.exists('click_history.json'):
        with open('click_history.json', 'r', encoding='utf-8') as f:
            click_history = json.load(f)

    # 기록된 클릭 재생
    for click in click_history:
        try:
            elem = driver.find_element(By.XPATH, click["xpath"])
            elem.click()
            print(f"✅ 기록된 클릭 수행: {click['xpath']}")
            time.sleep(1)
        except Exception as e:
            print(f"❌ 클릭 실패: {click['xpath']}, 오류: {e}")

# 4. 페이지 소스 가져오기
html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

# 5. 수집할 데이터 조건 입력
print("🎯 수집할 데이터 설정")
tag_name = input("수집할 태그 이름 입력 (예: div, span, a): ").strip()
class_name = input("필요한 경우 클래스명 입력 (없으면 엔터): ").strip()

# 6. 데이터 수집
print("✅ 데이터 필터링 시작...")

if class_name:
    items = soup.find_all(tag_name, class_=class_name)
else:
    items = soup.find_all(tag_name)

results = []
for item in tqdm(items, desc="데이터 수집 중"):
    text = item.get_text(strip=True)
    results.append([text])

# 7. 저장 폴더/파일 설정
save_folder = "crawl_result"
save_file = "result.csv"
os.makedirs(save_folder, exist_ok=True)

# 8. 결과 저장 (CSV)
with open(os.path.join(save_folder, save_file), mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Content"])  # CSV 헤더
    writer.writerows(results)

print(f"✅ 수집 완료 및 저장 완료! (경로: {save_folder}/{save_file})")

# 9. 클릭 기록 저장
if record_clicks:
    # (임시로 빈 리스트 저장)
    with open('click_history.json', 'w', encoding='utf-8') as f:
        json.dump(click_history, f, indent=4, ensure_ascii=False)
    print("✅ 클릭 기록 저장 완료 (click_history.json)")

# 10. 브라우저 종료
driver.quit()
