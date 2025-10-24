# 📊 Greenblatt Screener

A Python implementation of Joel Greenblatt’s **“Magic Formula”** investing strategy — ranking stocks by:
- **High Earnings Yield** (`EBIT / EV`)
- **High Return on Tangible Capital (ROTC)` (`EBIT / Tangible Capital`)

This script fetches financial data using [Yahoo Finance](https://pypi.org/project/yfinance/), computes both metrics, ranks all tickers, and exports a ranked CSV report.

---

## ⚙️ Features

✅ Multithreaded fetching for fast performance  
✅ Applies Greenblatt-style purity filters (positive EBIT, EV, tangible capital)  
✅ Outputs EV/EBIT, Payback period, and ROTC %  
✅ Saves results to `magic_formula_pure.csv`  
✅ Lists any tickers with missing financial data  

---

## 🚀 How to Run

1. Clone this repository:
   ```bash
   git clone https://github.com/sjmccormickresearch/Greenblatt-Screener.git
   cd Greenblatt-Screener
