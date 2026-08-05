"""Canonical 3-statement line items mapped to ordered XBRL tag fallback lists.

Different filers tag the same economic concept differently (e.g. Apple has no
`CostOfRevenue` tag, only `CostOfGoodsAndServicesSold`; some filers report
`Revenues`, others `RevenueFromContractWithCustomerExcludingAssessedTax`).
For each canonical line item we try tags in priority order and take the first
one present in a company's facts. This mapping was seeded by inspecting real
`companyfacts` data for all DEFAULT_TICKERS (see src/config.py).

Each entry: canonical_key -> (statement, label, [tag, ...] in priority order).
`statement` is one of "IS", "BS", "CF" and controls both display grouping in
the Excel builder and whether the value is a point-in-time ("instant") or
period ("duration") XBRL fact.
"""

INCOME_STATEMENT = "IS"
BALANCE_SHEET = "BS"
CASH_FLOW = "CF"

# statement -> whether facts are instant (balance sheet) or duration (IS/CF)
STATEMENT_PERIOD_TYPE = {
    INCOME_STATEMENT: "duration",
    BALANCE_SHEET: "instant",
    CASH_FLOW: "duration",
}

LINE_ITEMS = {
    # --- Income Statement ---
    "revenue": (INCOME_STATEMENT, "Revenue", [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ]),
    "cost_of_revenue": (INCOME_STATEMENT, "Cost of Revenue", [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfServices",
    ]),
    "research_and_development": (INCOME_STATEMENT, "Research & Development", [
        "ResearchAndDevelopmentExpense",
    ]),
    "sga": (INCOME_STATEMENT, "SG&A", [
        "SellingGeneralAndAdministrativeExpense",
        "GeneralAndAdministrativeExpense",
    ]),
    "operating_income": (INCOME_STATEMENT, "Operating Income", [
        "OperatingIncomeLoss",
    ]),
    "interest_expense": (INCOME_STATEMENT, "Interest Expense", [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestExpenseNonoperating",
    ]),
    "income_tax_expense": (INCOME_STATEMENT, "Income Tax Expense", [
        "IncomeTaxExpenseBenefit",
    ]),
    "net_income": (INCOME_STATEMENT, "Net Income", [
        "NetIncomeLoss",
    ]),
    "eps_diluted": (INCOME_STATEMENT, "Diluted EPS", [
        "EarningsPerShareDiluted",
    ]),

    # --- Balance Sheet ---
    "cash": (BALANCE_SHEET, "Cash & Equivalents", [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ]),
    "current_assets": (BALANCE_SHEET, "Total Current Assets", [
        "AssetsCurrent",
    ]),
    "ppe_net": (BALANCE_SHEET, "PP&E, Net", [
        "PropertyPlantAndEquipmentNet",
    ]),
    "total_assets": (BALANCE_SHEET, "Total Assets", [
        "Assets",
    ]),
    "current_liabilities": (BALANCE_SHEET, "Total Current Liabilities", [
        "LiabilitiesCurrent",
    ]),
    "long_term_debt": (BALANCE_SHEET, "Long-Term Debt", [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ]),
    "total_liabilities": (BALANCE_SHEET, "Total Liabilities", [
        "Liabilities",
    ]),
    "stockholders_equity": (BALANCE_SHEET, "Stockholders' Equity", [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),

    # --- Cash Flow Statement ---
    "cfo": (CASH_FLOW, "Cash from Operations", [
        "NetCashProvidedByUsedInOperatingActivities",
    ]),
    "cfi": (CASH_FLOW, "Cash from Investing", [
        "NetCashProvidedByUsedInInvestingActivities",
    ]),
    "cff": (CASH_FLOW, "Cash from Financing", [
        "NetCashProvidedByUsedInFinancingActivities",
    ]),
    "capex": (CASH_FLOW, "Capital Expenditures", [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ]),
    "depreciation_amortization": (CASH_FLOW, "D&A", [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
    ]),
}

# total_liabilities has no consistent tag for some filers (e.g. Amazon,
# Oracle, Intel omit it entirely). When absent, spreader.py derives it as
# total_assets - stockholders_equity and marks the value as derived.
DERIVED_LINE_ITEMS = {"total_liabilities": ("total_assets", "stockholders_equity", "subtract")}


def line_items_for_statement(statement: str) -> list:
    return [key for key, (stmt, _, _) in LINE_ITEMS.items() if stmt == statement]
