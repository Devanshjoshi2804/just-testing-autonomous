"""
AI Intelligence Insights Page
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List
import json

def render_intelligence_page(api_base_url: str):
    """Render the AI intelligence page"""
    st.header("🧠 AI Intelligence Insights")
    st.markdown("Explore patterns, insights, and recommendations from AI analysis")

    tabs = st.tabs(["📊 Summary", "🔍 Patterns", "💡 Insights", "🎯 Recommendations", "🗺️ API Structure"])

    with tabs[0]:
        render_summary_tab(api_base_url)

    with tabs[1]:
        render_patterns_tab(api_base_url)

    with tabs[2]:
        render_insights_tab(api_base_url)

    with tabs[3]:
        render_recommendations_tab(api_base_url)

    with tabs[4]:
        render_api_structure_tab(api_base_url)


def render_summary_tab(api_base_url: str):
    """Intelligence summary overview"""
    st.subheader("📊 Intelligence Summary")

    try:
        response = requests.get(f"{api_base_url}/api/v1/intelligence/summary")

        if response.status_code == 200:
            summary = response.json()

            # Top metrics
            col1, col2, col3, col4 = st.columns(4)

            pattern_stats = summary.get("pattern_stats", {})
            with col1:
                st.metric(
                    "Total Patterns",
                    pattern_stats.get("total_patterns", 0),
                    help="Total number of learned patterns"
                )

            with col2:
                st.metric(
                    "High Confidence",
                    pattern_stats.get("high_confidence_patterns", 0),
                    help="Patterns with confidence > 0.7"
                )

            with col3:
                st.metric(
                    "Insights Generated",
                    pattern_stats.get("insights_generated", 0),
                    help="Total AI-generated insights"
                )

            rl_stats = summary.get("rl_stats", {})
            with col4:
                st.metric(
                    "Time Saved",
                    f"{rl_stats.get('time_saved', 0):.1f}s",
                    help="Time saved by intelligent ordering"
                )

            st.markdown("---")

            # Two column layout
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.subheader("🎯 RL Optimizer Performance")

                # RL metrics chart
                rl_data = {
                    "Metric": ["Failures Caught", "Failures Missed", "Correct Skips"],
                    "Count": [
                        rl_stats.get("failures_caught", 0),
                        rl_stats.get("failures_missed", 0),
                        rl_stats.get("correct_skips", 0)
                    ]
                }

                fig = px.bar(
                    rl_data,
                    x="Metric",
                    y="Count",
                    title="RL Performance Metrics",
                    color="Metric",
                    color_discrete_map={
                        "Failures Caught": "#10b981",
                        "Failures Missed": "#ef4444",
                        "Correct Skips": "#3b82f6"
                    }
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

                # RL stats
                avg_reward = rl_stats.get("avg_reward_per_episode", 0)
                st.metric("Average Reward", f"{avg_reward:+.2f}")

            with col_right:
                st.subheader("📚 Pattern Distribution")

                # Pattern types distribution
                pattern_types = pattern_stats.get("pattern_types", {})

                if pattern_types:
                    fig = go.Figure(data=[go.Pie(
                        labels=list(pattern_types.keys()),
                        values=list(pattern_types.values()),
                        hole=0.4
                    )])
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No patterns learned yet. Run tests to generate patterns.")

            st.markdown("---")

            # Recent insights
            st.subheader("💡 Recent Insights")
            insights = summary.get("recent_insights", [])

            if insights:
                for insight in insights[:5]:
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.info(f"🔍 {insight.get('message', 'No insight')}")
                        with col2:
                            confidence = insight.get('confidence', 0)
                            st.metric("Confidence", f"{confidence:.0%}")
            else:
                st.info("No insights available yet. Run some tests to generate AI insights!")

        else:
            st.error("Failed to fetch intelligence summary")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_patterns_tab(api_base_url: str):
    """Learned patterns viewer"""
    st.subheader("🔍 Learned Patterns")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        endpoint_filter = st.text_input("Filter by Endpoint", placeholder="e.g., /api/users")

    with col2:
        pattern_type = st.selectbox(
            "Pattern Type",
            ["All", "failure", "success", "flaky", "performance"]
        )

    with col3:
        min_confidence = st.slider(
            "Min Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1
        )

    # Fetch patterns
    try:
        params = {
            "min_confidence": min_confidence
        }

        if endpoint_filter:
            params["endpoint"] = endpoint_filter

        if pattern_type != "All":
            params["pattern_type"] = pattern_type

        response = requests.get(
            f"{api_base_url}/api/v1/intelligence/patterns",
            params=params
        )

        if response.status_code == 200:
            patterns = response.json().get("patterns", [])

            if patterns:
                st.success(f"Found {len(patterns)} patterns")

                # Display patterns
                for pattern in patterns:
                    with st.expander(
                        f"{'🔴' if pattern.get('type') == 'failure' else '🟢'} "
                        f"{pattern.get('endpoint', 'Unknown')} - "
                        f"Confidence: {pattern.get('confidence', 0):.0%}"
                    ):
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.write(f"**Pattern Type:** {pattern.get('type', 'Unknown')}")
                            st.write(f"**Occurrences:** {pattern.get('occurrences', 0)}")
                            st.write(f"**Description:** {pattern.get('description', 'N/A')}")

                            if pattern.get('conditions'):
                                st.write("**Conditions:**")
                                st.json(pattern['conditions'])

                        with col2:
                            st.metric("Confidence", f"{pattern.get('confidence', 0):.0%}")
                            st.metric("Last Seen", pattern.get('last_seen', 'N/A')[:10])

                            if pattern.get('recommended_action'):
                                st.info(f"💡 {pattern.get('recommended_action')}")

            else:
                st.info("No patterns match the current filters.")

        else:
            st.error("Failed to fetch patterns")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_insights_tab(api_base_url: str):
    """AI-generated insights"""
    st.subheader("💡 AI-Generated Insights")

    try:
        response = requests.get(f"{api_base_url}/api/v1/intelligence/insights")

        if response.status_code == 200:
            insights = response.json().get("insights", [])

            if insights:
                # Group by category
                categories = {}
                for insight in insights:
                    category = insight.get("category", "General")
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(insight)

                # Display by category
                for category, cat_insights in categories.items():
                    st.markdown(f"### 📁 {category}")

                    for insight in cat_insights:
                        severity = insight.get("severity", "info")
                        icon = {
                            "critical": "🔴",
                            "warning": "🟡",
                            "info": "🔵",
                            "success": "🟢"
                        }.get(severity, "ℹ️")

                        with st.container():
                            col1, col2, col3 = st.columns([6, 2, 1])

                            with col1:
                                st.markdown(f"{icon} **{insight.get('title', 'Insight')}**")
                                st.write(insight.get('message', ''))

                            with col2:
                                confidence = insight.get('confidence', 0)
                                st.metric("Confidence", f"{confidence:.0%}")

                            with col3:
                                if insight.get('actionable'):
                                    st.button("Act", key=f"act_{insight.get('id')}")

                        st.markdown("---")

            else:
                st.info("No insights available yet. Run tests to generate insights!")

        else:
            st.error("Failed to fetch insights")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def render_recommendations_tab(api_base_url: str):
    """Endpoint-specific recommendations"""
    st.subheader("🎯 Testing Recommendations")

    # Endpoint selector
    endpoint_key = st.text_input(
        "Enter endpoint to get recommendations",
        placeholder="GET /api/users",
        help="Format: METHOD /path"
    )

    if endpoint_key:
        try:
            # URL encode the endpoint
            import urllib.parse
            encoded_endpoint = urllib.parse.quote(endpoint_key, safe='')

            response = requests.get(
                f"{api_base_url}/api/v1/intelligence/recommendations/{encoded_endpoint}"
            )

            if response.status_code == 200:
                recommendations = response.json().get("recommendations", [])

                if recommendations:
                    st.success(f"Found {len(recommendations)} recommendations")

                    for rec in recommendations:
                        with st.container():
                            col1, col2 = st.columns([4, 1])

                            with col1:
                                rec_type = rec.get("type", "general")
                                icon = {
                                    "test_data": "🎲",
                                    "priority": "⚡",
                                    "caution": "⚠️",
                                    "optimization": "🚀"
                                }.get(rec_type, "💡")

                                st.markdown(f"{icon} **{rec.get('title', 'Recommendation')}**")
                                st.write(rec.get('description', ''))

                                if rec.get('details'):
                                    with st.expander("Details"):
                                        st.json(rec['details'])

                            with col2:
                                confidence = rec.get('confidence', 0)
                                st.metric("Confidence", f"{confidence:.0%}")

                        st.markdown("---")

                else:
                    st.info(f"No recommendations available for `{endpoint_key}`")

            else:
                st.warning("Endpoint not found or no recommendations available")

        except Exception as e:
            st.error(f"Error: {str(e)}")


def render_api_structure_tab(api_base_url: str):
    """API structure visualization"""
    st.subheader("🗺️ API Structure Analysis")

    try:
        response = requests.get(f"{api_base_url}/api/v1/intelligence/api-structure")

        if response.status_code == 200:
            structure = response.json()

            # Entities
            st.markdown("### 📦 Detected Entities")
            entities = structure.get("entities", [])

            if entities:
                entity_data = []
                for entity in entities:
                    entity_data.append({
                        "Name": entity.get("name"),
                        "Type": entity.get("type"),
                        "Confidence": f"{entity.get('confidence', 0):.0%}",
                        "Endpoints": len(entity.get("related_endpoints", []))
                    })

                df = pd.DataFrame(entity_data)
                st.dataframe(df, use_container_width=True, hide_index=True)

            else:
                st.info("No entities detected yet. Upload and test an API to see structure analysis.")

            st.markdown("---")

            # Data flows
            st.markdown("### 🔄 Data Flows")
            flows = structure.get("data_flows", [])

            if flows:
                for flow in flows:
                    st.write(f"**{flow.get('from')}** → **{flow.get('to')}**")
                    st.caption(f"Field: `{flow.get('field')}` | Confidence: {flow.get('confidence', 0):.0%}")
                    st.markdown("---")
            else:
                st.info("No data flows detected yet.")

            # Dependencies
            st.markdown("### 🔗 Endpoint Dependencies")
            dependencies = structure.get("dependencies", {})

            if dependencies:
                dep_data = []
                for endpoint, deps in dependencies.items():
                    dep_data.append({
                        "Endpoint": endpoint,
                        "Depends On": ", ".join(deps) if deps else "None"
                    })

                df = pd.DataFrame(dep_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No dependencies detected yet.")

        else:
            st.error("Failed to fetch API structure")

    except Exception as e:
        st.error(f"Error: {str(e)}")
