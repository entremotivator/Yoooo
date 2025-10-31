import streamlit as st
import requests
import pandas as pd
import time
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Webhook + Sheets Dashboard", layout="wide")

st.title("📡 Webhook Sender + Google Sheets Live Dashboard")

# ------------------------------
# SIDEBAR - Webhook Sender
# ------------------------------
st.sidebar.header("Send Webhook Message")
webhook_url = "https://agentonline-u29564.vm.elestio.app/webhook-test/Imagetovideo/"

with st.sidebar.form("webhook_form"):
    message = st.text_area("Message", placeholder="Enter your message to send")
    image_url = st.text_input("Image URL (optional)", "")
    video_option = st.selectbox("Convert to:", ["Video", "Slideshow", "GIF"])
    send_btn = st.form_submit_button("🚀 Send Webhook")

if send_btn:
    payload = {"message": message, "image_url": image_url, "type": video_option}
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            st.sidebar.success("✅ Webhook sent successfully!")
        else:
            st.sidebar.error(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        st.sidebar.error(f"⚠️ Failed to send: {e}")

# ------------------------------
# GOOGLE SHEETS CONNECTION
# ------------------------------
st.subheader("📊 Live Data from Google Sheets")

# You must create a Google Cloud service account and share the sheet with its email
SERVICE_ACCOUNT_FILE = "service_account.json"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1kGsuraoXc4oMJfhzBNJLdAko61gdMszMPQDgiy8mr9o/edit?usp=sharing"
SHEET_NAME = "Sheet1"

@st.cache_data(ttl=30)
def load_sheet_data():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

try:
    df = load_sheet_data()
    if df.empty:
        st.info("No data found in sheet yet.")
    else:
        cols = st.columns(3)
        for i, row in df.iterrows():
            with cols[i % 3]:
                st.markdown(f"""
                <div style="background-color:#f8f9fa;padding:15px;border-radius:15px;
                box-shadow:0 2px 6px rgba(0,0,0,0.1);margin-bottom:10px;">
                    <h4 style="color:#333;">{row.get('Title','Untitled')}</h4>
                    <p><b>Status:</b> {row.get('Status','N/A')}</p>
                    <p><b>Created:</b> {row.get('Timestamp','')}</p>
                    <p><b>Details:</b> {row.get('Description','')}</p>
                </div>
                """, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error loading sheet: {e}")
    st.info("👉 Make sure you've created a service account JSON and shared your Google Sheet with it.")

st.caption("Auto-refresh every 30 seconds for live updates.")
