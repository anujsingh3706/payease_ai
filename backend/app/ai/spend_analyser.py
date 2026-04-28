# backend/app/ai/spend_analyser.py

"""
SPEND ANALYSER
──────────────
Uses NLP (keyword matching + TF-IDF) to auto-categorise transactions.
Then clusters spending into visual categories.

Categories:
  - Food & Dining       (zomato, swiggy, restaurant, cafe, food)
  - Shopping            (amazon, flipkart, myntra, mall, store)
  - Travel              (uber, ola, flight, railway, irctc, fuel)
  - Entertainment       (netflix, hotstar, prime, movie, gaming)
  - Utilities           (electricity, water, gas, broadband, phone)
  - Healthcare          (hospital, pharmacy, doctor, medicine, lab)
  - Education           (tuition, course, udemy, school, college)
  - Finance             (emi, insurance, loan, mutual fund, sip)
  - Salary / Income     (salary, credit, neft received)
  - Transfer            (transfer, sent, upi)
  - Others              (anything not matched)
"""

from typing   import List, Dict, Optional
from datetime import datetime, timedelta
from decimal  import Decimal
import re
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "zomato", "swiggy", "food", "restaurant", "cafe", "pizza",
        "burger", "biryani", "hotel", "dhaba", "kitchen", "eat",
        "lunch", "dinner", "breakfast", "snack", "bakery", "juice",
        "dominos", "mcdonalds", "kfc", "subway", "barbeque"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho",
        "mall", "store", "shop", "cloth", "dress", "shirt", "shoes",
        "electronics", "mobile", "laptop", "fashion", "retail",
        "snapdeal", "jiomart", "reliance", "dmart", "bigbasket"
    ],
    "Travel": [
        "uber", "ola", "rapido", "auto", "cab", "taxi", "flight",
        "railway", "irctc", "bus", "ticket", "fuel", "petrol", "diesel",
        "airport", "metro", "train", "redbus", "makemytrip", "goibibo",
        "oyo", "hotel", "hostel", "booking"
    ],
    "Entertainment": [
        "netflix", "hotstar", "prime", "amazon prime", "zee5", "sony",
        "movie", "cinema", "pvr", "inox", "gaming", "spotify", "youtube",
        "subscription", "entertainment", "concert", "event", "show"
    ],
    "Utilities": [
        "electricity", "electric", "bescom", "mseb", "water", "gas",
        "lpg", "broadband", "internet", "airtel", "jio", "bsnl", "vi",
        "phone", "recharge", "bill", "postpaid", "prepaid", "dth", "tata sky"
    ],
    "Healthcare": [
        "hospital", "clinic", "doctor", "medicine", "pharmacy", "medical",
        "apollo", "fortis", "medplus", "netmeds", "1mg", "health",
        "lab", "test", "scan", "dental", "eye", "insurance claim",
        "diagnostic", "pathology"
    ],
    "Education": [
        "school", "college", "university", "tuition", "coaching",
        "course", "udemy", "coursera", "fee", "education", "book",
        "stationery", "exam", "certification", "institute", "study"
    ],
    "Finance & Investment": [
        "emi", "loan", "insurance", "premium", "sip", "mutual fund",
        "investment", "stock", "zerodha", "groww", "upstox", "ppf",
        "fd", "fixed deposit", "nsc", "rd", "lic", "hdfc life"
    ],
    "Transfer": [
        "transfer", "sent", "neft", "rtgs", "imps", "upi", "paid to",
        "payment to", "wallet transfer"
    ],
    "Salary & Income": [
        "salary", "wage", "income", "credit", "received", "refund",
        "cashback", "reward", "bonus", "incentive", "dividend"
    ]
}


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-CATEGORISE A TRANSACTION
# ─────────────────────────────────────────────────────────────────────────────

def categorise_transaction(description: str) -> str:
    """
    Categorise a transaction based on its description using keyword matching.
    Returns the category name.
    """
    if not description:
        return "Others"

    desc_lower = description.lower().strip()

    # Check each category's keywords
    best_category = "Others"
    best_score    = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in desc_lower)
        if score > best_score:
            best_score    = score
            best_category = category

    return best_category


