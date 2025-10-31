import streamlit as st
import requests
import json
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Page config
st.set_page_config(
    page_title="Webhook & Sheets Dashboard",
    page_icon="🚀",
    layout="wide"
)

# Webhook URLs
WEBHOOK_URL = "https://agentonline-u29564.vm.elestio.app/webhook/0a07aa51-08e5-4ad7-a647-596bc9d1226f"
WEBHOOK_TEST_URL = "https://agentonline-u29564.vm.elestio.app/webhook-test/0a07aa51-08e5-4ad7-a647-596bc9d1226f"
SPREADSHEET_ID = "1kGsuraoXc4oMJfhzBNJLdAko61gdMszMPQDgiy8mr9o"

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'webhook_history' not in st.session_state:
    st.session_state.webhook_history = []
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False
if 'sheets_client' not in st.session_state:
    st.session_state.sheets_client = None
if 'sheets_data' not in st.session_state:
    st.session_state.sheets_data = None
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

def init_google_sheets(service_account_json):
    """Initialize Google Sheets connection"""
    try:
        creds_dict = json.loads(service_account_json)
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client, None
    except json.JSONDecodeError:
        return None, "Invalid JSON format"
    except Exception as e:
        return None, str(e)

def get_sheet_data(client, spreadsheet_id):
    """Fetch data from Google Sheets"""
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.get_worksheet(0)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Filter for prompt and video url columns (case-insensitive)
        if not df.empty:
            # Find columns that contain 'prompt' or 'video' (case-insensitive)
            prompt_cols = [col for col in df.columns if 'prompt' in col.lower()]
            video_cols = [col for col in df.columns if 'video' in col.lower() and 'url' in col.lower()]
            
            if prompt_cols and video_cols:
                df_filtered = df[[prompt_cols[0], video_cols[0]]]
                df_filtered.columns = ['Prompt', 'Video URL']
                return df_filtered, None
            else:
                return df, None  # Return all data if specific columns not found
        
        return df, None
    except Exception as e:
        return None, str(e)

def send_webhook(url, text_data):
    """Send POST request to webhook"""
    try:
        payload = {
            "text": text_data,
            "timestamp": datetime.now().isoformat()
        }
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text[:500],  # Limit response text
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout (10s)",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection failed - check webhook URL",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# Header
st.title("🚀 Webhook & Google Sheets Live Dashboard")
st.markdown("Send text to webhooks and monitor Google Sheets in real-time")
st.markdown("---")

# Sidebar - Configuration
with st.sidebar:
    st.header("🔐 Configuration")
    
    # Google Sheets Authentication
    with st.expander("📊 Google Sheets Setup", expanded=True):
        service_account_input = st.text_area(
            "Service Account JSON",
            height=200,
            placeholder='Paste your Google Cloud service account JSON here...',
            help="Get this from Google Cloud Console > IAM & Admin > Service Accounts"
        )
        
        if st.button("🔗 Connect to Sheets", use_container_width=True):
            if service_account_input:
                with st.spinner("Connecting..."):
                    client, error = init_google_sheets(service_account_input)
                    if client:
                        st.session_state.sheets_client = client
                        st.success("✅ Connected!")
                        # Fetch initial data
                        data, err = get_sheet_data(client, SPREADSHEET_ID)
                        if data is not None:
                            st.session_state.sheets_data = data
                            st.session_state.last_refresh = datetime.now()
                        else:
                            st.error(f"Error fetching data: {err}")
                    else:
                        st.error(f"❌ Connection failed: {error}")
            else:
                st.warning("Please paste your service account JSON")
        
        # Connection status
        if st.session_state.sheets_client:
            st.success("🟢 Connected to Google Sheets")
        else:
            st.info("🔴 Not connected")
    
    st.markdown("---")
    
    # Settings
    st.header("⚙️ Settings")
    
    st.session_state.auto_refresh = st.checkbox(
        "Auto-refresh Sheets",
        value=st.session_state.auto_refresh,
        help="Refresh Google Sheets data every 5 seconds"
    )
    
    refresh_interval = st.slider(
        "Refresh interval (seconds)",
        min_value=3,
        max_value=30,
        value=5,
        disabled=not st.session_state.auto_refresh
    )
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Webhook History", use_container_width=True):
        st.session_state.webhook_history = []
        st.success("History cleared!")
        time.sleep(1)
        st.rerun()

# Main content - Two columns
col1, col2 = st.columns([1, 1], gap="large")

