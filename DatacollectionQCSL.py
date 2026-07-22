import streamlit as st
import datetime
import pytz
import os
import json
import gspread
import uuid
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
SHEET_NAME = "QC Time Study DB" 
STYLES = ["Style 0", "Style 1", "Style 1", "Style 1S", "Style 4L", "Style 4LL", "Style 4S", "Style 6", "Stlye DC4", "Style DC5","Style DC6","Style SL"]
STEPS = [
    "QC_Start",
    "QC_Sample_Time_End",
    "Moisture_Test_End",
    "SizingTest_End",
    "UnsoundSorting_End",
    "HMI_End",
    "Reporting_End"
]

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================
@st.cache_resource
def get_gsheet_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def log_timestamp(batch_id, bin_num, style, step_name):
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).sheet1
    
    # If the sheet is empty, add the new header row including Batch_ID
    if len(sheet.row_values(1)) == 0:
        sheet.append_row(["Batch_ID", "Bin_Number", "Style", "Step", "Timestamp"])
        
    tz = pytz.timezone('Africa/Johannesburg')
    current_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    sheet.append_row([batch_id, bin_num, style, step_name, current_time])

# ==========================================
# 2. STATE RECOVERY 
# ==========================================
if 'current_step' not in st.session_state:
    if "step" in st.query_params:
        st.session_state.current_step = int(st.query_params["step"])
        st.session_state.batch_id = st.query_params.get("batch_id", "")
        st.session_state.bin_number = st.query_params.get("bin", "")
        st.session_state.style = st.query_params.get("style", STYLES[0])
    else:
        st.session_state.current_step = -1
        st.session_state.batch_id = ""
        st.session_state.bin_number = ""
        st.session_state.style = STYLES[0]

def sync_state_to_url():
    if st.session_state.current_step == -1:
        st.query_params.clear()
    else:
        st.query_params["step"] = st.session_state.current_step
        st.query_params["batch_id"] = st.session_state.batch_id
        st.query_params["bin"] = st.session_state.bin_number
        st.query_params["style"] = st.session_state.style

# ==========================================
# 3. USER INTERFACE
# ==========================================
st.set_page_config(page_title="QC Time Study", page_icon="⏱️")
st.title("⏱️ QC Time Study")

# Phase 1: Setup a new batch
if st.session_state.current_step == -1:
    st.header("Start New Batch")
    bin_input = st.text_input("Enter Bin Number:")
    style_input = st.selectbox("Select Style:", STYLES)
    
    if st.button("Start Recording", type="primary", use_container_width=True):
        if bin_input:
            # Generate a unique 8-character ID for this specific batch
            st.session_state.batch_id = str(uuid.uuid4())[:8].upper()
            st.session_state.bin_number = bin_input
            st.session_state.style = style_input
            st.session_state.current_step = 0
            sync_state_to_url()
            st.rerun()
        else:
            st.error("Please enter a Bin Number first.")

# Phase 2: Recording sequence
elif st.session_state.current_step < len(STEPS):
    current_step_name = STEPS[st.session_state.current_step]
    
    # Display the Batch ID so the user knows it's being tracked
    st.info(f"**Batch ID:** {st.session_state.batch_id} | **Bin:** {st.session_state.bin_number} | **Style:** {st.session_state.style}")
    st.progress(st.session_state.current_step / len(STEPS))
    st.subheader(f"Next Step: {current_step_name}")
    
    if st.button(f"⏺ RECORD {current_step_name}", type="primary", use_container_width=True):
        with st.spinner("Saving to Google Sheets..."):
            log_timestamp(
                st.session_state.batch_id, 
                st.session_state.bin_number, 
                st.session_state.style, 
                current_step_name
            )
        st.session_state.current_step += 1
        sync_state_to_url()
        st.rerun()
        
    if st.button("Cancel Batch", use_container_width=True):
        st.session_state.current_step = -1
        sync_state_to_url()
        st.rerun()

# Phase 3: Batch Complete
else:
    st.success(f"Successfully recorded all steps for Bin {st.session_state.bin_number}!")
    if st.button("Start Next Batch", type="primary", use_container_width=True):
        st.session_state.current_step = -1
        st.session_state.batch_id = ""
        st.session_state.bin_number = ""
        sync_state_to_url()
        st.rerun()