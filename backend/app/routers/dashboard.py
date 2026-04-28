# backend/app/routers/dashboard.py

from fastapi        import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database                  import get_db
from app.models.user               import User
from app.services.dashboard_service import DashboardService
from app.utils.dependencies        import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main dashboard — returns:
    - Account & wallet balance
    - Monthly stats
    - Recent transactions
    """
    return DashboardService.get_dashboard(db, current_user.id)