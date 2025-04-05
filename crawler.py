import time
import json
import os
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from product_keywords import product_keywords

# (1) 함수를 수정해서 "list_count", "ad_count", "prod_count"를 카운팅하고,
#     광고(ad) / 일반(prod)을 구분하며, 타겟 상품을 찾으면 해당 rank까지 수집하도록 변경했습니다.
def search_product_rank(driver, keyword, target_product_id):
    url = "https://search.shopping.naver.com/ns/search?query=" + keyword
    print(f"[정보] 이동: {url}")
    driver.get(url)
    time.sleep(3)  # 초기 페이지 로딩 대기 시간 증가

    SCROLL_CYCLES = 50  # 스크롤 시도 횟수 증가
    last_height = 0

    # (2) 새로운 변수들
    list_count = 0     # "compositeCardContainer_composite_card_container" 로 잡힌 상품 리스트 개수
    ad_count = 0       # 광고 상품 개수 (data-shp-contents-grp="ad")
    prod_count = 0     # 일반 상품 개수 (data-shp-contents-grp="prod")

    # (3) '새로운 li' 엘리먼트가 있는지 없는지 판별을 위해 사용
    processed_items = set()  
    no_new_items_count = 0
    consecutive_same_height_count = 0  # 페이지 높이가 연속으로 같은 횟수

    for cycle in range(1, SCROLL_CYCLES + 1):
        print(f"\n--- [정보] 스크롤 사이클 {cycle} ---")

        # 스크롤 로직 개선
        for step in range(5):  # 한번에 너무 많이 스크롤하지 않도록 수정
            driver.execute_script("window.scrollBy(0, 1000);")  # 스크롤 거리 감소
            time.sleep(0.5)  # 개별 스크롤 대기 시간 증가
        
        time.sleep(2)  # 전체 스크롤 후 대기 시간 증가

        # 현재 페이지 높이 확인
        current_height = driver.execute_script("return document.documentElement.scrollHeight")
        
        # 페이지 높이가 이전과 같은지 확인
        if current_height == last_height:
            consecutive_same_height_count += 1
        else:
            consecutive_same_height_count = 0

        # (4) li 태그 중에서 class가 "compositeCardContainer_composite_card_container" 를 포함하고
        #     "composite_card_container"도 포함하는 애들만 가져옵니다
        #     (__jr8cb 이런 랜덤 문구는 무시하기 위해)
        product_elements = driver.find_elements(
            By.CSS_SELECTOR,
            "li[class*='compositeCardContainer_composite_card_container'][class~='composite_card_container']"
        )

        new_items = 0
        # (5) 이제 product_elements를 순회하면서 ad인지 prod인지 구분하고,
        #     list_count, ad_count, prod_count 등을 카운트합니다.
        for product_el in product_elements:
            try:
                # li 요소의 전체 outerHTML을 기준으로 중복 체크
                outer_html = product_el.get_attribute("outerHTML")
                if outer_html in processed_items:
                    # 이미 처리한 li라면 건너뜀
                    continue
                processed_items.add(outer_html)
                new_items += 1

                # (5-1) list_count 증가
                list_count += 1

                # list_count가 1,000을 넘어가면 검색 중단
                if list_count > 1000:
                    print("[정보] 상품 수가 1,000개를 초과하여 검색을 중단합니다.")
                    return None

                # div.basicProductCard_basic_product_card__TdrHT > a 선택
                anchor_el = product_el.find_element(
                    By.CSS_SELECTOR,
                    "div.basicProductCard_basic_product_card__TdrHT > a"
                )

                # data-shp-contents-grp 확인 (광고인지, 일반상품인지 구분)
                contents_grp = anchor_el.get_attribute("data-shp-contents-grp")
                
                # 상품 ID 추출
                data_shp_contents_dtl = anchor_el.get_attribute("data-shp-contents-dtl")
                if not data_shp_contents_dtl:
                    continue

                try:
                    detail_list = json.loads(data_shp_contents_dtl)
                except:
                    continue

                # chnl_prod_no 추출
                prod_id = None
                for d in detail_list:
                    if d.get("key") == "chnl_prod_no":
                        prod_id = d.get("value")
                        break

                if not prod_id:
                    continue

                if contents_grp == "ad":
                    # 광고인 경우 ad_count++
                    ad_count += 1
                    print(f"{list_count} : {prod_id}, 광고")
                    # 광고 상품은 우리가 찾는 대상이 아니므로 계속 진행
                    continue
                elif contents_grp == "prod":
                    # 일반 상품이면 prod_count++
                    prod_count += 1
                    
                    if prod_id == target_product_id:
                        # (5-3) 타겟 상품을 찾았다면, data-shp-contents-rank를 가져옴
                        prod_rank = anchor_el.get_attribute("data-shp-contents-rank")
                        # 광고를 제외한 실제 순위 계산
                        real_rank = list_count - ad_count
                        print(f"{list_count} : {prod_id}, 제품, 찾던 상품! (순위: {real_rank})")
                        print(f"[정보] ★ 목표 상품({target_product_id}) 발견! ★")
                        print(f"     └ list_count={list_count}, ad_count={ad_count}, prod_count={prod_count}, rank={real_rank}")

                        # 순위만 반환하도록 수정
                        return real_rank
                    else:
                        print(f"{list_count} : {prod_id}, 제품, 찾던건 아님")

                # 광고도 아니고(prod도 아니고) 특정 다른 grp(가령 brand 등)가 있을 수 있지만
                # 문제에서 언급되지 않았으므로 일단 무시

            except Exception as e:
                # 오류나면 그냥 넘어감
                continue

        # (6) 스크롤 한 번 끝날 때마다 현재 누적된 카운트를 보여줍니다.
        print(f"[정보] 현재까지 총 리스트 개수: {list_count}, 광고(ad): {ad_count}, 일반상품(prod): {prod_count}")
        print(f"[정보] 새로 추가된 li 수: {new_items}")

        # 새로운 상품(li)이 없는 경우 카운트
        if new_items == 0:
            no_new_items_count += 1
        else:
            no_new_items_count = 0

        # 스크롤 중단 조건 수정
        if no_new_items_count >= 5 and consecutive_same_height_count >= 3:
            print("[정보] 연속 5번 이상 새로운 상품이 없고, 3번 연속 높이가 같음 -> 스크롤 중단")
            break

        last_height = current_height

    # (7) 여기에 도달했다는 것은 타겟 상품을 찾지 못했다는 의미이므로 None 리턴
    return None


