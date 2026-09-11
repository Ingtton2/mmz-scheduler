# mmz-scheduler — 식당 직원 스케줄링 앱

식당 사장님이 매달 직원 근무 스케줄을 **자동으로 배치**하고, 완성본을 **QR 코드**로 직원에게 공유하는 웹앱.

- 원본 스펙: [`restaurant_schedule_app_spec.md`](restaurant_schedule_app_spec.md)
- 기술 스택 설명 (쉬운 버전): [`docs/architecture.md`](docs/architecture.md)
- **인터넷 배포 가이드 (처음 하는 사람용)**: [`docs/DEPLOY.md`](docs/DEPLOY.md)

## 로컬 실행 vs 배포

| | 데이터베이스 | 실행 |
|---|---|---|
| 로컬 개발 | SQLite (`backend/app.db`, 자동 생성) | 아래 "실행 방법" |
| 배포 | PostgreSQL (`DATABASE_URL` 환경변수) | Render(백엔드+DB) + Vercel(프론트) — `docs/DEPLOY.md` |

## 진행 상황

- [x] **1단계 — 프로젝트 뼈대 + 기술 스택 확정**
- [x] **2단계 — 서버·화면 첫 실행 + 데이터베이스 표 8종 생성**
- [x] **3단계 — 사장님용 직원 등록 화면** (등록/목록/삭제 동작)
- [x] **4단계 — 연차 정보 자동계산 + 연차 신청 관리 + 사전 휴무 신청** (사장님이 대신 입력, 기간 단위 시작일~종료일)
      - 연차: 그날 쉬고 근무일수도 줄어듦 (잔여연차 차감). 기간 겹치면 거부.
      - 사전 휴무 신청: 그날 배치 제외되지만 근무일수는 유지 (다른 날로 채움), 연차 차감 없음, 월 최대 20일
- [x] **5단계 — 요일별 필요 인원 설정** (기본값 일괄 적용 + 요일별 개별 조정)
- [~] **6단계 — 자동배치 엔진 (OR-Tools)** ← 지금 여기
      - 스펙 5 우선순위 순: 연차 고정 → **관리 책임자 최소 1인 출근(하드)** → 포지션×시간대 인원 →
        포지션 매칭 → 사장/점장 마감 고정·사장 주말 회피 → 일반직원 오픈/마감 공정 분배 → 부족분 경고
      - 필요 인원: 포지션(홀/주방) × 시간대(오픈/미들/마감)별. 홀은 미들 없음.
      - 근무 코드: 홀 FO/FC · 주방 BO/BM/BC (코드에 포지션이 드러남 — 겸직 직원도 그날 어디서 일하는지 바로 보임)
                  · 파트타임 "풀오마"(하루 종일) · 사장/점장 항상 마감 → FC 또는 BC
      - 겸직 사장님(홀+주방)은 마감을 홀(FC) 우선 배치, 주방(BC)은 홀 인원 충분/주방 부족 시만
      - 역할: 일반 직원 / 점장(정직원과 동일 관리, 근무일은 마감 고정) / 사장님
      - 정직원·점장 월 휴일(D/O) = 기본휴무 일수에 **고정(사실상 하드)** — 근무일수 미달 시 최우선 벌점 + 못 맞추면 명확한 경고
      - 파트타임 근무요일 제한/고정
      - 공정성 편차는 같은 포지션 그룹끼리 비교 (화면에 직원별 O/M/C/풀오마 분포 표시)
      - 6일 이상 연속 근무 회피 (소프트 — 인원 부족으로 불가피하면 허용하고 경고)
      - 남음: 홀오픈/홀마감 등 포지션별 커스텀 코드 · 런치/디너 · && 코드
- 참고: 연차·기본휴무는 정직원 + 점장(정직원)만. 기본휴무 기본값 8일.
- [x] **7단계 — 배치 결과 수동 수정** (표 셀 클릭 → 근무 코드 변경 → 저장, `PATCH /api/schedule/entries`)
- [x] **8단계 — QR 공유 + 직원 조회** (공유 버튼 → 고유 URL·QR PNG, `/schedule/{code}` 에서 로그인 없이 근무표 조회)
- [x] **보안 — 관리자 로그인** (`/admin` 전체가 토큰 기반 로그인으로 보호, `ADMIN_USER`/`ADMIN_PASS` 설정 시에만 켜짐)
- [x] **9단계 — 직원 셀프서비스 계정** (`/join` 가입 신청 → 사장님 승인(`/admin/accounts`) → `/staff-login` 이름+PIN 로그인 → `/me` 이하에서 본인 연차/사전휴무 신청(다음 달분만, 20일 마감) + 본인 스케줄 조회. 사장님 계정은 즉시 승인, PIN 분실 시 관리자가 초기화)

### 표준 테스트 직원으로 초기화

```bash
cd backend && .venv/bin/python scripts/seed_demo.py
```

→ 사장 2 · 파트타임 1 · 정직원 7(홀 전담1 / 홀겸주2 / 주방 전담4) + 필요 인원(홀2·주방3) 세팅.
그 뒤 `/admin/schedule` 에서 "자동배치 실행".

### DB 내용 확인

```bash
cd backend && .venv/bin/python scripts/show_db.py
```

→ 만들어진 표 8개 목록 + 각 표의 줄 수 + 직원 표 내용(한글)을 출력합니다.
API 문서 화면(http://localhost:8000/docs)에서 직접 눌러볼 수도 있습니다.

## 구성

```
backend/   파이썬 서버 (FastAPI + OR-Tools + SQLite) — 계산·저장·QR
frontend/  화면 (React + Vite + TypeScript + Tailwind) — 사장님용/직원용 UI
```

## 실행 방법 (2단계에서 사용 예정)

### 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

→ 서버: http://localhost:8000 , API 문서: http://localhost:8000/docs

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

→ 화면: http://localhost:5173
