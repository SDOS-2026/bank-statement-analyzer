"""
semantic/categorizer.py


Architecture:
  - 3-tier matching: EXACT → SUBSTRING → REGEX (fastest → slowest)
  - Direction-aware: some categories only apply to debits or credits
  - Priority ordering: specific beats general (EMI beats TRANSFER)
  - All rules compiled once at import time (O(1) amortized per transaction)
  - Extensible: add rules without changing logic
"""

import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum


# ── Category taxonomy ─────────────────────────────────────────────────────────

class Category(str, Enum):
    # Income types
    SALARY          = "SALARY"
    BUSINESS_INCOME = "BUSINESS_INCOME"
    FREELANCE       = "FREELANCE"
    INTEREST        = "INTEREST"
    DIVIDEND        = "DIVIDEND"
    REFUND          = "REFUND"
    CASHBACK        = "CASHBACK"

    # Expense types
    FOOD            = "FOOD"
    GROCERIES       = "GROCERIES"
    TRANSPORT       = "TRANSPORT"
    FUEL            = "FUEL"
    UTILITIES       = "UTILITIES"
    TELECOM         = "TELECOM"
    RENT            = "RENT"
    EMI             = "EMI"
    INSURANCE       = "INSURANCE"
    INVESTMENT      = "INVESTMENT"
    ENTERTAINMENT   = "ENTERTAINMENT"
    SHOPPING        = "SHOPPING"
    HEALTHCARE      = "HEALTHCARE"
    EDUCATION       = "EDUCATION"
    TRAVEL          = "TRAVEL"
    HOTEL           = "HOTEL"
    FEES_CHARGES    = "FEES_CHARGES"
    TAXES           = "TAXES"
    CHARITY         = "CHARITY"

    # Transfer types
    TRANSFER_UPI    = "TRANSFER_UPI"
    TRANSFER_NEFT   = "TRANSFER_NEFT"
    TRANSFER_IMPS   = "TRANSFER_IMPS"
    TRANSFER_RTGS   = "TRANSFER_RTGS"
    TRANSFER_SELF   = "TRANSFER_SELF"   # own account transfer
    ATM_WITHDRAWAL  = "ATM_WITHDRAWAL"
    CASH_DEPOSIT    = "CASH_DEPOSIT"

    # Catch-all
    OTHER           = "OTHER"


# Direction hints: "debit" = only match on debit side, "credit" = credit only, None = either
@dataclass(frozen=True)
class Rule:
    pattern: str          # substring to search for (lowercased)
    category: Category
    direction: Optional[str] = None   # "debit", "credit", or None
    is_regex: bool = False
    priority: int = 50    # higher = checked first (0-100)


# ── Rule definitions ──────────────────────────────────────────────────────────
# Priority: 90=very specific, 70=specific, 50=standard, 30=generic fallback

