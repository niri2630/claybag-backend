from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.routers import auth, categories, products, uploads, users, orders, dashboard, payments, addresses, reviews

app = FastAPI(title="ClayBag API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (must be registered BEFORE static mount to avoid route shadowing)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(uploads.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
app.include_router(payments.router)
app.include_router(addresses.router)
app.include_router(reviews.router)

# Serve uploaded images at /media (separate from /uploads API router)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")


@app.get("/")
def root():
    return {"status": "ClayBag API running", "docs": "/docs"}
