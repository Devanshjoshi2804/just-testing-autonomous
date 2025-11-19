"""
Analytics and Reporting Page
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

def render_analytics_page(api_base_url: str):
    """Render the analytics page"""
    st.header("📊 Analytics & Reporting")
    st.markdown("Comprehensive analytics and performance metrics")

    tabs = st.tabs(["📈 Performance", "🎯 Coverage", "🔥 Heatmaps", "📉 Trends"])

    with tabs[0]:
        render_performance_tab(api_base_url)

    with tabs[1]:
        render_coverage_tab(api_base_url)

    with tabs[2]:
        render_heatmaps_tab(api_base_url)

    with tabs[3]:
        render_trends_tab(api_base_url)


def render_performance_tab(api_base_url: str):
    """Performance analytics"""
    st.subheader("📈 Performance Analytics")

    try:
        response = requests.get(f"{api_base_url}/api/v1/intelligence/performance-baselines")

        if response.status_code == 200:
            baselines = response.json().get("baselines", {})

            if baselines:
                # Convert to dataframe
                perf_data = []
                for endpoint, data in baselines.items():
                    perf_data.append({
                        "Endpoint": endpoint,
                        "Avg Response": f"{data.get('avg_response_time', 0):.3f}s",
                        "Min": f"{data.get('min_response_time', 0):.3f}s",
                        "Max": f"{data.get('max_response_time', 0):.3f}s",
                        "p95": f"{data.get('p95_response_time', 0):.3f}s",
                        "Samples": data.get('sample_count', 0)
                    })

                df = pd.DataFrame(perf_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("---")

                # Performance distribution chart
                st.subheader("⏱️ Response Time Distribution")

                endpoints = list(baselines.keys())[:10]  # Top 10
                avg_times = [baselines[ep].get('avg_response_time', 0) for ep in endpoints]

                fig = go.Figure(data=[
                    go.Bar(
                        x=endpoints,
                        y=avg_times,
                        marker_color='rgb(102, 126, 234)',
                        text=[f"{t:.3f}s" for t in avg_times],
                        textposition='auto',
                    )
                ])

                fig.update_layout(
                    title="Average Response Times by Endpoint",
                    xaxis_title="Endpoint",
                    yaxis_title="Response Time (seconds)",
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

                # Performance matrix
                st.markdown("---")
                st.subheader("🎯 Performance Matrix")

                col1, col2, col3 = st.columns(3)

                # Calculate stats
                all_avgs = [data.get('avg_response_time', 0) for data in baselines.values()]
                fast_endpoints = sum(1 for t in all_avgs if t < 0.5)
                medium_endpoints = sum(1 for t in all_avgs if 0.5 <= t < 2.0)
                slow_endpoints = sum(1 for t in all_avgs if t >= 2.0)

                with col1:
                    st.metric("🟢 Fast (< 0.5s)", fast_endpoints)

                with col2:
                    st.metric("🟡 Medium (0.5-2s)", medium_endpoints)

                with col3:
                    st.metric("🔴 Slow (> 2s)", slow_endpoints)

            else:
                st.info("No performance data available yet. Run tests to collect performance metrics.")

        else:
            st.error("Failed to fetch performance data")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_coverage_tab(api_base_url: str):
    """Test coverage analytics"""
    st.subheader("🎯 Test Coverage")

    # Generate sample coverage data (replace with real API call)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Endpoint Coverage", "85%", "+5%")

    with col2:
        st.metric("Status Code Coverage", "78%", "+12%")

    with col3:
        st.metric("Parameter Coverage", "92%", "+3%")

    with col4:
        st.metric("Schema Coverage", "88%", "+7%")

    st.markdown("---")

    # Coverage by HTTP method
    st.subheader("📍 Coverage by HTTP Method")

    method_data = {
        "Method": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "Endpoints": [45, 32, 18, 12, 8],
        "Tested": [40, 28, 15, 10, 6],
        "Coverage": [89, 88, 83, 83, 75]
    }

    fig = go.Figure(data=[
        go.Bar(name='Total', x=method_data['Method'], y=method_data['Endpoints'], marker_color='lightgray'),
        go.Bar(name='Tested', x=method_data['Method'], y=method_data['Tested'], marker_color='rgb(102, 126, 234)')
    ])

    fig.update_layout(
        barmode='overlay',
        title="Endpoint Coverage by HTTP Method",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Coverage details
    st.subheader("📋 Coverage Details")

    coverage_data = {
        "Category": ["Authentication", "User Management", "Products", "Orders", "Payments", "Admin"],
        "Total Endpoints": [8, 12, 25, 18, 10, 15],
        "Tested": [8, 11, 22, 16, 8, 12],
        "Coverage %": [100, 92, 88, 89, 80, 80],
        "Status": ["✅", "✅", "✅", "✅", "⚠️", "⚠️"]
    }

    df = pd.DataFrame(coverage_data)

    # Color code the coverage
    def color_coverage(val):
        if val >= 90:
            return 'background-color: #d1fae5'
        elif val >= 70:
            return 'background-color: #fef3c7'
        else:
            return 'background-color: #fee2e2'

    styled_df = df.style.applymap(color_coverage, subset=['Coverage %'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True)


def render_heatmaps_tab(api_base_url: str):
    """Heatmap visualizations"""
    st.subheader("🔥 Test Result Heatmaps")

    # Generate sample heatmap data
    st.markdown("### 📅 Daily Test Success Rate")

    # Create sample data for last 7 days, 24 hours
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    hours = list(range(24))

    # Generate random success rates
    np.random.seed(42)
    success_rates = np.random.randint(70, 100, size=(7, 24))

    fig = go.Figure(data=go.Heatmap(
        z=success_rates,
        x=hours,
        y=days,
        colorscale='RdYlGn',
        text=success_rates,
        texttemplate='%{text}%',
        textfont={"size": 8},
        colorbar=dict(title="Success %")
    ))

    fig.update_layout(
        title="Test Success Rate by Day and Hour",
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Endpoint failure heatmap
    st.markdown("### ❌ Endpoint Failure Patterns")

    endpoints = [f"Endpoint {i+1}" for i in range(10)]
    test_runs = [f"Run {i+1}" for i in range(15)]

    # Generate sample failure data (0 = success, 1 = failure)
    failures = np.random.choice([0, 1], size=(10, 15), p=[0.85, 0.15])

    fig = go.Figure(data=go.Heatmap(
        z=failures,
        x=test_runs,
        y=endpoints,
        colorscale=[[0, '#10b981'], [1, '#ef4444']],
        showscale=False,
        text=np.where(failures == 1, '❌', '✅'),
        texttemplate='%{text}',
        textfont={"size": 12}
    ))

    fig.update_layout(
        title="Test Results Matrix",
        xaxis_title="Test Run",
        yaxis_title="Endpoint",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 Darker red cells indicate failure patterns that might need attention.")


def render_trends_tab(api_base_url: str):
    """Trend analysis"""
    st.subheader("📉 Trend Analysis")

    # Time range selector
    col1, col2 = st.columns([3, 1])

    with col1:
        time_range = st.selectbox(
            "Time Range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 6 Months"]
        )

    with col2:
        st.metric("Data Points", "142")

    # Generate sample trend data
    days = 30
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Success rate trend
    st.markdown("### 📈 Success Rate Trend")

    success_rate = 80 + np.cumsum(np.random.randn(days) * 0.5)
    success_rate = np.clip(success_rate, 70, 95)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=success_rate,
        mode='lines+markers',
        name='Success Rate',
        line=dict(color='rgb(102, 126, 234)', width=3),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))

    # Add trend line
    z = np.polyfit(range(days), success_rate, 1)
    p = np.poly1d(z)
    fig.add_trace(go.Scatter(
        x=dates,
        y=p(range(days)),
        mode='lines',
        name='Trend',
        line=dict(color='red', width=2, dash='dash')
    ))

    fig.update_layout(
        title="Test Success Rate Over Time",
        xaxis_title="Date",
        yaxis_title="Success Rate (%)",
        height=400,
        yaxis=dict(range=[60, 100])
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Response time trend
    st.markdown("### ⏱️ Average Response Time Trend")

    response_time = 0.5 + np.cumsum(np.random.randn(days) * 0.02)
    response_time = np.clip(response_time, 0.2, 1.5)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=response_time,
        mode='lines+markers',
        name='Avg Response Time',
        line=dict(color='rgb(16, 185, 129)', width=3),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.2)'
    ))

    # Add SLA line
    fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="SLA Threshold (1s)")

    fig.update_layout(
        title="Average Response Time Over Time",
        xaxis_title="Date",
        yaxis_title="Response Time (s)",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Test volume trend
    st.markdown("### 📊 Test Volume Trend")

    test_volume = 50 + np.cumsum(np.random.randint(-5, 10, days))
    test_volume = np.clip(test_volume, 20, 200)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=dates,
        y=test_volume,
        name='Tests Executed',
        marker_color='rgb(102, 126, 234)'
    ))

    fig.update_layout(
        title="Daily Test Volume",
        xaxis_title="Date",
        yaxis_title="Number of Tests",
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    st.markdown("---")
    st.subheader("📊 Trend Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Success Rate Change", "+3.2%", delta="+3.2%")

    with col2:
        st.metric("Response Time Change", "-120ms", delta="-15%", delta_color="inverse")

    with col3:
        st.metric("Test Volume Change", "+45", delta="+28%")

    with col4:
        st.metric("Coverage Change", "+8%", delta="+8%")
