import streamlit as st
import streamlit.components.v1 as components
import requests
import time
import json
import concurrent.futures
from datetime import datetime, timedelta
import pytz
import yfinance as yf
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

st.set_page_config(
    page_title="OptionFlow Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit UI chrome
st.markdown("""
<style>
#MainMenu,footer,header,.stDeployButton{visibility:hidden;}
.block-container{padding:0!important;margin:0!important;max-width:100%!important;}
iframe{border:none!important;}
</style>
""", unsafe_allow_html=True)

IST = pytz.timezone("Asia/Kolkata")

# ── Symbol maps ──────────────────────────────────────────────────────────────
SYMBOLS = {
    # Markets
    "NIFTY":      {"sym": "^NSEI",      "label": "NIFTY 50",    "prefix": "₹", "dec": 2, "group": "markets"},
    "BANKNIFTY":  {"sym": "^NSEBANK",   "label": "BANK NIFTY",  "prefix": "₹", "dec": 2, "group": "markets"},
    "SENSEX":     {"sym": "^BSESN",     "label": "SENSEX",      "prefix": "₹", "dec": 2, "group": "markets"},
    "NASDAQ":     {"sym": "^IXIC",      "label": "NASDAQ",      "prefix": "",  "dec": 2, "group": "markets"},
    "DOW":        {"sym": "^DJI",       "label": "DOW JONES",   "prefix": "",  "dec": 2, "group": "markets"},
    "SP500":      {"sym": "^GSPC",      "label": "S&P 500",     "prefix": "",  "dec": 2, "group": "markets"},
    "DAX":        {"sym": "^GDAXI",     "label": "DAX",         "prefix": "",  "dec": 2, "group": "markets"},
    "FTSE":       {"sym": "^FTSE",      "label": "FTSE 100",    "prefix": "",  "dec": 2, "group": "markets"},
    "CAC":        {"sym": "^FCHI",      "label": "CAC 40",      "prefix": "",  "dec": 2, "group": "markets"},
    "ASX":        {"sym": "^AXJO",      "label": "ASX 200",     "prefix": "",  "dec": 2, "group": "markets"},
    "NIKKEI":     {"sym": "^N225",      "label": "NIKKEI 225",  "prefix": "",  "dec": 2, "group": "markets"},
    "SHANGHAI":   {"sym": "000001.SS",  "label": "SHANGHAI",    "prefix": "",  "dec": 2, "group": "markets"},
    # Volatility
    "INDIAVIX":   {"sym": "^INDIAVIX",  "label": "INDIA VIX",  "prefix": "",  "dec": 2, "group": "vix"},
    "USVIX":      {"sym": "^VIX",       "label": "US VIX",     "prefix": "",  "dec": 2, "group": "vix"},
    # Commodities
    "BRENT":      {"sym": "BZ=F",       "label": "BRENT CRUDE","prefix": "$", "dec": 2, "group": "commodities"},
    "GOLD":       {"sym": "GC=F",       "label": "GOLD",       "prefix": "$", "dec": 2, "group": "commodities"},
    "SILVER":     {"sym": "SI=F",       "label": "SILVER",     "prefix": "$", "dec": 2, "group": "commodities"},
    # Macro
    "US10Y":      {"sym": "^TNX",       "label": "US 10Y",     "prefix": "",  "dec": 3, "group": "macro"},
    "USDINR":     {"sym": "INR=X",      "label": "USD/INR",    "prefix": "₹", "dec": 4, "group": "macro"},
    # India stocks
    "RELIANCE":   {"sym": "RELIANCE.NS","label": "RELIANCE",   "prefix": "₹", "dec": 2, "group": "nifty_stocks"},
    "TCS":        {"sym": "TCS.NS",     "label": "TCS",        "prefix": "₹", "dec": 2, "group": "nifty_stocks"},
    "HDFCBANK":   {"sym": "HDFCBANK.NS","label": "HDFC BANK",  "prefix": "₹", "dec": 2, "group": "nifty_stocks"},
    "INFY":       {"sym": "INFY.NS",    "label": "INFY",       "prefix": "₹", "dec": 2, "group": "nifty_stocks"},
    "ICICIBANK":  {"sym": "ICICIBANK.NS","label":"ICICI BANK", "prefix": "₹", "dec": 2, "group": "nifty_stocks"},
    # US stocks
    "AAPL":       {"sym": "AAPL",       "label": "APPLE",      "prefix": "$", "dec": 2, "group": "nasdaq_stocks"},
    "NVDA":       {"sym": "NVDA",       "label": "NVIDIA",     "prefix": "$", "dec": 2, "group": "nasdaq_stocks"},
    "MSFT":       {"sym": "MSFT",       "label": "MICROSOFT",  "prefix": "$", "dec": 2, "group": "nasdaq_stocks"},
    "AMZN":       {"sym": "AMZN",       "label": "AMAZON",     "prefix": "$", "dec": 2, "group": "nasdaq_stocks"},
    "META":       {"sym": "META",       "label": "META",       "prefix": "$", "dec": 2, "group": "nasdaq_stocks"},
}

ALL_YF_SYMS = [v["sym"] for v in SYMBOLS.values()]

# ── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_one(item):
    key, cfg = item
    try:
        fi    = yf.Ticker(cfg["sym"]).fast_info
        price = getattr(fi, "last_price", None)
        prev  = getattr(fi, "previous_close", None)
        if price and prev and prev != 0:
            chg = price - prev
            pct = chg / prev * 100
        else:
            chg = pct = None
        return key, {"price": price, "change": chg, "pct": pct,
                     "label": cfg["label"], "prefix": cfg["prefix"],
                     "dec": cfg["dec"], "group": cfg["group"]}
    except Exception:
        return key, {"price": None, "change": None, "pct": None,
                     "label": cfg["label"], "prefix": cfg["prefix"],
                     "dec": cfg["dec"], "group": cfg["group"]}

@st.cache_data(ttl=8)
def fetch_all_prices():
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for key, data in ex.map(fetch_one, SYMBOLS.items()):
            results[key] = data
    return results

@st.cache_data(ttl=30)
def fetch_oc():
    try:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.nseindia.com/",
        })
        s.get("https://www.nseindia.com", timeout=5)
        time.sleep(0.3)
        s.get("https://www.nseindia.com/option-chain", timeout=5)
        time.sleep(0.2)
        r  = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=8)
        d  = r.json()["records"]
        ul = d.get("underlyingValue", 0)
        exp = (d.get("expiryDates") or ["—"])[0]
        filt = [x for x in d.get("data", []) if x.get("expiryDate") == exp]
        strikes = sorted(set(x["strikePrice"] for x in filt))
        atm = min(strikes, key=lambda x: abs(x - ul)) if strikes else ul
        idx = strikes.index(atm) if atm in strikes else len(strikes) // 2
        sel = set(strikes[max(0, idx - 5): idx + 6])
        rows = []
        for x in filt:
            sp = x.get("strikePrice")
            if sp not in sel: continue
            ce, pe = x.get("CE", {}), x.get("PE", {})
            rows.append({
                "strike": sp, "is_atm": sp == atm,
                "ce_ltp": ce.get("lastPrice", 0),
                "ce_oi":  ce.get("openInterest", 0),
                "ce_doi": ce.get("changeinOpenInterest", 0),
                "ce_iv":  ce.get("impliedVolatility", 0),
                "pe_ltp": pe.get("lastPrice", 0),
                "pe_oi":  pe.get("openInterest", 0),
                "pe_doi": pe.get("changeinOpenInterest", 0),
                "pe_iv":  pe.get("impliedVolatility", 0),
            })
        rows.sort(key=lambda x: x["strike"], reverse=True)
        return {"rows": rows, "ul": ul, "exp": exp, "atm": atm, "ok": True}
    except Exception as e:
        return {"rows": [], "ul": 0, "exp": "—", "atm": 0, "ok": False, "err": str(e)}

