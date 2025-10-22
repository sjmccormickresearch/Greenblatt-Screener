#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Magic Formula Screener (Fast Version)
-------------------------------------
Reads tickers from 'potential_stocks.txt' (e.g. LSE:RCH,LSE:PHAR,...)
Fetches financials concurrently using threads.
Computes:
 - Return on Tangible Capital (ROTC)
 - Earnings Yield (EBIT / EV)
Ranks them Greenblatt-style and exports results to CSV.
"""

# -------------------------------------------------
# Auto-install required packages if missing
# -------------------------------------------------
import importlib.util
import subprocess
import sys

def ensure_package(pkg):
    """Install a package quietly if not already present."""
    if importlib.util.find_spec(pkg) is None:
        print(f"📦 Installing {pkg} ...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", pkg]
            )
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
# Load tickers from file
# -------------------------------------------------
file_path = "potential_stocks.txt"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"⚠️  Can't find {file_path}. Please place it in the same folder.")

with open(file_path, "r") as f:
    content = f.read().strip()

tickers = [
    line.replace("LSE:", "").strip() + ".L"
    for line in content.split(",")
    if line.strip()
]

print(f"\n📂 Loaded {len(tickers)} tickers from {file_path}:")
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
# Fetch function for each ticker
# -------------------------------------------------
def fetch_ticker_data(t):
    """Fetch financials for a single ticker via yfinance."""
    try:
        stock = yf.Ticker(t)
        info = stock.info
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
        return {"Ticker": t, "Error": str(e)}

# -------------------------------------------------
# Multithreaded execution
# -------------------------------------------------
rows = []
max_threads = min(10, len(tickers))  # 10 threads is safe for Yahoo

start_time = time.time()
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

elapsed = time.time() - start_time
print(f"\n⏱️  Completed fetch for {len(tickers)} tickers in {elapsed:.1f}s\n")

# -------------------------------------------------
# Ranking & output
# -------------------------------------------------
df = pd.DataFrame(rows).dropna(subset=["ROTC", "Earnings Yield"])
if df.empty:
    print("⚠️  No valid data retrieved. Check your ticker list or internet connection.")
    sys.exit(0)

df["ROTC %"] = df["ROTC"] * 100
df["Earnings Yield %"] = df["Earnings Yield"] * 100
df["Rank_ROTC"] = df["ROTC"].rank(ascending=False)
df["Rank_EY"] = df["Earnings Yield"].rank(ascending=False)
df["Magic_Rank"] = (df["Rank_ROTC"] + df["Rank_EY"]).rank()
df = df.sort_values("Magic_Rank")

print("\n📊  Joel Greenblatt — Magic Formula Screener Results\n")
print("-" * 100)
for _, r in df.iterrows():
    print(
        f"{int(r['Magic_Rank']):2d}. {r['Ticker']:6} | "
        f"ROTC: {r['ROTC %']:6.1f}% | "
        f"Earnings Yield: {r['Earnings Yield %']:6.1f}% | "
        f"EV: {fmt(r['EV']):>10} | "
        f"EBIT: {fmt(r['EBIT']):>10}"
    )
print("-" * 100)

df.to_csv("magic_formula_results.csv", index=False)
print(f"\n✅ Done — results saved to 'magic_formula_results.csv'\n")
