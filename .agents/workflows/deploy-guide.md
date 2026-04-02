---
description: 리포트 자동 생성 및 GitHub Pages 웹 배포 (index.html 갱신 포함)
---
// turbo-all

1. 캐릭터 시뮬레이션을 실행하여 최신 데이터를 생성합니다.
   `python automated_run.py`

2. 마크다운 리포트를 기반으로 시각화용 HTML을 생성합니다.
   `python generate_html.py`

3. 생성된 HTML 파일을 루트의 index.html로 복사하여 웹 연동을 준비합니다.
   `cp Results/optimization_guide.html index.html`

4. 변경된 사항을 GitHub에 커밋하고 푸시합니다.
   `git add .`
   `git commit -m "Auto-deploy: Update simulation results and dashboard"`
   `git push origin main`
