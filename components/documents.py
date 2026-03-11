import streamlit as st

from components.db import delete_document, get_analysis_documents, save_document


def render_documents_list(supabase, project_id, logger):
    documents = get_analysis_documents(supabase, project_id, logger)

    if documents:
        st.markdown("**Uploaded Documents**")
        for doc in documents:
            col1, col2 = st.columns([3, 1])
            with col1:
                doc_type = (doc.get("doc_type") or "").replace("_", " ").title()
                st.markdown(f"**{doc_type}:** [{doc['file_name']}]({doc['file_url']})")
            with col2:
                if st.button("Delete", key=f"delete_{doc['id']}", help="Delete document"):
                    delete_document(supabase, doc["id"])
                    st.rerun()


def render_file_upload_section(supabase, project_id, logger, use_expander=True):
    st.subheader("Upload Additional Context (Optional)")

    nonce_key = f"upload_nonce_{project_id}"
    flash_key = f"upload_messages_{project_id}"
    if nonce_key not in st.session_state:
        st.session_state[nonce_key] = 0

    if flash_key in st.session_state:
        for success, message in st.session_state[flash_key]:
            if success:
                st.success(message)
            else:
                st.error(message)
        del st.session_state[flash_key]

    key_suffix = f"{project_id}_{st.session_state[nonce_key]}"

    upload_container = st.expander("Upload Documents", expanded=False) if use_expander else st.container()
    with upload_container:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Questions Document**")
            questions_file = st.file_uploader(
                "Upload Questions",
                type=["txt", "md", "pdf"],
                key=f"questions_{key_suffix}",
                help="Questions you plan to ask during the interview",
            )

            st.markdown("**Other Documents (optional, multiple files)**")
            other_documents_files = st.file_uploader(
                "Upload Other Documents",
                type=["pdf", "txt", "md", "json"],
                accept_multiple_files=True,
                key=f"other_documents_{key_suffix}",
                help="Upload one or more supporting files",
            )

        with col2:
            st.markdown("**Dictionary (optional)**")
            dictionary_file = st.file_uploader(
                "Upload Dictionary",
                type=["json", "txt"],
                key=f"dictionary_{key_suffix}",
                help="Custom terms or glossary for project analysis",
            )

            st.markdown("**Company Research (optional)**")
            company_research_file = st.file_uploader(
                "Upload Company Research",
                type=["pdf", "txt", "md"],
                key=f"company_research_{key_suffix}",
                help="Company background notes, briefs, or strategy docs",
            )

        if st.button("Save Documents", key=f"save_docs_{project_id}", use_container_width=False):
            upload_results = []

            if questions_file:
                upload_results.append(
                    save_document(
                        supabase,
                        project_id,
                        "questions",
                        questions_file.name,
                        questions_file.getvalue(),
                        logger,
                    )
                )

            if dictionary_file:
                upload_results.append(
                    save_document(
                        supabase,
                        project_id,
                        "dictionary",
                        dictionary_file.name,
                        dictionary_file.getvalue(),
                        logger,
                    )
                )

            if company_research_file:
                upload_results.append(
                    save_document(
                        supabase,
                        project_id,
                        "company_research",
                        company_research_file.name,
                        company_research_file.getvalue(),
                        logger,
                    )
                )

            if other_documents_files:
                for other_doc in other_documents_files:
                    upload_results.append(
                        save_document(
                            supabase,
                            project_id,
                            "other_documents",
                            other_doc.name,
                            other_doc.getvalue(),
                            logger,
                        )
                    )

            if not upload_results:
                st.info("No files selected.")
            else:
                success_count = sum(1 for success, _ in upload_results if success)
                error_count = len(upload_results) - success_count

                if success_count > 0 and error_count == 0:
                    st.session_state[flash_key] = upload_results
                    st.session_state[nonce_key] += 1
                    st.rerun()

                for success, message in upload_results:
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

    render_documents_list(supabase, project_id, logger)
