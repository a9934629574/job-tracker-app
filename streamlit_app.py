import html
import re
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Job Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ───────────────────────── Style ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;700;800&family=Inter:wght@400;500;600&display=swap');
:root{--bg:#0B1020;--panel:#141B30;--line:#26304D;--ink:#EEF1FB;--muted:#8F9ABB;
--a:#8B6CFF;--b:#22D3EE;--ok:#34D399;--wait:#FBBF24;--bad:#F87171;}
html,body,.stApp{background:radial-gradient(1200px 500px at 85% -10%,rgba(139,108,255,.18),transparent),var(--bg)!important;
  color:var(--ink)!important;font-family:'Inter',sans-serif;}
header[data-testid="stHeader"],#MainMenu,footer{display:none;}
.block-container{max-width:1250px;padding:2rem 2rem 4rem;}
h1,h2,h3,.sora{font-family:'Sora',sans-serif!important;letter-spacing:-.02em;}

.hero h1{font-size:2.6rem;font-weight:800;margin:0;
  background:linear-gradient(90deg,var(--a),var(--b));-webkit-background-clip:text;background-clip:text;color:transparent;}
.hero p{color:var(--muted);margin:.4rem 0 1.4rem;}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:.4rem 0 1.2rem;}
@media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr);}}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:1.1rem 1.2rem;position:relative;overflow:hidden;}
.kpi:before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--c);}
.kpi .l{color:var(--muted);font-size:.85rem}
.kpi .v{font-family:'Sora',sans-serif;font-weight:800;font-size:2.4rem;margin-top:.2rem;color:var(--c)}
.kpi .s{color:var(--muted);font-size:.78rem}

.chip{display:inline-block;font-size:.76rem;font-weight:600;padding:.25rem .65rem;border-radius:999px;}
.chip.ok{background:rgba(52,211,153,.14);color:var(--ok);} .chip.wait{background:rgba(251,191,36,.14);color:var(--wait);}
.sub{color:var(--muted);font-size:.85rem}

/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:.4rem;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{height:44px;padding:0 1.1rem;border-radius:12px 12px 0 0;color:var(--muted);font-weight:600;}
.stTabs [aria-selected="true"]{color:var(--ink)!important;background:linear-gradient(180deg,rgba(139,108,255,.22),transparent);}
.stTabs [data-baseweb="tab-highlight"]{background:linear-gradient(90deg,var(--a),var(--b))!important;height:3px;}

