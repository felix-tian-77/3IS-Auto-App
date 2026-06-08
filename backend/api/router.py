from fastapi import APIRouter
from backend.api.v1 import transactions, workers, downloads

api_router = APIRouter()
api_router.include_router(transactions.router, prefix="", tags=["transactions"])
api_router.include_router(workers.router, prefix="", tags=["workers"])
api_router.include_router(downloads.router, prefix="", tags=["downloads"])