@st.cache_data(ttl=120)
def fetch_news():
    articles = []
    feeds = [
        ("ET Markets",      "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Moneycontrol",    "https://www.moneycontrol.com/rss/latestnews.xml"),
        ("LiveMint",        "https://www.livemint.com/rss/markets"),
        ("Reuters India",   "https://feeds.reuters.com/reuters/INbusinessNews"),
        ("Yahoo Finance",   "https://finance.yahoo.com/news/rssindex"),
        ("Bloomberg Mkts",  "https://feeds.bloomberg.com/markets/news.rss"),
        ("CNBC World",      "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
        ("FX Street",       "https://www.fxstreet.com/rss/news"),
    ]
    for src, url in feeds:
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in list(root.iter("item"))[:8]:
                title = (item.findtext("title") or "").strip()
                link  = (item.findtext("link") or "").strip()
                pub   = item.findtext("pubDate") or ""
                if not title: continue
                try:
                    ts = int(parsedate_to_datetime(pub).timestamp())
                except Exception:
                    ts = int(time.time())
                articles.append({
                    "title": title, "source": src,
                    "url": link, "ts": ts,
                    "sentiment": classify_sentiment(title),
                    "relevance": score_relevance(title),
                })
        except Exception:
            pass
    seen, unique = set(), []
    for a in sorted(articles, key=lambda x: -x["ts"]):
        if a["title"] not in seen and a["relevance"] > 0:
            seen.add(a["title"])
            unique.append(a)
        if len(unique) >= 24: break
    return unique

def score_relevance(text):
    t = text.lower()
    keywords = [
        "nifty","sensex","bank nifty","india","rbi","sebi","rupee","inr",
        "fed","rate","inflation","gdp","recession","oil","crude","gold",
        "trump","tariff","geopolit","war","china","us market","nasdaq",
        "dow","vix","volatility","option","derivative","market","stock",
        "budget","policy","election","modi","rbi","yield","dollar",
        "interest rate","cpi","wpi","iip","fii","dii","fpi",
        "monsoon","crude","opec","middle east","ukraine","taiwan",
        "earning","result","quarter","fiscal","deficit","surplus",
    ]
    score = sum(1 for k in keywords if k in t)
    return score

def classify_sentiment(text):
    t = text.lower()
    bull = ["surge","rally","gain","rise","jump","high","record","bull","strong",
            "positive","boost","recover","growth","beat","profit","inflow","buy",
            "upgrade","breakout","support","outperform","soar","climb","up","green"]
    bear = ["fall","drop","crash","decline","loss","sell","bear","weak","down","cut",
            "deficit","outflow","concern","risk","recession","inflation","rate hike",
            "pressure","underperform","downgrade","warning","selloff","slump","red",
            "tariff","war","sanction","ban","tension","crisis","fear","panic"]
    bs = sum(1 for k in bull if k in t)
    brs = sum(1 for k in bear if k in t)
    if bs > brs: return "bull"
    if brs > bs: return "bear"
    return "neut"

def generate_strategies(articles, prices):
    vix  = (prices.get("INDIAVIX") or {}).get("price")
    usvix= (prices.get("USVIX") or {}).get("price")
    nifty_price = (prices.get("NIFTY") or {}).get("price")
    nifty_pct   = (prices.get("NIFTY") or {}).get("pct")
    bnf_pct     = (prices.get("BANKNIFTY") or {}).get("pct")
    gold_pct    = (prices.get("GOLD") or {}).get("pct")
    usdinr_pct  = (prices.get("USDINR") or {}).get("pct")
    us10y       = (prices.get("US10Y") or {}).get("price")

    bull_news = sum(1 for a in articles if a["sentiment"] == "bull")
    bear_news = sum(1 for a in articles if a["sentiment"] == "bear")
    total_news = max(len(articles), 1)
    news_bias = "bull" if bull_news > bear_news * 1.3 else ("bear" if bear_news > bull_news * 1.3 else "neut")

    def safe(v, d=2): return f"{v:.{d}f}" if v is not None else "N/A"

    strategies = []

    # ── Strategy 1: Based on VIX ──────────────────────────────────────────────
    if vix is not None:
        if vix < 12:
            strategies.append({
                "name": "Short Iron Condor — NIFTY",
                "bias": "sell",
                "confidence": "HIGH",
                "why": f"India VIX at {safe(vix)} — extremely low. Market pricing in complacency. Premium is cheap but theta decay is fast.",
                "action": f"Sell NIFTY Iron Condor: Buy {int(nifty_price*0.97) if nifty_price else 'X-300'} PE + Sell {int(nifty_price*0.98) if nifty_price else 'X-200'} PE | Sell {int(nifty_price*1.02) if nifty_price else 'X+200'} CE + Buy {int(nifty_price*1.03) if nifty_price else 'X+300'} CE. Target: 50% premium decay.",
                "hedge": "Hedge with far OTM Puts (1 lot per 5 lots sold) as tail risk cover.",
                "risk": "Low VIX can spike suddenly on global news — keep stop at 1.5x premium received.",
            })
        elif vix < 16:
            strategies.append({
                "name": "Short Strangle — NIFTY Weekly",
                "bias": "sell",
                "confidence": "HIGH",
                "why": f"India VIX at {safe(vix)} — moderate, ideal zone for option sellers. Premium is decent, IV not too elevated.",
                "action": f"Sell NIFTY Weekly Strangle: Sell {int(nifty_price*0.975) if nifty_price else 'X-250'} PE + Sell {int(nifty_price*1.025) if nifty_price else 'X+250'} CE (nearest expiry). Collect 0.5-1% premium each side.",
                "hedge": "Convert to Iron Condor if market moves >1% intraday. Hedge 1 lot far OTM PE.",
                "risk": "Exit if NIFTY moves beyond either strike. Max loss = unlimited, manage actively.",
            })
        elif vix < 22:
            strategies.append({
                "name": "Credit Spread — Defined Risk",
                "bias": "sell",
                "confidence": "MEDIUM",
                "why": f"VIX at {safe(vix)} — elevated. Avoid naked selling. Use defined risk spreads to collect premium safely.",
                "action": f"Sell NIFTY Bull Put Spread: Sell {int(nifty_price*0.97) if nifty_price else 'ATM-300'} PE + Buy {int(nifty_price*0.955) if nifty_price else 'ATM-450'} PE. Or sell Bear Call Spread if bearish.",
                "hedge": "Already hedged by structure. Add long ATM straddle if VIX spikes above 20.",
                "risk": "Max loss = spread width - premium received. Risk is fully defined.",
            })
        else:
            strategies.append({
                "name": "⛔ AVOID SELLING — Buy Volatility",
                "bias": "avoid",
                "confidence": "HIGH",
                "why": f"India VIX at {safe(vix)} — very high. Option premiums are expensive. Sellers face huge gap risk.",
                "action": "Do NOT sell naked options. If trading, BUY options — Long Straddle or Long Strangle on NIFTY near ATM. VIX mean-reversion will compress premiums in your favour.",
                "hedge": "If already short, close immediately or buy ATM hedges.",
                "risk": "High VIX = large moves expected. Tail risk is extreme for sellers.",
            })

    # ── Strategy 2: Momentum based ────────────────────────────────────────────
    if nifty_pct is not None and bnf_pct is not None:
        if nifty_pct > 1.2:
            strategies.append({
                "name": "Bear Call Spread — NIFTY (Fade the Rally)",
                "bias": "sell",
                "confidence": "MEDIUM",
                "why": f"NIFTY up {safe(nifty_pct)}% today. Strong rally — CE premiums are inflated. Sell calls at resistance.",
                "action": f"Sell Bear Call Spread: Sell {int(nifty_price*1.015) if nifty_price else 'ATM+150'} CE + Buy {int(nifty_price*1.025) if nifty_price else 'ATM+250'} CE. IV crush likely after rally settles.",
                "hedge": "Keep stop if NIFTY breaks above sold strike by 0.5%.",
                "risk": "If bullish trend continues, exit at 2x premium received.",
            })
        elif nifty_pct < -1.2:
            strategies.append({
                "name": "Bull Put Spread — NIFTY (Buy the Dip Theta)",
                "bias": "sell",
                "confidence": "MEDIUM",
                "why": f"NIFTY down {safe(abs(nifty_pct))}% today. PE premiums are inflated due to fear. Sell puts at support.",
                "action": f"Sell Bull Put Spread: Sell {int(nifty_price*0.985) if nifty_price else 'ATM-150'} PE + Buy {int(nifty_price*0.975) if nifty_price else 'ATM-250'} PE. Collect inflated put premium.",
                "hedge": "Exit if NIFTY breaks below sold strike by 0.5%.",
                "risk": "If panic continues, close at 1.5x premium received.",
            })
        elif abs(nifty_pct) < 0.4 and abs(bnf_pct) < 0.4:
            strategies.append({
                "name": "Short Straddle — Range Day Setup",
                "bias": "sell",
                "confidence": "MEDIUM",
                "why": f"NIFTY flat ({safe(nifty_pct)}%), BNF flat ({safe(bnf_pct)}%). Market is consolidating. Theta decay accelerates on flat days.",
                "action": f"Sell NIFTY ATM Straddle: Sell {int(nifty_price) if nifty_price else 'ATM'} CE + {int(nifty_price) if nifty_price else 'ATM'} PE same expiry. Max profit if NIFTY closes near same level.",
                "hedge": "Convert to Iron Fly — buy wings 200 points away to limit risk.",
                "risk": "If market breaks range, square off immediately. Use 1% NIFTY move as SL.",
            })

    # ── Strategy 3: Global macro ──────────────────────────────────────────────
    if usvix and usvix > 20:
        strategies.append({
            "name": "Protective Hedge — US VIX Spike",
            "bias": "hedge",
            "confidence": "HIGH",
            "why": f"US VIX at {safe(usvix)} — above 20. US fear is high. Indian markets typically lag US by 1 session.",
            "action": "Buy NIFTY next-day ATM Put as overnight hedge. Ratio: 1 lot PE per ₹10L portfolio. This is pure insurance, not a trade.",
            "hedge": "This strategy IS the hedge.",
            "risk": "Premium paid is the max loss. Keep to 0.1-0.2% of portfolio.",
        })

    if us10y and us10y > 4.5:
        strategies.append({
            "name": "Sell Bank NIFTY Calls — Rising Yield Pressure",
            "bias": "sell",
            "confidence": "MEDIUM",
            "why": f"US 10Y yield at {safe(us10y, 3)}%. High yields pressure banking stocks via NIM compression fears. Bank NIFTY likely to underperform.",
            "action": "Sell Bank NIFTY Bear Call Spread: Sell ATM+200 CE + Buy ATM+400 CE (weekly expiry).",
            "hedge": "Buy 1 lot NIFTY CE as macro hedge if yield rise is global risk-on.",
            "risk": "Exit if Bank NIFTY rises more than 1% against position.",
        })

    # ── Strategy 4: News-driven ───────────────────────────────────────────────
    if news_bias == "bear" and bear_news >= 5:
        strategies.append({
            "name": "Short-Term Defensive — Bear News Flow",
            "bias": "hedge",
            "confidence": "MEDIUM",
            "why": f"{bear_news} bearish headlines detected. Negative news flow increases gap-down risk overnight.",
            "action": "If holding short puts: Roll down strikes by 100-200 points. Add 1 lot ATM PE as hedge. Reduce overall position size by 30%.",
            "hedge": "Long 1 lot next-week ATM PE as overnight gap protection.",
            "risk": "Cost of hedge should not exceed 15% of premium received.",
        })

    # Overall market signal
    if not strategies:
        strategies.append({
            "name": "Monitor — No Clear Setup",
            "bias": "wait",
            "confidence": "LOW",
            "why": "Insufficient data or mixed signals. Markets are in price discovery mode.",
            "action": "Stay on sidelines. Wait for VIX to settle, clearer trend to emerge, or expiry week for best theta plays.",
            "hedge": "No position = no risk.",
            "risk": "Missing a trade is better than a forced low-probability trade.",
        })

    return {
        "strategies": strategies,
        "bull_news": bull_news,
        "bear_news": bear_news,
        "news_bias": news_bias,
        "vix": vix,
        "nifty_pct": nifty_pct,
    }

# ── Fetch data ────────────────────────────────────────────────────────────────
prices  = fetch_all_prices()
oc      = fetch_oc()
news    = fetch_news()
signal  = generate_strategies(news, prices)

# Convert to JSON for JS
prices_json  = json.dumps(prices)
oc_json      = json.dumps(oc)
news_json    = json.dumps(news[:20])
signal_json  = json.dumps(signal)

now_ist = datetime.now(IST).strftime("%d %b %Y %H:%M:%S IST")

# ── Render the full HTML terminal ────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>OptionFlow Terminal</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
:root{{
  --bg:#080c12;
  --surface:#0d1420;
  --surface2:#111927;
  --surface3:#162030;
  --border:#1e2d3d;
  --border2:#243447;
  --text:#d4e4f7;
  --muted:#4a6278;
  --muted2:#334d61;
  --green:#00d084;
  --green2:#00ff9d;
  --red:#ff3b5c;
  --red2:#ff6080;
  --amber:#ffb300;
  --blue:#3b9eff;
  --blue2:#5eb5ff;
  --purple:#a78bfa;
  --teal:#06b6d4;
  --scanline:rgba(0,200,130,0.03);
}}
html,body{{background:var(--bg);color:var(--text);font-family:'Space Grotesk',sans-serif;height:100%;overflow-x:hidden;}}

/* scanline overlay */
body::before{{
  content:'';position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,var(--scanline) 2px,var(--scanline) 4px);
}}