# (8) CSV 저장 함수를 수정하여 순위만 저장하도록 합니다.
def save_to_csv(product_id, keyword, rank):
    # results 폴더가 없으면 생성
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    filename = os.path.join(results_dir, f"{product_id}.csv")
    today = datetime.now().strftime("%y-%m-%d")

    file_exists = os.path.isfile(filename)

    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:  # utf-8-sig로 변경하여 Excel에서 한글 깨짐 방지
        writer = csv.writer(f)
        # 파일이 없으면 헤더 추가
        if not file_exists:
            writer.writerow(['날짜', '키워드', '순위'])
        writer.writerow([today, keyword, rank])


def main():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    driver_path = os.path.join(current_dir, "driver", "chromedriver")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        for product_id, keywords in product_keywords.items():
            print(f"\n=== 제품 ID: {product_id} 검색 시작 ===")
            for keyword in keywords:
                print(f"\n키워드 '{keyword}' 검색 중...")
                rank = search_product_rank(driver, keyword, product_id)

                if rank:
                    print(f"순위: {rank}")
                    save_to_csv(product_id, keyword, rank)
                else:
                    print("상품을 찾지 못했습니다.")
                    save_to_csv(product_id, keyword, "N/A")

                time.sleep(2)  # 다음 검색 전 대기

    finally:
        driver.quit()


if __name__ == "__main__":
    main()