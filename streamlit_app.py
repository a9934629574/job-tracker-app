import streamlit as st
import requests

# 1. Page Config
st.set_page_config(page_title="AI Job Assistant", layout="wide", initial_sidebar_state="collapsed")

# 2. Custom CSS for Hacker/Dashboard Aesthetic
st.markdown("""
<style>
    .stApp { background-color: #0B0E14 !important; color: #FFFFFF !important; }
    header { visibility: hidden; }
    
    .hacker-card {
        background-color: #151822;
        border: 1px solid #2A2D3D;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        transition: 0.3s;
        margin-bottom: 15px;
    }
    .hacker-card:hover { border-color: #6366F1; box-shadow: 0 0 15px rgba(99, 102, 241, 0.3); }
    .card-title { color: #A0AEC0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .card-value { font-size: 2.5rem; font-weight: 700; color: #FFFFFF; line-height: 1.1; }
    .card-sub { color: #718096; font-size: 0.75rem; margin-top: 5px; }
    
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

# 4. Fetch Supabase Data
headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
try:
    res = requests.get(f"{url}/rest/v1/applications?select=*&order=created_at.desc", headers=headers, timeout=5)
    jobs = res.json() if res.status_code == 200 else []
except:
    jobs = []

total_jobs = len(jobs)
autofilled = sum(1 for j in jobs if "Autofilled" in j.get("status", ""))
pending = total_jobs - autofilled
manual = sum(1 for j in jobs if j.get("title") == "Manual Inject")

# 5. HEADER
st.markdown("<h2 style='margin-bottom: 0;'>💼 Job Search Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#A0AEC0; margin-bottom: 30px;'>Automated tracking and intelligent AI application pipeline.</p>", unsafe_allow_html=True)

# 6. TOP METRIC CARDS 
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Total Jobs Tracked</div><div class="card-value">{total_jobs}</div><div class="card-sub">All database records</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Successfully Applied</div><div class="card-value">{autofilled}</div><div class="card-sub">Automated & Verified</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Pending Action</div><div class="card-value">{pending}</div><div class="card-sub">Awaiting Morning Run</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="hacker-card"><div class="card-title">Manual Links Injected</div><div class="card-value">{manual}</div><div class="card-sub">User submitted URLs</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 7. BOTTOM GRID: Recent Applications vs. AI Terminal
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.markdown("<h4 style='color: white;'>🏢 Recent Applications</h4>", unsafe_allow_html=True)
    if jobs:
        for row in jobs[:4]:  # Show top 4 most recent jobs
            company = row.get("company", "Unknown Company")
            title = row.get("title", "Unknown Role")
            status = row.get("status", "Ready")
            st.markdown(f'''
            <div class="hacker-card" style="padding: 15px;">
                <div class="card-title">{company}</div>
                <div class="card-value" style="font-size: 1.4rem;">{title}</div>
                <div class="card-sub" style="color:#6366F1; margin-top: 8px;">Status: {status}</div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("No jobs found in the database yet. Drop a link in the terminal to start!")

with right_col:
    st.markdown("<h4 style='color: white;'>📈 AI Assistant Terminal <span style='color:#48BB78; font-size:12px; border:1px solid #48BB78; padding:2px 5px; border-radius:4px;'>ONLINE</span></h4>", unsafe_allow_html=True)
    
    # 8. DIRECT REST API FOR GEMINI (Fixed to 2.5-flash)
    def ask_ai(prompt_text):
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": f"You are a helpful job tracking assistant. The user's database currently has {total_jobs} total jobs saved. User says: {prompt_text}"}]}]}
        try:
            req = requests.post(gemini_url, headers={"Content-Type": "application/json"}, json=payload)
            if req.status_code == 200:
                return "ai", req.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "error", f"Google API Error [{req.status_code}]: {req.text}"
        except Exception as e:
            return "error", f"Network crash: {str(e)}"

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = [("ai", "Job Assistant online. Paste a job application URL to add it to your queue, or ask me a question.")]

    if user_input := st.chat_input("Command or URL..."):
        st.session_state.chat_log.append(("user", user_input))
        
        # If user pastes a link, push to database
        if "http" in user_input:
            requests.post(f"{url}/rest/v1/applications", headers=headers, json={"title": "Manual Inject", "company": "Pending", "location": "Custom", "apply_url": user_input, "status": "Queued"})
            st.session_state.chat_log.append(("ai", f"Successfully injected {user_input} into the database. It will be processed during the next run."))
        else:
            # Talk directly to Gemini
            role, response = ask_ai(user_input)
            st.session_state.chat_log.append((role, response))

    # Display the stream
    st.markdown('<div class="stream-box">', unsafe_allow_html=True)
    for role, msg in st.session_state.chat_log:
        if role == "user":
            st.markdown(f'<div class="chat-user">➜ root@user:~# {msg}</div>', unsafe_allow_html=True)
        elif role == "error":
            st.markdown(f'<div class="chat-error">{msg}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-ai">{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
