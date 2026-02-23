import streamlit as st
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import hashlib
import secrets

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="HA Automation Form", layout="wide")
st.title("HA Data Integration")

query_params = st.query_params
project_token = query_params.get("token", None)

if project_token:
    st.sidebar.info("Project Access")
    menu = "Review Zoom Recordings"
else:
    menu = st.sidebar.selectbox(
        "Navigation",
        ["Create Project", "Review Zoom Recordings (All)"]
    )

# SECTION 1: CREATE PROJECT
if menu == "Create Project":
    st.header("Create New Project")
    
    with st.form("project_form", clear_on_submit=True):
        company_name = st.text_input("Client Company Name")
        project_name = st.text_input("Project Name")
        hubspot_url = st.text_input("HubSpot URL")
        notes = st.text_area("Notes")
        key_contact = st.text_input("Key Contact Full Name")
        meeting_type = st.text_input("Meeting Type")
        meeting_id = st.text_input("Meeting ID")
        meeting_number = st.text_input("Meeting Number")
        
        submitted = st.form_submit_button("Create Project")
        
        if submitted:
            if not project_name or not company_name:
                st.error("Project Name and Company Name are required!")
            else:
                project_token = secrets.token_urlsafe(32)
                
                data = {
                    "project_name": project_name,
                    "company_name": company_name,
                    "hubspot_url": hubspot_url,
                    "notes": notes,
                    "key_contact": key_contact,
                    "meeting_type": meeting_type,
                    "meeting_id": meeting_id,
                    "meeting_number": meeting_number,
                    "project_token": project_token,
                }
                
                response = supabase.table("projects").insert(data).execute()
                
                if response.data:
                    project_id = response.data[0]["project_id"]
                    
                    base_url = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")
                    secure_link = f"{base_url}?token={project_token}"
                    
                    st.session_state.project_created = True
                    st.session_state.project_name_created = project_name
                    st.session_state.secure_link = secure_link
                    
                    if N8N_WEBHOOK_URL:
                        try:
                            webhook_payload = {
                                "project_id": project_id,
                                "project_name": project_name,
                                "company_name": company_name,
                                "meeting_type": meeting_type,
                                "meeting_id": meeting_id,
                                "meeting_number": meeting_number,
                                "project_token": project_token,
                                "trigger_source": "streamlit_form"
                            }
                            
                            webhook_response = requests.post(
                                N8N_WEBHOOK_URL,
                                json=webhook_payload,
                                timeout=10
                            )
                            
                            if webhook_response.status_code == 200:
                                st.session_state.webhook_success = True
                            else:
                                st.session_state.webhook_warning = webhook_response.status_code
                        
                        except Exception as e:
                            st.session_state.webhook_error = str(e)
                    
                    st.rerun()
                else:
                    st.error("Error creating project. Please try again.")
    
    if st.session_state.get("project_created"):
        st.success(f"Project '{st.session_state.project_name_created}' created successfully!")
        
        st.info(f"**Share this link with your client:**")
        st.code(st.session_state.secure_link, language=None)
        st.caption("This link allows the client to review only their Zoom recordings.")
        
        if st.button("Create Another Project"):
            st.session_state.project_created = False
            st.session_state.project_name_created = None
            st.session_state.secure_link = None
            st.rerun()