RAW_RULES: list[Rule] = [

    # ── SALARY / INCOME ───────────────────────────────────────────────────────
    Rule("salary",               Category.SALARY,          "credit", priority=90),
    Rule("sal cr",               Category.SALARY,          "credit", priority=90),
    Rule("payroll",              Category.SALARY,          "credit", priority=90),
    Rule("hrsalary",             Category.SALARY,          "credit", priority=90),
    Rule("sal/",                 Category.SALARY,          "credit", priority=90),
    Rule("monthly pay",          Category.SALARY,          "credit", priority=90),
    Rule("neft-sal",             Category.SALARY,          "credit", priority=90),
    Rule("stipend",              Category.SALARY,          "credit", priority=85),
    Rule("wages",                Category.SALARY,          "credit", priority=85),
    Rule("incentive",            Category.BUSINESS_INCOME, "credit", priority=70),
    Rule("commission",           Category.BUSINESS_INCOME, "credit", priority=70),
    Rule("freelance",            Category.FREELANCE,       "credit", priority=80),
    Rule("upwork",               Category.FREELANCE,       "credit", priority=80),
    Rule("fiverr",               Category.FREELANCE,       "credit", priority=80),
    Rule("toptal",               Category.FREELANCE,       "credit", priority=80),
    Rule("huey tech",            Category.SALARY,          "credit", priority=85),
    Rule("infosys",              Category.SALARY,          "credit", priority=85),
    Rule("tcs",                  Category.SALARY,          "credit", priority=85),
    Rule("wipro",                Category.SALARY,          "credit", priority=85),

    # ── INTEREST / INVESTMENT RETURNS ─────────────────────────────────────────
    Rule("interest",             Category.INTEREST,        "credit", priority=88),
    Rule("int payout",           Category.INTEREST,        "credit", priority=90),
    Rule("monthly interest",     Category.INTEREST,        "credit", priority=90),
    Rule("credit interest",      Category.INTEREST,        "credit", priority=90),
    Rule("fd interest",          Category.INTEREST,        "credit", priority=90),
    Rule("rd interest",          Category.INTEREST,        "credit", priority=90),
    Rule("dividend",             Category.DIVIDEND,        "credit", priority=88),

    # ── REFUNDS ───────────────────────────────────────────────────────────────
    Rule("refund",               Category.REFUND,          "credit", priority=85),
    Rule("reversal",             Category.REFUND,          "credit", priority=85),
    Rule("corr wdl",             Category.REFUND,          "credit", priority=88),  # correction withdrawal reversed
    Rule("chargeback",           Category.REFUND,          "credit", priority=88),
    Rule("cashback",             Category.CASHBACK,        "credit", priority=88),
    Rule("reward",               Category.CASHBACK,        "credit", priority=75),
    Rule("loyalty",              Category.CASHBACK,        "credit", priority=70),

    # ── EMI / LOAN ────────────────────────────────────────────────────────────
    Rule("emi",                  Category.EMI,             "debit",  priority=92),
    Rule(" emi ",                Category.EMI,             "debit",  priority=95),
    Rule("loan",                 Category.EMI,             "debit",  priority=88),
    Rule("home loan",            Category.EMI,             "debit",  priority=92),
    Rule("car loan",             Category.EMI,             "debit",  priority=92),
    Rule("personal loan",        Category.EMI,             "debit",  priority=92),
    Rule("mortgage",             Category.EMI,             "debit",  priority=90),
    Rule("bajaj finance",        Category.EMI,             "debit",  priority=90),
    Rule("hdfc home",            Category.EMI,             "debit",  priority=90),
    Rule("lic emi",              Category.EMI,             "debit",  priority=92),
    Rule("nach debit",           Category.EMI,             "debit",  priority=90),
    Rule("nach/",                Category.EMI,             "debit",  priority=88),
    Rule("ecs",                  Category.EMI,             "debit",  priority=85),
    Rule("auto debit",           Category.EMI,             "debit",  priority=85),
    Rule("standing instruction", Category.EMI,             "debit",  priority=82),

    # ── CREDIT CARD PAYMENT ───────────────────────────────────────────────────
    Rule("credit card",          Category.EMI,             "debit",  priority=85),
    Rule("cc payment",           Category.EMI,             "debit",  priority=88),
    Rule("card payment",         Category.EMI,             "debit",  priority=85),
    Rule("hdfc cc",              Category.EMI,             "debit",  priority=88),
    Rule("icici cc",             Category.EMI,             "debit",  priority=88),
    Rule("sbi card",             Category.EMI,             "debit",  priority=88),

    # ── FOOD & BEVERAGES ──────────────────────────────────────────────────────
    Rule("zomato",               Category.FOOD,            "debit",  priority=88),
    Rule("swiggy",               Category.FOOD,            "debit",  priority=88),
    Rule("uber eats",            Category.FOOD,            "debit",  priority=88),
    Rule("faasos",               Category.FOOD,            "debit",  priority=88),
    Rule("box8",                 Category.FOOD,            "debit",  priority=88),
    Rule("freshmenu",            Category.FOOD,            "debit",  priority=88),
    Rule("ovenstory",            Category.FOOD,            "debit",  priority=88),
    Rule("dominos",              Category.FOOD,            "debit",  priority=88),
    Rule("domino",               Category.FOOD,            "debit",  priority=88),
    Rule("pizza hut",            Category.FOOD,            "debit",  priority=88),
    Rule("subway",               Category.FOOD,            "debit",  priority=85),
    Rule("mcdonald",             Category.FOOD,            "debit",  priority=88),
    Rule("kfc",                  Category.FOOD,            "debit",  priority=88),
    Rule("burger king",          Category.FOOD,            "debit",  priority=88),
    Rule("cafe",                 Category.FOOD,            "debit",  priority=72),
    Rule("starbucks",            Category.FOOD,            "debit",  priority=88),
    Rule("costa coffee",         Category.FOOD,            "debit",  priority=88),
    Rule("barista",              Category.FOOD,            "debit",  priority=82),
    Rule("haldiram",             Category.FOOD,            "debit",  priority=85),
    Rule("barbeque",             Category.FOOD,            "debit",  priority=82),
    Rule("restaurant",           Category.FOOD,            "debit",  priority=75),
    Rule("dhaba",                Category.FOOD,            "debit",  priority=75),
    Rule("hotel kitchen",        Category.FOOD,            "debit",  priority=75),

    # ── GROCERIES ────────────────────────────────────────────────────────────
    Rule("dmart",                Category.GROCERIES,       "debit",  priority=88),
    Rule("d-mart",               Category.GROCERIES,       "debit",  priority=88),
    Rule("reliance fresh",       Category.GROCERIES,       "debit",  priority=88),
    Rule("reliance smart",       Category.GROCERIES,       "debit",  priority=88),
    Rule("big bazaar",           Category.GROCERIES,       "debit",  priority=88),
    Rule("more supermarket",     Category.GROCERIES,       "debit",  priority=88),
    Rule("spencers",             Category.GROCERIES,       "debit",  priority=85),
    Rule("nature basket",        Category.GROCERIES,       "debit",  priority=85),
    Rule("grofers",              Category.GROCERIES,       "debit",  priority=88),
    Rule("blinkit",              Category.GROCERIES,       "debit",  priority=88),
    Rule("zepto",                Category.GROCERIES,       "debit",  priority=88),
    Rule("dunzo",                Category.GROCERIES,       "debit",  priority=82),
    Rule("jiomart",              Category.GROCERIES,       "debit",  priority=88),
    Rule("big basket",           Category.GROCERIES,       "debit",  priority=88),
    Rule("bigbasket",            Category.GROCERIES,       "debit",  priority=88),
    Rule("licious",              Category.GROCERIES,       "debit",  priority=82),
    Rule("supermarket",          Category.GROCERIES,       "debit",  priority=72),
    Rule("kirana",               Category.GROCERIES,       "debit",  priority=72),

    # ── TRANSPORT ────────────────────────────────────────────────────────────
    Rule("uber",                 Category.TRANSPORT,       "debit",  priority=85),
    Rule("ola",                  Category.TRANSPORT,       "debit",  priority=85),
    Rule("rapido",               Category.TRANSPORT,       "debit",  priority=85),
    Rule("olacabs",              Category.TRANSPORT,       "debit",  priority=88),
    Rule("meru",                 Category.TRANSPORT,       "debit",  priority=82),
    Rule("metro",                Category.TRANSPORT,       "debit",  priority=80),
    Rule("delhimetro",           Category.TRANSPORT,       "debit",  priority=88),
    Rule("mumbai metro",         Category.TRANSPORT,       "debit",  priority=88),
    Rule("dtc",                  Category.TRANSPORT,       "debit",  priority=75),
    Rule("bus",                  Category.TRANSPORT,       "debit",  priority=65),
    Rule("autorickshaw",         Category.TRANSPORT,       "debit",  priority=75),
    Rule("yulu",                 Category.TRANSPORT,       "debit",  priority=82),
    Rule("bounce",               Category.TRANSPORT,       "debit",  priority=80),

    # ── FUEL ──────────────────────────────────────────────────────────────────
    Rule("petrol",               Category.FUEL,            "debit",  priority=88),
    Rule("diesel",               Category.FUEL,            "debit",  priority=88),
    Rule("fuel",                 Category.FUEL,            "debit",  priority=85),
    Rule("hp petrol",            Category.FUEL,            "debit",  priority=90),
    Rule("indian oil",           Category.FUEL,            "debit",  priority=88),
    Rule("bharat petroleum",     Category.FUEL,            "debit",  priority=88),
    Rule("shell",                Category.FUEL,            "debit",  priority=82),
    Rule("fasttag",              Category.FUEL,            "debit",  priority=85),  # toll
    Rule("toll",                 Category.FUEL,            "debit",  priority=75),

    # ── UTILITIES ────────────────────────────────────────────────────────────
    Rule("electricity",          Category.UTILITIES,       "debit",  priority=88),
    Rule("water bill",           Category.UTILITIES,       "debit",  priority=88),
    Rule("gas bill",             Category.UTILITIES,       "debit",  priority=88),
    Rule("indane",               Category.UTILITIES,       "debit",  priority=85),
    Rule("hp gas",               Category.UTILITIES,       "debit",  priority=85),
    Rule("bharat gas",           Category.UTILITIES,       "debit",  priority=85),
    Rule("bses",                 Category.UTILITIES,       "debit",  priority=85),
    Rule("torrent power",        Category.UTILITIES,       "debit",  priority=85),
    Rule("tata power",           Category.UTILITIES,       "debit",  priority=85),
    Rule("mahadiscom",           Category.UTILITIES,       "debit",  priority=85),
    Rule("bescom",               Category.UTILITIES,       "debit",  priority=85),
    Rule("cesc",                 Category.UTILITIES,       "debit",  priority=85),
    Rule("mseb",                 Category.UTILITIES,       "debit",  priority=85),

    # ── TELECOM ───────────────────────────────────────────────────────────────
    Rule("jio",                  Category.TELECOM,         "debit",  priority=85),
    Rule("airtel",               Category.TELECOM,         "debit",  priority=85),
    Rule("vodafone",             Category.TELECOM,         "debit",  priority=85),
    Rule("vi recharge",          Category.TELECOM,         "debit",  priority=88),
    Rule("bsnl",                 Category.TELECOM,         "debit",  priority=85),
    Rule("mtnl",                 Category.TELECOM,         "debit",  priority=85),
    Rule("tata telecom",         Category.TELECOM,         "debit",  priority=85),
    Rule("act broadband",        Category.TELECOM,         "debit",  priority=85),
    Rule("hathway",              Category.TELECOM,         "debit",  priority=82),
    Rule("tikona",               Category.TELECOM,         "debit",  priority=82),
    Rule("broadband",            Category.TELECOM,         "debit",  priority=75),
    Rule("recharge",             Category.TELECOM,         "debit",  priority=72),
    Rule("prepaid",              Category.TELECOM,         "debit",  priority=65),
    Rule("mobile bill",          Category.TELECOM,         "debit",  priority=82),

    # ── RENT / HOUSING ───────────────────────────────────────────────────────
    Rule("rent",                 Category.RENT,            "debit",  priority=88),
    Rule("house rent",           Category.RENT,            "debit",  priority=90),
    Rule("rental",               Category.RENT,            "debit",  priority=85),
    Rule("lease",                Category.RENT,            "debit",  priority=80),
    Rule("maintenance",          Category.RENT,            "debit",  priority=68),
    Rule("society",              Category.RENT,            "debit",  priority=65),
    Rule("housing",              Category.RENT,            "debit",  priority=65),
    Rule("landlord",             Category.RENT,            "debit",  priority=85),

    # ── INSURANCE ────────────────────────────────────────────────────────────
    Rule("insurance",            Category.INSURANCE,       "debit",  priority=88),
    Rule("lic",                  Category.INSURANCE,       "debit",  priority=85),
    Rule("life insurance",       Category.INSURANCE,       "debit",  priority=90),
    Rule("health insurance",     Category.INSURANCE,       "debit",  priority=90),
    Rule("premium",              Category.INSURANCE,       "debit",  priority=72),
    Rule("hdfc life",            Category.INSURANCE,       "debit",  priority=88),
    Rule("icici lombard",        Category.INSURANCE,       "debit",  priority=88),
    Rule("star health",          Category.INSURANCE,       "debit",  priority=88),
    Rule("bajaj allianz",        Category.INSURANCE,       "debit",  priority=88),
    Rule("tata aig",             Category.INSURANCE,       "debit",  priority=88),
    Rule("new india",            Category.INSURANCE,       "debit",  priority=75),

    # ── INVESTMENT ───────────────────────────────────────────────────────────
    Rule("mutual fund",          Category.INVESTMENT,      "debit",  priority=90),
    Rule("mf sip",               Category.INVESTMENT,      "debit",  priority=92),
    Rule("sip",                  Category.INVESTMENT,      "debit",  priority=85),
    Rule("nps",                  Category.INVESTMENT,      "debit",  priority=88),
    Rule("ppf",                  Category.INVESTMENT,      "debit",  priority=88),
    Rule("epf",                  Category.INVESTMENT,      "debit",  priority=88),
    Rule("zerodha",              Category.INVESTMENT,      "debit",  priority=88),
    Rule("groww",                Category.INVESTMENT,      "debit",  priority=88),
    Rule("upstox",               Category.INVESTMENT,      "debit",  priority=88),
    Rule("angel broking",        Category.INVESTMENT,      "debit",  priority=88),
    Rule("5paisa",               Category.INVESTMENT,      "debit",  priority=88),
    Rule("paytm money",          Category.INVESTMENT,      "debit",  priority=85),
    Rule("coin by zerodha",      Category.INVESTMENT,      "debit",  priority=88),
    Rule("stocks",               Category.INVESTMENT,      "debit",  priority=70),
    Rule("shares",               Category.INVESTMENT,      "debit",  priority=70),
    Rule("fd booking",           Category.INVESTMENT,      "debit",  priority=88),
    Rule("rd installment",       Category.INVESTMENT,      "debit",  priority=88),

    # ── HEALTHCARE ───────────────────────────────────────────────────────────
    Rule("hospital",             Category.HEALTHCARE,      "debit",  priority=85),
    Rule("clinic",               Category.HEALTHCARE,      "debit",  priority=82),
    Rule("pharmacy",             Category.HEALTHCARE,      "debit",  priority=85),
    Rule("medplus",              Category.HEALTHCARE,      "debit",  priority=88),
    Rule("apollo pharmacy",      Category.HEALTHCARE,      "debit",  priority=88),
    Rule("netmeds",              Category.HEALTHCARE,      "debit",  priority=88),
    Rule("1mg",                  Category.HEALTHCARE,      "debit",  priority=88),
    Rule("pharmeasy",            Category.HEALTHCARE,      "debit",  priority=88),
    Rule("practo",               Category.HEALTHCARE,      "debit",  priority=85),
    Rule("doctor",               Category.HEALTHCARE,      "debit",  priority=72),
    Rule("lab test",             Category.HEALTHCARE,      "debit",  priority=80),
    Rule("thyrocare",            Category.HEALTHCARE,      "debit",  priority=85),
    Rule("dr lal path",          Category.HEALTHCARE,      "debit",  priority=85),

    # ── EDUCATION ────────────────────────────────────────────────────────────
    Rule("school fee",           Category.EDUCATION,       "debit",  priority=90),
    Rule("college fee",          Category.EDUCATION,       "debit",  priority=90),
    Rule("tuition",              Category.EDUCATION,       "debit",  priority=82),
    Rule("udemy",                Category.EDUCATION,       "debit",  priority=88),
    Rule("coursera",             Category.EDUCATION,       "debit",  priority=88),
    Rule("unacademy",            Category.EDUCATION,       "debit",  priority=88),
    Rule("byju",                 Category.EDUCATION,       "debit",  priority=88),
    Rule("vedantu",              Category.EDUCATION,       "debit",  priority=88),
    Rule("exam fee",             Category.EDUCATION,       "debit",  priority=88),
    Rule("admission",            Category.EDUCATION,       "debit",  priority=75),
    Rule("books",                Category.EDUCATION,       "debit",  priority=65),

    # ── SHOPPING ─────────────────────────────────────────────────────────────
    Rule("amazon",               Category.SHOPPING,        "debit",  priority=85),
    Rule("flipkart",             Category.SHOPPING,        "debit",  priority=85),
    Rule("myntra",               Category.SHOPPING,        "debit",  priority=88),
    Rule("ajio",                 Category.SHOPPING,        "debit",  priority=88),
    Rule("nykaa",                Category.SHOPPING,        "debit",  priority=88),
    Rule("meesho",               Category.SHOPPING,        "debit",  priority=88),
    Rule("snapdeal",             Category.SHOPPING,        "debit",  priority=88),
    Rule("shopclues",            Category.SHOPPING,        "debit",  priority=85),
    Rule("tata cliq",            Category.SHOPPING,        "debit",  priority=88),
    Rule("croma",                Category.SHOPPING,        "debit",  priority=85),
    Rule("vijay sales",          Category.SHOPPING,        "debit",  priority=85),
    Rule("reliance digital",     Category.SHOPPING,        "debit",  priority=88),

    # ── ENTERTAINMENT ────────────────────────────────────────────────────────
    Rule("netflix",              Category.ENTERTAINMENT,   "debit",  priority=90),
    Rule("amazon prime",         Category.ENTERTAINMENT,   "debit",  priority=90),
    Rule("hotstar",              Category.ENTERTAINMENT,   "debit",  priority=90),
    Rule("disney",               Category.ENTERTAINMENT,   "debit",  priority=88),
    Rule("spotify",              Category.ENTERTAINMENT,   "debit",  priority=90),
    Rule("gaana",                Category.ENTERTAINMENT,   "debit",  priority=88),
    Rule("wynk",                 Category.ENTERTAINMENT,   "debit",  priority=85),
    Rule("youtube premium",      Category.ENTERTAINMENT,   "debit",  priority=90),
    Rule("zee5",                 Category.ENTERTAINMENT,   "debit",  priority=88),
    Rule("sonyliv",              Category.ENTERTAINMENT,   "debit",  priority=88),
    Rule("pvr",                  Category.ENTERTAINMENT,   "debit",  priority=85),
    Rule("inox",                 Category.ENTERTAINMENT,   "debit",  priority=85),
    Rule("bookmyshow",           Category.ENTERTAINMENT,   "debit",  priority=88),
    Rule("theatre",              Category.ENTERTAINMENT,   "debit",  priority=72),
    Rule("movie",                Category.ENTERTAINMENT,   "debit",  priority=65),
    Rule("gaming",               Category.ENTERTAINMENT,   "debit",  priority=72),
    Rule("steam",                Category.ENTERTAINMENT,   "debit",  priority=82),

    # ── TRAVEL ───────────────────────────────────────────────────────────────
    Rule("makemytrip",           Category.TRAVEL,          "debit",  priority=88),
    Rule("goibibo",              Category.TRAVEL,          "debit",  priority=88),
    Rule("yatra",                Category.TRAVEL,          "debit",  priority=88),
    Rule("cleartrip",            Category.TRAVEL,          "debit",  priority=88),
    Rule("irctc",                Category.TRAVEL,          "debit",  priority=88),
    Rule("indigo",               Category.TRAVEL,          "debit",  priority=85),
    Rule("spicejet",             Category.TRAVEL,          "debit",  priority=85),
    Rule("air india",            Category.TRAVEL,          "debit",  priority=85),
    Rule("vistara",              Category.TRAVEL,          "debit",  priority=85),
    Rule("airline",              Category.TRAVEL,          "debit",  priority=75),
    Rule("flight",               Category.TRAVEL,          "debit",  priority=72),
    Rule("railways",             Category.TRAVEL,          "debit",  priority=75),
    Rule("train ticket",         Category.TRAVEL,          "debit",  priority=80),
    Rule("bus ticket",           Category.TRAVEL,          "debit",  priority=80),
    Rule("redbus",               Category.TRAVEL,          "debit",  priority=85),

    # ── HOTEL ────────────────────────────────────────────────────────────────
    Rule("oyo",                  Category.HOTEL,           "debit",  priority=88),
    Rule("airbnb",               Category.HOTEL,           "debit",  priority=88),
    Rule("fabhotels",            Category.HOTEL,           "debit",  priority=85),
    Rule("treebo",               Category.HOTEL,           "debit",  priority=85),
    Rule("taj hotel",            Category.HOTEL,           "debit",  priority=85),
    Rule("marriott",             Category.HOTEL,           "debit",  priority=85),
    Rule("hotels.com",           Category.HOTEL,           "debit",  priority=85),
    Rule("booking.com",          Category.HOTEL,           "debit",  priority=85),
    Rule("hotel",                Category.HOTEL,           "debit",  priority=62),

    # ── FEES & CHARGES ───────────────────────────────────────────────────────
    Rule("bank charge",          Category.FEES_CHARGES,    "debit",  priority=88),
    Rule("service charge",       Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("annual charge",        Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("maintenance charge",   Category.FEES_CHARGES,    "debit",  priority=82),
    Rule("sms charge",           Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("sms charges",          Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("account charge",       Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("quarterly avg bal",    Category.FEES_CHARGES,    "debit",  priority=88),
    Rule("min bal charge",       Category.FEES_CHARGES,    "debit",  priority=90),
    Rule("processing fee",       Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("late fee",             Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("penalty",              Category.FEES_CHARGES,    "debit",  priority=80),
    Rule("cheque return",        Category.FEES_CHARGES,    "debit",  priority=88),
    Rule("bounce charge",        Category.FEES_CHARGES,    "debit",  priority=88),
    Rule("gst charge",           Category.FEES_CHARGES,    "debit",  priority=85),
    Rule("platform fee",         Category.FEES_CHARGES,    "debit",  priority=82),
    Rule("convenience fee",      Category.FEES_CHARGES,    "debit",  priority=82),

    # ── TAXES ────────────────────────────────────────────────────────────────
    Rule("income tax",           Category.TAXES,           "debit",  priority=90),
    Rule("gst payment",          Category.TAXES,           "debit",  priority=90),
    Rule("tds",                  Category.TAXES,           "debit",  priority=85),
    Rule("advance tax",          Category.TAXES,           "debit",  priority=88),
    Rule("property tax",         Category.TAXES,           "debit",  priority=88),
    Rule("municipal tax",        Category.TAXES,           "debit",  priority=85),

    # ── ATM / CASH ───────────────────────────────────────────────────────────
    Rule("atm wdl",              Category.ATM_WITHDRAWAL,  "debit",  priority=92),
    Rule("atm withdrawal",       Category.ATM_WITHDRAWAL,  "debit",  priority=92),
    Rule("cash withdrawal",      Category.ATM_WITHDRAWAL,  "debit",  priority=90),
    Rule("atm",                  Category.ATM_WITHDRAWAL,  "debit",  priority=82),
    Rule("cash deposit",         Category.CASH_DEPOSIT,    "credit", priority=90),
    Rule("cdm",                  Category.CASH_DEPOSIT,    "credit", priority=85),

    # ── TRANSFERS — ordered specific → generic ────────────────────────────────
    # NEFT / RTGS / IMPS first (most specific)
    Rule("neft",                 Category.TRANSFER_NEFT,   None,     priority=80),
    Rule("rtgs",                 Category.TRANSFER_RTGS,   None,     priority=80),
    Rule("imps",                 Category.TRANSFER_IMPS,   None,     priority=80),

    # UPI — generic fallback (lowest priority so specific rules win)
    Rule("upi/cr/",              Category.TRANSFER_UPI,    "credit", priority=55),
    Rule("upi/dr/",              Category.TRANSFER_UPI,    "debit",  priority=55),
    Rule("upi",                  Category.TRANSFER_UPI,    None,     priority=45),
    Rule("by transfer",          Category.TRANSFER_UPI,    "credit", priority=42),
    Rule("to transfer",          Category.TRANSFER_UPI,    "debit",  priority=42),
    Rule("payment to",           Category.TRANSFER_UPI,    "debit",  priority=40),
    Rule("sent using paytm",     Category.TRANSFER_UPI,    "debit",  priority=55),
    Rule("pay to bharatpe",      Category.TRANSFER_UPI,    "debit",  priority=55),
    Rule("phonepe",              Category.TRANSFER_UPI,    None,     priority=52),
    Rule("gpay",                 Category.TRANSFER_UPI,    None,     priority=52),
    Rule("google pay",           Category.TRANSFER_UPI,    None,     priority=52),
    Rule("paytm",                Category.TRANSFER_UPI,    None,     priority=50),

    # Self transfer
    Rule("self transfer",        Category.TRANSFER_SELF,   None,     priority=85),
    Rule("own account",          Category.TRANSFER_SELF,   None,     priority=85),
    Rule("sweep in",             Category.TRANSFER_SELF,   None,     priority=82),
    Rule("sweep out",            Category.TRANSFER_SELF,   None,     priority=82),
    Rule("pos prch",             Category.SHOPPING,        "debit",  priority=70),

]


# ── Pre-compile rules sorted by priority (descending) ────────────────────────

_COMPILED_RULES: list[tuple] = []   # (priority, pattern_lower, category, direction, is_regex, compiled_re)

def _build_index():
    global _COMPILED_RULES
    sorted_rules = sorted(RAW_RULES, key=lambda r: r.priority, reverse=True)
    for rule in sorted_rules:
        compiled_re = re.compile(rule.pattern, re.IGNORECASE) if rule.is_regex else None
        _COMPILED_RULES.append((
            rule.priority,
            rule.pattern.lower(),
            rule.category,
            rule.direction,
            rule.is_regex,
            compiled_re,
        ))

_build_index()


# ── Public API ────────────────────────────────────────────────────────────────

def categorize(description: str, debit: float = None, credit: float = None) -> str:
    """
    Categorize a single transaction.

    Args:
        description: raw transaction description (narration)
        debit:  debit amount or None
        credit: credit amount or None

    Returns:
        Category string e.g. "FOOD", "SALARY", "EMI", "OTHER"
    """
    if not description:
        return Category.OTHER.value

    desc_lower = description.lower()

    # Determine direction for direction-aware rules
    is_debit  = debit  is not None and debit  > 0
    is_credit = credit is not None and credit > 0

    for (priority, pattern, category, direction, is_regex, compiled_re) in _COMPILED_RULES:
        # Direction filter
        if direction == "debit"  and not is_debit:
            continue
        if direction == "credit" and not is_credit:
            continue

        # Match
        if is_regex:
            if compiled_re.search(desc_lower):
                return category.value
        else:
            if pattern in desc_lower:
                return category.value

    return Category.OTHER.value


def categorize_dataframe(df) -> object:
    """
    Add a 'Category' column to a transactions DataFrame.
    Operates in-place and also returns the modified df.
    """
    import pandas as pd
    df = df.copy()
    df['Category'] = df.apply(
        lambda row: categorize(
            str(row.get('Description', '') or ''),
            row.get('Debit'),
            row.get('Credit'),
        ),
        axis=1
    )
    return df
