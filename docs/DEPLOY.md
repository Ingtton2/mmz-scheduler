# 인터넷에 배포하기 — 처음부터 끝까지

이 문서는 **한 번도 배포를 안 해본 사람** 기준입니다. 순서대로 따라 하면 됩니다.
막히면 그 단계 번호를 알려주세요.

소요 시간: 처음이면 넉넉히 1~2시간. 계정 3개 만들고 클릭 몇 번이 대부분입니다.
**돈 안 듭니다** (전부 무료 플랜). 카드 등록도 필요 없습니다.

---

## 0. 큰 그림

```
   [직원 휴대폰]
       │  QR 스캔 → https://내앱.vercel.app/schedule/abc123
       ▼
  ┌─────────────┐    /api 요청     ┌──────────────┐     ┌────────────┐
  │  Vercel     │ ───────────────▶ │  Render      │ ──▶ │ PostgreSQL │
  │ (프론트엔드) │                  │ (백엔드 서버) │     │ (Render)   │
  │  화면·표     │                  │ 자동배치·저장 │     │  데이터     │
  └─────────────┘                  └──────────────┘     └────────────┘
```

- **GitHub**: 코드 보관소. Render·Vercel이 여기서 코드를 가져갑니다.
- **Render**: 백엔드(파이썬 서버) + 데이터베이스를 돌립니다.
- **Vercel**: 프론트엔드(화면)를 돌립니다.

각각 무료 계정 하나씩 만들면 됩니다. GitHub 계정으로 Render·Vercel에 로그인할 수 있어서 편합니다.

---

## 1. GitHub — 코드 올리기

### 1-1. 계정 만들기
1. https://github.com 접속 → **Sign up**
2. 이메일 / 비밀번호 / 사용자이름 입력 → 이메일 인증
3. 무료 플랜(Free) 선택

### 1-2. 이 코드를 GitHub에 올리기

이미 이 프로젝트에는 GitHub 저장소가 연결돼 있습니다
(`https://github.com/Ingtton2/mmz-scheduler`). 코드는 로컬에 **커밋까지 완료**된
상태이니, 아래 한 줄만 실행하면 올라갑니다.

터미널에서 프로젝트 폴더(`mmz-scheduler`)로 이동한 뒤:

```bash
git push -f origin main
```

> `-f`(강제)를 쓰는 이유: 기존 저장소에는 예전 테스트 파일(`index.html`)만
> 들어 있어서 새 코드로 통째로 덮어씁니다. 혼자 쓰는 저장소라 안전합니다.
>
> 처음이면 GitHub 로그인 창이 뜹니다. 브라우저에서 승인하거나,
> "Personal access token"을 만들어 비밀번호 대신 붙여넣으면 됩니다
> (GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
> → Generate new token → `repo` 체크 → 생성 → 복사).

**다른 저장소에 올리고 싶다면**: GitHub에서 **New repository** → 이름 입력 →
Create → 나오는 안내 중 `git remote add origin ...` 대신 아래처럼:

```bash
git remote set-url origin https://github.com/<내아이디>/<저장소이름>.git
git push -u origin main
```

### 1-3. 확인
브라우저에서 저장소 페이지를 새로고침 → `backend/`, `frontend/`, `render.yaml`,
`docs/` 등이 보이면 성공.

---

## 2. Render — 백엔드 + 데이터베이스

### 2-1. 계정 만들기
1. https://render.com → **Get Started** → **GitHub로 로그인** (권장)
2. Render가 GitHub 저장소 접근 권한을 요청 → 승인 (원하면 이 저장소만 선택)

### 2-2. Blueprint로 한 번에 만들기

이 프로젝트 루트에 `render.yaml` 이 있어서, 백엔드 서버와 PostgreSQL을
**한 번에** 만들 수 있습니다.

1. Render 대시보드 → 우측 상단 **New +** → **Blueprint**
2. 방금 연결한 `mmz-scheduler` 저장소 선택 → **Connect**
3. Render가 `render.yaml`을 읽어 만들 항목을 보여줍니다:
   - `mmz-scheduler-db` (PostgreSQL, Free)
   - `mmz-scheduler-api` (Web Service, Free)
