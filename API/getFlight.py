import requests
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv
import os
import folium
import csv

# .env 파일에서 환경 변수 로드
load_dotenv()
username=os.getenv('OPENSKY_USERNAME')
password=os.getenv('OPENSKY_PASSWORD')

#api 호출
def get_all_fights():
    """
    전 세계 모든 항공기 정보 조회
    """
    url = "https://opensky-network.org/api/states/all"

    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        data = response.json()

        print("API 호출 성공:", data)
        print(f"현재 추적 중인 항공기: {len(data['states'])}대")
        print("데이터 수신 시간:", datetime.fromtimestamp(data['time']).strftime('%Y-%m-%d %H:%M:%S UTC'))

        return data
    except requests.exceptions.RequestException as e:
        print("API 호출 실패:", e)
        return None
    
# data=get_all_fights()


def get_korean_flights():
    """
    대한민국 영공을 비행 중인 항공기 정보 조회

    좌표 기준:
    - 위도: 33.0~39.0 (제주도부터 휴전선)
    - 경도: 124.0~132.0 (서해부터 동해)
    """
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    data = response.json()

    korean_flights=[]
    
    for state in data['states']:
        # 위도와 경도가 없는 경우 제외
        if state[5] is None or state[6] is None:
            continue

        lon=state[5] # 경도
        lat=state[6] # 위도

        # 대한민국 영공 내에 있는지 확인
        if 33.0<=lat<=39.0 and 124.0<=lon<=132.0:
            korean_flights.append({
                'icao24': state[0],
                'callsign': state[1].strip() if state[1] else 'UNKNOWN',
                'country': state[2],
                'longtitude': lon,
                'latitude': lat,
                'altitude_m': state[7], # 미터 단위 고도
                'altitude_ft': state[7] * 3.28084 if state[7] is not None else None, # 미터를 피트로 변환
                'velocity_ms': state[9], # 미터/초 단위 속도
                'velocity_knots': state[9] * 1.94384 if state[9] else None, # 미터/초를 노트로 변환
                'heading': state[10], # 항공기의 방향 (도)
                'vertical_rate': state[11], # 수직 속도 (미터/초)
                'on_ground': state[8], # 지상 착륙 여부
                'timestamp': datetime.fromtimestamp(data['time']).strftime('%Y-%m-%d %H:%M:%S UTC') if state[3] else None
            })

    df = pd.DataFrame(korean_flights)

    print(f"한국 상공 항공기: {len(df)}대")
    print(f"공중: {len(df[df['on_ground']==False])}대")
    print(f"지상: {len(df[df['on_ground']==True])}대")

    return df

# korean_df=get_korean_flights()

def get_flights_with_auth(username, password):
    """
    인증된 사용자를 위한 항공기 정보 조회
    """
    url = "https://opensky-network.org/api/states/all"

    try:
        response = requests.get(url, auth=(username, password))
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        data = response.json()

        print("인증된 API 호출 성공:", data)
        print(f"현재 추적 중인 항공기: {len(data['states'])}대")
        print("데이터 수신 시간:", datetime.fromtimestamp(data['time']).strftime('%Y-%m-%d %H:%M:%S UTC'))

        return data
    except requests.exceptions.RequestException as e:
        print("인증된 API 호출 실패:", e)
        return None
    

def track_specific_aircraft(icao24, username=None, password=None):
    """
    특정 항공기(ICAO24 식별자 기준) 추적
    """
    url = f"https://opensky-network.org/api/states/all?icao24={icao24}"

    auth = (username, password) if username else None
    response = requests.get(url, auth=auth)
    data = response.json()

    if not data['states']:
        print(f"ICAO24 {icao24}에 해당하는 항공기를 찾을 수 없습니다.")
        return None
    
    state = data['states'][0]

    info={
        'icao24': state[0],
        'callsign': state[1].strip() if state[1] else 'UNKNOWN',
        'country': state[2],
        'longtitude': state[5], # 경도
        'latitude': state[6], # 위도
        '고도(ft)': state[7] * 3.28084 if state[7] is not None else None,
        'velocity_ms': state[9],
        '속도(knots)': state[9] * 1.94384 if state[9] else None,
        '방향': state[10],
        'vertical_rate': state[11],
        '지상여부': '지상' if state[8] else '공중',
        '업데이트': datetime.fromtimestamp(state[3]).strftime('%Y-%m-%d %H:%M:%S')
    }

    print(f"ICAO24 {icao24} 항공기 정보:", info)
    for key, Value in info.items():
        print(f"{key}: {Value}")

    return info


