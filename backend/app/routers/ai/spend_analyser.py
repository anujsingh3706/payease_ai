# backend/app/routers/ai/spend_analyser.py

from fastapi        import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy     import func, extract
from datetime       import datetime, timedelta
from typing         import Optional

from app.database            import get_db
from app.models.user         import User
from app.models.transaction  import Transaction, TransactionStatus
from app.ai.spend_analyser   import (
    build_spend_summary, categorise_transaction,
    compare_monthly_spend
)
from app.utils.dependencies  import get_current_user

router = APIRouter(prefix="/api/v1/ai/spend", tags=["📊 Spend Analyser"])


def txn_to_dict(t: Transaction) -> dict:
    return {
        "id":               str(t.id),
        "amount":           float(t.amount),
        "transaction_type": t.transaction_type.value,
        "description":      t.description or "",
        "category":         t.category,
        "date":             t.initiated_at.isoformat() if t.initiated_at else "",
        "initiated_at":     t.initiated_at
    }


# ── This Month Summary ────────────────────────────────────────────────────────

@router.get("/summary")
async def spend_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get this month's complete spending summary.

    Returns:
    - Spend by category (with percentages)
    - Total spent / received
    - Savings rate
    - AI-generated insights & tips
    - Top spending days
    """
    month_start = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= month_start
    ).all()

    txn_dicts = [txn_to_dict(t) for t in txns]

    # Auto-categorise any un-categorised transactions
    for i, txn in enumerate(txn_dicts):
        if not txn["category"] or txn["category"] == "Others":
            txn_dicts[i]["category"] = categorise_transaction(txn["description"])
            # Update DB
            txns[i].category = txn_dicts[i]["category"]

    db.commit()

    summary = build_spend_summary(txn_dicts)
    return {
        **summary,
        "period": f"{month_start.strftime('%B %Y')}",
        "generated_at": datetime.utcnow().isoformat()
    }


# ── Custom Date Range ─────────────────────────────────────────────────────────

@router.get("/summary/range")
async def spend_summary_range(
    from_date: datetime = Query(...),
    to_date:   datetime = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get spend summary for a custom date range"""

    if (to_date - from_date).days > 365:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Date range cannot exceed 1 year")

    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= from_date,
        Transaction.initiated_at <= to_date
    ).all()

    txn_dicts = [txn_to_dict(t) for t in txns]
    summary   = build_spend_summary(txn_dicts)

    return {
        **summary,
        "period": f"{from_date.strftime('%d %b')} – {to_date.strftime('%d %b %Y')}"
    }


# ── Month-on-Month Comparison ─────────────────────────────────────────────────

@router.get("/compare")
async def compare_months(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare this month vs last month spending.
    Shows which categories increased/decreased.
    """
    now         = datetime.utcnow()
    this_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_start  = (this_start - timedelta(days=1)).replace(day=1)
    last_end    = this_start

    def get_month_txns(start, end):
        return db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_status == TransactionStatus.SUCCESS,
            Transaction.initiated_at >= start,
            Transaction.initiated_at < end
        ).all()

    this_txns = get_month_txns(this_start, now)
    last_txns = get_month_txns(last_start, last_end)

    this_dicts = [txn_to_dict(t) for t in this_txns]
    last_dicts = [txn_to_dict(t) for t in last_txns]

    this_summary = build_spend_summary(this_dicts)
    last_summary = build_spend_summary(last_dicts)

    # Extract just amounts for comparison
    this_cats = {k: v["amount"] for k, v in this_summary["categories"].items()}
    last_cats = {k: v["amount"] for k, v in last_summary["categories"].items()}

    comparison = compare_monthly_spend(this_cats, last_cats)

    overall_change = 0
    if last_summary["total_spent"] > 0:
        overall_change = (
            (this_summary["total_spent"] - last_summary["total_spent"])
            / last_summary["total_spent"] * 100
        )

    return {
        "this_month":      this_summary["period"] if "period" in this_summary else now.strftime("%B"),
        "last_month":      last_start.strftime("%B %Y"),
        "this_total_spent": this_summary["total_spent"],
        "last_total_spent": last_summary["total_spent"],
        "overall_change_pct": round(overall_change, 1),
        "overall_trend":   "↑ You spent more" if overall_change > 5 else (
                           "↓ You spent less" if overall_change < -5 else "→ Similar spending"
        ),
        "category_comparison": comparison,
        "this_insights":   this_summary["insights"],
    }


# ── Auto-Categorise All Transactions ─────────────────────────────────────────

@router.post("/categorise-all")
async def categorise_all_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk auto-categorise all uncategorised transactions.
    Uses NLP keyword matching.
    """
    uncategorised = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.category.is_(None)
    ).all()

    count = 0
    for txn in uncategorised:
        txn.category = categorise_transaction(txn.description or "")
        count += 1

    db.commit()

    return {
        "message":      f"✅ Categorised {count} transactions",
        "total_updated": count
    }


# ── Category Drill-down ───────────────────────────────────────────────────────

@router.get("/category/{category_name}")
async def category_transactions(
    category_name: str,
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all transactions for a specific category"""
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

    txns = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.category == category_name,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= month_start
    ).order_by(Transaction.initiated_at.desc()).limit(limit).all()

    total = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.category == category_name,
        Transaction.transaction_status == TransactionStatus.SUCCESS,
        Transaction.initiated_at >= month_start
    ).scalar() or 0

    return {
        "category":    category_name,
        "total_spent": round(float(total), 2),
        "count":       len(txns),
        "transactions": [txn_to_dict(t) for t in txns]
    }