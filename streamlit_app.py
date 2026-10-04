import html
import json
import re
import time
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
.chip.no{background:rgba(248,113,113,.14);color:var(--bad);} .chip.blue{background:rgba(139,108,255,.18);color:#B7A6FF;}

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

def sb(method, path, prefer=None, **kw):
    h = dict(SB_H)
    if prefer: h["Prefer"] = prefer
    return requests.request(method, f"{SB_URL}/rest/v1/{path}", headers=h, timeout=10, **kw)

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

def model_order():
    """Preferred model first, then newer-to-older Flash, Flash-Lite, Pro, then stable aliases."""
    names, _ = gemini_models()
    ver = lambda n: tuple(int(x) for x in re.findall(r"\d+", n)) or (0,)
    bad = ("image", "tts", "audio", "live", "embedding", "robotics", "computer", "exp", "thinking", "preview")
    ok = lambda n: not any(b in n for b in bad)
    flash = sorted([n for n in names if "flash" in n and "lite" not in n and ok(n)], key=ver, reverse=True)
    lite = sorted([n for n in names if "lite" in n and ok(n)], key=ver, reverse=True)
    pro = sorted([n for n in names if "pro" in n and ok(n)], key=ver, reverse=True)
    prev = sorted([n for n in names if "flash" in n and "preview" in n], key=ver, reverse=True)
    order = [st.session_state.get("model")] + flash[:3] + lite[:2] + pro[:1] + prev[:1] + ["gemini-flash-latest", "gemini-flash-lite-latest"]
    out = []
    for m in order:
        if m and m not in out: out.append(m)
    return out

def call_gemini(text):
    """Try each model in order. Retry once on busy errors, then fall back to the next model."""
    errs = []
    for m in model_order()[:7]:
        for attempt in (0, 1):
            try:
                r = requests.post(f"{G_BASE}/models/{m}:generateContent", timeout=40,
                                  headers={"Content-Type": "application/json", "x-goog-api-key": G_KEY},
                                  json={"contents": [{"parts": [{"text": text}]}]})
            except requests.RequestException:
                errs.append(f"{m}: network error"); break
            if r.status_code == 200:
                try:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"], m, errs
                except (KeyError, IndexError):
                    errs.append(f"{m}: empty reply"); break
            if r.status_code in (401, 403):
                return None, None, [f"Gemini rejected your key ({r.status_code}). Check GEMINI_API_KEY."]
            if r.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(1.5); continue
            errs.append(f"{m}: {r.status_code}"); break
    return None, None, errs

LEVELS = ["Any", "Entry", "Mid", "Senior"]
DEFAULTS = {"roles": "Product Manager", "skills": "", "remote": True, "cities": "Hyderabad", "avoid": "", "level": "Any", "resume": ""}

def current_profile():
    s_ = st.session_state
    return {k: s_.get(f"p_{k}", v) for k, v in DEFAULTS.items()}

def split(v): return [x.strip().lower() for x in str(v).split(",") if x.strip()]

def match(j, p):
    """Rule-based fit: role in title + location rule (remote anywhere, on-site only in chosen cities)."""
    title = (j.get("title") or "").lower(); loc = (j.get("location") or "").lower()
    if any(a in f"{title} {loc} {(j.get('company') or '').lower()}" for a in split(p["avoid"])):
        return "No", "Contains a keyword you skip"
    roles = split(p["roles"])
    role_ok = (not roles) or any(r in title or all(w in title for w in r.split()) for r in roles)
    if not role_ok: return "No", "Title doesn't match your roles"
    if "remote" in loc or "remote" in title or "anywhere" in loc or "work from home" in loc:
        return ("Good", "Remote") if p["remote"] else ("No", "Remote jobs are off")
    if any(c in loc for c in split(p["cities"])): return "Good", "In your city"
    if not loc or loc in ("custom", "unknown"): return "Maybe", "Location unknown"
    return "No", "Outside your cities"

def read_resume(f):
    if f.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(f).pages).strip()
    return f.read().decode("utf-8", "ignore")

def save_profile():
    r = sb("POST", "job_profile?on_conflict=id", prefer="resolution=merge-duplicates,return=minimal",
           json={"id": 1, "data": current_profile()})
    return r.status_code < 300, r.text[:200]

def ask_ai(prompt, jobs, stats):
    p = current_profile()
    recent = "; ".join(f"{j.get('title')} at {j.get('company')} ({j.get('status')})" for j in jobs[:10])
    ctx = (f"You help track job applications. {stats}. Most recent: {recent or 'none'}. "
           f"Preferences: roles={p['roles']}; remote anywhere={p['remote']}; on-site cities={p['cities']}; level={p['level']}. "
           f"Resume: {p['resume'][:3000] or 'not provided'}. Be concise.")
    out, m, errs = call_gemini(f"{ctx}\n\nUser: {prompt}")
    if out: return "assistant", out + f"\n\n*via {m}*"
    return "error", "All models failed: " + "; ".join(errs[-4:]) + ". Try again in a minute."

