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

# Enhanced step definitions with clear descriptions/notes for the operator
STEPS_INFO = [
    {
        "name": "QC_Start", 
        "label": "Start QC Process", 
        "note": "Tap when you start the QC process for the bin."
    },
    {
        "name": "QC_Sample_Time_End", 
        "label": "Sample Time End", 
        "note": "Tap when you are done collecting the styling and unsound samples (1Kg/3Kg)"
    },
    {
        "name": "Looking_Unsound_ForeignMatter_In_Sample", 
        "label": "Searching through Sample for Unsound/Foreign Matter", 
        "note": "Tap when you are done with the initial search for Unsound/Foreign Matte"
    },
    {
        "name": "Moisture_Test_End", 
        "label": "Moisture Test Complete", 
        "note": "Tap when you have started the moisture anaylses on the machine"
    },
    {
        "name": "SizingTest_End", 
        "label": "Sizing Test Complete", 
        "note": "Tap when you are finished with the sizing test"
    },
    {
        "name": "UnsoundSorting_End", 
        "label": "Unsound Sorting Complete", 
        "note": "Tap when defect and unsound sorting is finished."
    },
    {
        "name": "HMI_End", 
        "label": "HMI Entry Complete", 
        "note": "Tap when you have finished inputing and getting the bin result on the HMI"
    },
    {
        "name": "Reporting_End", 
        "label": "Reporting Complete", 
        "note": "Tap when final reporting and paperwork is completed."
    }
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

def log_timestamp(batch_id, clock_num, bin_num, style, step_name):
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).sheet1
    
    if len(sheet.row_values(1)) == 0:
        sheet.append_row(["Batch_ID", "Clock_Number", "Bin_Number", "Style", "Step", "Timestamp"])
        
    tz = pytz.timezone('Africa/Johannesburg')
    current_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    sheet.append_row([batch_id, clock_num, bin_num, style, step_name, current_time])

# ==========================================
# 2. STATE RECOVERY (Persistent Clock Number)
# ==========================================
if 'clock_number' not in st.session_state:
    st.session_state.clock_number = st.query_params.get("clock", "")

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
    # Always keep the clock number in the query params if present
    if st.session_state.clock_number:
        st.query_params["clock"] = st.session_state.clock_number
        
    if st.session_state.current_step == -1:
        # Clear batch parameters but retain clock
        for param in ["step", "batch_id", "bin", "style"]:
            if param in st.query_params:
                del st.query_params[param]
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
    
    # Pre-fill with the remembered clock number
    clock_input = st.text_input("Enter Clock Number:", value=st.session_state.clock_number)
    bin_input = st.text_input("Enter Bin Number:")
    style_input = st.selectbox("Select Style:", STYLES)
    
    if st.button("Start Recording", type="primary", use_container_width=True):
        if clock_input and bin_input:
            st.session_state.clock_number = clock_input
            st.session_state.batch_id = str(uuid.uuid4())[:8].upper()
            st.session_state.bin_number = bin_input
            st.session_state.style = style_input
            st.session_state.current_step = 0
            sync_state_to_url()
            st.rerun()
        else:
            st.error("Please enter both a Clock Number and a Bin Number first.")

# Phase 2: Recording sequence
elif st.session_state.current_step < len(STEPS_INFO):
    current_step_info = STEPS_INFO[st.session_state.current_step]
    
    st.info(f"**Operator:** {st.session_state.clock_number} | **Bin:** {st.session_state.bin_number} | **Style:** {st.session_state.style}")
    st.progress(st.session_state.current_step / len(STEPS_INFO))
    
    st.subheader(f"Step {st.session_state.current_step + 1} of {len(STEPS_INFO)}: {current_step_info['label']}")
    st.markdown(f"> **Note:** {current_step_info['note']}")
    
    if st.button(f"⏺ RECORD {current_step_info['label'].upper()}", type="primary", use_container_width=True):
        with st.spinner("Saving to Google Sheets..."):
            log_timestamp(
                st.session_state.batch_id,
                st.session_state.clock_number,
                st.session_state.bin_number, 
                st.session_state.style, 
                current_step_info['name']
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
        # Note: clock_number is intentionally preserved here!
        sync_state_to_url()
        st.rerun()