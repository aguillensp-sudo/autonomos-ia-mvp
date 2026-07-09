from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from src.api.routers import health, p04  # noqa: E402  (must load env before importing routers)

app = FastAPI(title="Autónomos IA MVP — P04 API")

app.include_router(health.router)
app.include_router(p04.router)
