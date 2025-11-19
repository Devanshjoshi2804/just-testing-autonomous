"""
AutoTest-RL Frontend Dashboard
Main Streamlit Application
"""
import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
import json
import time

# Configure page
st.set_page_config(
    page_title="AutoTest-RL Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://api:8000")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .status-badge {
        padding: 5px 15px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .status-success {
        background-color: #10b981;
        color: white;
    }
    .status-error {
        background-color: #ef4444;
        color: white;
    }
    .status-warning {
        background-color: #f59e0b;
        color: white;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

def check_api_health() -> Dict[str, Any]:
    """Check API health status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health/detailed", timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_recent_tests(limit: int = 10) -> List[Dict]:
    """Get recent test sessions"""
    try:
        # This would need to be implemented in your API
        response = requests.get(f"{API_BASE_URL}/api/v1/tests/recent?limit={limit}")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_intelligence_summary() -> Dict[str, Any]:
    """Get intelligence summary"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/intelligence/summary")
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

# Main Dashboard
def main():
    # Header
    st.markdown('<h1 class="main-header">🚀 AutoTest-RL Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("### Intelligent API Testing with Reinforcement Learning + AI")

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=AutoTest-RL", width=300)
        st.markdown("---")

        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "📄 Documents", "🧪 Tests", "🧠 Intelligence", "📊 Analytics"],
            key="navigation"
        )

        st.markdown("---")

        # System Status
        st.subheader("System Status")
        health = check_api_health()

        if health.get("status") == "healthy":
            st.success("✅ All Systems Operational")
        else:
            st.error("❌ System Issues Detected")

        # Component status
        if "components" in health:
            components = health["components"]
            st.metric("Database", "✅" if components.get("database") == "healthy" else "❌")
            st.metric("Redis", "✅" if components.get("redis") == "healthy" else "❌")
            st.metric("ChromaDB", "✅" if components.get("chromadb") == "healthy" else "❌")

    # Main Content Based on Navigation
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📄 Documents":
        show_documents()
    elif page == "🧪 Tests":
        show_tests()
    elif page == "🧠 Intelligence":
        show_intelligence()
    elif page == "📊 Analytics":
        show_analytics()

def show_dashboard():
    """Main dashboard view"""
    st.header("System Overview")

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)

    # Get intelligence summary for metrics
    intelligence = get_intelligence_summary()

    with col1:
        st.metric(
            label="Total Documents",
            value=intelligence.get("total_documents", 0),
            delta="+2 today"
        )

    with col2:
        st.metric(
            label="Tests Executed",
            value=intelligence.get("total_tests", 0),
            delta="+15 today"
        )

    with col3:
        st.metric(
            label="Success Rate",
            value=f"{intelligence.get('success_rate', 0):.1f}%",
            delta="+2.3%"
        )

    with col4:
        st.metric(
            label="AI Insights",
            value=intelligence.get("insights_generated", 0),
            delta="New"
        )

    st.markdown("---")

    # Two column layout
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📈 Testing Activity")

        # Sample data for demo - replace with real data
        activity_data = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'Tests': [10 + i * 2 for i in range(30)],
            'Passed': [8 + i * 2 for i in range(30)],
            'Failed': [2 for _ in range(30)]
        })

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=activity_data['Date'],
            y=activity_data['Tests'],
            mode='lines+markers',
            name='Total Tests',
            line=dict(color='#667eea', width=3)
        ))
        fig.add_trace(go.Scatter(
            x=activity_data['Date'],
            y=activity_data['Passed'],
            mode='lines',
            name='Passed',
            line=dict(color='#10b981', width=2)
        ))
        fig.add_trace(go.Scatter(
            x=activity_data['Date'],
            y=activity_data['Failed'],
            mode='lines',
            name='Failed',
            line=dict(color='#ef4444', width=2)
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Recent Tests
        st.subheader("🕒 Recent Test Sessions")
        recent_tests = get_recent_tests(5)

        if recent_tests:
            for test in recent_tests:
                with st.expander(f"Test Session {test.get('session_id', 'N/A')[:8]}..."):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Status:** {test.get('status', 'Unknown')}")
                    with col2:
                        st.write(f"**Endpoints:** {test.get('total_endpoints', 0)}")
                    with col3:
                        st.write(f"**Success Rate:** {test.get('success_rate', 0):.1f}%")
        else:
            st.info("No recent test sessions available. Upload a document to get started!")

    with col_right:
        st.subheader("🎯 Quick Actions")

        if st.button("📄 Upload New Document", use_container_width=True):
            st.session_state.navigation = "📄 Documents"
            st.rerun()

        if st.button("🧪 Run Tests", use_container_width=True):
            st.session_state.navigation = "🧪 Tests"
            st.rerun()

        if st.button("🧠 View Intelligence", use_container_width=True):
            st.session_state.navigation = "🧠 Intelligence"
            st.rerun()

        st.markdown("---")

        st.subheader("💡 AI Insights")

        insights = intelligence.get("recent_insights", [])
        if insights:
            for insight in insights[:3]:
                st.info(f"🔍 {insight.get('message', 'No insights available')}")
        else:
            st.info("Run some tests to generate AI insights!")

        st.markdown("---")

        st.subheader("📊 System Metrics")

        # Intelligence stats
        pattern_stats = intelligence.get("pattern_stats", {})
        st.metric("Patterns Learned", pattern_stats.get("total_patterns", 0))
        st.metric("High Confidence", pattern_stats.get("high_confidence_patterns", 0))

        # RL stats
        rl_stats = intelligence.get("rl_stats", {})
        st.metric("Time Saved", f"{rl_stats.get('time_saved', 0):.1f}s")
        st.metric("Failures Caught", rl_stats.get("failures_caught", 0))

def show_documents():
    """Document upload and management"""
    try:
        from pages.documents import render_documents_page
        render_documents_page(API_BASE_URL)
    except Exception as e:
        st.error(f"Error loading documents page: {str(e)}")
        st.info("Please check that all dependencies are installed correctly.")

def show_tests():
    """Test execution and results"""
    try:
        from pages.tests import render_tests_page
        render_tests_page(API_BASE_URL)
    except Exception as e:
        st.error(f"Error loading tests page: {str(e)}")
        st.info("Please check that all dependencies are installed correctly.")

def show_intelligence():
    """AI Intelligence insights"""
    try:
        from pages.intelligence import render_intelligence_page
        render_intelligence_page(API_BASE_URL)
    except Exception as e:
        st.error(f"Error loading intelligence page: {str(e)}")
        st.info("Please check that all dependencies are installed correctly.")

def show_analytics():
    """Analytics and reporting"""
    try:
        from pages.analytics import render_analytics_page
        render_analytics_page(API_BASE_URL)
    except Exception as e:
        st.error(f"Error loading analytics page: {str(e)}")
        st.info("Please check that all dependencies are installed correctly.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.write("Please check:")
        st.write("1. All dependencies are installed: `pip install -r requirements.txt`")
        st.write("2. API is running at:", API_BASE_URL)
        st.write("3. All page modules are present in the pages/ directory")
