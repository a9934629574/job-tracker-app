import streamlit as st
from supabase import create_client
import pandas as pd

# App configuration & Standalone PWA headers
st.set_page_config(page_title="Job Agent", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Job Agent">
    <link rel="apple-touch-icon" href="https://img.icons8.com/fluency/192/briefcase.png">
    <style>
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💼 Job Hunter: Hyderabad & Remote")

# Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

response = supabase.table("applications").select("*").order("created_at", desc=True).execute()
data = response.data

if data:
    for row in data:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.subheader(row['title'])
            st.write(f"🏢 **{row['company']}** | 📍 {row['location']}")
        with col2:
            st.info(row['status'])
        with col3:
            st.link_button("Open & Submit", row['apply_url'], use_container_width=True)
        st.divider()
else:
    st.write("No matching jobs logged yet.")
