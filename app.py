import logging
import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

from components.views import (
    render_admin_projects_view,
    render_create_project_view,
    render_review_zoom_recordings_view,
)

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

st.set_page_config(page_title="HA Automation Form", layout="wide")
st.title("HA Data Integration")

project_token = st.query_params.get("token", None)

if project_token:
    st.sidebar.info("Project Access")
    menu = "Review Zoom Recordings"
else:
    menu = st.sidebar.selectbox(
        "Navigation",
        ["Create Project", "Review Zoom Recordings (All)"],
    )

if menu == "Create Project":
    render_create_project_view(supabase, N8N_WEBHOOK_URL)
elif menu == "Review Zoom Recordings" or project_token:
    render_review_zoom_recordings_view(supabase, project_token, logger)
elif menu == "Review Zoom Recordings (All)":
    render_admin_projects_view(supabase, logger)