/* ── Header ── */
.header{{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 20px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,#0a1018 0%,var(--bg) 100%);
  position:sticky;top:0;z-index:100;
}}
.logo{{font-size:1.2rem;font-weight:700;letter-spacing:-0.5px;}}
.logo span{{color:var(--green);}}
.logo sub{{font-size:.55rem;color:var(--muted);font-family:'JetBrains Mono',monospace;letter-spacing:2px;vertical-align:middle;margin-left:4px;}}
.header-right{{display:flex;align-items:center;gap:12px;}}
.live-pill{{
  display:flex;align-items:center;gap:5px;
  background:rgba(0,208,132,.08);border:1px solid rgba(0,208,132,.2);
  color:var(--green);font-size:.62rem;font-weight:600;
  padding:3px 10px;border-radius:20px;letter-spacing:1.5px;
  font-family:'JetBrains Mono',monospace;
}}
.dot{{width:5px;height:5px;border-radius:50%;background:var(--green);animation:blink 1s infinite;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
#clock{{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:var(--muted);}}
#fetch-status{{font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--muted2);}}

/* ── Layout ── */
.main{{padding:12px 18px;}}
.section-hd{{
  font-size:.58rem;font-weight:700;letter-spacing:3px;color:var(--muted);
  text-transform:uppercase;margin:16px 0 8px 0;
  display:flex;align-items:center;gap:10px;
}}
.section-hd::after{{content:'';flex:1;height:1px;background:var(--border);}}

/* ── Ticker Card ── */
.grid{{display:grid;gap:6px;}}
.g7{{grid-template-columns:repeat(7,1fr);}}
.g5{{grid-template-columns:repeat(5,1fr);}}
.g3{{grid-template-columns:repeat(3,1fr);}}
.g2{{grid-template-columns:repeat(2,1fr);}}
.g2-5{{grid-template-columns:repeat(2,1fr) 5fr;}}

.tc{{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:10px 12px;position:relative;overflow:hidden;cursor:default;
  transition:border-color .2s;
}}
.tc:hover{{border-color:var(--border2);}}
.tc::after{{
  content:'';position:absolute;top:0;left:0;right:0;height:1.5px;border-radius:8px 8px 0 0;
  background:var(--muted2);transition:background .3s;
}}
.tc.up::after{{background:linear-gradient(90deg,var(--green),transparent);}}
.tc.dn::after{{background:linear-gradient(90deg,var(--red),transparent);}}
.tc.vx{{background:linear-gradient(135deg,#0e0a1a,var(--surface));}}
.tc.vx::after{{background:linear-gradient(90deg,var(--purple),transparent)!important;}}

.tc-name{{font-size:.58rem;color:var(--muted);font-weight:600;letter-spacing:.8px;margin-bottom:4px;text-transform:uppercase;}}
.tc-price{{font-size:1rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:var(--text);line-height:1.2;transition:color .2s;}}
.tc-price.vxc{{color:var(--purple);}}
.tc-row{{display:flex;align-items:baseline;gap:6px;margin-top:2px;}}
.tc-pct{{font-size:.68rem;font-family:'JetBrains Mono',monospace;font-weight:500;}}
.tc-pts{{font-size:.6rem;color:var(--muted);font-family:'JetBrains Mono',monospace;}}
.up-c{{color:var(--green);}}
.dn-c{{color:var(--red);}}
.fl-c{{color:var(--muted);}}

/* flash on price update — NO blink, just subtle glow */
@keyframes glow-up{{0%{{box-shadow:0 0 0 1px rgba(0,208,132,.5),inset 0 0 12px rgba(0,208,132,.06)}}100%{{box-shadow:none}}}}
@keyframes glow-dn{{0%{{box-shadow:0 0 0 1px rgba(255,59,92,.5),inset 0 0 12px rgba(255,59,92,.06)}}100%{{box-shadow:none}}}}
.glow-up{{animation:glow-up .8s ease-out;}}
.glow-dn{{animation:glow-dn .8s ease-out;}}

/* ── Option Chain ── */
.oc-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:12px;overflow-x:auto;}}
.oc-meta{{display:flex;gap:16px;margin-bottom:10px;font-size:.68rem;flex-wrap:wrap;}}
.oc-meta strong{{font-family:'JetBrains Mono',monospace;}}
table.oc{{width:100%;border-collapse:collapse;font-size:.68rem;font-family:'JetBrains Mono',monospace;}}
table.oc th{{
  background:var(--surface2);color:var(--muted);padding:6px 8px;
  font-size:.55rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;
  border-bottom:1px solid var(--border);white-space:nowrap;
}}
table.oc td{{padding:5px 8px;border-bottom:1px solid rgba(30,45,61,.5);white-space:nowrap;}}
table.oc tr:hover td{{background:var(--surface2);}}
.atm td{{background:rgba(59,158,255,.05)!important;}}
.atm td:nth-child(5){{border-left:1px solid var(--blue);border-right:1px solid var(--blue);}}

/* ── News ── */
.news-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;}}
.nc{{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:11px 13px;transition:border-color .2s;cursor:pointer;text-decoration:none;display:block;
}}
.nc:hover{{border-color:var(--border2);}}
.nc.bull-n{{border-left:2px solid var(--green);}}
.nc.bear-n{{border-left:2px solid var(--red);}}
.nc.neut-n{{border-left:2px solid var(--muted2);}}
.nc-src{{font-size:.55rem;color:var(--muted);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;}}
.nc-title{{font-size:.75rem;color:var(--text);line-height:1.45;margin-bottom:5px;font-weight:400;}}
.nc-foot{{display:flex;align-items:center;gap:6px;}}
.nc-tag{{font-size:.52rem;font-weight:700;letter-spacing:.8px;padding:2px 6px;border-radius:3px;text-transform:uppercase;}}
.tag-bull{{background:rgba(0,208,132,.1);color:var(--green);}}
.tag-bear{{background:rgba(255,59,92,.1);color:var(--red);}}
.tag-neut{{background:rgba(74,98,120,.15);color:var(--muted);}}
.nc-time{{font-size:.55rem;color:var(--muted);font-family:'JetBrains Mono',monospace;}}

/* ── Strategy Cards ── */
.strat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;}}
.sc{{
  background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px 16px;
  position:relative;overflow:hidden;
}}
.sc.sell{{border-left:3px solid var(--green);}}
.sc.hedge{{border-left:3px solid var(--amber);}}
.sc.avoid{{border-left:3px solid var(--red);}}
.sc.wait{{border-left:3px solid var(--muted2);}}
.sc-badge{{
  font-size:.55rem;font-weight:700;letter-spacing:1px;padding:2px 8px;border-radius:3px;
  text-transform:uppercase;display:inline-block;margin-bottom:6px;
}}
.badge-sell{{background:rgba(0,208,132,.1);color:var(--green);}}
.badge-hedge{{background:rgba(255,179,0,.1);color:var(--amber);}}
.badge-avoid{{background:rgba(255,59,92,.1);color:var(--red);}}
.badge-wait{{background:rgba(74,98,120,.1);color:var(--muted);}}
.conf-high{{color:var(--green);font-size:.55rem;font-weight:700;margin-left:6px;}}
.conf-med{{color:var(--amber);font-size:.55rem;font-weight:700;margin-left:6px;}}
.conf-low{{color:var(--muted);font-size:.55rem;font-weight:700;margin-left:6px;}}
.sc-name{{font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:6px;}}
.sc-why{{font-size:.72rem;color:var(--muted);line-height:1.5;margin-bottom:8px;}}
.sc-action{{
  background:var(--surface2);border:1px solid var(--border);border-radius:5px;
  padding:8px 10px;font-size:.7rem;color:var(--text);line-height:1.5;margin-bottom:6px;
  font-family:'JetBrains Mono',monospace;
}}
.sc-label{{font-size:.55rem;color:var(--muted);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px;}}
.sc-hedge{{font-size:.68rem;color:var(--amber);line-height:1.4;margin-bottom:5px;}}
.sc-risk{{font-size:.65rem;color:var(--red2);line-height:1.4;}}

