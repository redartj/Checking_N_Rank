# make_report.py (예시 코드)

import os
import pandas as pd
from glob import glob

def make_report():
    # 결과 CSV들이 들어있는 폴더
    csv_folder = "./results"
    
    # 최종적으로 만들 엑셀 파일 이름
    output_excel = "product_rank_report.xlsx"

    # ExcelWriter로 여러 시트를 쓸 수 있음
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        # results 폴더에 있는 모든 .csv 파일을 찾음
        for csv_file in glob(os.path.join(csv_folder, "*.csv")):
            # 파일명에서 제품ID 추출
            # 예: "./results/6086408637.csv" → "6086408637"
            basename = os.path.basename(csv_file)  # "6086408637.csv"
            product_id = os.path.splitext(basename)[0]  # "6086408637"

            # CSV 읽어오기
            df = pd.read_csv(csv_file, encoding='utf-8')
            # df.columns = ['날짜','키워드','순위'] 라고 가정 (이미 헤더가 그렇게 되어있다면 건너뛰어도 됨)

            # 날짜를 datetime으로 변환(선택)
            # 만약 '날짜' 형식이 "23-04-03" 이런 식이라면
            df['날짜'] = pd.to_datetime(df['날짜'], format='%y-%m-%d')
            
            # 순위를 숫자로
            # 혹시 'N/A' 같은 값이 있을 수도 있으니 예외처리 필요
            df['순위'] = pd.to_numeric(df['순위'], errors='coerce')

            # 피벗: index=날짜, columns=키워드, values=순위
            pivot_df = df.pivot(index='날짜', columns='키워드', values='순위')
            
            # 날짜 내림차순 정렬
            pivot_df.sort_index(ascending=False, inplace=True)

            # 시트 이름은 "상품ID" 정도로
            pivot_df.to_excel(writer, sheet_name=product_id)

    print(f"[완료] {output_excel} 파일이 생성되었습니다.")

if __name__ == "__main__":
    make_report()