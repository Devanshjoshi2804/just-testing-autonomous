"""
Test Execution and Results Page
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import json

def render_tests_page(api_base_url: str):
    """Render the tests execution page"""
    st.header("🧪 Test Execution & Results")

    tabs = st.tabs(["▶️ Run Tests", "📊 Test Results", "🕒 Test History"])

    with tabs[0]:
        render_run_tests_tab(api_base_url)

    with tabs[1]:
        render_test_results_tab(api_base_url)

    with tabs[2]:
        render_test_history_tab(api_base_url)


def render_run_tests_tab(api_base_url: str):
    """Tab for running new tests"""
    st.subheader("▶️ Start New Test Session")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Fetch available documents
        try:
            response = requests.get(f"{api_base_url}/api/v1/documents/")
            if response.status_code == 200:
                documents = response.json().get("documents", [])

                if documents:
                    # Pre-select if coming from documents page
                    default_index = 0
                    if hasattr(st.session_state, 'selected_doc_for_test'):
                        try:
                            doc_ids = [doc.get("id") for doc in documents]
                            default_index = doc_ids.index(st.session_state.selected_doc_for_test)
                        except ValueError:
                            pass

                    selected_doc = st.selectbox(
                        "Select Document to Test",
                        options=[doc.get("id") for doc in documents],
                        format_func=lambda x: next(
                            (f"{doc.get('filename')} ({doc.get('endpoint_count', 0)} endpoints)"
                             for doc in documents if doc.get("id") == x),
                            "Unknown"
                        ),
                        index=default_index
                    )

                    # Test configuration
                    st.markdown("### Test Configuration")

                    use_rl = st.checkbox(
                        "Enable Hybrid Intelligence (RL + LLM + Patterns)",
                        value=True,
                        help="Use advanced AI for intelligent test prioritization"
                    )

                    comprehensive_mode = st.checkbox(
                        "Comprehensive Mode",
                        value=False,
                        help="Generate comprehensive test suite with semantic analysis and mutation testing"
                    )

                    max_retries = st.slider(
                        "Max Retries per Test",
                        min_value=1,
                        max_value=5,
                        value=3,
                        help="Number of retry attempts for failed tests"
                    )

                    ordered = st.checkbox(
                        "Intelligent Test Ordering",
                        value=True,
                        help="Use AI to determine optimal test execution order"
                    )

                    # Run button
                    if st.button("🚀 Start Testing", type="primary", use_container_width=True):
                        with st.spinner("Starting test execution..."):
                            try:
                                payload = {
                                    "document_id": selected_doc,
                                    "use_rl": use_rl,
                                    "comprehensive_mode": comprehensive_mode,
                                    "max_retries": max_retries,
                                    "ordered": ordered
                                }

                                response = requests.post(
                                    f"{api_base_url}/api/v1/tests/start",
                                    json=payload
                                )

                                if response.status_code == 200:
                                    result = response.json()
                                    session_id = result.get("session_id")

                                    st.success(f"✅ Test session started!")
                                    st.info(f"📝 Session ID: `{session_id}`")

                                    # Store in session state
                                    st.session_state.current_test_session = session_id

                                    # Show progress
                                    st.markdown("---")
                                    render_test_progress(api_base_url, session_id)

                                else:
                                    st.error(f"❌ Failed to start tests: {response.text}")

                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

                else:
                    st.warning("📭 No documents available. Please upload a document first.")

        except Exception as e:
            st.error(f"Error fetching documents: {str(e)}")

    with col_right:
        st.subheader("ℹ️ Test Configuration Guide")

        st.markdown("""
        ### 🧠 Hybrid Intelligence
        Combines:
        - **RL Optimizer**: Learns from past test results
        - **LLM Orchestrator**: Strategic test planning
        - **Pattern Learner**: Detects failure patterns
        - **Semantic Analyzer**: Understands API structure

        ### 📋 Test Modes

        **Standard Mode**
        - Quick test execution
        - Basic test data generation
        - Suitable for simple APIs

        **Comprehensive Mode**
        - Semantic analysis of API structure
        - Mutation testing for edge cases
        - Enhanced test data generation
        - Best for complex APIs

        ### 🔄 Intelligent Ordering
        - Tests critical endpoints first
        - Respects dependencies
        - Optimizes execution time
        - Learns optimal sequences

        ### ⚡ Retry Logic
        - Auto-fixes failed tests
        - Learns from errors
        - Adapts test data
        - Self-healing capabilities
        """)


def render_test_progress(api_base_url: str, session_id: str):
    """Render real-time test progress"""
    st.subheader("📊 Test Progress")

    progress_container = st.empty()
    status_container = st.empty()
    results_container = st.empty()

    # Poll for progress
    max_polls = 120  # 10 minutes max
    poll_count = 0

    while poll_count < max_polls:
        try:
            response = requests.get(f"{api_base_url}/api/v1/tests/{session_id}/status")

            if response.status_code == 200:
                status = response.json()

                # Progress bar
                total = status.get("total_tests", 1)
                completed = status.get("completed_tests", 0)
                progress = completed / total if total > 0 else 0

                progress_container.progress(progress, text=f"Progress: {completed}/{total} tests")

                # Status
                test_status = status.get("status", "unknown")
                if test_status == "completed":
                    status_container.success(f"✅ Test session completed!")

                    # Show summary
                    with results_container:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Tests", status.get("total_tests", 0))
                        with col2:
                            st.metric("Passed", status.get("passed", 0))
                        with col3:
                            st.metric("Failed", status.get("failed", 0))
                        with col4:
                            st.metric("Success Rate", f"{status.get('success_rate', 0):.1f}%")

                    break

                elif test_status == "running":
                    status_container.info(f"⏳ Testing in progress...")

                elif test_status == "failed":
                    status_container.error(f"❌ Test session failed")
                    break

                else:
                    status_container.warning(f"Status: {test_status}")

        except Exception as e:
            status_container.error(f"Error checking status: {str(e)}")
            break

        time.sleep(5)
        poll_count += 1

    if poll_count >= max_polls:
        status_container.warning("⏰ Status check timed out. Check Test History for results.")


def render_test_results_tab(api_base_url: str):
    """Tab for viewing current test results"""
    st.subheader("📊 Current Test Results")

    if hasattr(st.session_state, 'current_test_session'):
        session_id = st.session_state.current_test_session

        try:
            # Fetch results
            response = requests.get(f"{api_base_url}/api/v1/tests/{session_id}/results")

            if response.status_code == 200:
                results = response.json()

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Tests", results.get("total_tests", 0))
                with col2:
                    passed = results.get("passed", 0)
                    st.metric("Passed", passed, delta=None)
                with col3:
                    failed = results.get("failed", 0)
                    st.metric("Failed", failed, delta=None)
                with col4:
                    success_rate = results.get("success_rate", 0)
                    st.metric("Success Rate", f"{success_rate:.1f}%")

                # Results visualization
                st.markdown("---")

                if results.get("test_results"):
                    test_data = results["test_results"]

                    # Create dataframe
                    df_data = []
                    for test in test_data:
                        df_data.append({
                            "Endpoint": test.get("endpoint", "Unknown"),
                            "Method": test.get("method", "GET"),
                            "Status": "✅ Passed" if test.get("success") else "❌ Failed",
                            "Status Code": test.get("status_code", "N/A"),
                            "Response Time": f"{test.get('response_time', 0):.2f}s",
                            "Attempts": test.get("attempts", 1)
                        })

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # Detailed results
                    st.markdown("---")
                    st.subheader("🔍 Detailed Results")

                    for idx, test in enumerate(test_data):
                        status_icon = "✅" if test.get("success") else "❌"
                        with st.expander(f"{status_icon} {test.get('method', 'GET')} {test.get('endpoint', 'Unknown')}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write("**Request**")
                                st.json(test.get("request", {}))

                            with col2:
                                st.write("**Response**")
                                st.json(test.get("response", {}))

                            if not test.get("success") and test.get("error"):
                                st.error(f"**Error:** {test.get('error')}")

                else:
                    st.info("No test results available yet.")

            else:
                st.error("Failed to fetch test results")

        except Exception as e:
            st.error(f"Error: {str(e)}")

    else:
        st.info("No active test session. Start a new test to see results.")


def render_test_history_tab(api_base_url: str):
    """Tab for viewing historical test sessions"""
    st.subheader("🕒 Test History")

    try:
        # This would need to be implemented in your API
        # For now, showing placeholder
        st.info("Test history feature coming soon! This will show all previous test sessions.")

        # Placeholder data
        history_data = {
            "Session ID": ["abc123...", "def456...", "ghi789..."],
            "Document": ["API Doc 1", "API Doc 2", "API Doc 1"],
            "Date": ["2024-01-15", "2024-01-14", "2024-01-13"],
            "Total Tests": [25, 30, 25],
            "Passed": [23, 28, 24],
            "Failed": [2, 2, 1],
            "Success Rate": ["92%", "93%", "96%"]
        }

        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error: {str(e)}")