/* ── Signal Summary Bar ── */
.sig-bar{{
  border-radius:8px;padding:12px 16px;margin-bottom:10px;border:1px solid;
  display:flex;align-items:center;gap:16px;
}}
.sig-bull{{background:rgba(0,208,132,.04);border-color:rgba(0,208,132,.2);}}
.sig-bear{{background:rgba(255,59,92,.04);border-color:rgba(255,59,92,.2);}}
.sig-neut{{background:rgba(74,98,120,.06);border-color:rgba(30,45,61,.5);}}
.sig-icon{{font-size:1.5rem;}}
.sig-text h3{{font-size:.82rem;font-weight:600;margin-bottom:2px;}}
.sig-text p{{font-size:.7rem;color:var(--muted);line-height:1.4;}}
.news-stat{{
  text-align:center;padding:6px 12px;border-radius:6px;background:var(--surface2);
  border:1px solid var(--border);white-space:nowrap;
}}
.news-stat .n{{font-size:1rem;font-weight:700;font-family:'JetBrains Mono',monospace;}}
.news-stat .l{{font-size:.55rem;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;}}

/* ── Footer ── */
.footer{{
  font-size:.58rem;color:var(--muted2);
  padding:10px 18px;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;margin-top:8px;
  font-family:'JetBrains Mono',monospace;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:4px;}}