def categorise_bulk(transactions: List[dict]) -> List[dict]:
    """Categorise a list of transactions"""
    for txn in transactions:
        if not txn.get("category") or txn["category"] == "Others":
            txn["category"] = categorise_transaction(
                txn.get("description", "")
            )
    return transactions


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY SPEND SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def build_spend_summary(transactions: List[dict]) -> dict:
    """
    Build a comprehensive spend summary from a list of transactions.

    Input: list of transaction dicts with keys:
           amount, transaction_type, description, category, initiated_at

    Output: category breakdown, trends, insights
    """
    if not transactions:
        return {
            "total_spent":    0,
            "total_received": 0,
            "categories":     {},
            "insights":       ["No transaction data available"],
            "top_category":   None
        }

    total_spent    = 0.0
    total_received = 0.0
    categories: Dict[str, float] = {}
    daily_spend: Dict[str, float] = {}

    for txn in transactions:
        amount = float(txn.get("amount", 0))
        txn_type = txn.get("transaction_type", "").lower()
        category = txn.get("category") or categorise_transaction(
            txn.get("description", "")
        )
        date_str = str(txn.get("date", txn.get("initiated_at", "")))[:10]

        is_debit = txn_type in ["debit", "transfer", "payment", "wallet_topup"]
        is_credit = txn_type in ["credit", "wallet_topup"]

        if is_debit:
            total_spent += amount
            categories[category] = categories.get(category, 0) + amount
            daily_spend[date_str] = daily_spend.get(date_str, 0) + amount
        elif is_credit:
            total_received += amount

    # Sort categories by spend
    sorted_cats = dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))
    top_category = list(sorted_cats.keys())[0] if sorted_cats else None

    # ── Generate AI Insights ──────────────────────────────────────────────────
    insights = generate_spend_insights(
        categories, total_spent, total_received, daily_spend
    )

    # ── Category percentages ──────────────────────────────────────────────────
    cat_with_pct = {}
    for cat, amt in sorted_cats.items():
        cat_with_pct[cat] = {
            "amount":     round(amt, 2),
            "percentage": round((amt / max(total_spent, 1)) * 100, 1)
        }

    # ── Top spending days ─────────────────────────────────────────────────────
    top_days = sorted(daily_spend.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total_spent":     round(total_spent, 2),
        "total_received":  round(total_received, 2),
        "net_flow":        round(total_received - total_spent, 2),
        "savings_rate":    round(
            (total_received - total_spent) / max(total_received, 1) * 100, 1
        ),
        "categories":      cat_with_pct,
        "top_category":    top_category,
        "top_spend_days":  [{"date": d, "amount": round(a, 2)} for d, a in top_days],
        "insights":        insights,
        "total_transactions": len(transactions)
    }


# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_spend_insights(
    categories: dict,
    total_spent: float,
    total_received: float,
    daily_spend: dict
) -> List[str]:
    """
    Generate human-readable financial insights from spend data.
    These are the kind of tips a financial advisor would give.
    """
    insights = []

    if not categories:
        return ["No spending data to analyse."]

    # ── Insight 1: Top category ───────────────────────────────────────────────
    if categories:
        top_cat    = max(categories, key=categories.get)
        top_amount = categories[top_cat]
        top_pct    = (top_amount / max(total_spent, 1)) * 100
        insights.append(
            f"🏆 Highest spend: {top_cat} at ₹{top_amount:,.0f} "
            f"({top_pct:.0f}% of total spending)"
        )

    # ── Insight 2: Food spending alert ───────────────────────────────────────
    food_spend = categories.get("Food & Dining", 0)
    if food_spend > 0 and total_spent > 0:
        food_pct = (food_spend / total_spent) * 100
        if food_pct > 30:
            insights.append(
                f"🍔 Food & Dining is {food_pct:.0f}% of spending. "
                "Consider meal planning to save ₹2,000-₹5,000/month."
            )

    # ── Insight 3: Entertainment alert ───────────────────────────────────────
    ent_spend = categories.get("Entertainment", 0)
    if ent_spend > 2000:
        insights.append(
            f"🎬 Entertainment spend: ₹{ent_spend:,.0f}. "
            "Check for unused subscriptions."
        )

    # ── Insight 4: Savings rate ───────────────────────────────────────────────
    if total_received > 0:
        savings_rate = (total_received - total_spent) / total_received * 100
        if savings_rate < 10:
            insights.append(
                f"⚠️ Savings rate: {savings_rate:.0f}%. "
                "Experts recommend saving at least 20% of income."
            )
        elif savings_rate >= 30:
            insights.append(
                f"🌟 Excellent! Savings rate of {savings_rate:.0f}%. "
                "Consider investing the surplus in SIP/FD."
            )

    # ── Insight 5: Finance obligations ───────────────────────────────────────
    finance_spend = categories.get("Finance & Investment", 0)
    if finance_spend > 0 and total_received > 0:
        finance_pct = (finance_spend / total_received) * 100
        if finance_pct > 50:
            insights.append(
                f"🏦 EMI/loans consuming {finance_pct:.0f}% of income. "
                "This is above the 50% safe limit."
            )

    # ── Insight 6: Shopping patterns ─────────────────────────────────────────
    shopping_spend = categories.get("Shopping", 0)
    if shopping_spend > 10000:
        insights.append(
            f"🛍️ Shopping spend: ₹{shopping_spend:,.0f}. "
            "Make a wishlist and wait 48 hrs before buying to avoid impulse purchases."
        )

    # ── Insight 7: Investment nudge ───────────────────────────────────────────
    invest_spend = categories.get("Finance & Investment", 0)
    if invest_spend < 1000 and total_received > 20000:
        insights.append(
            "💡 Consider starting a SIP with just ₹500/month — "
            "₹500/month for 20 years @ 12% = ₹4.99 Lakhs!"
        )

    if not insights:
        insights.append("✅ Your spending looks healthy! Keep it up.")

    return insights


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def compare_monthly_spend(
    current_month: dict,
    previous_month: dict
) -> dict:
    """Compare spending between two months"""
    comparisons = {}

    all_cats = set(list(current_month.keys()) + list(previous_month.keys()))
    for cat in all_cats:
        curr = current_month.get(cat, 0)
        prev = previous_month.get(cat, 0)
        if prev > 0:
            change_pct = ((curr - prev) / prev) * 100
        else:
            change_pct = 100.0 if curr > 0 else 0.0

        comparisons[cat] = {
            "current":    round(curr, 2),
            "previous":   round(prev, 2),
            "change_pct": round(change_pct, 1),
            "trend":      "↑ Increased" if change_pct > 5 else (
                          "↓ Decreased" if change_pct < -5 else "→ Stable"
            )
        }

    return comparisons