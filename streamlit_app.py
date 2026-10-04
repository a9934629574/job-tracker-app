import streamlit as st
import requests
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="AI Job Agent", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    header {visibility: hidden;}
    [data-testid="stMetric"] {
        background-color: #1E2130;
        padding: 15px 20px;
        border-radius: 10px;
        border-left: 4px solid #6366F1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# 2. Clean Secrets
url = st.secrets["SUPABASE_URL"].strip().replace('"', '').replace("'", "").rstrip('/')
key = st.secrets["SUPABASE_KEY"].strip().replace('"', '').replace("'", "")
gemini_key = st.secrets["GEMINI_API_KEY"].strip().replace('"', '').replace("'", "")

try:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception:
    st.error("Failed to connect to Gemini AI.")

# 3. Direct HTTP Connection (Bypassing the buggy Supabase library)
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

try:
    # Fetch data directly from the REST API
    endpoint = f"{url}/rest/v1/applications?select=*&order=created_at.desc"
    res = requests.get(endpoint, headers=headers, timeout=10)
    
    if res.status_code == 200:
        jobs = res.json()
    else:
        st.error(f"Database Rejected Connection: {res.status_code} - {res.text}")
        st.stop()
except Exception as e:
    st.error(f"Direct connection failed. Streamlit is blocking the network: {e}")
    st.stop()

# Calculate Stats
total_jobs = len(jobs)
autofilled = sum(1 for j in jobs if "Autofilled" in j.get("status", ""))
pending = total_jobs - autofilled

# 4. Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.title("Live Dashboard")
    st.divider()
    page = st.radio("Navigation", ["📊 Live Job Stream", "💬 Chat with AI"])

# 5. Main Dashboard View
if page == "📊 Live Job Stream":
    st.subheader("Live Dashboard & Real-Time Stream")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs Found", total_jobs)
    col2.metric("Autofilled / Ready", autofilled)
    col3.metric("Pending Review", pending)
    
    st.divider()
    st.markdown("### ⚡ Real-Time Job Stream")
    
    if jobs:
        for row in jobs:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{row.get('title', 'Unknown Role')}**")
                c2.markdown(f"🏢 {row.get('company', 'Unknown Company')}")
                c3.markdown(f"`{row.get('status', 'Ready')}`")
                c4.link_button("Review & Submit", row.get('apply_url', '#'), use_container_width=True)
                st.markdown("<hr style='margin: 0.5em 0px; border-color: #2A2D3D;'>", unsafe_allow_html=True)
    else:
        st.info("No jobs found in the database yet. Waiting for morning run...")

# 6. AI Chat View
elif page == "💬 Chat with AI":
    st.subheader("AI Assistant")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "System online. Drop a link to autofill, or ask me for your latest stats."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Command or URL..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if "http" in prompt:
                # Direct POST request to save the link
                payload = {
                    "title": "Manual Extraction",
                    "company": "Pending",
                    "location": "Custom",
                    "apply_url": prompt,
                    "status": "Queued for Next Run"
                }
                post_res = requests.post(f"{url}/rest/v1/applications", headers=headers, json=payload)
                
                if post_res.status_code in [200, 201]:
                    reply = "✅ **Link captured.** Added to the database queue."
                else:
                    reply = f"❌ Failed to save. Database code: {post_res.status_code}"
            else:
                context = f"Total jobs: {total_jobs}. Recent jobs: {jobs[:3]}"
                try:
                    ai_response = model.generate_content(f"You are a sleek AI job agent. Answer briefly based on this data: {context}. User says: {prompt}")
                    reply = ai_response.text
                except:
                    reply = "AI is currently unavailable. Check your Gemini API key."
            st.markdown(reply)
            
        st.session_state.messages.append({"role": "assistant", "content": reply})
