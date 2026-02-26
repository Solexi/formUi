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

TEST_MEETINGS = [
    {
        "id": "98765432100",
        "topic": "Client Strategy Call",
        "start_time": "2026-02-20T14:00:00Z",
        "duration": 45,
        "host_email": "john@company.com",
        "recording_files": [
            {
                "id": "rec_001",
                "file_type": "MP4",
                "file_extension": "mp4",
                "file_size": 23456789,
                "download_url": "http://raw.githubusercontent.com/Solexi/Solexi/main/3248217-uhd_3840_2160_25fps(1).mp4",
                "status": "completed"
            },
            {
                "id": "transcript_001",
                "file_type": "TRANSCRIPT",
                "file_extension": "vtt",
                "download_url": "https://drive.google.com/uc?export=download&id=1Xs2sp0sByYGhBuR7zfF6D1oSEOAfvcOJ",
                "status": "completed"
            }
        ]
    },
    {
        "id": "11223344556",
        "topic": "Product Demo - Q4 Review",
        "start_time": "2026-02-18T10:30:00Z",
        "duration": 60,
        "host_email": "sarah@company.com",
        "recording_files": [
            {
                "id": "rec_002",
                "file_type": "MP4",
                "file_extension": "mp4",
                "file_size": 45678901,
                "download_url": "http://raw.githubusercontent.com/Solexi/Solexi/main/3248217-uhd_3840_2160_25fps(1).mp4",
                "status": "completed"
            }
        ]
    },
    {
        "id": "55667788990",
        "topic": "Team Sync - Sprint Planning",
        "start_time": "2026-02-15T09:00:00Z",
        "duration": 30,
        "host_email": "mike@company.com",
        "recording_files": []
    }
]

