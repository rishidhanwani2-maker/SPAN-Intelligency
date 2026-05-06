import streamlit as st
import requests
import time
import threading
import json
import concurrent.futures
from datetime import datetime, timedelta
import pytz
import yfinance as yf

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OptionFlow — Real-Time Screener",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
:root{
  --bg:#0d1117;--surface:#161b22;--surface2:#1c2230;--surface3:#21262d;
  --border:#30363d;--text:#e6edf3;--muted:#7d8590;
  --green:#3fb950;--red:#f85149;--amber:#d29922;
  --blue:#58a6ff;--purple:#bc8cff;--teal:#39d353;
}
*{font-family:'DM Sans',sans-serif;box-sizing:border-box;}
html,body,.stApp{background:var(--bg)!important;color:var(--text)!important;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:1rem 1.6rem!important;max-width:100%!important;}

/* ── Header ── */
.app-header{display:flex;align-items:center;justify-content:space-between;
  padding:.8rem 0 1rem 0;border-bottom:1px solid var(--border);margin-bottom:.8rem;}
.app-logo{font-size:1.35rem;font-weight:700;letter-spacing:-.5px;}
.app-logo span{color:var(--blue);}
.live-badge{display:inline-flex;align-items:center;gap:5px;
  background:rgba(63,185,80,.1);border:1px solid rgba(63,185,80,.3);
  color:var(--green);font-size:.68rem;font-weight:600;
  padding:3px 10px;border-radius:20px;letter-spacing:.8px;}
.live-dot{width:6px;height:6px;border-radius:50%;
  background:var(--green);animation:pulse 1s infinite;}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.8)}}

/* ── Section label ── */
.sl{font-size:.6rem;font-weight:700;letter-spacing:2.5px;color:var(--muted);
  text-transform:uppercase;margin:1rem 0 .5rem 0;
  display:flex;align-items:center;gap:8px;}
.sl::after{content:'';flex:1;height:1px;background:var(--border);}

/* ── Ticker Card ── */
.tc{background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:11px 13px;position:relative;overflow:hidden;
  min-height:88px;transition:border-color .15s;}
.tc:hover{border-color:rgba(88,166,255,.4);}
.tc::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:10px 10px 0 0;}
.tc.up::before{background:linear-gradient(90deg,var(--green),transparent);}
.tc.dn::before{background:linear-gradient(90deg,var(--red),transparent);}
.tc.fl::before{background:linear-gradient(90deg,var(--muted),transparent);}
.tc.vx{background:linear-gradient(135deg,#15101f,var(--surface));border-color:rgba(188,140,255,.2);}
.tc-name{font-size:.65rem;color:var(--muted);font-weight:600;letter-spacing:.5px;margin-bottom:3px;text-transform:uppercase;}
.tc-price{font-size:1.08rem;font-weight:600;font-family:'DM Mono',monospace;line-height:1.2;}
.tc-price.vxc{color:var(--purple);}
.tc-row{display:flex;align-items:center;gap:7px;margin-top:3px;}
.tc-pct{font-size:.72rem;font-family:'DM Mono',monospace;font-weight:500;}
.tc-pts{font-size:.65rem;color:var(--muted);font-family:'DM Mono',monospace;}
.up-c{color:var(--green);} .dn-c{color:var(--red);} .fl-c{color:var(--muted);}

/* ── Flash on update ── */
@keyframes fup{0%{background:rgba(63,185,80,.2)}100%{background:transparent}}
@keyframes fdn{0%{background:rgba(248,81,73,.2)}100%{background:transparent}}
.fup{animation:fup .8s ease-out;} .fdn{animation:fdn .8s ease-out;}

/* ── Option Chain ── */
.oc-wrap{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px;overflow-x:auto;}
.oc-meta{display:flex;gap:18px;margin-bottom:10px;font-size:.72rem;flex-wrap:wrap;}
table.oc{width:100%;border-collapse:collapse;font-size:.73rem;font-family:'DM Mono',monospace;}
table.oc th{background:var(--surface2);color:var(--muted);padding:7px 8px;
  font-size:.58rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;
  border-bottom:1px solid var(--border);white-space:nowrap;}
table.oc td{padding:6px 8px;border-bottom:1px solid rgba(48,54,61,.4);white-space:nowrap;}
table.oc tr:hover td{background:var(--surface2);}
.atm td{background:rgba(31,111,235,.06)!important;}
.atm td:nth-child(5){border-left:2px solid var(--blue);border-right:2px solid var(--blue);}

/* ── News ── */
.news-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px;}
.news-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:13px 15px;transition:border-color .15s;}
.news-card:hover{border-color:rgba(88,166,255,.4);}
.news-source{font-size:.6rem;color:var(--muted);font-weight:600;letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px;}
.news-title{font-size:.82rem;font-weight:500;color:var(--text);line-height:1.4;margin-bottom:6px;}
.news-time{font-size:.62rem;color:var(--muted);}
.news-tag{display:inline-block;font-size:.58rem;font-weight:600;letter-spacing:.5px;
  padding:2px 7px;border-radius:4px;margin-right:4px;text-transform:uppercase;}
