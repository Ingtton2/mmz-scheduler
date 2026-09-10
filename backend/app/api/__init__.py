"""
API 엔드포인트(주소) 모음.

여기서 기능별 라우터를 하나(api_router)로 묶고,
app/main.py 가 이걸 "/api" 접두어로 앱에 연결합니다.

앞으로 추가될 라우터 (계획):
  routes_work_codes.py   근무 코드 설정          (스펙 10.2)
  routes_share.py        공유 URL + QR 발급       (스펙 7)
  routes_public.py       직원 조회 전용           (스펙 6.2)
"""

from fastapi import APIRouter

from app.api import (
    routes_dayoff,
    routes_leave,
    routes_public,
    routes_schedule,
    routes_staff,
    routes_staffing,
)

api_router = APIRouter()
api_router.include_router(routes_staff.router)
api_router.include_router(routes_leave.router)
api_router.include_router(routes_dayoff.router)
api_router.include_router(routes_staffing.router)
api_router.include_router(routes_schedule.router)
api_router.include_router(routes_public.router)
