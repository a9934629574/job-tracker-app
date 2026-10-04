import streamlit as st
from supabase import create_client
import google.generativeai as genai

# 1. Page Config (Must be first)
st.set_page_config(page_title="AI Job Agent", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for the glowing metric cards
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

# 2. Secure Connection (Using .strip() to fix invisible space errors)
try:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    supabase = create_client(url, key)
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"].strip())
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Connection Error: {e}. Please check Streamlit Secrets.")
    st.stop()

# 3. Fetch Data
response = supabase.table("applications").select("*").order("created_at", desc=True).execute()
jobs = response.data if response.data else []

# Calculate Stats for the Dashboard
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
    st.caption("Monitoring job portals and auto-filling applications in real-time.")
    
    # Metric Cards (Like your screenshot)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs Found", total_jobs)
    col2.metric("Autofilled / Ready", autofilled)
    col3.metric("Pending Review", pending)
    
    st.divider()
    
    # Job List
    st.markdown("### ⚡ Real-Time Job Stream")
    if jobs:
        for row in jobs:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**{row['title']}**")
                c2.markdown(f"🏢 {row['company']}")
                c3.markdown(f"`{row['status']}`")
                c4.link_button("Review & Submit", row['apply_url'], use_container_width=True)
                st.markdown("<hr style='margin: 0.5em 0px; border-color: #2A2D3D;'>", unsafe_allow_html=True)
    else:
        st.info("Waiting for the morning scanner to find jobs...")

# 6. AI Chat View
elif page == "💬 Chat with AI":
    st.subheader("AI Assistant")
    st.caption("Paste a job link here to add it to the manual queue, or ask me for an update.")
    
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
                supabase.table("applications").insert({
                    "title": "Manual Extraction",
                    "company": "Pending",
                    "location": "Custom",
                    "apply_url": prompt,
                    "status": "Queued for Next Run"
                }).execute()
                reply = "✅ **Link captured.** Added to the database queue for the next automation run."
            else:
                context = f"Total jobs: {total_jobs}. Recent jobs: {jobs[:3]}"
                ai_response = model.generate_content(f"You are a sleek AI job agent. Answer briefly based on this data: {context}. User says: {prompt}")
                reply = ai_response.text
            st.markdown(reply)
            
        st.session_state.messages.append({"role": "assistant", "content": reply})
