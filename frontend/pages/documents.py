"""
Document Upload and Management Page
"""
import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from typing import Dict, Any, List

def render_documents_page(api_base_url: str):
    """Render the documents management page"""
    st.header("📄 Document Management")
    st.markdown("Upload and manage API documentation for automated testing")

    # Two column layout
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📤 Upload New Document")

        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an API documentation file",
            type=["pdf", "json"],
            help="Upload PDF or JSON API documentation"
        )

        if uploaded_file is not None:
            # Show file details
            st.info(f"📁 **File:** {uploaded_file.name}")
            st.info(f"📏 **Size:** {uploaded_file.size / 1024:.2f} KB")

            # Upload button
            if st.button("🚀 Upload & Process", type="primary", use_container_width=True):
                with st.spinner("Uploading and processing document..."):
                    try:
                        # Upload file
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                        response = requests.post(
                            f"{api_base_url}/api/v1/documents/upload",
                            files=files
                        )

                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"✅ Document uploaded successfully!")
                            st.json(result)

                            # Store in session state
                            if "uploaded_docs" not in st.session_state:
                                st.session_state.uploaded_docs = []
                            st.session_state.uploaded_docs.append(result)

                        else:
                            st.error(f"❌ Upload failed: {response.text}")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        st.markdown("---")

        st.subheader("📋 Supported Formats")
        st.markdown("""
        - **PDF**: API documentation in PDF format
        - **JSON**: OpenAPI/Swagger specifications
        - **Size Limit**: 50 MB
        """)

    with col_right:
        st.subheader("📚 Uploaded Documents")

        # Fetch document list
        try:
            response = requests.get(f"{api_base_url}/api/v1/documents/")
            if response.status_code == 200:
                documents = response.json().get("documents", [])

                if documents:
                    # Create dataframe for display
                    doc_data = []
                    for doc in documents:
                        doc_data.append({
                            "ID": doc.get("id", "N/A")[:12] + "...",
                            "Name": doc.get("filename", "Unknown"),
                            "Type": doc.get("type", "Unknown"),
                            "Endpoints": doc.get("endpoint_count", 0),
                            "Date": doc.get("uploaded_at", "N/A")[:10]
                        })

                    df = pd.DataFrame(doc_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Document details
                    st.markdown("---")
                    selected_doc = st.selectbox(
                        "Select document for details",
                        options=[doc.get("id") for doc in documents],
                        format_func=lambda x: next(
                            (doc.get("filename") for doc in documents if doc.get("id") == x),
                            "Unknown"
                        )
                    )

                    if selected_doc:
                        doc = next((d for d in documents if d.get("id") == selected_doc), None)
                        if doc:
                            with st.expander("📄 Document Details", expanded=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Filename:** {doc.get('filename')}")
                                    st.write(f"**Type:** {doc.get('type')}")
                                    st.write(f"**Size:** {doc.get('size', 0) / 1024:.2f} KB")
                                with col2:
                                    st.write(f"**Endpoints:** {doc.get('endpoint_count', 0)}")
                                    st.write(f"**Status:** {doc.get('status', 'Unknown')}")
                                    st.write(f"**Uploaded:** {doc.get('uploaded_at', 'N/A')[:10]}")

                                # Action buttons
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("🧪 Run Tests", key=f"test_{selected_doc}", use_container_width=True):
                                        st.session_state.selected_doc_for_test = selected_doc
                                        st.session_state.navigation = "🧪 Tests"
                                        st.rerun()

                                with col2:
                                    if st.button("📊 View Results", key=f"results_{selected_doc}", use_container_width=True):
                                        st.info("Navigate to Tests page to view results")

                                with col3:
                                    if st.button("🗑️ Delete", key=f"delete_{selected_doc}", use_container_width=True):
                                        try:
                                            del_response = requests.delete(
                                                f"{api_base_url}/api/v1/documents/{selected_doc}"
                                            )
                                            if del_response.status_code == 200:
                                                st.success("Document deleted!")
                                                st.rerun()
                                            else:
                                                st.error("Failed to delete document")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")

                else:
                    st.info("📭 No documents uploaded yet. Upload your first document to get started!")

            else:
                st.error("Failed to fetch documents")

        except Exception as e:
            st.error(f"Error fetching documents: {str(e)}")

    # Statistics
    st.markdown("---")
    st.subheader("📊 Document Statistics")

    col1, col2, col3, col4 = st.columns(4)

    try:
        response = requests.get(f"{api_base_url}/api/v1/documents/")
        if response.status_code == 200:
            documents = response.json().get("documents", [])

            with col1:
                st.metric("Total Documents", len(documents))

            with col2:
                total_endpoints = sum(doc.get("endpoint_count", 0) for doc in documents)
                st.metric("Total Endpoints", total_endpoints)

            with col3:
                pdf_count = sum(1 for doc in documents if doc.get("type") == "pdf")
                st.metric("PDF Documents", pdf_count)

            with col4:
                json_count = sum(1 for doc in documents if doc.get("type") == "json")
                st.metric("JSON Documents", json_count)

    except Exception as e:
        st.error(f"Error fetching statistics: {str(e)}")
