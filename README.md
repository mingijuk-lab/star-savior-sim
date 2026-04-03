# Star Savior DPS Simulation System (v29.0)

스타 세이비어 캐릭터들의 성능을 최신 데미지 공식 및 기믹에 따라 정밀하게 시뮬레이션하고 최적화하기 위한 통합 엔진입니다.

> **최종 갱신**: 2026-04-03

## 🚀 주요 기능

### 1. 턴 기반 정밀 DPS 시뮬레이션
- **5개 여정(Journey) + 축복(Blessing)** 조합 전수 탐색으로 캐릭터별 최적 빌드 도출
- **Standard(궁극기 사용)** / **No-Ult(AX 스택 특화)** 두 가지 전략을 병렬 비교
- 5턴/10턴/15턴 구간별 DPS 추적

### 2. 하이-피델리티 메커니즘 구현
- **프레이**: HR(하이롤) + 냉각(Cooling) 독립 스택, 달속성파티 동맹 HR 가속, 강제 협상(DI +100%)
- **로자리아**: 업화(Ignition) 확률 누적 + 발화(3스택 추가 기본기), 궁극기 AG+50%
- **유미나**: 출혈 DOT, 치명타→행게+15%, 카탈리스트(경력직 용병) AoE 기본기
- **샤를(바니걸)**: 점화 스택 기반 궁극기 DI + 쿨타임 초기화
- **클레어(바니걸)**: 냉각 5→특수기 추가타, 턴당 치확+10% 패시브

### 3. 빌드 진화 경로 (Scaling Profile)
- 부옵션 0%~50% 성장에 따른 실시간 최적 빌드(장비+여정+축복) 변화 추적
- 공격력%/치피/치확 3개 스탯별 전환점 포착 + DPS/MaxHit 수치 표기

### 4. 방어력 통합 계산
- DEF Penetration + DEF Reduction(스마일 궁극기 30%) 반영
- 유효 방어력 기반 실전 DPS 산출

### 5. GitHub Pages 인터랙티브 대시보드
- PyScript 기반 브라우저 내 실시간 시뮬레이터 (커스텀 부옵 입력)
- 캐릭터 검색, 카드 펼치기/접기, 전략 탭 전환

## 📁 프로젝트 구조

```text
📁 Star/
│
├── 📁 Core/ (핵심 엔진 — 모든 파일 _v5 접미사)
│   ├── 📄 models_v5.py              ← 데이터 도메인 모델 (StatType, Modifier, Character, Journey)
│   ├── 📄 data_loader_v5.py         ← JSON/MD 데이터 로더 (4+2 조합, 여정, 축복 파서)
│   ├── 📄 calc_engine_v5.py         ← [핵심] 턴 기반 DPS 시뮬레이션 + 5여정 최적화 엔진
│   └── 📄 gear_sensitivity_v5.py    ← 부옵션 성장 Scaling Profile 분석기
│
├── 📁 Data/ (마스터 데이터)
│   ├── 📄 characters.json           ← [엔진용] 캐릭터 스탯/스킬/패시브 통합 데이터
│   ├── 📄 equipments.json           ← 장비(4+2), 여정(12+), 축복(AX/FX/EX/속도) 통합 데이터
│   ├── 📄 캐릭터_스펙_마스터.md      ← [작성용] 캐릭터별 상세 스탯·스킬 계수
│   └── 📄 사이클_로테이션_마스터.md   ← [엔진/감사용] 턴별 행동·버프 테이블 + JSON
│
├── 📁 Docs/ (참조 문서)
│   ├── 📄 파일_관리_인덱스.md        ← 파일 구조 + 상황별 업데이트 가이드
│   ├── 📄 시뮬레이션_가이드라인_v14.md ← 통합 시뮬레이션 규칙 마스터
│   ├── 📄 아르카나_엔진_구현_가이드.md ← 여정/축복 ↔ 엔진 변수 매핑
│   ├── 📄 공식_디테일_가이드.md       ← 대미지 공식 상세
│   ├── 📄 시각화_가이드.md            ← HTML 대시보드 파이프라인
│   └── 📄 여정 특수 잠재.md           ← AX/FX/EX 상세 레퍼런스
│
├── 📁 Results/ (분석 결과)
│   ├── 📄 dps_results.csv            ← 시뮬 로우 데이터
│   ├── 📄 optimization_guide.md      ← [최종 리포트] 캐릭터별 최적 빌드 가이드
│   └── 📄 optimization_guide.html    ← HTML 대시보드
│
├── 📁 Tools/ (유틸리티)
│   ├── 📄 extract_characters.py      ← MD → characters.json 추출기
│   ├── 📄 update_rotations.py        ← characters.json → 로테이션 MD 자동 생성기
│   └── 📄 generate_saviors.py        ← 공식 데이터 → 스펙 마스터 초기 엔트리 생성기
│
├── 📄 automated_run.py               ← 부옵 0 기본값 자동 시뮬 실행기
├── 📄 generate_html.py               ← MD → HTML 변환기 (PyScript 포함)
├── 📄 verify_engine.py               ← 엔진 스택 로직 검증 스크립트
└── 📄 index.html                     ← GitHub Pages 배포용
```

