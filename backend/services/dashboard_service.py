from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.transaction import Transaction, TransactionStatus
from backend.models.worker import Worker, WorkerStatus

STATUS_LABELS: dict[str, str] = {
    "SUCCESS": "成功",
    "RUNNING": "处理中",
    "PENDING": "待处理",
    "FAIL": "失败",
}


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _day_bounds(now: datetime) -> tuple[datetime, datetime]:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        return today_start, yesterday_start

    @staticmethod
    def _safe_rate(numerator: int, denominator: int) -> float:
        if not denominator:
            return 0.0
        return round(numerator / denominator * 100, 1)

    @staticmethod
    def _safe_avg_minutes(avg_ms: float | None) -> float:
        if not avg_ms:
            return 0.0
        return round(avg_ms / 60000, 1)

    async def _count_in_range(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Transaction.transaction_id)).where(
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
        )
        return result.scalar() or 0

    async def _count_status_in_range(
        self, status: TransactionStatus, start: datetime, end: datetime
    ) -> int:
        result = await self.db.execute(
            select(func.count(Transaction.transaction_id)).where(
                Transaction.created_at >= start,
                Transaction.created_at < end,
                Transaction.status == status,
            )
        )
        return result.scalar() or 0

    async def _avg_duration_in_range(
        self, start: datetime, end: datetime
    ) -> float:
        result = await self.db.execute(
            select(func.avg(Transaction.duration_ms)).where(
                Transaction.created_at >= start,
                Transaction.created_at < end,
                Transaction.duration_ms.isnot(None),
            )
        )
        avg_ms = result.scalar() or 0
        return self._safe_avg_minutes(avg_ms)

    async def get_dashboard_stats(self) -> dict:
        now = datetime.utcnow()
        today_start, yesterday_start = self._day_bounds(now)
        yesterday_end = today_start

        today_count = await self._count_in_range(today_start, now)
        yesterday_count = await self._count_in_range(yesterday_start, yesterday_end)

        success_today = await self._count_status_in_range(
            TransactionStatus.SUCCESS, today_start, now
        )
        success_yesterday = await self._count_status_in_range(
            TransactionStatus.SUCCESS, yesterday_start, yesterday_end
        )

        avg_duration_today = await self._avg_duration_in_range(today_start, now)
        avg_duration_yesterday = await self._avg_duration_in_range(
            yesterday_start, yesterday_end
        )

        online_workers = (
            await self.db.execute(
                select(func.count(Worker.worker_id)).where(
                    Worker.status == WorkerStatus.ONLINE
                )
            )
        ).scalar() or 0
        busy_workers = (
            await self.db.execute(
                select(func.count(Worker.worker_id)).where(
                    Worker.status == WorkerStatus.BUSY
                )
            )
        ).scalar() or 0

        device_load = 0
        if online_workers > 0:
            device_load = int(busy_workers / online_workers * 100)

        hourly_trend = []
        for h in range(8, 19):
            hour_start = today_start.replace(hour=h)
            hour_end = hour_start + timedelta(hours=1)
            count = await self._count_in_range(hour_start, hour_end)
            hourly_trend.append({"hour": h, "count": count})

        status_groups = [
            TransactionStatus.SUCCESS,
            TransactionStatus.RUNNING,
            TransactionStatus.PENDING,
            TransactionStatus.FAIL,
        ]
        status_distribution = []
        for status_enum in status_groups:
            count = await self._count_status_in_range(
                status_enum, today_start, now
            )
            status_distribution.append(
                {
                    "status": STATUS_LABELS[status_enum.value],
                    "count": count,
                }
            )

        recent_result = await self.db.execute(
            select(Transaction)
            .order_by(Transaction.created_at.desc())
            .limit(10)
        )
        recent_txns = recent_result.scalars().all()

        worker_ids = [t.worker_id for t in recent_txns if t.worker_id]
        workers_by_id: dict = {}
        if worker_ids:
            w_result = await self.db.execute(
                select(Worker).where(Worker.worker_id.in_(worker_ids))
            )
            for w in w_result.scalars().all():
                workers_by_id[w.worker_id] = w

        recent_list = []
        for t in recent_txns:
            worker = workers_by_id.get(t.worker_id) if t.worker_id else None
            recent_list.append(
                {
                    "transaction_id": t.transaction_id,
                    # business_type & status are VARCHAR-backed (see models/*),
                    # so the attribute comes back as a plain str.
                    "business_type": t.business_type,
                    "status": t.status,
                    "customer_phone_encrypted": t.customer_phone_encrypted,
                    "duration_ms": t.duration_ms,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "worker": (
                        {"hostname": worker.hostname} if worker else None
                    ),
                }
            )

        return {
            "today_count": today_count,
            "yesterday_count": yesterday_count,
            "success_rate": self._safe_rate(success_today, today_count),
            "yesterday_success_rate": self._safe_rate(
                success_yesterday, yesterday_count
            ),
            "avg_duration_minutes": avg_duration_today,
            "yesterday_avg_duration_minutes": avg_duration_yesterday,
            "device_load": device_load,
            "online_devices": online_workers,
            "busy_devices": busy_workers,
            "hourly_trend": hourly_trend,
            "status_distribution": status_distribution,
            "recent_transactions": recent_list,
        }
