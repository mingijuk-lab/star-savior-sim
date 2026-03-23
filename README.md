# Star Savior DPS Simulation System

이 프로젝트는 스타 세이비어 캐릭터들의 성능을 다양한 장비, 아르카나, 여정 조합에 따라 시뮬레이션하고 분석하기 위한 도구입니다.

## 주요 기능
- **상세 시뮬레이션**: 캐릭터의 스탯, 스킬 계수, 패시브, 아르카나 효과 등을 정밀하게 반영하여 DPS를 계산합니다.
- **최적성 분석**: 수천 가지의 조합 중 각 캐릭터에게 가장 적합한 상위 2개 조합을 추출합니다.
- **시각화 리더보드**: 계산 결과를 차트와 카드로 시각화하여 한눈에 비교할 수 있는 HTML 보고서를 생성합니다.

## 프로젝트 구조
- `Core/`: 핵심 계산 로직
  - `calc_dps.py` — DPS 시뮬레이션 엔진 (모듈화 구조)
  - `compare_builds.py` — 캐릭터별 빌드 비교 리포트 생성기
  - `generate_html.py` — 리더보드 HTML 생성
- `Data/`: 캐릭터 스펙 및 스킬 사이클 마스터 데이터 (`.md`)
- `Docs/`: 시뮬레이션 규칙 및 가이드라인
- `Results/`: 시뮬레이션 결과 (`.csv`, `.html`)

## 실행 방법
1. **시뮬레이션 수행**:
   ```bash
   python Core/calc_dps.py
   ```
   실행 후 `Results/dps_results.csv` 파일이 생성됩니다.

2. **리더보드 생성**:
   ```bash
   python Core/generate_html.py
   ```
   실행 후 `Results/dps_results.html` 파일이 생성됩니다. 이 파일을 브라우저로 열어 결과를 확인하세요.

## 환경 요구사항
- **Python 3.x**: 별도의 외부 라이브러리 설치 없이 실행 가능합니다 (표준 라이브러리만 사용).
- **웹 브라우저**: 결과 시각화 확인용 (Tailwind CSS, Chart.js CDN 사용).