# SECTION 2: REVIEW ZOOM RECORDINGS
elif menu == "Review Zoom Recordings" or project_token:
    
    st.header("Review Zoom Recordings")
    
    if project_token:
        project_response = supabase.table("projects") \
            .select("project_id, project_name, company_name") \
            .eq("project_token", project_token) \
            .execute()
        
        if not project_response.data:
            st.error("Invalid or expired access token.")
            st.stop()
        
        selected_project = project_response.data[0]
        selected_project_id = selected_project["project_id"]
        
        st.success(f"Reviewing recordings for: **{selected_project['company_name']} - {selected_project['project_name']}**")
    
    else:
        projects_response = supabase.table("projects") \
            .select("project_id, project_name, company_name, project_token") \
            .order("created_at", desc=True) \
            .execute()
        
        if not projects_response.data:
            st.info("No projects found. Create a project first.")
            st.stop()
        
        project_options = {
            f"{p['company_name']} - {p['project_name']}": p
            for p in projects_response.data
        }
        
        selected_project_label = st.selectbox(
            "Select Project",
            list(project_options.keys())
        )
        
        selected_project = project_options[selected_project_label]
        selected_project_id = selected_project["project_id"]
        
        if selected_project.get("project_token"):
            base_url = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")
            secure_link = f"{base_url}?token={selected_project['project_token']}"
            
            with st.expander("Share Secure Link with Client"):
                st.code(secure_link, language=None)
                st.caption("This link allows clients to review only their recordings")
    
    recordings = supabase.table("zoom_meetings") \
        .select("*") \
        .eq("project_id", selected_project_id) \
        .eq("processed", False) \
        .order("meeting_date", desc=True) \
        .execute()
    
    if not recordings.data:
        st.info("No pending recordings for this project. All caught up!")
        st.stop()

    for idx, record in enumerate(recordings.data):
        st.divider()
        
        col_header, col_status = st.columns([3, 1])
        
        with col_header:
            st.subheader(f"{record['meeting_topic']}")
        
        with col_status:
            st.caption(f"Status: Pending Review")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Meeting ID:** `{record['meeting_id']}`")
            st.write(f"**Date:** {record['meeting_date']}")
            
            # if record.get('file_url'):
            #     st.write(f"**Files:** [View in Drive]({record['file_url']})")
        
        with col2:
            st.write(f"**Duration:** {record.get('duration', 'N/A')} min")
            st.write(f"**Host:** {record.get('host_id', 'N/A')[:20]}...")
        
        st.markdown("---")
        
        action_col1, action_col2, action_col3 = st.columns([1, 2, 1])
        
        with action_col1:
            if st.button(
                "Accept Recording",
                key=f"accept_{record['zoom_record_id']}",
                type="primary",
                use_container_width=True
            ):
                supabase.table("zoom_meetings") \
                    .update({
                        "processed": True,
                        "processed_at": datetime.now().isoformat(),
                        "status": "approved"
                    }) \
                    .eq("zoom_record_id", record["zoom_record_id"]) \
                    .execute()
                
                n8n_wf3_url = os.getenv("N8N_WF3_WEBHOOK_URL")
                
                if n8n_wf3_url:
                    try:
                        wf3_payload = {
                            "project_id": selected_project_id,
                            "meeting_id": record["meeting_id"],
                            "zoom_record_id": record["zoom_record_id"],
                            "status": "approved",
                            "trigger_source": "streamlit_approval"
                        }
                        
                        wf3_response = requests.post(
                            n8n_wf3_url,
                            json=wf3_payload,
                            timeout=10
                        )
                        
                        if wf3_response.status_code == 200:
                            st.success("Recording approved! Workflow 3 triggered.")
                        else:
                            st.warning(f"Approved, but workflow trigger failed (status {wf3_response.status_code})")
                    
                    except Exception as e:
                        st.error(f"Workflow 3 trigger failed: {str(e)}")
                else:
                    st.success("Recording approved!")
                
                st.rerun()
        
        with action_col2:
            override_meeting_id = st.text_input(
                "Or enter different Meeting ID",
                key=f"override_input_{record['zoom_record_id']}",
                placeholder="Enter Meeting ID to use instead"
            )
        
        with action_col3:
            if st.button(
                "Submit Correct Meeting ID",
                key=f"override_btn_{record['zoom_record_id']}",
                use_container_width=True
            ):
                if override_meeting_id:
                    supabase.table("zoom_meetings") \
                        .update({
                            "override_meeting_id": override_meeting_id,
                            "status": "override_requested",
                            "processed": True,
                            "processed_at": datetime.now().isoformat()
                        }) \
                        .eq("zoom_record_id", record["zoom_record_id"]) \
                        .execute()
                    
                    # TRIGGER WORKFLOW 3 WITH OVERRIDE
                    n8n_wf3_url = os.getenv("N8N_WF3_WEBHOOK_URL")
                    
                    if n8n_wf3_url:
                        try:
                            wf3_payload = {
                                "project_id": selected_project_id,
                                "meeting_id": override_meeting_id,  # Use override ID
                                "zoom_record_id": record["zoom_record_id"],
                                "status": "override_approved",
                                "original_meeting_id": record["meeting_id"],
                                "trigger_source": "streamlit_override"
                            }
                            
                            wf3_response = requests.post(
                                n8n_wf3_url,
                                json=wf3_payload,
                                timeout=10
                            )
                            
                            if wf3_response.status_code == 200:
                                st.success(f"Override submitted! Using Meeting ID: {override_meeting_id}")
                            # else:
                            #     st.warning(f"Override saved, but workflow trigger failed (status {wf3_response.status_code})")
                        
                        except Exception as e:
                            st.error(f"Workflow trigger failed: {str(e)}")
                    else:
                        st.success(f"Override Meeting ID saved: {override_meeting_id}")
                    
                    st.rerun()
                else:
                    st.warning("Please enter a Meeting ID first")


# ==========================================
# ADMIN VIEW: ALL PROJECTS
# ==========================================
elif menu == "Review Zoom Recordings (All)":
    st.header("All Projects Overview")
    
    projects_response = supabase.table("projects") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    
    if not projects_response.data:
        st.info("No projects found.")
        st.stop()
    
    for project in projects_response.data:
        with st.expander(f"{project['company_name']} - {project['project_name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Project ID:** {project['project_id']}")
                st.write(f"**Contact:** {project.get('key_contact', 'N/A')}")
                st.write(f"**Created:** {project.get('created_at', 'N/A')[:10]}")
            
            with col2:
                st.write(f"**Meeting Type:** {project.get('meeting_type', 'N/A')}")
                st.write(f"**Meeting ID:** {project.get('meeting_id', 'N/A')}")
                st.write(f"**HubSpot:** {project.get('hubspot_url', 'N/A')[:30]}...")
            
            # Show secure link
            if project.get("project_token"):
                base_url = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")
                secure_link = f"{base_url}?token={project['project_token']}"
                st.code(secure_link, language=None)