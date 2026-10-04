import streamlit as st
from supabase import create_client
import google.generativeai as genai

st.set_page_config(page_title="Job Agent", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<meta name="apple-mobile-web-app-capable" content="yes"><style>header {visibility: hidden;}</style>""", unsafe_allow_html=True)

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("💼 AI Job Assistant")
tab1, tab2 = st.tabs(["📋 Dashboard", "💬 Chat with AI"])

with tab1:
    data = supabase.table("applications").select("*").order("created_at", desc=True).execute()
    if data.data:
        for row in data.data:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.markdown(f"**{row['title']}** at {row['company']} (📍 {row['location']})")
            col2.info(row['status'])
            col3.link_button("Open & Submit", row['apply_url'], use_container_width=True)
            st.divider()
    else:
        st.write("No jobs logged yet.")

with tab2:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hi! Ask about your jobs, or paste a link and say 'fill this form'."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Talk to your assistant..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if "http" in prompt and "fill" in prompt.lower():
                supabase.table("applications").insert({
                    "title": "Manual Request",
                    "company": "Pending Extraction",
                    "location": "Custom",
                    "apply_url": prompt,
                    "status": "Queued for Morning Run"
                }).execute()
                reply = "I've saved this link! I will autofill it during my next morning run."
            else:
                recent = supabase.table("applications").select("*").limit(5).execute()
                ai_response = model.generate_content(f"You are a job assistant. User said: '{prompt}'. Context: {recent.data}")
                reply = ai_response.text
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