</style>
</head>
<body>

<!-- ── Header ── -->
<div class="header">
  <div class="logo">Option<span>Flow</span><sub>TERMINAL</sub></div>
  <div class="header-right">
    <span id="fetch-status">initializing...</span>
    <span id="clock"></span>
    <span class="live-pill"><span class="dot"></span>LIVE</span>
  </div>
</div>

<div class="main" id="app">

<!-- ── MARKETS ── -->
<div class="section-hd">📊 Global Markets</div>
<div class="grid g7" id="markets-grid"></div>

<!-- ── VIX ── -->
<div class="section-hd">🌡 Volatility Index</div>
<div class="grid" style="grid-template-columns:repeat(2,1fr) 5fr" id="vix-grid"></div>

<!-- ── COMMODITIES ── -->
<div class="section-hd">🛢 Commodities</div>
<div class="grid" style="grid-template-columns:repeat(3,1fr) 4fr" id="comm-grid"></div>

<!-- ── MACRO ── -->
<div class="section-hd">🏦 Macro</div>
<div class="grid" style="grid-template-columns:repeat(2,1fr) 5fr" id="macro-grid"></div>

<!-- ── NIFTY STOCKS ── -->
<div class="section-hd">📈 Top NIFTY 50 Stocks</div>
<div class="grid g5" id="nifty-stocks-grid"></div>