4. **Apply** 클릭
5. 몇 분 기다리면 배포가 끝납니다 (첫 배포는 파이썬 라이브러리 설치라 5~10분 걸림).
   `mmz-scheduler-api` 상태가 **Live** 가 되면 완료.

### 2-3. 백엔드 주소 확인
`mmz-scheduler-api` 서비스 페이지 상단에 주소가 있습니다:
```
https://mmz-scheduler-api.onrender.com
```
(끝의 임의 문자열은 다를 수 있음)

이 주소 뒤에 `/health` 를 붙여 브라우저로 열어보세요:
```
https://mmz-scheduler-api.onrender.com/health
→ {"status":"ok","app":"mmz-scheduler"}
```
이게 뜨면 백엔드 + DB 정상. **이 주소를 메모해두세요.** 3단계에서 씁니다.

> ⚠️ 무료 플랜은 **15분간 아무도 안 쓰면 서버가 잠듭니다.** 다음 접속 시
> 깨어나느라 30초~1분 걸립니다(그 뒤엔 빠름). 실사용엔 지장 없지만
> "느리다"고 느낄 수 있어요. 유료($7/월)로 올리면 안 잠듭니다.

---

## 3. Vercel — 프론트엔드

### 3-1. 계정 만들기
1. https://vercel.com → **Sign Up** → **Continue with GitHub**
2. 권한 승인

### 3-2. `vercel.json` 에 백엔드 주소 넣기 (중요)

프론트엔드가 `/api` 요청을 어디로 보낼지 알려줘야 합니다.

1. 파일 `frontend/vercel.json` 을 엽니다.
2. 이 줄의 주소를 **2단계에서 메모한 Render 백엔드 주소**로 바꿉니다:
   ```json
   "destination": "https://mmz-scheduler-api.onrender.com/api/:path*"
   ```
   →
   ```json
   "destination": "https://<내-Render-주소>.onrender.com/api/:path*"
   ```
3. 저장하고 GitHub에 다시 올립니다:
   ```bash
   git add frontend/vercel.json
   git commit -m "set backend url for vercel"
   git push origin main
   ```

### 3-3. Vercel에 프로젝트 만들기
1. Vercel 대시보드 → **Add New...** → **Project**
2. `mmz-scheduler` 저장소 → **Import**
3. 설정 화면에서:
   - **Root Directory**: `frontend` 로 지정 (Edit 눌러서 `frontend` 선택)
   - Framework Preset: `Vite` (자동으로 잡힘)
   - Build/Output: 그대로 두면 됨
   - Environment Variables: **비워둡니다** (필요 없음)
4. **Deploy** 클릭 → 1~2분 뒤 완료

### 3-4. 프론트엔드 주소 확인
배포가 끝나면 주소가 나옵니다:
```
https://mmz-scheduler.vercel.app
```
열어보면 관리자 화면이 뜹니다. 단, 아직 백엔드와 **CORS 연결**이 안 돼서
"직원 목록 불러오기 실패" 같은 에러가 날 수 있습니다 → 4단계에서 해결.

**이 주소를 메모해두세요.**

---

## 4. 서로 연결하기 (환경변수)

백엔드가 "이 프론트엔드 주소는 믿어도 된다"는 걸 알아야 합니다.

1. Render 대시보드 → `mmz-scheduler-api` → 왼쪽 **Environment**
2. **Add Environment Variable** 로 아래 2개를 추가:

   | Key | Value |
   |---|---|
   | `FRONTEND_ORIGINS` | `https://mmz-scheduler.vercel.app` (3단계 주소) |
   | `PUBLIC_BASE_URL` | `https://mmz-scheduler.vercel.app` (똑같이) |

   > `FRONTEND_ORIGINS` : 이 주소에서 오는 요청을 허용 (CORS).
   > `PUBLIC_BASE_URL`  : QR 코드에 넣을 주소 (직원이 스캔하면 여기로 감).

3. **Save Changes** → Render가 자동으로 재배포합니다 (1~2분).

4. 다시 `https://mmz-scheduler.vercel.app` 를 열면 정상 동작합니다.

---

## 5. 실제로 써보기

