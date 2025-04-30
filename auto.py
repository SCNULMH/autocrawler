from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import csv
import os

# 🔧 크롬 드라이버 설정
service = Service('./chromedriver.exe')
options = Options()
options.add_argument('--start-maximized')
driver = webdriver.Chrome(service=service, options=options)

# 1. 페이지 접속
url = input("크롤링할 사이트 URL 입력: ")
if not url.startswith("http"):
    url = "https://" + url
else:
    url = url
driver.get(url)
print(f"✅ 페이지 접속 완료: {url}")
time.sleep(2)

# 2. 키워드 or 클릭으로 수집 대상 지정
use_keyword_search = input("📌 키워드로 HTML 요소를 검색하시겠습니까? (Y/N): ").strip().lower()
if use_keyword_search == 'y':
    keyword_text = input("🔍 입력할 키워드 (요소 안 텍스트 일부): ").strip()
    matched_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword_text}')]")
    if not matched_elements:
        print("❌ 해당 키워드를 포함한 요소를 찾을 수 없습니다.")
        driver.quit()
        exit()
    target_elem = matched_elements[0]
    print(f"✅ 첫 번째 매칭 요소: <{target_elem.tag_name}>")
else:
    print("\n🖱️ 수집할 텍스트 요소를 클릭한 후 콘솔에서 엔터 ▶️")
    input("✔️ 클릭 완료 후 Enter ▶ ")
    target_elem = driver.switch_to.active_element
    print(f"📝 클릭한 요소 텍스트: {target_elem.text.strip()}")

# 3. 반복 블록 자동 탐색
def find_repeating_parent(element):
    for _ in range(10):
        try:
            class_name = element.get_attribute("class")
            tag_name = element.tag_name
            if class_name:
                class_part = class_name.split()[0]
                selector = f"{tag_name}.{class_part}"
                matches = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(matches) >= 2 and tag_name in ["div", "li", "section", "article"]:
                    return selector
            element = element.find_element(By.XPATH, "..")
        except:
            break
    return None

block_selector = find_repeating_parent(target_elem)
if not block_selector:
    print("❌ 반복 구조를 자동으로 찾지 못했습니다.")
    driver.quit()
    exit()
print(f"✅ 반복 블록 CSS 선택자: {block_selector}")

# 4. 필터 키워드 및 설정
keyword = input("🔍 필터링할 키워드가 있다면 입력 (엔터=전체 수집): ").strip()
max_count_input = input("📦 수집할 최대 개수 입력 (엔터=무제한): ").strip()
max_count = int(max_count_input) if max_count_input.isdigit() else None
field_name = input("📄 저장할 컬럼명 입력 (예: 내용): ").strip() or "내용"

# 5. 수집 함수
collected = []

def collect_from_current_page():
    elements = driver.find_elements(By.CSS_SELECTOR, block_selector)
    for elem in elements:
        try:
            text = elem.text.strip()
            if keyword and keyword not in text:
                continue
            if text not in collected:
                collected.append(text)
                print(f"✅ 수집: {text[:60]}")
            if max_count and len(collected) >= max_count:
                return
        except:
            continue

# 6. 페이지 수집 루프
page = 1
while True:
    print(f"📄 페이지 {page} 수집 중...")
    collect_from_current_page()
    if max_count and len(collected) >= max_count:
        break

    try:
        next_btn = driver.find_element(By.XPATH, '//li[@class="next"]/a')
        next_btn.click()
        page += 1
        time.sleep(2)
        continue
    except:
        print("🔽 Next 버튼 없음. 스크롤 다운 시작...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            collect_from_current_page()
            if max_count and len(collected) >= max_count:
                break
        break

# 7. 결과 저장
os.makedirs("crawl_result", exist_ok=True)
file_name = f"crawl_result/result_{int(time.time())}.csv"
with open(file_name, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([field_name])
    for item in collected:
        writer.writerow([item])

print(f"\n✅ 수집 완료! 총 {len(collected)}개 항목")
print(f"📁 저장 경로: {file_name}")
driver.quit()