## 🛠️ 사용 방법

### 0. 환경 설정
```bash
pip install -r requirements.txt  # pandas
```

### 1. 데이터 동기화 (캐릭터 스펙 변경 시)
```bash
# 스펙 마스터 MD → characters.json 추출
python Tools/extract_characters.py

# characters.json → 로테이션 MD 자동 생성
$env:PYTHONPATH="."; python Tools/update_rotations.py
```

### 2. 최적 빌드 시뮬레이션 (대화형)
```bash
# 부옵션 직접 입력
$env:PYTHONPATH="."; python -m Core.calc_engine_v5
```

### 3. 자동 시뮬레이션 (기본값)
```bash
# 부옵 0 기본값으로 자동 실행
$env:PYTHONPATH="."; python automated_run.py
```

### 4. HTML 대시보드 생성
```bash
python generate_html.py
# → Results/optimization_guide.html + index.html 생성
```

### 5. 엔진 검증
```bash
$env:PYTHONPATH="."; python verify_engine.py
```

## 📊 현재 등록 캐릭터 (18명)

| 캐릭터 | 분류 | 주요 메커니즘 |
|--------|------|-------------|
| 프레이 | 캐스터 | HR + 냉각 스택, 달속성파티 변형(3종) |
| 로자리아 | 레인저 | 업화 + 격동, 추가 기본기 (패시브1lv 변형) |
| 유미나 | 레인저 | 도약 스택, 출혈 DOT, 치명타→AG (패시브1lv 변형) |
| 힐데 | 디펜더 | 점화 스택, 체력 계수 |
| 루나 | 캐스터 | 궁극기 치피+20% |
| 리디아 | 레인저 | 약화 상태 공격력+6%×5 |
| 릴리 | 캐스터 | 행게+10%, 토끼씨 수사자문 |
| 뮤리엘 | 캐스터 | 연소, 전체 공격 |
| 샤를 | 스트라이커 | 럭키 토큰, 점화 |
| 스마일 | 레인저 | 방감30%, 트리거 특수기 |
| 스칼렛(바니걸) | 레인저 | 세븐볼, 치확+15% |
| 아세라 | 스트라이커 | 특수기당 치피+6%×5 |
| 에핀델 | 어쌔신 | 냉각5 DI+20% |
| 클레어(바니걸) | 스트라이커 | 냉각5→추가타, 턴당 치확+10%×3 |
| 키라 | 어쌔신 | 행게+10% (계수 미상) |
| 레이시 | 레인저 | 꿈결 DI+20% |
| 샤를(바니걸) | 어쌔신 | 점화 궁쿨 초기화 (3종 변형) |
| 벨리스 | 레인저 | 도약 스택, 전체 공격, 행게+50% |

## ⚠️ 환경 및 유의사항
- **Python 3.10+** 필요
- **PYTHONPATH**: 모듈 임포트를 위해 반드시 프로젝트 루트에서 `$env:PYTHONPATH="."`를 설정한 후 실행
- **핵심 파일은 _v5 접미사**: `calc_engine_v5.py`, `models_v5.py`, `data_loader_v5.py`, `gear_sensitivity_v5.py`