.tag-bull{background:rgba(63,185,80,.12);color:var(--green);border:1px solid rgba(63,185,80,.2);}
.tag-bear{background:rgba(248,81,73,.12);color:var(--red);border:1px solid rgba(248,81,73,.2);}
.tag-neut{background:rgba(125,133,144,.12);color:var(--muted);border:1px solid rgba(125,133,144,.2);}

/* ── Signal Box ── */
.signal-box{border-radius:10px;padding:14px 18px;margin-top:10px;border:1px solid;}
.signal-box.bull{background:rgba(63,185,80,.06);border-color:rgba(63,185,80,.25);}
.signal-box.bear{background:rgba(248,81,73,.06);border-color:rgba(248,81,73,.25);}
.signal-box.neut{background:rgba(125,133,144,.06);border-color:rgba(125,133,144,.2);}
.sig-title{font-size:.7rem;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}
.sig-bull{color:var(--green);} .sig-bear{color:var(--red);} .sig-neut{color:var(--muted);}
.sig-body{font-size:.82rem;line-height:1.6;color:var(--text);}
.sig-rec{font-size:.78rem;font-weight:600;margin-top:8px;padding:7px 12px;
  border-radius:7px;display:inline-block;}
.rec-sell{background:rgba(63,185,80,.1);color:var(--green);}
.rec-wait{background:rgba(210,153,34,.1);color:var(--amber);}
.rec-avoid{background:rgba(248,81,73,.1);color:var(--red);}

/* ── Footer ── */
.ts-bar{display:flex;justify-content:space-between;font-size:.62rem;color:var(--muted);
  padding:.5rem 0;border-top:1px solid var(--border);margin-top:.8rem;}

/* Streamlit widget overrides */
div[data-testid="stButton"] button{
  background:var(--surface2)!important;border:1px solid var(--border)!important;
  color:var(--text)!important;font-size:.73rem!important;padding:5px 12px!important;border-radius:7px!important;}
div[data-testid="stButton"] button:hover{border-color:var(--blue)!important;color:var(--blue)!important;}
div[data-testid="stSelectbox"] > div > div{
  background:var(--surface2)!important;border-color:var(--border)!important;color:var(--text)!important;}
