# path: app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Auth 路由（注意：各檔本身不再有 prefix="/auth"）
from app.routers.auth_guest import router as auth_guest_router
from app.routers.auth_refresh import router as auth_refresh_router

# 功能路由
from app.routers.me import router as me_router
from app.routers.checkins import router as checkins_router
from app.routers.runs import router as runs_router
from app.routers.trainings import router as trainings  # 👈 新增這行
from app.routers.store import router as store
from app.routers.inventory import router as inventory
from app.routers.achievements import router as achievements  # 👈 新增這行
from app.routers.challenges import router as challenges
from app.routers.training_plans import router as training_plans
from app.models.gym import Gym  # noqa
from app.routers.auth_google import router as auth_google  # noqa

app = FastAPI(title="Chicken Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 統一在這裡掛 /auth 前綴
app.include_router(auth_guest_router,   prefix="/auth")
app.include_router(auth_refresh_router, prefix="/auth")

# 其他功能
app.include_router(me_router)
app.include_router(checkins_router)
app.include_router(runs_router)
app.include_router(trainings)  # 👈 新增這行
app.include_router(store)
app.include_router(inventory)
app.include_router(achievements)  # 👈 新增這行
app.include_router(challenges)
app.include_router(training_plans)
app.include_router(auth_google)

@app.get("/")
def root():
    return {"ok": True}