# Left column - Webhook sender
with col1:
    st.header("📤 Send to Webhook")
    
    # Webhook selection
    webhook_type = st.radio(
        "Select Webhook Type",
        ["🟢 Production", "🧪 Test"],
        horizontal=True
    )
    
    selected_url = WEBHOOK_URL if "Production" in webhook_type else WEBHOOK_TEST_URL
    
    # Display selected URL
    st.text("Selected URL:")
    st.code(selected_url, language="text")
    
    # Text input
    text_input = st.text_area(
        "Message Content",
        height=150,
        placeholder="Enter your message here...",
        help="This text will be sent as JSON payload to the webhook"
    )
    
    # Action buttons
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        send_button = st.button("🚀 Send", use_container_width=True, type="primary")
    
    with col_b:
        test_button = st.button("🧪 Test", use_container_width=True)
    
    with col_c:
        clear_input = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_input:
        st.rerun()
    
    # Send webhook
    if send_button:
        if text_input.strip():
            with st.spinner("Sending to webhook..."):
                result = send_webhook(selected_url, text_input)
                
                # Add to history
                st.session_state.webhook_history.insert(0, {
                    "type": webhook_type,
                    "message": text_input,
                    **result
                })
                
                # Show result
                if result["success"]:
                    st.success(f"✅ Sent successfully! Status: {result['status_code']}")
                    with st.expander("📝 Response"):
                        st.code(result['response'], language="json")
                else:
                    st.error(f"❌ Failed: {result['error']}")
        else:
            st.warning("⚠️ Please enter a message")
    
    # Test connection
    if test_button:
        with st.spinner("Testing connection..."):
            result = send_webhook(selected_url, "Connection test from Streamlit")
            
            if result["success"]:
                st.success(f"✅ Connection OK! Status: {result['status_code']}")
            else:
                st.error(f"❌ Connection failed: {result['error']}")
    
    # Recent webhook history
    st.markdown("---")
    st.subheader("📋 Recent Requests")
    
    if st.session_state.webhook_history:
        # Show last 5 requests
        for i, item in enumerate(st.session_state.webhook_history[:5]):
            status_icon = "✅" if item['success'] else "❌"
            webhook_label = item['type'].replace("🟢 ", "").replace("🧪 ", "")
            
            with st.expander(
                f"{status_icon} [{item['timestamp']}] {webhook_label}",
                expanded=(i == 0)
            ):
                st.write("**Message:**")
                st.text(item['message'][:200] + "..." if len(item['message']) > 200 else item['message'])
                
                if item['success']:
                    st.success(f"Status Code: {item['status_code']}")
                    if item['response']:
                        st.code(item['response'], language="json")
                else:
                    st.error(f"Error: {item['error']}")
    else:
        st.info("💭 No webhook requests sent yet")

# Right column - Google Sheets live view
with col2:
    st.header("📊 Google Sheets Live View")
    
    if st.session_state.sheets_client:
        # Refresh controls
        col_x, col_y, col_z = st.columns([2, 1, 1])
        
        with col_y:
            manual_refresh = st.button("🔄 Refresh", use_container_width=True)
        
        with col_z:
            if st.session_state.last_refresh:
                st.caption(f"Updated: {st.session_state.last_refresh.strftime('%H:%M:%S')}")
        
        # Fetch data on manual refresh or auto-refresh
        should_refresh = manual_refresh
        if st.session_state.auto_refresh:
            if st.session_state.last_refresh is None:
                should_refresh = True
            elif (datetime.now() - st.session_state.last_refresh).seconds >= refresh_interval:
                should_refresh = True
        
        if should_refresh:
            with st.spinner("Fetching data..."):
                data, error = get_sheet_data(st.session_state.sheets_client, SPREADSHEET_ID)
                if data is not None:
                    st.session_state.sheets_data = data
                    st.session_state.last_refresh = datetime.now()
                else:
                    st.error(f"Error: {error}")
        
        # Display data
        if st.session_state.sheets_data is not None:
            df = st.session_state.sheets_data
            
            if not df.empty:
                st.success(f"📈 {len(df)} rows loaded")
                
                # Display dataframe
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=400
                )
                
                # Show video URLs as clickable links
                st.markdown("---")
                st.subheader("🎥 Video URLs")
                
                if 'Video URL' in df.columns:
                    video_urls = df['Video URL'].dropna()
                    if len(video_urls) > 0:
                        for idx, url in enumerate(video_urls):
                            if url and str(url).strip():
                                st.markdown(f"**Row {idx+1}:** [{url}]({url})")
                    else:
                        st.info("No video URLs found")
                else:
                    st.info("Video URL column not found")
                
                # Download button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"sheets_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("📭 Spreadsheet is empty")
        else:
            st.info("👆 Click Refresh to load data")
        
        # Auto-refresh trigger
        if st.session_state.auto_refresh:
            time.sleep(1)
            st.rerun()
            
    else:
        st.info("🔌 Connect to Google Sheets in the sidebar to view live data")
        st.markdown("""
        **Setup Instructions:**
        1. Go to Google Cloud Console
        2. Create a Service Account
        3. Download JSON key file
        4. Share your Google Sheet with the service account email
        5. Paste the JSON content in the sidebar
        """)

# Footer
st.markdown("---")
st.caption("💡 Tip: Use the Test webhook to verify connectivity before sending important data")
