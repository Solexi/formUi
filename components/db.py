import os
import streamlit as st


def safe_execute(query_builder, logger, user_context="database operation"):
    """Execute a Supabase query and surface connection errors cleanly in the UI."""
    try:
        return query_builder.execute()
    except Exception as exc:
        logger.exception("Supabase %s failed: %s", user_context, exc)
        st.error(
            f"Could not complete {user_context}. Please verify SUPABASE_URL, internet/DNS, and Supabase project availability."
        )
        st.info(f"Technical details: {exc}")
        st.stop()


def save_document(supabase, project_id, doc_type, file_name, file_content, logger):
    try:
        folder_path = f"projects/{project_id}/{doc_type}"
        original_name = os.path.basename(file_name)
        safe_name = "_".join(original_name.split())
        file_path = f"{folder_path}/{safe_name}"

        supabase.storage.from_("documents").upload(
            file_path,
            file_content,
            {"upsert": "true"},
        )

        public_url = supabase.storage.from_("documents").get_public_url(file_path)
        logger.info("File uploaded to storage at %s, public URL: %s", file_path, public_url)

        doc_record_base = {
            "project_id": project_id,
            "doc_type": doc_type,
            "file_name": safe_name,
            "file_url": public_url,
        }

        user_id = st.session_state.get("auth_user_id")
        candidate_records = [doc_record_base]

        if user_id:
            candidate_records.extend([
                {**doc_record_base, "uploaded_by": user_id},
                {**doc_record_base, "created_by": user_id},
                {**doc_record_base, "user_id": user_id},
                {**doc_record_base, "reviewer_user_id": user_id},
            ])

        insert_error = None
        for candidate in candidate_records:
            try:
                supabase.table("analysis_documents").insert(candidate).execute()
                return True, f"Document '{safe_name}' saved successfully."
            except Exception as exc:
                insert_error = exc
                error_text = str(exc).lower()
                if "column" in error_text and "does not exist" in error_text:
                    continue
                if "row-level security" in error_text or "violates row-level security policy" in error_text:
                    continue
                break

        if insert_error:
            message = str(insert_error)
            if "analysis_documents_transcript_id_fkey" in message or (
                "violates foreign key constraint" in message.lower() and "transcripts" in message.lower()
            ):
                return (
                    False,
                    "Database schema mismatch: analysis_documents.project_id is still constrained to transcripts. "
                    "Update the foreign key so project_id references projects(project_id), then retry.",
                )
            if "row-level security" in message.lower() or "violates row-level security policy" in message.lower():
                return (
                    False,
                    "Document uploaded to storage, but database insert was blocked by RLS policy on `analysis_documents`. "
                    "Add an INSERT policy for authenticated reviewers (for example, allow when auth.uid() matches your ownership column).",
                )
            return False, f"Failed to save document metadata: {insert_error}"

        return False, "Failed to save document metadata due to an unknown insert policy issue."
    except Exception as exc:
        return False, f"Failed to save document: {exc}"


def get_analysis_documents(supabase, project_id, logger):
    try:
        result = supabase.table("analysis_documents").select("*").eq("project_id", project_id)
        result = safe_execute(result, logger, "loading uploaded documents")
        return result.data or []
    except Exception as exc:
        logger.error("Failed to fetch documents: %s", exc)
        return []


def delete_document(supabase, doc_id):
    try:
        supabase.table("analysis_documents").delete().eq("id", doc_id).execute()
        st.success("Document deleted.")
    except Exception as exc:
        st.error(f"Failed to delete document: {exc}")