</style>
""", unsafe_allow_html=True)

# ─── Symbol maps ───────────────────────────────────────────────────────────────
MARKETS = {
    "NIFTY 50":   "^NSEI",   "BANK NIFTY": "^NSEBANK",
    "SENSEX":     "^BSESN",  "GIFT NIFTY": "^NSEI",
    "NASDAQ":     "^IXIC",   "DOW JONES":  "^DJI",
    "S&P 500":    "^GSPC",   "DAX":        "^GDAXI",
    "FTSE 100":   "^FTSE",   "CAC 40":     "^FCHI",
    "ASX 200":    "^AXJO",   "NIKKEI 225": "^N225",
    "SHANGHAI":   "000001.SS",
}
VOLATILITY  = {"INDIA VIX": "^INDIAVIX", "US VIX": "^VIX"}
COMMODITIES = {"BRENT CRUDE": "BZ=F", "GOLD": "GC=F", "SILVER": "SI=F"}
MACRO       = {"US 10Y YIELD": "^TNX", "USD/INR": "INR=X"}
TOP_NIFTY   = {
    "RELIANCE":   "RELIANCE.NS", "TCS":       "TCS.NS",
    "HDFC BANK":  "HDFCBANK.NS", "INFY":      "INFY.NS",
    "ICICI BANK": "ICICIBANK.NS",
}
TOP_NASDAQ  = {"APPLE":"AAPL","NVIDIA":"NVDA","MICROSOFT":"MSFT","AMAZON":"AMZN","META":"META"}

ALL_SYMS = list(dict.fromkeys(
    list(MARKETS.values()) + list(VOLATILITY.values()) +
    list(COMMODITIES.values()) + list(MACRO.values()) +
    list(TOP_NIFTY.values()) + list(TOP_NASDAQ.values())
))

# ─── Helpers ───────────────────────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")

def fmt(v, d=2):
    if v is None: return "—"
    return f"{v:,.{d}f}"

def fmt_oi(v):
    if v is None: return "—"
    a = abs(v)
    s = "-" if v < 0 else ""
    if a >= 1_00_00_000: return f"{s}{a/1_00_00_000:.1f}Cr"
    if a >= 1_00_000:    return f"{s}{a/1_00_000:.1f}L"
    if a >= 1_000:       return f"{s}{a/1_000:.1f}K"
    return str(int(v))

def ago(ts):
    diff = datetime.now(IST) - datetime.fromtimestamp(ts, IST)
    m = int(diff.total_seconds() / 60)
    if m < 1: return "just now"
    if m < 60: return f"{m}m ago"
    return f"{m//60}h ago"

# ─── Data fetchers ─────────────────────────────────────────────────────────────

def fetch_one(sym):
    try:
        fi    = yf.Ticker(sym).fast_info
        price = getattr(fi, "last_price", None)
        prev  = getattr(fi, "previous_close", None)
        if price and prev and prev != 0:
            chg = price - prev
            pct = chg / prev * 100
        else:
            chg = pct = None
        return sym, {"price": price, "change": chg, "pct": pct}
    except Exception:
        return sym, {"price": None, "change": None, "pct": None}

def fetch_all(symbols):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        for sym, data in ex.map(fetch_one, symbols):
            results[sym] = data
    return results

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
        time.sleep(0.3)
        r  = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=8)
        d  = r.json()["records"]
        ul = d.get("underlyingValue", 0)
        exp = (d.get("expiryDates") or ["—"])[0]
        filt = [x for x in d.get("data", []) if x.get("expiryDate") == exp]
        strikes = sorted(set(x["strikePrice"] for x in filt))
        atm = min(strikes, key=lambda x: abs(x - ul)) if strikes else ul
        idx = strikes.index(atm) if atm in strikes else len(strikes)//2
        sel = set(strikes[max(0, idx-5): idx+6])
        rows = []
        for x in filt:
            sp = x.get("strikePrice")
            if sp not in sel: continue
            ce, pe = x.get("CE", {}), x.get("PE", {})
            rows.append({
                "strike": sp, "is_atm": sp == atm,
                "ce_ltp": ce.get("lastPrice",0),   "ce_oi": ce.get("openInterest",0),
                "ce_doi": ce.get("changeinOpenInterest",0), "ce_iv": ce.get("impliedVolatility",0),
                "pe_ltp": pe.get("lastPrice",0),   "pe_oi": pe.get("openInterest",0),
                "pe_doi": pe.get("changeinOpenInterest",0), "pe_iv": pe.get("impliedVolatility",0),
            })
        rows.sort(key=lambda x: x["strike"], reverse=True)
        return {"rows": rows, "ul": ul, "exp": exp, "atm": atm, "ok": True}
    except Exception as e:
        return {"rows": [], "ul": 0, "exp": "—", "atm": 0, "ok": False, "err": str(e)}

# ─── News fetcher ──────────────────────────────────────────────────────────────

def fetch_news():
    """
    Fetch news from multiple FREE sources:
    1. GNews API (free tier: 100 req/day)
    2. NewsData.io (free tier: 200 req/day)
    3. Yahoo Finance RSS (unlimited)
    4. Economic Times RSS (unlimited)
    Returns list of {title, source, url, published_at(unix), sentiment}
    """
    articles = []

    # ── Source 1: Yahoo Finance RSS (free, no key) ──
    rss_feeds = [
        ("Yahoo Finance", "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI,^NSEBANK&region=IN&lang=en-US"),
        ("ET Markets",    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Moneycontrol",  "https://www.moneycontrol.com/rss/latestnews.xml"),
    ]
    try:
        import xml.etree.ElementTree as ET
        for src_name, url in rss_feeds:
            try:
                r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    title = item.findtext("title", "").strip()
                    link  = item.findtext("link", "").strip()
                    pub   = item.findtext("pubDate", "")
                    if not title: continue
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub)
                        ts = int(dt.timestamp())
                    except Exception:
                        ts = int(time.time())
                    articles.append({
                        "title": title, "source": src_name,
                        "url": link, "ts": ts,
                        "sentiment": classify_sentiment(title),
                    })
            except Exception:
                pass
    except Exception:
        pass

    # ── Source 2: NSE Announcements (free) ──
    try:
        r = requests.get(
            "https://www.nseindia.com/api/corporate-announcements?index=equities&from_date=&to_date=&symbol=&issuer=",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"},
            timeout=5,
        )
        for a in r.json()[:5]:
            title = a.get("subject") or a.get("desc", "")
            articles.append({
                "title": f"[NSE] {title}",
                "source": "NSE India",
                "url": "https://www.nseindia.com",
                "ts": int(time.time()),
                "sentiment": classify_sentiment(title),
            })
    except Exception:
        pass

    # Deduplicate + sort by recency + limit 20
    seen = set()
    unique = []
    for a in sorted(articles, key=lambda x: x["ts"], reverse=True):
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
        if len(unique) >= 20: break

    return unique

def classify_sentiment(text):
    """Rule-based sentiment classifier for financial news."""
    t = text.lower()
    bull_kw = [
        "surge","rally","gain","rise","jump","high","record","up","bull","strong",
        "positive","boost","recover","growth","beat","profit","inflow","buy",
        "upgrade","breakout","support","holds","above","outperform",
    ]
    bear_kw = [
        "fall","drop","crash","decline","loss","sell","bear","weak","down","cut",
        "deficit","outflow","concern","risk","recession","inflation","rate hike",
        "pressure","below","underperform","downgrade","warning","sell-off","slump",
    ]
    bs = sum(1 for k in bull_kw if k in t)
    brs = sum(1 for k in bear_kw if k in t)
    if bs > brs: return "bull"
    if brs > bs: return "bear"
    return "neut"

def generate_signal(articles, quotes):
    """
    Generate option-selling signal from news + market data.
    Returns dict with: bias, summary, recommendation, reasoning
    """
    bull_count = sum(1 for a in articles if a["sentiment"] == "bull")
    bear_count = sum(1 for a in articles if a["sentiment"] == "bear")
    neut_count = sum(1 for a in articles if a["sentiment"] == "neut")
    total = max(len(articles), 1)

    # VIX reading
    vix_india = (quotes.get("^INDIAVIX") or {}).get("price")
    vix_us    = (quotes.get("^VIX") or {}).get("price")
    nifty_pct = (quotes.get("^NSEI") or {}).get("pct")
    bnf_pct   = (quotes.get("^NSEBANK") or {}).get("pct")

    # VIX interpretation
    vix_signal = "neut"
    vix_note   = ""
    if vix_india:
        if vix_india < 13:
            vix_signal = "bull"; vix_note = f"India VIX at {fmt(vix_india)} (very low) — premium rich, ideal for selling."
        elif vix_india < 18:
            vix_signal = "bull"; vix_note = f"India VIX at {fmt(vix_india)} (moderate) — decent premium for option sellers."
        elif vix_india < 25:
            vix_signal = "neut"; vix_note = f"India VIX at {fmt(vix_india)} (elevated) — premiums high but risk of big moves."
        else:
            vix_signal = "bear"; vix_note = f"India VIX at {fmt(vix_india)} (very high) — dangerous for naked option selling."

    # Market momentum
    mkt_note = ""
    if nifty_pct is not None and bnf_pct is not None:
        if abs(nifty_pct) < 0.5 and abs(bnf_pct) < 0.5:
            mkt_note = "Markets are range-bound today — favorable for short straddle/strangle."
        elif nifty_pct > 1.5:
            mkt_note = f"NIFTY up {fmt(nifty_pct)}% — consider selling calls at resistance."
        elif nifty_pct < -1.5:
            mkt_note = f"NIFTY down {fmt(abs(nifty_pct))}% — consider selling puts near support."
        else:
            mkt_note = f"NIFTY {fmt(nifty_pct)}% — directional bias weak, theta strategies viable."

    # News bias
    news_bias = "bull" if bull_count > bear_count else ("bear" if bear_count > bull_count else "neut")
    news_note = f"{bull_count} bullish, {bear_count} bearish, {neut_count} neutral headlines."

    # Final signal
    if vix_signal == "bear":
        bias = "bear"
        rec  = "⛔ AVOID SELLING — High VIX, wait for stability"
        rec_cls = "rec-avoid"
        summary = f"High volatility environment. {vix_note} {mkt_note} News flow: {news_note} Avoid short options until VIX normalises below 20."
    elif vix_signal == "bull" and news_bias != "bear":
        bias = "bull"
        rec  = "✅ SELL PREMIUM — Conditions favourable"
        rec_cls = "rec-sell"
        summary = f"Good setup for option sellers. {vix_note} {mkt_note} News flow: {news_note} Consider Iron Condor or short strangle on NIFTY/BNF at 1-2 SD levels."
    else:
        bias = "neut"
        rec  = "⏳ WAIT & WATCH — Mixed signals"
        rec_cls = "rec-wait"
        summary = f"Mixed signals — be cautious. {vix_note} {mkt_note} News flow: {news_note} Wait for clearer directional cue or VIX to settle before initiating shorts."

    return {"bias": bias, "summary": summary, "rec": rec, "rec_cls": rec_cls}

# ─── Card HTML ─────────────────────────────────────────────────────────────────
def card_html(label, d, prefix="", decimals=2, vix=False):
    p = d.get("price"); chg = d.get("change"); pct = d.get("pct")
    if p is None:
        return f'''<div class="tc fl">
            <div class="tc-name">{label}</div>
            <div class="tc-price">—</div>
            <div class="tc-row"><span class="tc-pct fl-c">— / —</span></div>
        </div>'''
    up = (chg or 0) >= 0
    dc = "up" if up else "dn"
    cc = "up-c" if up else "dn-c"
    ar = "▲" if up else "▼"
    sg = "+" if up else ""
    vc = "vxc" if vix else ""
    v2 = "vx" if vix else ""
    return f'''<div class="tc {dc} {v2}">
        <div class="tc-name">{label}</div>
        <div class="tc-price {vc}">{prefix}{fmt(p, decimals)}</div>
        <div class="tc-row">
            <span class="tc-pct {cc}">{ar} {sg}{fmt(pct,2)}%</span>
            <span class="tc-pts">{sg}{fmt(chg,2)}</span>
        </div>
    </div>'''

def section(t):
    st.markdown(f'<div class="sl">{t}</div>', unsafe_allow_html=True)

def render_group(sym_map, quotes, ncols, prefix="", decimals=2, vix=False):
    cols = st.columns(ncols)
    for i, (label, sym) in enumerate(sym_map.items()):
        with cols[i % ncols]:
            st.markdown(card_html(label, quotes.get(sym, {}), prefix, decimals, vix), unsafe_allow_html=True)

# ─── Static Header ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div class="app-logo">Option<span>Flow</span> ⚡</div>
  <div style="display:flex;align-items:center;gap:10px;">
    <span class="live-badge"><span class="live-dot"></span>LIVE</span>
    <span style="font-size:.65rem;color:var(--muted);">Real-Time Option Selling Screener</span>
  </div>
</div>""", unsafe_allow_html=True)

