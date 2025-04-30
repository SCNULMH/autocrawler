# smart_crawler_auto.py

import re
import time
import csv
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── undetected‐chromedriver + stealth 설정 ─────────────────────────────
ua = UserAgent()
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument(f'user-agent={ua.random}')
options.add_argument('--start-maximized')
driver = uc.Chrome(options=options)
wait = WebDriverWait(driver, 10)
stealth(driver,
        languages=["ko-KR","ko"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
)

# ─── 1. URL 접속 & 대표 요소 선택 ─────────────────────────────────────
url = input("🌐 크롤링할 사이트 URL 입력: ").strip()
if not url.startswith("http"):
    url = "https://" + url
driver.get(url)
time.sleep(2)

keyword = input("🔍 요소 검색 키워드: ").strip()
cands = driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
if not cands:
    print("❌ 요소를 찾지 못했습니다."); driver.quit(); exit()
print(f"{len(cands)}개 후보 발견:")
for i,e in enumerate(cands):
    txt = e.text.strip().replace('\n',' ')
    print(f"[{i}] <{e.tag_name}> ▶ {txt[:40]}")
idx = int(input("선택할 요소 번호: "))
target = cands[idx]

# ─── 2. CSS selector 자동 추출 ─────────────────────────────────────────
selector = driver.execute_script("""
  function getCssSelector(el) {
    let path = [];
    while(el.nodeType===1 && el.tagName.toLowerCase()!=='html') {
      let sel = el.tagName.toLowerCase();
      if(el.className) sel += '.'+el.className.trim().split(/\\s+/)[0];
      path.unshift(sel);
      el=el.parentNode;
    }
    return path.join(' > ');
  }
  return getCssSelector(arguments[0]);
""", target)
os.makedirs("crawl_result", exist_ok=True)
with open("crawl_result/selector.txt","w",encoding="utf-8") as f:
    f.write(selector)
print("→ 수집 대상 selector:", selector)

# ─── 3. 최대 수집 개수 설정 ───────────────────────────────────────────
mc = input("📦 최대 수집 개수 (엔터=무제한): ").strip()
max_count = int(mc) if mc.isdigit() else None

# ─── 4. 수집 함수 정의 ─────────────────────────────────────────────────
collected = set()
def collect_page():
    for el in driver.find_elements(By.CSS_SELECTOR, selector):
        t = el.text.strip()
        if t and t not in collected:
            collected.add(t)
            print("✅", t[:60])
            if max_count and len(collected)>=max_count:
                return True
    return False

# ─── 5. 페이지 순회 ───────────────────────────────────────────────────
page = 1
while True:
    print(f"\n📄 페이지 {page} 수집 중…")
    if collect_page():
        break

    # 5-1. <link rel="next">
    try:
        href = driver.find_element(By.CSS_SELECTOR,'link[rel="next"]').get_attribute('href')
        driver.get(href); page+=1; time.sleep(2); continue
    except: pass

    # 5-2. a[rel="next"]
    try:
        btn = driver.find_element(By.CSS_SELECTOR,'a[rel="next"]')
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'a[rel="next"]')))
        btn.click(); page+=1; time.sleep(2); continue
    except: pass

    # 5-3. Google-specific: id="pnnext"
    try:
        gnext = driver.find_element(By.ID, "pnnext")
        driver.execute_script("arguments[0].scrollIntoView();", gnext)
        gnext.click(); page+=1; time.sleep(2); continue
    except: pass

    # 5-4. li.next > a (quotes.toscrape.com 등)
    try:
        nxt = driver.find_element(By.CSS_SELECTOR, 'li.next > a')
        if nxt.is_displayed():
            nxt.click(); page+=1; time.sleep(2); continue
    except: pass

    # 5-5. “다음” 텍스트/클래스 기반 버튼
    clicked = False
    for xp in ['//a[normalize-space()="다음"]','//button[normalize-space()="다음"]','//a[contains(@class,"next")]']:
        try:
            nb = driver.find_element(By.XPATH, xp)
            if nb.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView();", nb)
                try: nb.click()
                except: driver.execute_script("arguments[0].click();", nb)
                page+=1; time.sleep(2); clicked=True; break
        except: pass
    if clicked: continue

    # 5-6. 숫자 페이징 자동 탐지
    anchors = driver.find_elements(By.TAG_NAME,'a')
    nums = [(int(a.text), a) for a in anchors if a.text.isdigit()]
    if len(nums)>=2:
        nums.sort(key=lambda x:x[0])
        for num,a in nums:
            if num == page+1:
                driver.execute_script("arguments[0].scrollIntoView();", a)
                try: a.click()
                except: driver.execute_script("arguments[0].click();", a)
                page=num; time.sleep(2); clicked=True; break
    if clicked: continue

    # 5-7. URL 파라미터 기반 page+1
    p = urlparse(driver.current_url)
    qs = parse_qs(p.query, keep_blank_values=True)
    bumped = False
    for k,v in qs.items():
        if re.search(r'page|pg|p$|start|offset', k, re.IGNORECASE) and v and v[0].isdigit():
            qs[k] = [str(int(v[0])+1)]
            newq = urlencode(qs, doseq=True)
            next_url = urlunparse((p.scheme,p.netloc,p.path,p.params,newq,p.fragment))
            driver.get(next_url); page+=1; time.sleep(2); bumped=True; break
    if bumped: continue

    # 5-8. 무한 스크롤 fallback
    print("🔽 페이징 탐지 실패 → 무한 스크롤")
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
        time.sleep(2)
        if collect_page(): break
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h==last_h or (max_count and len(collected)>=max_count):
            print("⛔ 더 이상 로드할 콘텐츠가 없습니다."); break
        last_h=new_h
    break

# ─── 6. 결과 CSV 저장 ─────────────────────────────────────────────────
out = f"crawl_result/result_{int(time.time())}.csv"
with open(out,'w',encoding="utf-8",newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["내용"])
    for t in sorted(collected):
        writer.writerow([t])

print(f"\n✅ 전체 수집 완료: {len(collected)}개")
print("📁 저장 경로:", out)
driver.quit()