def analyze_airport_traffic(airport_lat, airport_lon, radius_km=50):
    """
    특정 공항 주변 반경 내 항공기 교통량 분석

    Args:
        airport_lat: 공항 위도
        airport_lon: 공항 경도
        radius_km: 반경 (킬로미터)
    """
    import math

    def distance(lat1, lon1, lat2, lon2):
        # 두 지점 간 거리 계산 Haversine 공식 사용
        R = 6371  # 지구 반경 (킬로미터)

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c
    
    url="https://opensky-network.org/api/states/all"
    response=requests.get(url)
    data=response.json()

    nearby_aircraft=[]

    # 항공기 위치 정보 순회
    for state in data['states']:
        if state[5] is None or state[6] is None:
            continue

        dist = distance(airport_lat, airport_lon, state[6], state[5])

        if dist <=radius_km:
            nearby_aircraft.append({
                'callsign': state[1].strip() if state[1] else 'UNKNOWN',
                'distance_km': round(dist, 1),
                'altitude_ft': int(state[7] * 3.28084) if state[7] is not None else None,
                'on_ground': state[8]
            })

    df=pd.DataFrame(nearby_aircraft)

    print(f"반경 {radius_km}km 내 항공기: {len(df)}대")
    print(f"공중: {len(df[df['on_ground']==False])}대")
    print(f"지상: {len(df[df['on_ground']==True])}대")

    return df


# 인천국제공항 좌표
# icn_traffic = analyze_airport_traffic(37.4602, 126.4407, radius_km=50) 

# print("\n가장 가까운 5대:")
# print(icn_traffic.sort_values('distance_km').head(5))


def create_flight_map(df,center_lat=37.4602, center_lon=126.4406):
    """
    항공기 위치를 지도에 시각화

    Args:
        df: 항공기 데이터프레임
        center_lat: 지도 중심 위도
        center_lon: 지도 중심 경도
    """

    m=folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        titles='OpenStree'
    )

    # 공항 마커
    folium.Marker(
        [center_lat, center_lon],
        popup='인천국제공항',
        icon=folium.Icon(color='red', icon='plane')
    ).add_to(m)

    # 항공기 마커
    for idx, row in df.iterrows():
        if row['on_ground']:
            color='gray'
            icon='stop'
        else:
            color='blue'
            icon='plane'
        
        popup_text= f"""
            <b>{row['callsign']}</b><br>
            고도: {row['altitude_ft']} ft<br>
            속도: {row['velocity_knots']} knots<br>
            방향: {row['heading']}°
        """
        # 
        folium.Marker(
            location=[row['latitude'], row['longtitude']],
            popup=popup_text,
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(m)
    
    # 지도를 HTML 파일로 저장
    m.save('korean_flights.html')
    print("지도 저장 완료: korean_flights.html")

    return m

# korean_df=get_korean_flights()
# create_flight_map(korean_df)


def collect_continuous_data(duration_minutes=60, interval_seconds=60):
    """
    일정 기간 동안 주기적으로 항공기 데이터 수집

    Args:
        duration_minutes: 총 수집 시간 (분)
        interval_seconds: 수집 간격 (초)
    """
    filename= f"flight_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # CSV 파일 헤더 작성
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'icao24', 'callsign', 'country', 'longtitude', 'latitude',
            'altitude_m', 'velocity_ms',
            'heading', 'vertical_rate', 'on_ground'
        ])

    start_time=time.time()
    end_time=start_time + duration_minutes * 60
    collection_count=0

    print(f"데이터 수집 시작")
    print(f"기간: {duration_minutes}분, 간격: {interval_seconds}초")
    print(f"저장 파일: {filename}")

    try:
        while time.time()<end_time:
            collection_count +=1
            current_time=datetime.now()

            # 데이터 수집
            url = "https://opensky-network.org/api/states/all"
            response = requests.get(url)
            data = response.json()
            
            saved_count=0
            # 한국 상공 필터링 및 저장
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                for state in data['states']:
                    if state[5] is None or state[6] is None:
                        continue

                    lon, lat = state[5], state[6]

                    if 33.0 <= lat <= 39.0 and 124.0 <= lon <= 132.0:
                        writer.writerow([
                            current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            state[0],
                            state[1].strip() if state[1] else 'UNKNOWN',
                            state[2],
                            lon,
                            lat,
                            state[7],
                            state[9],
                            state[10],
                            state[11],
                            state[8]
                        ])
                        saved_count += 1
            
            elapsed = int(time.time() - start_time) # 경과 시간
            remaining = int(end_time - time.time()) # 남은 시간

            print(f"[{collection_count}] {current_time.strftime('%H:%M:%S')} - 수집 완료, 저장된 항공기: {saved_count}대, 경과: {elapsed}s, 남은 시간: {remaining}s")

            # 다음 수집까지 대기
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("데이터 수집 중단됨 by 사용자")

    print("데이터 수집 완료")
    print(f"총 수집 횟수: {collection_count}")
    print(f"저장 파일: {filename}")

    df = pd.read_csv(filename)
    print(f"총 저장된 항공기 데이터: {len(df)}행")

