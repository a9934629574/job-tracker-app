import html
from datetime import datetime

import requests
import streamlit as st

st.set_page_config(page_title="Job Assistant", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")

# ───────────────────────── Styling ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Figtree:wght@400;500;600&display=swap');
:root{--bg:#EEF1F6;--panel:#FFFFFF;--ink:#101828;--muted:#667085;--line:#E2E6EE;--accent:#2F4BFF;--ok:#12B76A;--wait:#F79009;}
.stApp{background:var(--bg)!important;color:var(--ink)!important;font-family:'Figtree',sans-serif;}
header[data-testid="stHeader"],#MainMenu,footer{visibility:hidden;height:0;}
.block-container{max-width:1280px;padding:2.2rem 2rem 3rem;}
h1,h2,h3,.display{font-family:'Bricolage Grotesque',sans-serif!important;letter-spacing:-.02em;color:var(--ink)!important;}

.top{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;margin-bottom:1.6rem;flex-wrap:wrap;}
.top h1{font-size:2.5rem;margin:0;line-height:1.05;}
.top p{color:var(--muted);margin:.5rem 0 0;max-width:46ch;line-height:1.5;}
.live{display:inline-flex;align-items:center;gap:.5rem;background:var(--panel);border:1px solid var(--line);
  padding:.45rem .9rem;border-radius:999px;font-size:.85rem;color:var(--muted);}
.live i{width:8px;height:8px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 4px rgba(18,183,106,.18);}

.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:1.4rem 1.5rem;}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:1rem;}
@media(max-width:900px){.kpis{grid-template-columns:repeat(2,1fr);}}
.kpi .l{color:var(--muted);font-size:.85rem;}
.kpi .v{font-family:'Bricolage Grotesque',sans-serif;font-size:2.6rem;font-weight:700;line-height:1.1;margin-top:.3rem;}
.kpi .s{color:var(--muted);font-size:.8rem;margin-top:.2rem;}

.funnel{margin-bottom:1.4rem;}
.funnel .row{display:flex;justify-content:space-between;font-size:.9rem;margin-bottom:.7rem;}
.funnel .row b{font-family:'Bricolage Grotesque',sans-serif;font-size:1.05rem;}
.bar{display:flex;height:16px;border-radius:999px;overflow:hidden;background:var(--line);}
.bar span{display:block;height:100%;}
.legend{display:flex;gap:1.4rem;margin-top:.8rem;font-size:.82rem;color:var(--muted);}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:.4rem;}

.ledger-h{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:.4rem;}
.ledger-h h3{margin:0;font-size:1.25rem;}
.ledger-h span{color:var(--muted);font-size:.85rem;}
.job{display:grid;grid-template-columns:1fr auto;gap:.8rem;align-items:center;padding:.95rem 0;border-top:1px solid var(--line);}
.job:first-of-type{border-top:none;}
.job .t{font-weight:600;font-size:1rem;}
.job .m{color:var(--muted);font-size:.85rem;margin-top:.15rem;}
.job a{color:var(--accent);text-decoration:none;font-weight:600;font-size:.85rem;margin-left:.9rem;}
.job a:hover{text-decoration:underline;}
.chip{display:inline-flex;align-items:center;font-size:.78rem;font-weight:600;padding:.28rem .65rem;border-radius:999px;white-space:nowrap;}
.chip.ok{background:rgba(18,183,106,.12);color:#067647;}
.chip.wait{background:rgba(247,144,9,.14);color:#B54708;}
.empty{text-align:center;color:var(--muted);padding:2.5rem 1rem;line-height:1.6;}

/* inputs */
div[data-baseweb="input"],div[data-baseweb="select"]>div{background:var(--panel)!important;border-color:var(--line)!important;border-radius:12px!important;}
.stTextInput input{color:var(--ink)!important;}
.stButton>button{border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font-weight:600;}
.stButton>button:hover{border-color:var(--accent);color:var(--accent);}
[data-testid="stChatInput"]{border-radius:14px;}
[data-testid="stChatMessage"]{background:transparent;}
div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--panel);border-radius:18px;}
</style>
""", unsafe_allow_html=True)

# ───────────────────────── Secrets & data ─────────────────────────
def clean(v: str) -> str:
    return v.strip().strip("\"'")

SUPABASE_URL = clean(st.secrets["SUPABASE_URL"]).rstrip("/")
SUPABASE_KEY = clean(st.secrets["SUPABASE_KEY"])
GEMINI_KEY = clean(st.secrets["GEMINI_API_KEY"])
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")

HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}


@st.cache_data(ttl=15, show_spinner=False)
def fetch_jobs():
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/applications?select=*&order=created_at.desc",
                         headers=HEADERS, timeout=8)
        if r.status_code == 200:
            return r.json(), None
        return [], f"Database returned {r.status_code}: {r.text[:200]}"
    except requests.RequestException as e:
        return [], f"Could not reach the database: {e}"


jobs, db_error = fetch_jobs()
total = len(jobs)
applied = sum(1 for j in jobs if "Autofilled" in (j.get("status") or ""))
queued = total - applied
companies = len({(j.get("company") or "").strip().lower() for j in jobs if j.get("company") and j["company"] != "Pending"})
rate = round(applied / total * 100) if total else 0

# ───────────────────────── Header ─────────────────────────
st.markdown(f"""
<div class="top">
  <div>
    <h1>Job Assistant</h1>
    <p>Every job your scanner finds, and where each application stands.</p>
  </div>
  <div class="live"><i></i>Synced at {datetime.now():%H:%M:%S}</div>
