"""Default configuration for the statement spreader."""

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "NVDA", "ORCL", "ADBE", "CRM", "INTC",
]

DEFAULT_NUM_YEARS = 4

# SEC requires a descriptive User-Agent identifying the requester.
# https://www.sec.gov/os/webmaster-faq#developers
SEC_USER_AGENT = "statement-spreader (portfolio project) cjcassidy06@gmail.com"

CACHE_DIR = "cache"
DEFAULT_OUTPUT_PATH = "output/spread.xlsx"

# SEC asks for no more than ~10 requests/sec; we stay well under that.
REQUEST_DELAY_SECONDS = 0.2