<!-- ── NASDAQ STOCKS ── -->
<div class="section-hd">🇺🇸 Top NASDAQ Stocks</div>
<div class="grid g5" id="nasdaq-stocks-grid"></div>

<!-- ── OPTION CHAIN ── -->
<div class="section-hd">⚡ NIFTY Option Chain — NSE Live</div>
<div class="oc-wrap" id="oc-wrap">Loading option chain...</div>

<!-- ── NEWS + SIGNAL ── -->
<div class="section-hd">📰 Market Intelligence & Trading Signals</div>
<div id="signal-area"></div>
<div id="news-area"></div>

</div>

<div class="footer">
  <span>OptionFlow Terminal ⚡ — For Educational Purposes Only. Not Financial Advice.</span>
  <span>Data: yfinance · NSE India · RSS Feeds</span>
  <span id="last-update">Last update: {now_ist}</span>
</div>

<script>
// ── Initial data from Python ──────────────────────────────────────────────────
let prices  = {prices_json};
let oc      = {oc_json};
let news    = {news_json};
let signal  = {signal_json};
let prevPrices = {{}};

// ── Clock ─────────────────────────────────────────────────────────────────────
function updateClock() {{
  const now = new Date();
  const ist = new Date(now.toLocaleString("en-US", {{timeZone:"Asia/Kolkata"}}));
  const pad = n => String(n).padStart(2,'0');
  document.getElementById('clock').textContent =
    pad(ist.getDate()) + ' ' + ist.toLocaleString('en-US',{{month:'short'}}) + ' ' +
    pad(ist.getHours()) + ':' + pad(ist.getMinutes()) + ':' + pad(ist.getSeconds()) + ' IST';
}}
setInterval(updateClock, 1000);
updateClock();

// ── Format helpers ────────────────────────────────────────────────────────────
function fmt(v, d=2) {{
  if (v == null) return '—';
  return v.toLocaleString('en-IN', {{minimumFractionDigits:d, maximumFractionDigits:d}});
}}
function fmtOI(v) {{
  if (v == null) return '—';
  const a = Math.abs(v), s = v < 0 ? '-' : '';
  if (a >= 1e7) return s + (a/1e7).toFixed(1) + 'Cr';
  if (a >= 1e5) return s + (a/1e5).toFixed(1) + 'L';
  if (a >= 1e3) return s + (a/1e3).toFixed(1) + 'K';
  return String(Math.round(v));
}}
function ago(ts) {{
  const m = Math.floor((Date.now()/1000 - ts) / 60);
  if (m < 1) return 'just now';
  if (m < 60) return m + 'm ago';
  return Math.floor(m/60) + 'h ago';
}}

// ── Render a single ticker card ───────────────────────────────────────────────
function renderCard(key, d, isVix=false) {{
  const p = d.price, chg = d.change, pct = d.pct;
  const prefix = d.prefix || '';
  const dec = d.dec || 2;
  const up = chg != null && chg >= 0;
  const dirCls = chg == null ? '' : (up ? 'up' : 'dn');
  const cc = chg == null ? 'fl-c' : (up ? 'up-c' : 'dn-c');
  const ar = chg == null ? '' : (up ? '▲' : '▼');
  const sg = chg != null && chg >= 0 ? '+' : '';
  const vxc = isVix ? 'vxc' : '';
  const vxCard = isVix ? 'vx' : '';

  const prev = prevPrices[key];
  let glowCls = '';
  if (prev != null && p != null && p !== prev) {{
    glowCls = p > prev ? 'glow-up' : 'glow-dn';
  }}

  return `<div class="tc ${{dirCls}} ${{vxCard}} ${{glowCls}}" id="tc-${{key}}">
    <div class="tc-name">${{d.label}}</div>
    <div class="tc-price ${{vxc}}">${{p != null ? prefix + fmt(p, dec) : '—'}}</div>
    <div class="tc-row">
      <span class="tc-pct ${{cc}}">${{pct != null ? ar+' '+sg+fmt(pct)+'%' : '—'}}</span>
      <span class="tc-pts">${{chg != null ? sg+fmt(chg) : ''}}</span>
    </div>
  </div>`;
}}

// ── Render all grids ──────────────────────────────────────────────────────────
const MARKET_KEYS  = ['NIFTY','BANKNIFTY','SENSEX','NASDAQ','DOW','SP500','DAX','FTSE','CAC','ASX','NIKKEI','SHANGHAI'];
const VIX_KEYS     = ['INDIAVIX','USVIX'];
const COMM_KEYS    = ['BRENT','GOLD','SILVER'];
const MACRO_KEYS   = ['US10Y','USDINR'];
const NIFTY_KEYS   = ['RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK'];
const NASDAQ_KEYS  = ['AAPL','NVDA','MSFT','AMZN','META'];

function renderGroup(gridId, keys, isVix=false) {{
  const el = document.getElementById(gridId);
  if (!el) return;
  el.innerHTML = keys.map(k => renderCard(k, prices[k] || {{}}, isVix)).join('');
}}