def format_datetime(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return iso_string

def fetch_meeting_details(meeting_id):
    # Replace with actual Zoom API call when available
    meeting = next((m for m in TEST_MEETINGS if m["id"] == meeting_id), None)
    return meeting

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
            .select("project_id, project_name, company_name, folder_url") \
            .eq("project_token", project_token) \
            .execute()
        
        if not project_response.data:
            st.error("Invalid or expired access token.")
            st.stop()
        
        selected_project = project_response.data[0]
        selected_project_id = selected_project["project_id"]
        
        st.success(f"Reviewing recordings for: **{selected_project['company_name']} - {selected_project['project_name']}**")
        if selected_project.get("folder_url"):
            st.markdown(f"**Google Drive Folder:** [Open Folder]({selected_project['folder_url']})")
    
    else:
        projects_response = supabase.table("projects") \
            .select("project_id, project_name, company_name, project_token, folder_url") \
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

        if selected_project.get("folder_url"):
            st.markdown(f"**Google Drive Folder:** [Open Folder]({selected_project['folder_url']})")
        
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
            meeting_date = format_datetime(record['meeting_date']) if record.get('meeting_date') else 'N/A'
            st.write(f"**Date:** {meeting_date}")
        
        with col2:
            duration_value = record.get('duration')
            if duration_value and duration_value != 'N/A':
                st.write(f"**Duration:** {duration_value} min")
            else:
                st.write(f"**Duration:** N/A")
            
            host_id = record.get('host_id', 'N/A')
            if len(str(host_id)) > 20:
                st.write(f"**Host:** {str(host_id)[:20]}...")
            else:
                st.write(f"**Host:** {host_id}")
        
        st.markdown("---")
        
        if f"loaded_meeting_{record['zoom_record_id']}" not in st.session_state:
            st.session_state[f"loaded_meeting_{record['zoom_record_id']}"] = None
        
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
                "Load Meeting",
                key=f"load_meeting_{record['zoom_record_id']}",
                use_container_width=True
            ):
                if override_meeting_id:
                    meeting_details = fetch_meeting_details(override_meeting_id)
                    st.session_state[f"loaded_meeting_{record['zoom_record_id']}"] = meeting_details
                    st.rerun()
                else:
                    st.warning("Please enter a Meeting ID first")

        loaded_meeting = st.session_state.get(f"loaded_meeting_{record['zoom_record_id']}")
        if loaded_meeting:
            with st.container():
                st.markdown("### Meeting Details Preview")
                
                details_col1, details_col2 = st.columns(2)
                
                with details_col1:
                    st.info(f"**Topic:** {loaded_meeting['topic']}")
                    st.info(f"**Meeting ID:** `{loaded_meeting['id']}`")
                    st.info(f"**Host:** {loaded_meeting['host_email']}")
                
                with details_col2:
                    formatted_time = format_datetime(loaded_meeting['start_time'])
                    st.info(f"**Scheduled:** {formatted_time}")
                    st.info(f"**Duration:** {loaded_meeting['duration']} minutes")

                    if loaded_meeting.get('recording_files'):
                        recordings_count = len(loaded_meeting['recording_files'])
                        st.info(f"**Recordings:** {recordings_count} file(s) available")

                if loaded_meeting.get('recording_files'):
                    with st.expander("📁 Recording Files", expanded=False):
                        for rec_file in loaded_meeting['recording_files']:
                            file_type = rec_file.get('file_type', 'Unknown')
                            status = rec_file.get('status', 'Unknown')
                            
                            col_file1, col_file2 = st.columns([3, 1])
                            with col_file1:
                                st.write(f"**{file_type}** - {rec_file.get('file_extension', '').upper()}")
                                if rec_file.get('file_size'):
                                    size_mb = rec_file['file_size'] / (1024 * 1024)
                                    st.caption(f"Size: {size_mb:.2f} MB")
                            with col_file2:
                                st.caption(f"Status: {status}")
                else:
                    st.warning("⚠️ No recording files available for this meeting")
                
                confirm_col1, confirm_col2 = st.columns([1, 1])
                
                with confirm_col1:
                    if st.button(
                        "✓ Use This Meeting ID",
                        key=f"confirm_override_{record['zoom_record_id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        supabase.table("zoom_meetings") \
                            .update({
                                "override_meeting_id": override_meeting_id,
                                "status": "override_requested",
                                "processed": True,
                                "processed_at": datetime.now().isoformat()
                            }) \
                            .eq("zoom_record_id", record["zoom_record_id"]) \
                            .execute()
                        
                        n8n_wf3_url = os.getenv("N8N_WF3_WEBHOOK_URL")
                        
                        if n8n_wf3_url:
                            try:
                                wf3_payload = {
                                    "project_id": selected_project_id,
                                    "meeting_id": override_meeting_id,
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
                            
                            except Exception as e:
                                st.error(f"Workflow trigger failed: {str(e)}")
                        else:
                            st.success(f"Override Meeting ID saved: {override_meeting_id}")

                        st.session_state[f"loaded_meeting_{record['zoom_record_id']}"] = None
                        st.rerun()
                
                with confirm_col2:
                    if st.button(
                        "✗ Try Different Meeting ID",
                        key=f"cancel_override_{record['zoom_record_id']}",
                        use_container_width=True
                    ):
                        st.session_state[f"loaded_meeting_{record['zoom_record_id']}"] = None
                        st.rerun()
        
        elif override_meeting_id:
            if st.button(
                "Submit Correct Meeting ID",
                key=f"override_btn_{record['zoom_record_id']}",
                use_container_width=False
            ):
                st.warning("⚠️ Please click 'Load Meeting' first to verify the meeting details before submitting.")

# ADMIN VIEW: ALL PROJECTS
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

                created_at = project.get('created_at', 'N/A')
                if created_at != 'N/A':
                    created_date = format_datetime(created_at)
                    st.write(f"**Created:** {created_date}")
                else:
                    st.write(f"**Created:** N/A")
            
            with col2:
                st.write(f"**Meeting Type:** {project.get('meeting_type', 'N/A')}")
                st.write(f"**Meeting ID:** {project.get('meeting_id', 'N/A')}")
                hubspot = project.get('hubspot_url', 'N/A')
                if len(str(hubspot)) > 30:
                    st.write(f"**HubSpot:** {str(hubspot)[:30]}...")
                else:
                    st.write(f"**HubSpot:** {hubspot}")

                folder_url = project.get('folder_url')
                if folder_url:
                    st.markdown(f"**Google Drive Folder:** [Open Folder]({folder_url})")
                else:
                    st.write("**Google Drive Folder:** N/A")
            
            # Show secure link
            if project.get("project_token"):
                base_url = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")
                secure_link = f"{base_url}?token={project['project_token']}"
                st.code(secure_link, language=None)