</div>
""", unsafe_allow_html=True)

if db_error:
    st.error(f"{db_error}. Check SUPABASE_URL and SUPABASE_KEY in your secrets.")

# ───────────────────────── KPIs ─────────────────────────
st.markdown(f"""
<div class="kpis">
  <div class="panel kpi"><div class="l">Jobs found</div><div class="v">{total}</div><div class="s">In your database</div></div>
  <div class="panel kpi"><div class="l">Applications filled</div><div class="v">{applied}</div><div class="s">Autofilled successfully</div></div>
  <div class="panel kpi"><div class="l">Waiting</div><div class="v">{queued}</div><div class="s">Not applied yet</div></div>
  <div class="panel kpi"><div class="l">Companies</div><div class="v">{companies}</div><div class="s">Unique employers</div></div>
</div>
<div class="panel funnel">
  <div class="row"><span>Application progress</span><b>{rate}% filled</b></div>
  <div class="bar"><span style="width:{rate}%;background:var(--ok)"></span><span style="width:{100 - rate if total else 0}%;background:var(--wait);opacity:.55"></span></div>
  <div class="legend"><span><i class="dot" style="background:var(--ok)"></i>Filled · {applied}</span><span><i class="dot" style="background:var(--wait)"></i>Waiting · {queued}</span></div>
</div>
""", unsafe_allow_html=True)

# ───────────────────────── Main grid ─────────────────────────
left, right = st.columns([1.35, 1], gap="large")

with left:
    f1, f2, f3 = st.columns([2.4, 1.2, 0.8])
    query = f1.text_input("Search", placeholder="Search by title, company or location", label_visibility="collapsed")
    status_filter = f2.selectbox("Status", ["All", "Filled", "Waiting"], label_visibility="collapsed")
    if f3.button("Refresh", use_container_width=True):
        fetch_jobs.clear()
        st.rerun()

    def is_filled(j):
        return "Autofilled" in (j.get("status") or "")

    shown = [
        j for j in jobs
        if (status_filter == "All" or (status_filter == "Filled") == is_filled(j))
        and query.lower() in " ".join(str(j.get(k) or "") for k in ("title", "company", "location")).lower()
    ]

    rows = ""
    for j in shown[:50]:
        title = html.escape(j.get("title") or "Untitled role")
        meta = " · ".join(html.escape(str(j[k])) for k in ("company", "location") if j.get(k))
        link = j.get("apply_url") or ""
        link_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">Open</a>' if link.startswith("http") else ""
        chip = '<span class="chip ok">Filled</span>' if is_filled(j) else '<span class="chip wait">Waiting</span>'
        rows += f'<div class="job"><div><div class="t">{title}</div><div class="m">{meta}{link_html}</div></div>{chip}</div>'

    if not rows:
        rows = '<div class="empty">No jobs match.<br>Paste a job link in the assistant to add one.</div>'

    st.markdown(
        f'<div class="panel"><div class="ledger-h"><h3>Jobs</h3><span>Showing {min(len(shown), 50)} of {len(shown)}</span></div>{rows}</div>',
        unsafe_allow_html=True,
    )

with right:
    st.markdown("### Assistant")
    st.caption("Ask about your jobs, or paste a job link to add it to the queue.")

    def ask_ai(prompt: str):
        recent = "; ".join(f"{j.get('title')} at {j.get('company')} ({j.get('status')})" for j in jobs[:10])
        context = (f"You help a user track job applications. Database: {total} jobs, {applied} filled, {queued} waiting. "
                   f"Most recent: {recent or 'none'}.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        try:
            r = requests.post(url, headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY},
                              json={"contents": [{"parts": [{"text": f"{context}\n\nUser: {prompt}"}]}]}, timeout=30)
            if r.status_code == 200:
                return "assistant", r.json()["candidates"][0]["content"]["parts"][0]["text"]
            return "error", f"Gemini returned {r.status_code}: {r.text[:300]}"
        except (requests.RequestException, KeyError, IndexError) as e:
            return "error", f"Assistant request failed: {e}"

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = [("assistant", "Hi! Ask me about your applications, or paste a job link and I'll queue it.")]

    box = st.container(height=470, border=True)
    prompt = st.chat_input("Ask a question or paste a job link")

    if prompt:
        st.session_state.chat_log.append(("user", prompt))
        if prompt.strip().startswith("http"):
            try:
                r = requests.post(f"{SUPABASE_URL}/rest/v1/applications", headers=HEADERS, timeout=8,
                                  json={"title": "Added manually", "company": "Pending", "location": "Custom",
                                        "apply_url": prompt.strip(), "status": "Queued"})
                ok = r.status_code in (200, 201, 204)
                fetch_jobs.clear()
                st.session_state.chat_log.append(("assistant" if ok else "error",
                                                  "Added to your queue." if ok else f"Couldn't save it ({r.status_code}): {r.text[:200]}"))
            except requests.RequestException as e:
                st.session_state.chat_log.append(("error", f"Couldn't save it: {e}"))
        else:
            with box, st.spinner("Thinking…"):
                st.session_state.chat_log.append(ask_ai(prompt))
        st.rerun()

    with box:
        for role, msg in st.session_state.chat_log:
            if role == "error":
                st.error(msg)
            else:
                with st.chat_message(role):
                    st.markdown(msg)