h1, h2, h3, h4 = st.columns([4, 1, 1, 1])
with h2:
    refresh_sec = st.selectbox("Speed", [3, 5, 10, 15], index=1, label_visibility="collapsed")
with h3:
    st.markdown('<div style="padding-top:4px;font-size:.65rem;color:var(--muted);">sec refresh</div>', unsafe_allow_html=True)
with h4:
    if st.button("↻ Force"):
        st.cache_data.clear(); st.rerun()

# ─── LIVE FRAGMENT — re-runs every N seconds without full page reload ──────────
@st.fragment(run_every=5)
def live_prices():
    now = datetime.now(IST).strftime("%d %b %Y  %H:%M:%S IST")
    st.markdown(f'<div style="font-size:.62rem;color:var(--muted);text-align:right;margin-bottom:.4rem;">⏱ {now}</div>', unsafe_allow_html=True)

    # Fetch all prices concurrently
    quotes = fetch_all(ALL_SYMS)

    # ── Markets ──────────────────────────────────────────────────────────────
    section("📊 Global Markets")
    render_group(MARKETS, quotes, ncols=7)

    # ── Volatility ───────────────────────────────────────────────────────────
    section("🌡 Volatility")
    vc = st.columns([1, 1, 5])
    for i, (label, sym) in enumerate(VOLATILITY.items()):
        with vc[i]:
            st.markdown(card_html(label, quotes.get(sym, {}), vix=True), unsafe_allow_html=True)

    # ── Commodities ──────────────────────────────────────────────────────────
    section("🛢 Commodities")
    render_group(COMMODITIES, quotes, ncols=7, prefix="$")

    # ── Macro ────────────────────────────────────────────────────────────────
    section("🏦 Macro")
    mc = st.columns([1, 1, 5])
    for i, (label, sym) in enumerate(MACRO.items()):
        with mc[i]:
            pr = "₹" if "INR" in sym else ""
            dc = 4 if "INR" in sym else 3
            st.markdown(card_html(label, quotes.get(sym, {}), prefix=pr, decimals=dc), unsafe_allow_html=True)

    # ── Stocks ───────────────────────────────────────────────────────────────
    section("📈 Top NIFTY 50 Stocks")
    render_group(TOP_NIFTY, quotes, ncols=5, prefix="₹")

    section("🇺🇸 Top NASDAQ Stocks")
    render_group(TOP_NASDAQ, quotes, ncols=5, prefix="$")

    # ── Option Chain ─────────────────────────────────────────────────────────
    section("⚡ NIFTY Option Chain — NSE Live")
    oc = fetch_oc()
    rows, ul, exp, atm = oc["rows"], oc["ul"], oc["exp"], oc["atm"]
    meta = f"""<div class="oc-meta">
        <span style="color:var(--muted)">Underlying: <strong style="color:var(--blue)">₹{fmt(ul)}</strong></span>
        <span style="color:var(--muted)">Expiry: <strong style="color:var(--text)">{exp}</strong></span>
        <span style="color:var(--muted)">ATM: <strong style="color:var(--amber)">{int(atm) if atm else '—'}</strong></span>
    </div>"""
    if rows:
        t = '<table class="oc"><thead><tr>'
        for h, c in [("CE LTP","green"),("CE OI","green"),("CE ΔOI","green"),("CE IV%","green"),
                      ("STRIKE","amber"),("PE IV%","red"),("PE ΔOI","red"),("PE OI","red"),("PE LTP","red")]:
            t += f'<th style="color:var(--{c})">{h}</th>'
        t += "</tr></thead><tbody>"
        for r in rows:
            ac = "atm" if r["is_atm"] else ""
            d1 = f'+{fmt_oi(r["ce_doi"])}' if r["ce_doi"] >= 0 else fmt_oi(r["ce_doi"])
            d2 = f'+{fmt_oi(r["pe_doi"])}' if r["pe_doi"] >= 0 else fmt_oi(r["pe_doi"])
            t += f"""<tr class="{ac}">
                <td style="color:var(--green)">{fmt(r['ce_ltp'])}</td>
                <td style="color:var(--muted)">{fmt_oi(r['ce_oi'])}</td>
                <td style="color:var(--green)">{d1}</td>
                <td>{fmt(r['ce_iv'])}%</td>
                <td style="color:var(--amber);font-weight:700;text-align:center">{int(r['strike'])}</td>
                <td>{fmt(r['pe_iv'])}%</td>
                <td style="color:var(--red)">{d2}</td>
                <td style="color:var(--muted)">{fmt_oi(r['pe_oi'])}</td>
                <td style="color:var(--red)">{fmt(r['pe_ltp'])}</td>
            </tr>"""
        t += "</tbody></table>"
        st.markdown(f'<div class="oc-wrap">{meta}{t}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="oc-wrap">{meta}<div style="color:var(--muted);font-size:.78rem;padding:10px 0">NSE blocks cloud IPs — run locally for live option chain.</div></div>', unsafe_allow_html=True)

    # ── NEWS + SIGNAL ─────────────────────────────────────────────────────────
    section("📰 Market News & Option Selling Signal")

    news = fetch_news()
    signal = generate_signal(news, quotes)

    # Signal box
    bias_map = {"bull": ("✅ BULLISH BIAS", "sig-bull", "bull"),
                "bear": ("⚠️ BEARISH BIAS", "sig-bear", "bear"),
                "neut": ("⏳ NEUTRAL", "sig-neut", "neut")}
    sig_label, sig_cls, sig_box_cls = bias_map[signal["bias"]]

    st.markdown(f"""
    <div class="signal-box {sig_box_cls}">
        <div class="sig-title {sig_cls}">{sig_label} — Option Selling Outlook</div>
        <div class="sig-body">{signal['summary']}</div>
        <span class="sig-rec {signal['rec_cls']}">{signal['rec']}</span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    # News grid
    if news:
        tag_map = {
            "bull": '<span class="news-tag tag-bull">BULLISH</span>',
            "bear": '<span class="news-tag tag-bear">BEARISH</span>',
            "neut": '<span class="news-tag tag-neut">NEUTRAL</span>',
        }
        grid = '<div class="news-grid">'
        for a in news[:12]:
            tag   = tag_map.get(a["sentiment"], "")
            title = a["title"][:110] + ("…" if len(a["title"]) > 110 else "")
            grid += f"""<div class="news-card">
                <div class="news-source">{a['source']}</div>
                <div class="news-title">{title}</div>
                <div>{tag}<span class="news-time">{ago(a['ts'])}</span></div>
            </div>"""
        grid += "</div>"
        st.markdown(grid, unsafe_allow_html=True)
    else:
        st.info("News loading… (RSS feeds may take a moment)")

    # Footer
    st.markdown(f"""
    <div class="ts-bar">
        <span>OptionFlow ⚡ — Option Selling Screener</span>
        <span>yfinance · NSE India · RSS Feeds · Refreshing every 5s</span>
        <span>Updated: {now}</span>
    </div>""", unsafe_allow_html=True)

live_prices()
