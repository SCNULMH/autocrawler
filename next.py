import os
import pandas as pd
from bs4 import BeautifulSoup

# 1. selector 불러오기
selector_path = "crawl_result/selector.txt"
if not os.path.exists(selector_path):
    print("❌ selector.txt 파일이 없습니다.")
    exit()

with open(selector_path, "r", encoding="utf-8") as f:
    selector = f.read().strip()

# 2. 자동 축약
parts = [p.strip() for p in selector.split(">")]
if len(parts) > 2:
    short_selector = " > ".join(parts[-2:])
    print(f"📦 선택자 자동 축약 적용: {short_selector}")
else:
    short_selector = selector
print(f"🔍 최종 적용 선택자: {short_selector}")

# 3. 키워드 필터
use_keyword_filter = input("🔍 특정 키워드 필터를 적용할까요? (Y/N): ").strip().lower()
filter_mode = "none"
keywords = []

if use_keyword_filter == "y":
    filter_mode = input("✅ 포함할까요(I) 제외할까요(E)? (I/E): ").strip().lower()
    raw = input("📌 키워드 입력 (쉼표로 구분): ").strip()
    keywords = [kw.strip() for kw in raw.split(",") if kw.strip()]
    print(f"🎯 적용 키워드 ({'포함' if filter_mode == 'i' else '제외'}): {keywords}")

# 4. 텍스트 길이 제한
use_length_filter = input("📏 텍스트 길이 제한을 둘까요? (Y/N): ").strip().lower()
min_len, max_len = 0, 9999
if use_length_filter == "y":
    min_len = int(input("🔢 최소 글자 수 입력 (예: 10): ").strip())
    max_len = int(input("🔢 최대 글자 수 입력 (예: 50): ").strip())
    print(f"📏 적용 길이 범위: {min_len} ~ {max_len}자")

# 5. CSV 파일 로드
csv_files = [f for f in os.listdir("crawl_result") if f.startswith("result_") and f.endswith(".csv")]
if not csv_files:
    print("❌ result_*.csv 파일이 없습니다.")
    exit()

csv_files.sort(reverse=True)
csv_path = f"crawl_result/{csv_files[0]}"
print(f"📄 대상 CSV 파일: {csv_path}")
df = pd.read_csv(csv_path)

# 6. 정제 및 필터링
filtered_set = set()

# ✅ fallback 선택자 리스트 (가장 먼저 성공한 selector 사용)
fallback_selectors = [short_selector, "strong.cnf_news_title", "a.cnf_news_area"]

for html in df["내용"]:
    try:
        soup = BeautifulSoup(f"<div>{html}</div>", "html.parser")
        matches = []

        # fallback selector 순차 적용
        for sel in fallback_selectors:
            matches = soup.select(sel)
            if matches:
                break

        for elem in matches:
            text = elem.get_text(strip=True)
            if not text:
                continue
            if not (min_len <= len(text) <= max_len):
                continue
            if filter_mode == "i" and not any(kw in text for kw in keywords):
                continue
            if filter_mode == "e" and any(kw in text for kw in keywords):
                continue
            filtered_set.add(text)
    except:
        continue

# 7. 저장
output_path = "crawl_result/title_only.csv"
pd.DataFrame(sorted(filtered_set), columns=["제목"]).to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"\n✅ 정제 완료: {len(filtered_set)}개 고유 제목 추출됨")
print(f"📁 저장 완료: {output_path}")
