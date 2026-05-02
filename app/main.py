from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.routers import auth, categories, products, uploads, users, orders, dashboard, payments, addresses, reviews, company_profiles, wallet, referrals, reports, contact, coupons

app = FastAPI(title="ClayBag API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers both with and without /api prefix
# This allows the app to work behind ALB (/api/*) and locally (/*)
all_routers = [auth, categories, products, uploads, users, orders, dashboard, payments, addresses, reviews, company_profiles, wallet, referrals, reports, contact, coupons]

for r in all_routers:
    app.include_router(r.router)
    app.include_router(r.router, prefix="/api")

# Serve uploaded images at /media (separate from /uploads API router)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/")
@app.get("/api")
def root():
    return {"status": "ClayBag API running", "docs": "/docs"}