/* inputs: always readable */
input,textarea,[data-baseweb="select"] *{color:var(--ink)!important;}
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="select"]>div{background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:12px!important;}
div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within{border-color:var(--a)!important;box-shadow:0 0 0 3px rgba(139,108,255,.25)!important;}
[data-testid="stChatInput"],[data-testid="stChatInput"] textarea{background:var(--panel)!important;color:var(--ink)!important;}
[data-testid="stChatInput"]{border:1px solid var(--line);border-radius:14px;}
[data-testid="stChatMessage"]{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;}
[data-testid="stChatMessage"] *{color:var(--ink);}
.stButton>button,.stLinkButton>a,.stFormSubmitButton>button{border-radius:11px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font-weight:600;transition:.15s;}
.stButton>button:hover,.stLinkButton>a:hover,.stFormSubmitButton>button:hover{border-color:var(--a);transform:translateY(-1px);box-shadow:0 6px 18px rgba(139,108,255,.25);}
.stFormSubmitButton>button,.stButton>button[kind="primary"]{background:linear-gradient(90deg,var(--a),var(--b))!important;border:none!important;color:#0B1020!important;}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;border-radius:14px!important;background:var(--panel);}
</style>
""", unsafe_allow_html=True)

# ───────────────────────── Config ─────────────────────────
def clean(v): return str(v).strip().strip("\"'")

SB_URL = clean(st.secrets["SUPABASE_URL"]).rstrip("/")
SB_KEY = clean(st.secrets["SUPABASE_KEY"])
G_KEY = clean(st.secrets["GEMINI_API_KEY"])
G_BASE = "https://generativelanguage.googleapis.com/v1beta"
SB_H = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}

def sb(method, path, **kw):
    return requests.request(method, f"{SB_URL}/rest/v1/{path}", headers=SB_H, timeout=10, **kw)

@st.cache_data(ttl=10, show_spinner=False)
def fetch_jobs():
    try:
        r = sb("GET", "applications?select=*&order=created_at.desc&limit=2000")
        return (r.json(), None) if r.status_code == 200 else ([], f"Database error {r.status_code}: {r.text[:200]}")
    except requests.RequestException as e:
        return [], f"Can't reach the database: {e}"

@st.cache_data(ttl=1800, show_spinner=False)
def gemini_models():
    """Ask Google which models this key can actually use, newest Flash first."""
    try:
        r = requests.get(f"{G_BASE}/models?pageSize=200", headers={"x-goog-api-key": G_KEY}, timeout=10)
        r.raise_for_status()
        names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception:
        return [], None
    bad = ("image", "tts", "audio", "live", "embedding", "robotics", "computer", "preview", "exp", "thinking")
    flash = [n for n in names if "flash" in n and not any(b in n for b in bad)] or [n for n in names if "flash" in n] or names
    ver = lambda n: tuple(int(x) for x in re.findall(r"\d+", n)) or (0,)
    flash.sort(key=lambda n: (ver(n), "lite" not in n), reverse=True)
    return names, (flash[0] if flash else None)

def ask_ai(prompt, jobs, stats):
    names, auto = gemini_models()
    model = st.session_state.get("model") or auto
    if not model:
        return "error", "Couldn't find a usable Gemini model. Check your GEMINI_API_KEY on the Diagnostics tab."
    recent = "; ".join(f"{j.get('title')} at {j.get('company')} ({j.get('status')})" for j in jobs[:10])
    ctx = f"You help track job applications. {stats}. Most recent: {recent or 'none'}. Be concise."
    try:
        r = requests.post(f"{G_BASE}/models/{model}:generateContent", timeout=40,
                          headers={"Content-Type": "application/json", "x-goog-api-key": G_KEY},
                          json={"contents": [{"parts": [{"text": f"{ctx}\n\nUser: {prompt}"}]}]})
        if r.status_code == 200:
            return "assistant", r.json()["candidates"][0]["content"]["parts"][0]["text"]
        gemini_models.clear()
        msg = r.json().get("error", {}).get("message", r.text)[:220]
        return "error", f"Gemini ({model}) said {r.status_code}: {msg}"
    except Exception as e:
        return "error", f"Assistant failed: {e}"

# ───────────────────────── Data ─────────────────────────
jobs, db_err = fetch_jobs()
filled = lambda j: "Autofilled" in (j.get("status") or "")
total = len(jobs); applied = sum(map(filled, jobs)); waiting = total - applied
companies = len({(j.get("company") or "").lower() for j in jobs if j.get("company") and j["company"] != "Pending"})
stats = f"Database has {total} jobs, {applied} filled, {waiting} waiting"

st.markdown(f"""<div class="hero"><h1>Job Assistant</h1>
<p>Track every job, fill applications, and ask questions. Last synced {datetime.now():%H:%M:%S}.</p></div>""", unsafe_allow_html=True)
if db_err:
    st.error(db_err)

t_dash, t_jobs, t_add, t_chat, t_diag = st.tabs(["📊 Dashboard", "📋 Jobs", "➕ Add jobs", "🤖 Assistant", "🛠 Diagnostics"])

# ───────────────────────── Dashboard ─────────────────────────
with t_dash:
    def kpi(label, val, sub, color): return f'<div class="kpi" style="--c:{color}"><div class="l">{label}</div><div class="v">{val}</div><div class="s">{sub}</div></div>'
    st.markdown('<div class="kpis">' + kpi("Jobs found", total, "In your database", "#8B6CFF") + kpi("Filled", applied, "Applications autofilled", "#34D399")
                + kpi("Waiting", waiting, "Not applied yet", "#FBBF24") + kpi("Companies", companies, "Unique employers", "#22D3EE") + "</div>", unsafe_allow_html=True)
    if not jobs:
        st.info("No jobs to show yet. Add one in the **Add jobs** tab. If your table already has rows, your Supabase key may be blocked by Row Level Security; see **Diagnostics**.")
    else:
        c1, c2 = st.columns([1, 1.6], gap="large")
        with c1:
            st.markdown("##### Application status")
            df = pd.DataFrame({"Status": ["Filled", "Waiting"], "Jobs": [applied, waiting]})
            st.altair_chart(alt.Chart(df).mark_arc(innerRadius=62, stroke="#141B30").encode(
                theta="Jobs:Q", color=alt.Color("Status:N", scale=alt.Scale(domain=["Filled", "Waiting"], range=["#34D399", "#FBBF24"]),
                legend=alt.Legend(orient="bottom", title=None, labelColor="#EEF1FB"))).properties(height=250).configure_view(strokeWidth=0), use_container_width=True)
        with c2:
            st.markdown("##### Jobs found per day")
            d = pd.to_datetime(pd.Series([j.get("created_at") for j in jobs]), errors="coerce", utc=True).dt.date.value_counts().sort_index().reset_index()
            d.columns = ["Day", "Jobs"]
            st.altair_chart(alt.Chart(d.tail(30)).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color="#8B6CFF").encode(
                x=alt.X("Day:T", title=None, axis=alt.Axis(labelColor="#8F9ABB")), y=alt.Y("Jobs:Q", title=None, axis=alt.Axis(labelColor="#8F9ABB", gridColor="#26304D")),
                tooltip=["Day:T", "Jobs:Q"]).properties(height=250).configure_view(strokeWidth=0), use_container_width=True)
        top = pd.Series([j.get("company") for j in jobs if j.get("company") and j["company"] != "Pending"]).value_counts().head(8).reset_index()
        if len(top):
            top.columns = ["Company", "Jobs"]
            st.markdown("##### Top companies")
            st.altair_chart(alt.Chart(top).mark_bar(cornerRadiusEnd=5, color="#22D3EE").encode(
                y=alt.Y("Company:N", sort="-x", title=None, axis=alt.Axis(labelColor="#EEF1FB")), x=alt.X("Jobs:Q", title=None, axis=alt.Axis(labelColor="#8F9ABB", gridColor="#26304D")),
                tooltip=["Company", "Jobs"]).properties(height=max(120, 30 * len(top))).configure_view(strokeWidth=0), use_container_width=True)

# ───────────────────────── Jobs ─────────────────────────
with t_jobs:
    f1, f2, f3, f4 = st.columns([3, 1.4, 1.2, 0.8])
    q = f1.text_input("Search", placeholder="🔍  Search title, company or location", label_visibility="collapsed")
    sf = f2.selectbox("Status", ["All", "Waiting", "Filled"], label_visibility="collapsed")
    per = f3.selectbox("Per page", [10, 25, 50], index=1, label_visibility="collapsed")
    if f4.button("↻ Refresh", use_container_width=True):
        fetch_jobs.clear(); st.rerun()
    shown = [j for j in jobs if (sf == "All" or (sf == "Filled") == filled(j))
             and q.lower() in " ".join(str(j.get(k) or "") for k in ("title", "company", "location")).lower()]
    pages = max(1, -(-len(shown) // per))
    page = st.number_input("Page", 1, pages, 1, label_visibility="collapsed") if pages > 1 else 1
    st.markdown(f'<div class="sub">{len(shown)} jobs · page {page} of {pages}</div>', unsafe_allow_html=True)
    if not shown:
        st.info("No jobs match your filters.")
    for i, j in enumerate(shown[(page - 1) * per: page * per]):
        jid, link = j.get("id"), j.get("apply_url") or ""
        with st.container(border=True):
            c = st.columns([5, 1.1, 0.9, 0.9, 0.7], vertical_alignment="center")
            meta = " · ".join(html.escape(str(j[k])) for k in ("company", "location") if j.get(k))
            c[0].markdown(f"**{html.escape(j.get('title') or 'Untitled role')}**  \n<span class='sub'>{meta}</span>", unsafe_allow_html=True)
            c[1].markdown('<span class="chip ok">Filled</span>' if filled(j) else '<span class="chip wait">Waiting</span>', unsafe_allow_html=True)
            if link.startswith("http"): c[2].link_button("Open", link, use_container_width=True)
            if not filled(j) and jid is not None and c[3].button("✓ Done", key=f"d{jid}{i}", use_container_width=True, help="Mark as applied"):
                r = sb("PATCH", f"applications?id=eq.{jid}", json={"status": "Autofilled"})
                (st.toast("Marked as filled ✅") if r.status_code < 300 else st.toast(f"Failed: {r.text[:120]}"))
                fetch_jobs.clear(); st.rerun()
            if jid is not None and c[4].button("🗑", key=f"x{jid}{i}", help="Delete"):
                r = sb("DELETE", f"applications?id=eq.{jid}")
                (st.toast("Deleted") if r.status_code < 300 else st.toast(f"Failed: {r.text[:120]}"))
                fetch_jobs.clear(); st.rerun()

# ───────────────────────── Add ─────────────────────────
with t_add:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("##### Add one job")
        with st.form("one", clear_on_submit=True):
            title = st.text_input("Job title", placeholder="Frontend Engineer")
            company = st.text_input("Company", placeholder="Acme Inc.")
            location = st.text_input("Location", placeholder="Remote")
            url = st.text_input("Apply link", placeholder="https://…")
            if st.form_submit_button("Add to queue", use_container_width=True):
                if not url.startswith("http"):
                    st.error("Add a valid apply link starting with http.")
                else:
                    r = sb("POST", "applications", json={"title": title or "Added manually", "company": company or "Pending",
                                                          "location": location or "Custom", "apply_url": url, "status": "Queued"})
                    if r.status_code < 300: st.success("Added ✅"); fetch_jobs.clear()
                    else: st.error(f"Couldn't save: {r.text[:200]}")
    with b:
        st.markdown("##### Paste many links")
        with st.form("many", clear_on_submit=True):
            blob = st.text_area("One link per line", height=230, placeholder="https://…\nhttps://…")
            if st.form_submit_button("Add all", use_container_width=True):
                links = [l.strip() for l in blob.splitlines() if l.strip().startswith("http")]
                if not links: st.error("No valid links found.")
                else:
                    rows = [{"title": "Added manually", "company": "Pending", "location": "Custom", "apply_url": l, "status": "Queued"} for l in links]
                    r = sb("POST", "applications", json=rows)
                    if r.status_code < 300: st.success(f"Added {len(rows)} jobs ✅"); fetch_jobs.clear()
                    else: st.error(f"Couldn't save: {r.text[:200]}")

# ───────────────────────── Assistant ─────────────────────────
with t_chat:
    st.session_state.setdefault("chat", [("assistant", "Hi! Ask me anything about your applications, or paste a job link and I'll queue it.")])
    top = st.columns([1, 1, 1, 1, 0.8])
    quick = None
    for col, text in zip(top, ["Summarize my jobs", "What should I apply to first?", "How many are waiting?", "Give me interview tips"]):
        if col.button(text, use_container_width=True): quick = text
    if top[4].button("Clear chat", use_container_width=True):
        st.session_state.chat = st.session_state.chat[:1]; st.rerun()
    box = st.container(height=430, border=False)
    prompt = st.chat_input("Ask a question or paste a job link…") or quick
    if prompt:
        st.session_state.chat.append(("user", prompt))
        if prompt.strip().startswith("http"):
            r = sb("POST", "applications", json={"title": "Added manually", "company": "Pending", "location": "Custom", "apply_url": prompt.strip(), "status": "Queued"})
            fetch_jobs.clear()
            st.session_state.chat.append(("assistant", "Added to your queue ✅") if r.status_code < 300 else ("error", f"Couldn't save: {r.text[:200]}"))
        else:
            with st.spinner("Thinking…"):
                st.session_state.chat.append(ask_ai(prompt, jobs, stats))
    with box:
        for role, msg in st.session_state.chat:
            if role == "error": st.error(msg)
            else:
                with st.chat_message(role): st.markdown(msg)

# ───────────────────────── Diagnostics ─────────────────────────
with t_diag:
    st.markdown("##### Connections")
    d1, d2 = st.columns(2)
    d1.metric("Database", "Connected ✅" if not db_err else "Problem ❌")
    names, auto = gemini_models()
    d2.metric("Gemini", "Connected ✅" if names else "Problem ❌")
    if names:
        flash = [n for n in names if "flash" in n] or names
        choice = st.selectbox("Model used by the assistant", ["Auto (newest Flash)"] + flash)
        st.session_state["model"] = None if choice.startswith("Auto") else choice
        st.caption(f"Auto currently picks: `{auto}`")
    else:
        st.error("Couldn't list Gemini models. Your GEMINI_API_KEY is probably invalid or expired.")
    if st.button("Re-check connections"):
        fetch_jobs.clear(); gemini_models.clear(); st.rerun()
    st.markdown("##### Seeing 0 jobs but your table has rows?")
    st.markdown("Supabase blocks the anon key from reading tables with Row Level Security turned on. In Supabase, open **Authentication → Policies → applications** and add a `SELECT` policy (and `INSERT`, `UPDATE`, `DELETE` if you want the buttons to work), or use your service-role key in `SUPABASE_KEY`.")