# collect_continuous_data(duration_minutes=1, interval_seconds=10)

def analyze_icn_cju_route():
    """
    인천(ICN) - 제주(CJU) 노선 항공기 분석
    """
    korean_df= get_korean_flights()

    # 인천공항 주변 (위도: 37.3~37.6, 경도: 126.3~126.6)
    icn_area = korean_df[
        (korean_df['latitude']>37.3)& (korean_df['latitude']<37.6)&
        (korean_df['longtitude']>126.3)& (korean_df['longtitude']<126.6)
    ]

    # 제주공항 주변 (위도: 33.4~33.6, 경도: 126.4~126.6)
    cju_area= korean_df[
        (korean_df['latitude']>33.4)& (korean_df['latitude']<33.6)&
        (korean_df['longtitude']>126.4)& (korean_df['longtitude']<126.6)
    ]

    # 인천-제주 노선 상공 (위도: 33.4~36.5, 경도: 126.0~127.0, 고도 20000ft 이상)
    route_area = korean_df[
        (korean_df['latitude']>33.4)& (korean_df['latitude']<36.5)&
        (korean_df['longtitude']>126.0)& (korean_df['longtitude']<127.0)&
        (korean_df['altitude_ft']>20000)  # 고도 20000ft 이상(순항고도)
    ]

    print(f"인천공항 주변 항공기: {len(icn_area)}대")
    if len(icn_area)>0:
        print(icn_area[['callsign','altitude_ft', 'on_ground']])

    print(f"제주공항 주변 항공기: {len(cju_area)}대")
    if len(cju_area)>0:
        print(cju_area[['callsign','altitude_ft', 'on_ground']])

    print(f"인천-제주 노선 상공 항공기: {len(route_area)}대")
    if len(route_area)>0:
        print(route_area[['callsign','altitude_ft', 'velocity_knots', 'heading']])
        print(f"\n평균 순항 고도: {route_area['altitude_ft'].mean():.0f} ft")
        print(f"평균 속도: {route_area['velocity_knots'].mean():.0f} knots")

# analyze_icn_cju_route()

def get_incheon_flights(date: datetime) -> list:
    """인천공항 하루치 출발 데이터 조회"""
    
    begin = int(date.timestamp())
    end   = int((date + timedelta(days=1)).timestamp())
    
    url = "https://opensky-network.org/api/flights/departure"
    params = {
        "airport": "RKSI",
        "begin": begin,
        "end": end
    }
    
    # 비회원은 요청 제한 있음 — 무료 계정 만들면 여유로워짐
    resp = requests.get(url, params=params, timeout=30)
    
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 429:
        print("Rate limit — 10초 대기")
        time.sleep(10)
        return get_incheon_flights(date)  # 재시도
    else:
        print(f"에러: {resp.status_code}")
        return []

# 사용 예시
flights = get_incheon_flights(datetime(2024, 3, 1))
print(flights[0])