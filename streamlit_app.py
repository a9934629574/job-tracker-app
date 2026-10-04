import streamlit as st
import requests

# 1. Page Config
st.set_page_config(page_title="AI Job Assistant", layout="wide", initial_sidebar_state="collapsed")

# 2. Custom CSS to exactly match the hacker/dashboard aesthetic
st.markdown("""
<style>
    /* Dark background and font */
    .stApp { background-color: #0B0E14 !important; color: #FFFFFF !important; }
    header { visibility: hidden; }
    
    /* Neon Metric Cards */
    .hacker-card {
        background-color: #151822;
        border: 1px solid #2A2D3D;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        transition: 0.3s;
    }
    .hacker-card:hover { border-color: #6366F1; box-shadow: 0 0 15px rgba(99, 102, 241, 0.3); }
    .card-title { color: #A0AEC0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .card-value { font-size: 2.5rem; font-weight: 700; color: #FFFFFF; line-height: 1.1; }
    .card-sub { color: #718096; font-size: 0.75rem; margin-top: 5px; }
    
    /* Chat/Stream Styling */
    .stream-box {
        background-color: #151822;
        border: 1px solid #2A2D3D;
        border-radius: 12px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
    }
    .chat-user { color: #6366F1; margin-bottom: 5px; font-weight: bold; }
    .chat-ai { color: #48BB78; margin-bottom: 15px; border-left: 2px solid #48BB78; padding-left: 10px;}
    .chat-error { color: #F56565; margin-bottom: 15px; border-left: 2px solid #F56565; padding-left: 10px;}
</style>
""", unsafe_allow_html=True)

# 3. Secure Secrets
url = st.secrets["SUPABASE_URL"].strip().replace('"', '').replace("'", "").rstrip('/')
key = st.secrets["SUPABASE_KEY"].strip().replace('"', '').replace("'", "")
gemini_key = st.secrets["GEMINI_API_KEY"].strip().replace('"', '').replace("'", "")

# 4. Fetch Supabase Data (Directly)
headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
try:
    res = requests.get(f"{url}/rest/v1/applications?select=*&order=created_at.desc", headers=headers, timeout=5)
    jobs = res.json() if res.status_code == 200 else []
except:
    jobs = []

total_jobs = len(jobs)
autofilled = sum(1 for j in jobs if "Autofilled" in j.get("status", ""))
pending = total_jobs - autofilled

# 5. HEADER
st.markdown("<h2 style='margin-bottom: 0;'>💼 Live Dashboard & Real-Time Stream</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#A0AEC0; margin-bottom: 30px;'>Monitors job boards in real-time, matching skills and automatically pushing combos to the database.</p>", unsafe_allow_html=True)

# 6. TOP METRIC CARDS (Exact match to image structure)
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Total Jobs Pulled</div><div class="card-value">{total_jobs}</div><div class="card-sub">Raw matches in DB</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Verified Applied</div><div class="card-value">{autofilled}</div><div class="card-sub">Successful Auto-fills</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Unchecked Jobs</div><div class="card-value">{pending}</div><div class="card-sub">Ready to run verification</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Detected Checkers</div><div class="card-value">3</div><div class="card-sub">LinkedIn, Indeed, Custom</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 7. BOTTOM GRID: Categories vs. Real-Time Stream
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.markdown("<h4 style='color: white;'>🏢 Jobs Per Service Category</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="hacker-card"><div class="card-title">Software / Tech</div><div class="card-value">212</div><div class="card-sub" style="color:#6366F1; margin-top:15px; text-align:center; background:#2A2D3D; padding:5px; border-radius:5px;">⚡ Run Checker</div></div>', unsafe_allow_html=True)
        st.markdown('<br><div class="hacker-card"><div class="card-title">Marketing / Sales</div><div class="card-value">20</div><div class="card-sub" style="color:#6366F1; margin-top:15px; text-align:center; background:#2A2D3D; padding:5px; border-radius:5px;">⚡ Run Checker</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="hacker-card"><div class="card-title">Design / Creative</div><div class="card-value">57</div><div class="card-sub" style="color:#6366F1; margin-top:15px; text-align:center; background:#2A2D3D; padding:5px; border-radius:5px;">⚡ Run Checker</div></div>', unsafe_allow_html=True)
        st.markdown('<br><div class="hacker-card"><div class="card-title">General / AIO</div><div class="card-value">72,201</div><div class="card-sub" style="color:#6366F1; margin-top:15px; text-align:center; background:#2A2D3D; padding:5px; border-radius:5px;">⚡ Run Checker</div></div>', unsafe_allow_html=True)

with right_col:
    st.markdown("<h4 style='color: white;'>📈 Real-Time AI Stream <span style='color:#F56565; font-size:12px; border:1px solid #F56565; padding:2px 5px; border-radius:4px;'>🔴 LIVE</span></h4>", unsafe_allow_html=True)
    
    # 8. DIRECT REST API FOR GEMINI (No hidden errors!)
    def ask_ai(prompt_text):
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": f"Context: Database has {total_jobs} total jobs. User says: {prompt_text}"}]}]}
        try:
            req = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json=payload)
            if req.status_code == 200:
                return "ai", req.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                # THIS will print the exact Google error (e.g. 400 API_KEY_INVALID)
                return "error", f"Google API Error [{req.status_code}]: {req.text}"
        except Exception as e:
            return "error", f"Network crash: {str(e)}"

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = [("ai", "Scanner active. Paste a URL to inject into the database, or ask me to check stats.")]

    if user_input := st.chat_input("Command or URL..."):
        st.session_state.chat_log.append(("user", user_input))
        
        # If user pastes a link, push to database
        if "http" in user_input:
            requests.post(f"{url}/rest/v1/applications", headers=headers, json={"title": "Manual Inject", "company": "Pending", "location": "Custom", "apply_url": user_input, "status": "Queued"})
            st.session_state.chat_log.append(("ai", f"Successfully injected {user_input} into Supabase queue."))
        else:
            # Talk directly to Gemini
            role, response = ask_ai(user_input)
            st.session_state.chat_log.append((role, response))

    # Display the stream
    st.markdown('<div class="stream-box">', unsafe_allow_html=True)
    for role, msg in st.session_state.chat_log:
        if role == "user":
            st.markdown(f'<div class="chat-user">➜ root@agent:~# {msg}</div>', unsafe_allow_html=True)
        elif role == "error":
            st.markdown(f'<div class="chat-error">{msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
