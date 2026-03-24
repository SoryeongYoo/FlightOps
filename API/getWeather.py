"""
기상청 공공데이터 API를 활용한 인천공항 기상 데이터 수집
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")

class WeatherDataCollector:
    def __init__(self, api_key):
        """
        api_key: 기상청 공공데이터포털에서 발급받은 인증키
        https://www.data.go.kr/ 에서 발급
        """
        self.api_key = api_key
        self.base_url = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
        
        # 인천공항 지점번호: 112 (정확한 번호는 기상청 확인 필요)
        self.icn_stn_id = "112"
    
    def get_daily_weather(self, target_date):
        """일별 기상 데이터 조회"""
        params = {
            'serviceKey': self.api_key,
            'numOfRows': '24',  # 시간별 데이터
            'pageNo': '1',
            'dataType': 'JSON',
            'dataCd': 'ASOS',
            'dateCd': 'HR',  # 시간별
            'startDt': target_date.strftime('%Y%m%d'),
            'endDt': target_date.strftime('%Y%m%d'),
            'stnIds': self.icn_stn_id
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception: {e}")
            return None
    
    def collect_range(self, start_date, end_date):
        """기간별 데이터 수집"""
        current_date = start_date
        all_data = []
        
        while current_date <= end_date:
            print(f"Collecting weather for {current_date.date()}")
            
            daily_weather = self.get_daily_weather(current_date)
            if daily_weather:
                all_data.append(daily_weather)
            
            current_date += timedelta(days=1)
            time.sleep(1)  # API 제한
        
        # DataFrame 변환 및 저장
        if all_data:
            df = pd.DataFrame(all_data)
            
            output_dir = Path("data/raw/weather")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"icn_weather_{start_date.date()}_{end_date.date()}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"✓ Saved: {output_file}")
            return df
        
        return None

# 사용 예시
if __name__ == "__main__":
    # API 키는 환경변수나 설정 파일에서 읽어오기
    api_key = "YOUR_API_KEY_HERE"
    
    collector = WeatherDataCollector(api_key)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    df = collector.collect_range(start_date, end_date)