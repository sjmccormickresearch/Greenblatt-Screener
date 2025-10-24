#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Greenblatt Screener — Pure Magic Formula (Final Clean Version)
--------------------------------------------------------------
Ranks stocks using Joel Greenblatt’s “Magic Formula”:
 - High Earnings Yield (EBIT / EV)
 - High Return on Tangible Capital (EBIT / Tangible Capital)

Now includes:
 - 0.1s delay to avoid Yahoo rate limits
 - Clean, minimal console output (no tie clutter)
 - Auto-install for pandas & yfinance
 - Missing / invalid ticker separation
 - Saves results to 'greenblatt_results.csv'
"""

# -------------------------------------------------
# Auto-install required packages
# -------------------------------------------------
import importlib.util
import subprocess
import sys

def ensure_package(pkg):
    if importlib.util.find_spec(pkg) is None:
        print(f"📦 Installing {pkg} ...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])
            print(f"✅ Installed {pkg}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {pkg}. Please run: pip install {pkg}")
            sys.exit(1)

for package in ["pandas", "yfinance"]:
    ensure_package(package)

# -------------------------------------------------
# Imports
# -------------------------------------------------
import pandas as pd
import yfinance as yf
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# -------------------------------------------------
# Load tickers
# -------------------------------------------------
file_path = "potential_stocks.txt"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"⚠️  Can't find {file_path}.")

with open(file_path, "r") as f:
    tickers = [
        line.replace("LSE:", "").strip() + ".L"
        for line in f.read().strip().split(",")
        if line.strip()
    ]

print(f"\n📂 Loaded {len(tickers)} tickers from {file_path}")
print(", ".join(tickers))
print("\n🚀 Fetching financials using multithreading...\n")

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_first_available(df, keys):
    for key in keys:
        if key in df.index:
            return df.loc[key].iloc[0]
    return None

# -------------------------------------------------
# Fetch
# -------------------------------------------------
def fetch_ticker_data(t):
    """Fetch financials for a single ticker via yfinance."""
    try:
        time.sleep(0.1)  # rate-limit safety
        stock = yf.Ticker(t)
        info = stock.info

        # Catch invalid tickers or Yahoo 404s
        if not info or "longName" not in info:
            return {"Ticker": t, "Error": "Quote not found"}

        bs = stock.balance_sheet
        is_ = stock.financials
        if bs.empty or is_.empty:
            return {"Ticker": t, "Error": "Empty financials"}

        ebit = get_first_available(is_, ["EBIT", "Ebit", "Operating Income"])
        total_current_assets = get_first_available(bs, ["Total Current Assets"])
        cash = get_first_available(bs, [
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Cash"
        ])
        total_current_liabilities = get_first_available(bs, ["Total Current Liabilities"])
        short_term_debt = get_first_available(bs, ["Short Term Debt", "Current Debt"])
        net_ppe = get_first_available(bs, [
            "Property Plant Equipment",
            "Property, Plant & Equipment Net",
            "Net PPE"
        ])
        total_debt = get_first_available(bs, ["Total Debt", "Long Term Debt"]) or 0

        # Calculate tangible capital and metrics
        op_nwc = (total_current_assets or 0) - (cash or 0) - (total_current_liabilities or 0) + (short_term_debt or 0)
        tangible_cap = (net_ppe or 0) + op_nwc
        rotc = ebit / tangible_cap if (ebit is not None and tangible_cap) else None

        market_cap = info.get("marketCap")
        if market_cap is None and info.get("sharesOutstanding") and info.get("currentPrice"):
            market_cap = info["sharesOutstanding"] * info["currentPrice"]

        ev = (market_cap or 0) + (total_debt or 0) - (cash or 0)
        earnings_yield = ebit / ev if (ebit is not None and ev) else None

        return {
            "Ticker": t,
            "EBIT": ebit,
            "Tangible Capital": tangible_cap,
            "ROTC": rotc,
            "EV": ev,
            "Earnings Yield": earnings_yield
        }

    except Exception as e:
        return {"Ticker": t, "Error": str(e)}

# -------------------------------------------------
# Multithreaded fetch
# -------------------------------------------------
rows = []
max_threads = min(5, len(tickers))
start = time.time()

with ThreadPoolExecutor(max_workers=max_threads) as executor:
    futures = {executor.submit(fetch_ticker_data, t): t for t in tickers}
    for i, future in enumerate(as_completed(futures), 1):
        t = futures[future]
        try:
            result = future.result()
            rows.append(result)
            print(f"[{i}/{len(tickers)}] ✅ {t}")
        except Exception as e:
            print(f"[{i}/{len(tickers)}] ❌ {t} error: {e}")

print(f"\n⏱️  Completed fetch for {len(tickers)} tickers in {time.time()-start:.1f}s\n")

# -------------------------------------------------
# Ranking & output
# -------------------------------------------------
df = pd.DataFrame(rows)
no_data = df[df["EBIT"].isna() | df["EV"].isna() | df["Tangible Capital"].isna()]
valid_df = df.dropna(subset=["EBIT", "EV", "Tangible Capital"])

# Greenblatt filters
valid_df = valid_df[
    (valid_df["EBIT"] > 0) &
    (valid_df["EV"] > 0) &
    (valid_df["Tangible Capital"] > 1e6)
]

# Metrics
valid_df["ROTC"] = valid_df["EBIT"] / valid_df["Tangible Capital"]
valid_df["Earnings Yield"] = valid_df["EBIT"] / valid_df["EV"]
valid_df = valid_df[(valid_df["ROTC"] < 2) & (valid_df["Earnings Yield"] < 1)]

# Ranks
valid_df["Rank_ROTC"] = valid_df["ROTC"].rank(ascending=False)
valid_df["Rank_EY"] = valid_df["Earnings Yield"].rank(ascending=False)
valid_df["Magic_Rank_Score"] = valid_df["Rank_ROTC"] + valid_df["Rank_EY"]
valid_df = valid_df.sort_values("Magic_Rank_Score").reset_index(drop=True)
valid_df["Magic_Rank"] = valid_df.index + 1

# Display fields
valid_df["ROTC %"] = valid_df["ROTC"] * 100
valid_df["Earnings Yield %"] = valid_df["Earnings Yield"] * 100
valid_df["EV/EBIT"] = 1 / valid_df["Earnings Yield"]
valid_df["Payback (yrs)"] = 1 / valid_df["Earnings Yield"]

# -------------------------------------------------
# Print ranked results
# -------------------------------------------------
print("\n📊  Joel Greenblatt — Magic Formula Screener Results\n"
      " Stocks are ranked by both EV/EBIT and ROTC and summed.\n")
print("-" * 110)

for _, r in valid_df.iterrows():
    print(
        f"{int(r['Magic_Rank']):3d}. {r['Ticker']:6} | "
        f"ROTC: {r['ROTC %']:7.1f}% | "
        f"Earnings Yield: {r['Earnings Yield %']:6.1f}% | "
        f"EV/EBIT: {r['EV/EBIT']:6.1f}× | "
        f"Payback: {r['Payback (yrs)']:5.1f} yrs"
    )

print("-" * 110)

# -------------------------------------------------
# Missing / invalid ticker handling
# -------------------------------------------------
if not no_data.empty:
    missing_unique = sorted(no_data["Ticker"].unique())
    invalid = df[df["Error"].notna()]["Ticker"].unique().tolist()
    incomplete = [t for t in missing_unique if t not in invalid]

    if invalid:
        pd.DataFrame(invalid, columns=["Ticker"]).to_csv("invalid_tickers.csv", index=False)
        print(f"🚫 {len(invalid)} invalid tickers saved to 'invalid_tickers.csv'")

    if incomplete:
        pd.DataFrame(incomplete, columns=["Ticker"]).to_csv("missing_tickers.csv", index=False)
        print(f"💾 {len(incomplete)} incomplete tickers saved to 'missing_tickers.csv'")

    total = len(invalid) + len(incomplete)
    print(f"\n⚠️  Total {total} tickers with missing or incomplete financial data.")
else:
    print("\n✅ All tickers returned financial data.")

# -------------------------------------------------
# Save final ranked output
# -------------------------------------------------
valid_df.to_csv("greenblatt_results.csv", index=False)
print(f"✅ Done — results saved to 'greenblatt_results.csv'\n")
