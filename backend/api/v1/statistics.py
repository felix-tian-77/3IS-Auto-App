from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.database import get_db
from backend.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/statistics/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    service = DashboardService(db)
    return await service.get_dashboard_stats()