# ───────────────────────── Data ─────────────────────────
jobs, db_err = fetch_jobs()
filled = lambda j: "Autofilled" in (j.get("status") or "")
total = len(jobs); applied = sum(map(filled, jobs)); waiting = total - applied
companies = len({(j.get("company") or "").lower() for j in jobs if j.get("company") and j["company"] != "Pending"})
stats = f"Database has {total} jobs, {applied} filled, {waiting} waiting"
if "profile_loaded" not in st.session_state:
    saved = {}
    try:
        r = sb("GET", "job_profile?id=eq.1&select=data")
        if r.status_code == 200 and r.json(): saved = r.json()[0]["data"]
    except Exception:
        pass
    st.session_state["profile_loaded"] = True
    for k, v in {**DEFAULTS, **saved}.items(): st.session_state.setdefault(f"p_{k}", v)

st.markdown(f"""<div class="hero"><h1>Job Assistant</h1>
<p>Track every job, fill applications, and ask questions. Last synced {datetime.now():%H:%M:%S}.</p></div>""", unsafe_allow_html=True)
if db_err:
    st.error(db_err)

t_dash, t_jobs, t_prof, t_add, t_chat, t_diag = st.tabs(["📊 Dashboard", "📋 Jobs", "🎯 Profile", "➕ Add jobs", "🤖 Assistant", "🛠 Diagnostics"])

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
    sf = f2.selectbox("Status", ["All", "Waiting", "Filled", "Matches my profile"], label_visibility="collapsed")
    per = f3.selectbox("Per page", [10, 25, 50], index=1, label_visibility="collapsed")
    if f4.button("↻ Refresh", use_container_width=True):
        fetch_jobs.clear(); st.rerun()
    P = current_profile()
    M = {id(j): match(j, P) for j in jobs}
    def status_ok(j):
        if sf == "All": return True
        if sf == "Matches my profile": return M[id(j)][0] == "Good" and not filled(j)
        return (sf == "Filled") == filled(j)
    shown = [j for j in jobs if status_ok(j)
             and q.lower() in " ".join(str(j.get(k) or "") for k in ("title", "company", "location")).lower()]
    pages = max(1, -(-len(shown) // per))
    page = st.number_input("Page", 1, pages, 1, label_visibility="collapsed") if pages > 1 else 1
    st.markdown(f'<div class="sub">{len(shown)} jobs · page {page} of {pages}</div>', unsafe_allow_html=True)
    todo = [j for j in jobs if M[id(j)][0] == "Good" and not filled(j) and j.get("status") != "Approved" and j.get("id") is not None]
    if todo and st.button(f"✅ Approve {len(todo)} matching jobs for auto-apply", type="primary"):
        ids = ",".join(str(j["id"]) for j in todo[:200])
        r = sb("PATCH", f"applications?id=in.({ids})", json={"status": "Approved"})
        st.toast(f"Approved {min(len(todo), 200)} jobs ✅" if r.status_code < 300 else f"Failed: {r.text[:150]}")
        fetch_jobs.clear(); st.rerun()
    if not shown:
        st.info("No jobs match your filters.")
    for i, j in enumerate(shown[(page - 1) * per: page * per]):
        jid, link = j.get("id"), j.get("apply_url") or ""
        with st.container(border=True):
            c = st.columns([5, 1.1, 0.9, 0.9, 0.7], vertical_alignment="center")
            meta = " · ".join(html.escape(str(j[k])) for k in ("company", "location") if j.get(k))
            c[0].markdown(f"**{html.escape(j.get('title') or 'Untitled role')}**  \n<span class='sub'>{meta}</span>", unsafe_allow_html=True)
            lvl, why = M[id(j)]
            stat = '<span class="chip ok">Filled</span>' if filled(j) else ('<span class="chip blue">Approved</span>' if j.get("status") == "Approved" else '<span class="chip wait">Waiting</span>')
            fit = {"Good": "ok", "Maybe": "wait", "No": "no"}[lvl]
            c[1].markdown(f'{stat}<br><span class="chip {fit}" title="{why}">{lvl} fit</span>', unsafe_allow_html=True)
            if link.startswith("http"): c[2].link_button("Open", link, use_container_width=True)
            if not filled(j) and jid is not None and c[3].button("✓ Done", key=f"d{jid}{i}", use_container_width=True, help="Mark as applied"):
                r = sb("PATCH", f"applications?id=eq.{jid}", json={"status": "Autofilled"})
                (st.toast("Marked as filled ✅") if r.status_code < 300 else st.toast(f"Failed: {r.text[:120]}"))
                fetch_jobs.clear(); st.rerun()
            if jid is not None and c[4].button("🗑", key=f"x{jid}{i}", help="Delete"):
                r = sb("DELETE", f"applications?id=eq.{jid}")
                (st.toast("Deleted") if r.status_code < 300 else st.toast(f"Failed: {r.text[:120]}"))
                fetch_jobs.clear(); st.rerun()

# ───────────────────────── Profile ─────────────────────────
with t_prof:
    if "pending_fill" in st.session_state:
        for k, v in st.session_state.pop("pending_fill").items(): st.session_state[f"p_{k}"] = v
    L, R = st.columns([1.1, 1], gap="large")
    with L:
        st.markdown("##### 1. Your resume")
        up = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"], label_visibility="collapsed")
        if up is not None and st.session_state.get("last_resume") != (up.name, up.size):
            try:
                st.session_state["p_resume"] = read_resume(up); st.session_state["last_resume"] = (up.name, up.size)
            except Exception as e:
                st.error(f"Couldn't read that file ({e}). Paste your resume text below instead.")
        st.text_area("Resume text", key="p_resume", height=250, placeholder="Or paste your resume here…")
        analyze = st.button("✨ Fill my preferences from my resume", use_container_width=True)
        if analyze:
            if len(st.session_state.p_resume.strip()) < 80:
                st.warning("Add your resume first.")
            else:
                with st.spinner("Reading your resume…"):
                    out, m, errs = call_gemini('From this resume return ONLY JSON like {"roles": "comma separated job titles to target", "skills": "comma separated top skills", "level": "Entry|Mid|Senior"}.\n\nResume:\n' + st.session_state.p_resume[:8000])
                fill = None
                try:
                    data = json.loads(re.search(r"\{.*\}", out, re.S).group(0))
                    fill = {k: (data[k] if isinstance(data[k], str) else ", ".join(data[k])) for k in ("roles", "skills") if k in data}
                    if data.get("level") in LEVELS: fill["level"] = data["level"]
                except Exception:
                    st.error("Couldn't read the AI's answer. " + "; ".join(errs[-3:]))
                if fill:
                    st.session_state["pending_fill"] = fill; st.rerun()
    with R:
        st.markdown("##### 2. What you want")
        st.text_input("Roles (comma separated)", key="p_roles", placeholder="Product Manager, Associate Product Manager")
        st.text_area("Key skills", key="p_skills", height=80)
        st.selectbox("Experience level", LEVELS, key="p_level")
        st.toggle("🌍 Remote jobs from anywhere are fine", key="p_remote")
        st.text_input("On-site / hybrid only in these cities", key="p_cities", placeholder="Hyderabad, Bengaluru")
        st.text_input("Skip jobs containing", key="p_avoid", placeholder="intern, sales")
        if st.button("💾 Save preferences", type="primary", use_container_width=True):
            ok, err = save_profile()
            if ok: st.success("Saved ✅")
            else:
                st.error(f"Couldn't save to the database: {err}")
                st.markdown("Run this once in the Supabase SQL editor, then save again:")
                st.code("create table if not exists job_profile (id int primary key, data jsonb not null);\nalter table job_profile enable row level security;\ncreate policy \"open\" on job_profile for all using (true) with check (true);", language="sql")
    st.markdown("##### Your waiting jobs, scored against these preferences")
    pend = [j for j in jobs if not filled(j)]
    cnt = [sum(1 for j in pend if match(j, current_profile())[0] == k) for k in ("Good", "Maybe", "No")]
    m1, m2, m3 = st.columns(3)
    m1.metric("Good fit", cnt[0]); m2.metric("Maybe", cnt[1]); m3.metric("Not a fit", cnt[2])
    st.caption("Go to the Jobs tab and press **Approve matching jobs** to mark the good fits as Approved.")

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
        st.caption("Fallback order: " + " → ".join(model_order()[:7]))
    else:
        st.error("Couldn't list Gemini models. Your GEMINI_API_KEY is probably invalid or expired.")
    if st.button("Re-check connections"):
        fetch_jobs.clear(); gemini_models.clear(); st.rerun()
    st.markdown("##### Seeing 0 jobs but your table has rows?")
    st.markdown("Supabase blocks the anon key from reading tables with Row Level Security turned on. In Supabase, open **Authentication → Policies → applications** and add a `SELECT` policy (and `INSERT`, `UPDATE`, `DELETE` if you want the buttons to work), or use your service-role key in `SUPABASE_KEY`.")
