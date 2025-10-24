#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Magic Formula Screener (Pure Greenblatt Version — Final Stable)
---------------------------------------------------------------
Now includes:
 - 0.1s delay to avoid rate limits
 - Tie marker & Tie_Group column
 - Counted summary of missing tickers
 - Automatic 'missing_tickers.csv' export
 - Handles Yahoo 404 / 'Quote not found' gracefully
"""

# -------------------------------------------------
# Auto-install required packages if missing
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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

def fmt(num):
    if num is None or pd.isna(num):
        return "-"
    if abs(num) >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    else:
        return f"{num:.2f}"

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
            return {"Ticker": t}

        bs = stock.balance_sheet
        is_ = stock.financials
        if bs.empty or is_.empty:
            return {"Ticker": t}

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

        op_nwc = (total_current_assets or 0) - (cash or 0) - (total_current_liabilities or 0) + (short_term_debt or 0)
        tangible_cap = (net_ppe or 0) + op_nwc
        rotc = ebit / tangible_cap if tangible_cap else None

        market_cap = info.get("marketCap")
        if market_cap is None and info.get("sharesOutstanding") and info.get("currentPrice"):
            market_cap = info["sharesOutstanding"] * info["currentPrice"]

        ev = (market_cap or 0) + (total_debt or 0) - (cash or 0)
        earnings_yield = ebit / ev if ev else None

        return {
            "Ticker": t,
            "EBIT": ebit,
            "Tangible Capital": tangible_cap,
            "ROTC": rotc,
            "EV": ev,
            "Earnings Yield": earnings_yield
        }

    except Exception as e:
        if "Quote not found" in str(e):
            print(f"⚠️  Quote not found for {t}")
        else:
            print(f"⚠️  Error fetching {t}: {e}")
        return {"Ticker": t}

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

# Sort & reset
valid_df = valid_df.sort_values("Magic_Rank_Score").reset_index(drop=True)
valid_df["Magic_Rank"] = valid_df.index + 1
valid_df["Tie"] = valid_df["Magic_Rank_Score"].round(2).diff().fillna(1) == 0
valid_df["Tie_Group"] = (valid_df["Tie"] == False).cumsum()

# Display fields
valid_df["ROTC %"] = valid_df["ROTC"] * 100
valid_df["Earnings Yield %"] = valid_df["Earnings Yield"] * 100
valid_df["EV/EBIT"] = 1 / valid_df["Earnings Yield"]
valid_df["Payback (yrs)"] = 1 / valid_df["Earnings Yield"]

# -------------------------------------------------
# Print results
# -------------------------------------------------
print("\n📊  Joel Greenblatt — PURE Magic Formula Screener Results\n"
      " Stocks are ranked by both EV/EBIT and ROTC and summed.\n")
print("-" * 115)

for _, r in valid_df.iterrows():
    tie_marker = " ← tied" if r["Tie"] else ""
    print(
        f"{int(r['Magic_Rank']):3d}. {r['Ticker']:6} | "
        f"ROTC: {r['ROTC %']:7.1f}% | "
        f"Earnings Yield: {r['Earnings Yield %']:6.1f}% | "
        f"EV/EBIT: {r['EV/EBIT']:6.1f}× | "
        f"Payback: {r['Payback (yrs)']:5.1f} yrs | "
        f"Tie Group: {int(r['Tie_Group']):3d}{tie_marker}"
    )

print("-" * 115)

# -------------------------------------------------
# Missing data summary + save missing tickers
# -------------------------------------------------
if not no_data.empty:
    missing_unique = sorted(no_data["Ticker"].unique())
    count = len(missing_unique)
    print(f"\n⚠️  {count} tickers with missing or no financial data:")
    print(", ".join(missing_unique))
    pd.DataFrame(missing_unique, columns=["Ticker"]).to_csv("missing_tickers.csv", index=False)
    print("💾 Missing tickers saved to 'missing_tickers.csv'\n")
else:
    print("\n✅ All tickers returned financial data.")

# -------------------------------------------------
# Save main output
# -------------------------------------------------
valid_df.to_csv("magic_formula_pure.csv", index=False)
print(f"✅ Done — results saved to 'magic_formula_pure.csv'\n")