function renderOC() {{
  const el = document.getElementById('oc-wrap');
  if (!oc.rows || oc.rows.length === 0) {{
    el.innerHTML = `<div class="oc-meta">
      <span style="color:var(--muted)">Underlying: <strong style="color:var(--blue);font-family:'JetBrains Mono',monospace">₹${{fmt(oc.ul)}}</strong></span>
      <span style="color:var(--muted)">Expiry: <strong>${{oc.exp}}</strong></span>
    </div>
    <div style="color:var(--muted);font-size:.72rem;padding:10px 0">
      NSE blocks cloud IPs. Option chain unavailable on Streamlit Cloud. Run locally for live chain.
    </div>`;
    return;
  }}
  let html = `<div class="oc-meta">
    <span style="color:var(--muted)">Underlying: <strong style="color:var(--blue);font-family:'JetBrains Mono',monospace">₹${{fmt(oc.ul)}}</strong></span>
    <span style="color:var(--muted)">Expiry: <strong style="font-family:'JetBrains Mono',monospace">${{oc.exp}}</strong></span>
    <span style="color:var(--muted)">ATM Strike: <strong style="color:var(--amber);font-family:'JetBrains Mono',monospace">${{oc.atm}}</strong></span>
  </div>
  <table class="oc"><thead><tr>
    <th style="color:var(--green)">CE LTP</th><th style="color:var(--green)">CE OI</th>
    <th style="color:var(--green)">CE ΔOI</th><th style="color:var(--green)">CE IV%</th>
    <th style="color:var(--amber)">STRIKE</th>
    <th style="color:var(--red)">PE IV%</th><th style="color:var(--red)">PE ΔOI</th>
    <th style="color:var(--red)">PE OI</th><th style="color:var(--red)">PE LTP</th>
  </tr></thead><tbody>`;
  oc.rows.forEach(r => {{
    const ac = r.is_atm ? 'atm' : '';
    const d1 = (r.ce_doi >= 0 ? '+' : '') + fmtOI(r.ce_doi);
    const d2 = (r.pe_doi >= 0 ? '+' : '') + fmtOI(r.pe_doi);
    html += `<tr class="${{ac}}">
      <td style="color:var(--green)">${{fmt(r.ce_ltp)}}</td>
      <td style="color:var(--muted)">${{fmtOI(r.ce_oi)}}</td>
      <td style="color:${{r.ce_doi>=0?'var(--green)':'var(--red)'}}">${{d1}}</td>
      <td>${{fmt(r.ce_iv)}}%</td>
      <td style="color:var(--amber);font-weight:700;text-align:center">${{r.strike}}</td>
      <td>${{fmt(r.pe_iv)}}%</td>
      <td style="color:${{r.pe_doi>=0?'var(--green)':'var(--red)'}}">${{d2}}</td>
      <td style="color:var(--muted)">${{fmtOI(r.pe_oi)}}</td>
      <td style="color:var(--red)">${{fmt(r.pe_ltp)}}</td>
    </tr>`;
  }});
  html += '</tbody></table>';
  el.innerHTML = html;
}}

function renderSignal() {{
  const s = signal;
  const biasMap = {{
    bull: {{cls:'sig-bull', icon:'✅', title:'BULLISH BIAS — Sell Premium'}},
    bear: {{cls:'sig-bear', icon:'⚠️', title:'BEARISH BIAS — Hedge First'}},
    neut: {{cls:'sig-neut', icon:'⏳', title:'NEUTRAL — Wait for Setup'}},
  }};
  const b = biasMap[s.news_bias] || biasMap.neut;
  let html = `<div class="sig-bar ${{b.cls}}">
    <span class="sig-icon">${{b.icon}}</span>
    <div class="sig-text">
      <h3 style="color:${{s.news_bias==='bull'?'var(--green)':s.news_bias==='bear'?'var(--red)':'var(--muted)'}}">${{b.title}}</h3>
      <p>News: ${{s.bull_news}} bullish · ${{s.bear_news}} bearish headlines | India VIX: ${{s.vix!=null?s.vix.toFixed(2):'N/A'}} | NIFTY: ${{s.nifty_pct!=null?(s.nifty_pct>=0?'+':'')+s.nifty_pct.toFixed(2)+'%':'N/A'}}</p>
    </div>
    <div style="display:flex;gap:6px;margin-left:auto">
      <div class="news-stat"><div class="n" style="color:var(--green)">${{s.bull_news}}</div><div class="l">Bull</div></div>
      <div class="news-stat"><div class="n" style="color:var(--red)">${{s.bear_news}}</div><div class="l">Bear</div></div>
    </div>
  </div>`;

  // Strategy cards
  html += '<div class="strat-grid">';
  (s.strategies || []).forEach(st => {{
    const bMap = {{sell:'badge-sell',hedge:'badge-hedge',avoid:'badge-avoid',wait:'badge-wait'}};
    const cMap = {{HIGH:'conf-high',MEDIUM:'conf-med',LOW:'conf-low'}};
    html += `<div class="sc ${{st.bias}}">
      <div>
        <span class="sc-badge ${{bMap[st.bias]||'badge-wait'}}">${{st.bias.toUpperCase()}}</span>
        <span class="${{cMap[st.confidence]||'conf-low'}}">● ${{st.confidence}}</span>
      </div>
      <div class="sc-name">${{st.name}}</div>
      <div class="sc-why">${{st.why}}</div>
      <div class="sc-label">📋 Action</div>
      <div class="sc-action">${{st.action}}</div>
      <div class="sc-label">🛡 Hedge</div>
      <div class="sc-hedge">${{st.hedge}}</div>
      <div class="sc-label">⚠️ Risk</div>
      <div class="sc-risk">${{st.risk}}</div>
    </div>`;
  }});
  html += '</div>';
  document.getElementById('signal-area').innerHTML = html;
}}

function renderNews() {{
  if (!news || news.length === 0) {{
    document.getElementById('news-area').innerHTML = '<div style="color:var(--muted);font-size:.72rem;padding:10px 0">Loading news…</div>';
    return;
  }}
  const tagMap = {{bull:'tag-bull',bear:'tag-bear',neut:'tag-neut'}};
  const tagLabel = {{bull:'BULLISH',bear:'BEARISH',neut:'NEUTRAL'}};
  let html = '<div class="section-hd" style="margin-top:14px">🗞 Latest Market News</div><div class="news-grid">';
  news.slice(0,18).forEach(a => {{
    const t = a.title.length > 95 ? a.title.slice(0,95)+'…' : a.title;
    const bc = a.sentiment === 'bull' ? 'bull-n' : a.sentiment === 'bear' ? 'bear-n' : 'neut-n';
    html += `<a class="nc ${{bc}}" href="${{a.url}}" target="_blank" rel="noopener">
      <div class="nc-src">${{a.source}}</div>
      <div class="nc-title">${{t}}</div>
      <div class="nc-foot">
        <span class="nc-tag ${{tagMap[a.sentiment]}}">${{tagLabel[a.sentiment]}}</span>
        <span class="nc-time">${{ago(a.ts)}}</span>
      </div>
    </a>`;
  }});
  html += '</div>';
  document.getElementById('news-area').innerHTML = html;
}}

