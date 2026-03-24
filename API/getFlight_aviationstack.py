import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows용
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# EDA 코드
df = pd.read_csv(r"C:\Users\soryu\Desktop\archive\flights_sample_3m.csv")

# 기본 정보
print("=== 데이터 크기 ===")
print(f"행: {len(df):,}  |  컬럼: {df.shape[1]}")

print("\n=== 결측치 비율 ===")
null_pct = (df.isnull().sum() / len(df) * 100).round(1)
print(null_pct[null_pct > 0])

print("\n=== 지연 기초 통계 ===")
print(df['ARR_DELAY'].describe().round(1))

print("\n=== 항공사별 평균 지연 (상위 10) ===")
carrier_delay = (
    df.groupby('AIRLINE')['ARR_DELAY']
    .mean()
    .sort_values(ascending=False)
    .head(10)
    .round(1)
)
print(carrier_delay)

print("\n=== 지연 원인별 평균 (분) ===")
delay_cols = [
    'DELAY_DUE_CARRIER',
    'DELAY_DUE_WEATHER',
    'DELAY_DUE_NAS',
    'DELAY_DUE_SECURITY',
    'DELAY_DUE_LATE_AIRCRAFT'
]
print(df[delay_cols].mean().round(1).sort_values(ascending=False))

# 시각화
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Flight Delay EDA — Kaggle Dataset', fontsize=14)

# 1. 지연시간 분포
ax = axes[0, 0]
delay_clipped = df['ARR_DELAY'].clip(-30, 180).dropna()
ax.hist(delay_clipped, bins=60, color='steelblue', edgecolor='none', alpha=0.8)
ax.axvline(0, color='red', linewidth=1, linestyle='--', label='정시')
ax.axvline(15, color='orange', linewidth=1, linestyle='--', label='15분')
ax.set_title('도착 지연 분포')
ax.set_xlabel('지연 (분)')
ax.set_ylabel('편수')
ax.legend(fontsize=9)

# 2. 지연 원인 비중
ax = axes[0, 1]
cause_means = df[delay_cols].mean().sort_values()
labels = ['항공사', '기상', 'NAS', '보안', '전편지연']
colors = ['#e07b54', '#5b9bd5', '#70ad47', '#ffc000', '#9e7cb9']
bars = ax.barh(labels, cause_means.values, color=colors, edgecolor='none')
ax.set_title('지연 원인별 평균 (분)')
ax.set_xlabel('분')
for bar, val in zip(bars, cause_means.values):
    ax.text(val + 0.1, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}', va='center', fontsize=9)

# 3. 월별 평균 지연
ax = axes[1, 0]
df['FL_DATE'] = pd.to_datetime(df['FL_DATE'])
df['MONTH'] = df['FL_DATE'].dt.month
monthly = df.groupby('MONTH')['ARR_DELAY'].mean()
ax.plot(monthly.index, monthly.values, marker='o', color='steelblue', linewidth=2)
ax.set_title('월별 평균 지연')
ax.set_xlabel('월')
ax.set_ylabel('평균 지연 (분)')
ax.set_xticks(range(1, 13))
ax.grid(axis='y', alpha=0.3)

# 4. 결항률
ax = axes[1, 1]
cancel_rate = df.groupby('AIRLINE')['CANCELLED'].mean().sort_values(ascending=False).head(8) * 100
ax.bar(range(len(cancel_rate)), cancel_rate.values, color='salmon', edgecolor='none')
ax.set_title('항공사별 결항률 (상위 8)')
ax.set_ylabel('%')
ax.set_xticks(range(len(cancel_rate)))
ax.set_xticklabels(cancel_rate.index, rotation=30, ha='right', fontsize=8)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(r"c:\workspaces\FlightOps\data\eda_summary.png", dpi=150, bbox_inches='tight')
plt.show()
print("\n그래프 저장 완료 → data/eda_summary.png")