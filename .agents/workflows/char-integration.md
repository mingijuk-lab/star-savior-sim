---
description: 신규 캐릭터 시뮬레이션 통합 (데이터 등록, 엔진 연동, UI 동기화)
---
// turbo-all

1. **캐릭터 데이터 등록 (Master Data)**
   - `Data/캐릭터_스펙_마스터.md`에 새로운 캐릭터 섹션을 추가합니다. (JSON 블록 필수)
   - `Data/사이클_로테이션_마스터.md`에 새로운 캐릭터 로테이션 섹션을 추가합니다. (JSON 블록 필수)

2. **데이터베이스 동기화 (Data Sync)**
   - 등록된 마스터 데이터를 JSON 파일 및 테이블 형식으로 동기화합니다.
   ```powershell
   python Tools/extract_characters.py
   python Tools/update_rotations.py
   ```

3. **시뮬레이션 엔진 로직 구현 (Engine Implementation)**
   - `Core/calc_engine_v5.py`에서 캐릭터의 고유 기믹(Passives, Multi-hit scaling, Special Buffs 등)을 구현합니다.
   - `omega_star` 등 새로운 상태 변수가 필요하면 `calculate_dps` 초기에 초기화합니다.

4. **웹 UI 동기화 (Web UI Sync)**
   - 로컬 엔진 코드와 캐릭터 데이터를 웹 시뮬레이션 환경(index.html VFS)에 반영합니다.
   ```powershell
   python Tools/sync_vfs.py
   ```
   - `index.html` 내 `buildCharTree` 함수에 새로운 파티 변형(예: 별속성 파티) 감지 로직이 필요한지 확인하고 업데이트합니다.

5. **성능 검증 (Verification)**
   - 캐릭터별 검증 스크립트(예: `verify_omega.py`)를 작성하여 의도한 DPS가 산출되는지 확인합니다.
   - `python verify_engine.py`를 실행하여 기존 캐릭터 성능에 회귀 오류가 없는지 확인합니다.

6. **배포 리포트 갱신 (Optional)**
   - 전체 리포트를 갱신하려면 다음 명령을 실행합니다.
   ```powershell
   python automated_run.py
   python generate_html.py
   ```
