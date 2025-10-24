# 📊 Greenblatt Screener

A Python implementation of Joel Greenblatt’s **“Magic Formula”** investing strategy — ranking stocks by:

- **High Earnings Yield** — `EBIT / EV`  
- **High Return on Tangible Capital (ROTC)** — `EBIT / Tangible Capital`

This script fetches financial data using [Yahoo Finance](https://pypi.org/project/yfinance/), computes both metrics, ranks all tickers, and exports a clean ranked CSV report.

---

## ⚙️ Features

- ✅ Auto-installs required dependencies (`pandas`, `yfinance`)  
- ⚡ Multithreaded fetching with built-in rate-limit delay  
- 🧮 Applies Greenblatt-style purity filters (positive EBIT, EV, tangible capital)  
- 📈 Outputs EV/EBIT, Payback period, and ROTC %  
- 💾 Saves ranked results to `greenblatt_results.csv`  
- 🧾 Exports invalid and missing tickers to `invalid_tickers.csv` and `missing_tickers.csv`

---

## 🚀 How to Run

1. **Clone this repository**  
   ```bash
   git clone https://github.com/sjmccormickresearch/Greenblatt-Screener.git
   cd Greenblatt-Screener
   ```

2. **Run the screener directly**  
   ```bash
   python Greenblatt-Screener.py
   ```
   *(The script will automatically install any missing packages on first run.)*

3. **Add or edit your tickers in `potential_stocks.txt`**  
   ```text
   LSE:POS,LSE:CRL,LSE:NTBR,LSE:AET
   ```

4. **View results**  
   - Terminal output: ranked summary of the top stocks  
   - CSV output: `greenblatt_results.csv`  
   - Missing/invalid tickers (if any): `missing_tickers.csv`, `invalid_tickers.csv`

---

## 📈 Example Output

```
📊  Joel Greenblatt — Magic Formula Screener Results
--------------------------------------------------------------
  1. POS.L  | ROTC: 108.2% | Earnings Yield: 23.1% | EV/EBIT: 4.3× | Payback: 4.3 yrs
  2. CRL.L  | ROTC: 150.5% | Earnings Yield: 18.7% | EV/EBIT: 5.3× | Payback: 5.3 yrs
  3. NTBR.L | ROTC:  84.3% | Earnings Yield: 23.5% | EV/EBIT: 4.2× | Payback: 4.2 yrs
  4. AET.L  | ROTC:  62.4% | Earnings Yield: 74.4% | EV/EBIT: 1.3× | Payback: 1.3 yrs
--------------------------------------------------------------
💾  18 incomplete tickers saved to 'missing_tickers.csv'
🚫   5 invalid tickers saved to 'invalid_tickers.csv'
✅  Results saved to 'greenblatt_results.csv'
```

---

## 🧩 Notes

- For best results, keep under ~500 tickers per run (Yahoo rate limits apply).  
- Each new run overwrites previous CSVs for a clean snapshot.  
- Pure Python — no API keys or external accounts needed.  
- Ideal for quantitative and fundamental screening workflows.

---

## 👤 Author

**Steven McCormick**  
[GitHub](https://github.com/sjmccormickresearch)