1. `https://mmz-scheduler.vercel.app/admin/staff` → 직원 몇 명 등록
2. `/admin/staffing` → 필요 인원 설정 (기본값 그대로 저장해도 됨)
3. `/admin/schedule` → 연/월 고르고 **자동배치 실행**
4. 필요하면 표의 칸을 클릭해 수정 → **수정 저장**
5. **공유 (QR)** 클릭 → QR 코드가 나옴
6. 휴대폰 카메라로 그 QR을 스캔 → 브라우저에 그 달 근무표가 뜸 (로그인 없음)
   - "미리보기 ↗" 버튼으로 PC에서도 직원 화면을 확인할 수 있습니다.

QR은 캡처해서 인쇄하거나 단톡방에 올리면 됩니다.

---

## 6. 자주 겪는 문제

| 증상 | 원인 / 해결 |
|---|---|
| 화면은 뜨는데 "불러오기 실패" | 4단계 `FRONTEND_ORIGINS` 를 안 넣었거나 주소 오타. Render Environment 확인 후 Save(재배포). |
| 첫 접속이 30초~1분 걸림 | 정상. Render 무료 서버가 잠들었다 깨는 중. 두 번째부터 빠름. |
| QR을 찍으면 `localhost:5173` 로 감 | 4단계 `PUBLIC_BASE_URL` 을 Vercel 주소로 안 바꿈. 고치고 재배포 후 **스케줄을 다시 공유**. |
| `/api` 요청이 404 | 3-2에서 `vercel.json` 의 백엔드 주소를 안 바꿨거나, Root Directory 를 `frontend` 로 안 함. |
| Render 빌드 실패 (`ortools` 등) | `render.yaml` 의 `PYTHON_VERSION: 3.12.8` 확인. 그래도 안 되면 3.11.9 로 낮춰보기. |
| 새로고침하면 페이지가 404 | `frontend/vercel.json` 이 저장소에 올라갔는지 확인 (SPA 라우팅 설정). |
| 코드를 고쳤는데 배포에 반영 안 됨 | `git push origin main` 을 했는지 확인. Render·Vercel은 push 하면 자동 재배포됩니다. |

---

## 7. 알아둘 무료 플랜 한계

- **Render 웹서비스**: 15분 idle 시 잠듦(첫 요청 느림). 월 750시간 무료.
- **Render PostgreSQL**: 무료 DB는 **만든 지 90일 뒤 만료**됩니다. 만료 전에
  새 무료 DB를 만들고 `DATABASE_URL` 을 갈아끼우면 됩니다(데이터는 옮겨야 함).
  계속 쓸 거면 유료 DB($7/월)나 [Neon](https://neon.tech)·[Supabase](https://supabase.com)
  같은 무료 Postgres로 옮기는 걸 추천.
- **Vercel**: 개인 프로젝트는 넉넉합니다. 신경 쓸 것 거의 없음.

---

## 8. 관리자 화면 잠그기 (반드시 설정하세요)

`ADMIN_USER`/`ADMIN_PASS` 를 설정하지 않으면 `https://내앱.vercel.app/admin/...`
주소를 아는 사람은 **누구나** 직원을 추가/삭제할 수 있습니다. 실제로 서비스한다면
꼭 설정하세요. 직원 조회용(`/schedule/코드`)은 로그인 여부와 상관없이 항상 열려 있습니다.

1. Render → `mmz-scheduler-api` → 왼쪽 **Environment** → **Add Environment Variable**:

   | Key | Value |
   |---|---|
   | `ADMIN_USER` | 원하는 아이디 (예: `boss`) |
   | `ADMIN_PASS` | 원하는 비밀번호 (충분히 길게) |

2. **Save Changes** → 자동 재배포 (1~2분).

3. 재배포가 끝난 뒤 `https://내앱.vercel.app/admin` 에 들어가면 로그인 화면이
   먼저 뜹니다. 방금 만든 아이디/비밀번호를 입력하면 관리자 화면이 열립니다.
   (브라우저 팝업이 아니라 앱 안의 로그인 페이지입니다. 로그인은 7일간 유지되고,
   헤더의 "로그아웃" 버튼으로 언제든 끝낼 수 있습니다.)

> 지금 단계는 사장님 1명을 위한 간단한 공용 비밀번호입니다. 직원별 계정
> (전화번호 인증 등)은 스펙 9번 "직원 셀프서비스 계정" 단계에서 별도로 추가됩니다.