// ── Initial render ────────────────────────────────────────────────────────────
function renderAll() {{
  renderGroup('markets-grid', MARKET_KEYS);
  renderGroup('vix-grid', VIX_KEYS, true);
  renderGroup('comm-grid', COMM_KEYS);
  renderGroup('macro-grid', MACRO_KEYS);
  renderGroup('nifty-stocks-grid', NIFTY_KEYS);
  renderGroup('nasdaq-stocks-grid', NASDAQ_KEYS);
  renderOC();
  renderSignal();
  renderNews();
}}
renderAll();

// ── Live price polling via Streamlit's own rerun mechanism ───────────────────
// We use the parent window's postMessage to trigger Streamlit re-fetch
// but update prices IN-PLACE without page reload using DOM diffing

let fetchInterval = null;
let isFirstLoad = true;

async function pollPrices() {{
  document.getElementById('fetch-status').textContent = 'fetching...';
  try {{
    // Fetch from Yahoo Finance Finance directly via a CORS-friendly proxy
    // Use allorigins as CORS proxy for Yahoo Finance JSON API
    const symsToFetch = [
      '^NSEI','^NSEBANK','^BSESN','^IXIC','^DJI','^GSPC','^GDAXI',
      '^FTSE','^FCHI','^AXJO','^N225','000001.SS',
      '^INDIAVIX','^VIX',
      'BZ=F','GC=F','SI=F',
      '^TNX','INR=X',
      'RELIANCE.NS','TCS.NS','HDFCBANK.NS','INFY.NS','ICICIBANK.NS',
      'AAPL','NVDA','MSFT','AMZN','META'
    ];

    const symStr = symsToFetch.join('%2C');
    const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${{symStr}}&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent,regularMarketPreviousClose`;
    
    // Use allorigins CORS proxy
    const proxyUrl = `https://api.allorigins.win/get?url=${{encodeURIComponent(url)}}`;
    const resp = await fetch(proxyUrl, {{signal: AbortSignal.timeout(8000)}});
    const wrapper = await resp.json();
    const data = JSON.parse(wrapper.contents);
    
    const result = data?.quoteResponse?.result || [];
    
    // Map Yahoo sym -> our key
    const symToKey = {{}};
    Object.entries(prices).forEach(([k, v]) => {{
      symToKey[v.label] = k; // fallback
    }});
    // Direct symbol map
    const directMap = {{
      '^NSEI':'NIFTY','^NSEBANK':'BANKNIFTY','^BSESN':'SENSEX',
      '^IXIC':'NASDAQ','^DJI':'DOW','^GSPC':'SP500','^GDAXI':'DAX',
      '^FTSE':'FTSE','^FCHI':'CAC','^AXJO':'ASX','^N225':'NIKKEI',
      '000001.SS':'SHANGHAI','^INDIAVIX':'INDIAVIX','^VIX':'USVIX',
      'BZ=F':'BRENT','GC=F':'GOLD','SI=F':'SILVER',
      '^TNX':'US10Y','INR=X':'USDINR',
      'RELIANCE.NS':'RELIANCE','TCS.NS':'TCS','HDFCBANK.NS':'HDFCBANK',
      'INFY.NS':'INFY','ICICIBANK.NS':'ICICIBANK',
      'AAPL':'AAPL','NVDA':'NVDA','MSFT':'MSFT','AMZN':'AMZN','META':'META',
    }};

    result.forEach(q => {{
      const key = directMap[q.symbol];
      if (!key || !prices[key]) return;
      const p = q.regularMarketPrice;
      const chg = q.regularMarketChange;
      const pct = q.regularMarketChangePercent;
      if (p == null) return;

      prevPrices[key] = prices[key].price;
      prices[key] = {{...prices[key], price:p, change:chg, pct:pct}};
    }});

    // Update cards in-place (NO page reload, NO flicker)
    [...MARKET_KEYS,...VIX_KEYS,...COMM_KEYS,...MACRO_KEYS,...NIFTY_KEYS,...NASDAQ_KEYS].forEach(k => {{
      const el = document.getElementById('tc-'+k);
      if (el) {{
        const d = prices[k] || {{}};
        const isVix = VIX_KEYS.includes(k);
        const newHtml = renderCardHTML(k, d, isVix);
        // Only update if price changed
        if (prevPrices[k] !== (prices[k]||{{}}).price) {{
          el.outerHTML = newHtml;
        }}
      }}
    }});

    const now = new Date().toLocaleTimeString('en-IN', {{timeZone:'Asia/Kolkata',hour12:false}});
    document.getElementById('fetch-status').textContent = `✓ ${{now}}`;
    document.getElementById('last-update').textContent = `Last update: ${{now}} IST`;

  }} catch(e) {{
    document.getElementById('fetch-status').textContent = `⚠ retry...`;
    console.warn('Price fetch error:', e);
  }}
}}

// Pure HTML renderer (no DOM dependency, used for update)
function renderCardHTML(key, d, isVix=false) {{
  const p = d.price, chg = d.change, pct = d.pct;
  const prefix = d.prefix || '';
  const dec = d.dec || 2;
  const up = chg != null && chg >= 0;
  const dirCls = chg == null ? '' : (up ? 'up' : 'dn');
  const cc = chg == null ? 'fl-c' : (up ? 'up-c' : 'dn-c');
  const ar = chg == null ? '' : (up ? '▲' : '▼');
  const sg = chg != null && chg >= 0 ? '+' : '';
  const vxc = isVix ? 'vxc' : '';
  const vxCard = isVix ? 'vx' : '';

  const prev = prevPrices[key];
  let glowCls = '';
  if (prev != null && p != null && p !== prev) {{
    glowCls = p > prev ? 'glow-up' : 'glow-dn';
  }}

  return `<div class="tc ${{dirCls}} ${{vxCard}} ${{glowCls}}" id="tc-${{key}}">
    <div class="tc-name">${{d.label}}</div>
    <div class="tc-price ${{vxc}}">${{p != null ? prefix + fmt(p, dec) : '—'}}</div>
    <div class="tc-row">
      <span class="tc-pct ${{cc}}">${{pct != null ? ar+' '+sg+fmt(pct)+'%' : '—'}}</span>
      <span class="tc-pts">${{chg != null ? sg+fmt(chg) : ''}}</span>
    </div>
  </div>`;
}}

// ── Start polling every 3 seconds ─────────────────────────────────────────────
setTimeout(pollPrices, 1000); // first fetch after 1s
setInterval(pollPrices, 3000); // then every 3s

</script>
</body>
</html>"""

components.html(HTML, height=4200, scrolling=True)
