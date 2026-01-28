"""
Streamlit Dashboard for Short-Term Rental System.

This dashboard provides a web interface for viewing property data,
investment opportunities, and market insights.
"""

import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any

# Configure Streamlit page
st.set_page_config(
    page_title="Short-Term Rental Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


# ============================================================================
# API Functions
# ============================================================================


def fetch_markets() -> List[Dict[str, Any]]:
    """Fetch all markets from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/markets")
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"Error fetching markets: {e}")
        return []


def fetch_properties(
    market_id: Optional[str] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    min_occupancy: Optional[float] = None,
    max_occupancy: Optional[float] = None,
    min_rating: Optional[float] = None,
    is_guest_favorite: Optional[bool] = None,
    is_reliable_data: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """Fetch properties from the API with filters."""
    params = {
        "page": page,
        "page_size": page_size,
        "sort_order": sort_order,
    }
    if market_id:
        params["market_id"] = market_id
    if min_bedrooms is not None:
        params["min_bedrooms"] = min_bedrooms
    if max_bedrooms is not None:
        params["max_bedrooms"] = max_bedrooms
    if min_revenue is not None:
        params["min_revenue"] = min_revenue
    if max_revenue is not None:
        params["max_revenue"] = max_revenue
    if min_occupancy is not None:
        params["min_occupancy"] = min_occupancy
    if max_occupancy is not None:
        params["max_occupancy"] = max_occupancy
    if min_rating is not None:
        params["min_rating"] = min_rating
    if is_guest_favorite is not None:
        params["is_guest_favorite"] = is_guest_favorite
    if is_reliable_data is not None:
        params["is_reliable_data"] = is_reliable_data
    if sort_by:
        params["sort_by"] = sort_by

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/properties", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching properties: {e}")
        return {"data": [], "total": 0, "page": 1, "page_size": page_size, "total_pages": 0}


def fetch_top_opportunities(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch top investment opportunities from the API."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/investment-scores/top-opportunities",
            params={"limit": limit}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"Error fetching top opportunities: {e}")
        return []


def fetch_top_performers(limit: int = 20, market_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch top performers from the API."""
    params = {"limit": limit}
    if market_id:
        params["market_id"] = market_id

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/insights/top-performers",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"Error fetching top performers: {e}")
        return []


def fetch_properties_with_scores(
    market_id: Optional[str] = None,
    bedrooms: Optional[float] = None,
    min_revenue: Optional[float] = None,
    min_total_score: Optional[float] = None,
    opportunity_tier: Optional[str] = None,
    is_top_opportunity: Optional[bool] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch properties with investment scores for charts."""
    params = {"limit": limit}
    if market_id:
        params["market_id"] = market_id
    if bedrooms is not None:
        params["bedrooms"] = bedrooms
    if min_revenue is not None:
        params["min_revenue"] = min_revenue
    if min_total_score is not None:
        params["min_total_score"] = min_total_score
    if opportunity_tier:
        params["opportunity_tier"] = opportunity_tier
    if is_top_opportunity is not None:
        params["is_top_opportunity"] = is_top_opportunity

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/properties/with-scores",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"Error fetching properties with scores: {e}")
        return []


# ============================================================================
# Chart Functions
# ============================================================================


def create_revenue_by_bedroom_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create a bar chart showing revenue by bedroom count."""
    if not properties:
        return go.Figure()

    df = pd.DataFrame(properties)
    df = df[df["bedrooms"].notna() & df["revenue"].notna()]
    
    if df.empty:
        return go.Figure()

    # Group by bedroom count and calculate average revenue
    avg_revenue_by_bedrooms = df.groupby("bedrooms")["revenue"].mean().reset_index()
    avg_revenue_by_bedrooms = avg_revenue_by_bedrooms.sort_values("bedrooms")

    fig = px.bar(
        avg_revenue_by_bedrooms,
        x="bedrooms",
        y="revenue",
        title="Average Revenue by Bedroom Count",
        labels={"bedrooms": "Bedrooms", "revenue": "Average Revenue ($)"},
        color="revenue",
        color_continuous_scale="Viridis"
    )
    fig.update_layout(
        xaxis_title="Number of Bedrooms",
        yaxis_title="Average Revenue ($)",
        hovermode="x unified"
    )
    return fig


def create_opportunity_tier_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create a pie chart showing distribution of opportunity tiers."""
    if not properties:
        return go.Figure()

    df = pd.DataFrame(properties)
    df = df[df["opportunity_tier"].notna()]
    
    if df.empty:
        return go.Figure()

    tier_counts = df["opportunity_tier"].value_counts().reset_index()
    tier_counts.columns = ["Opportunity Tier", "Count"]

    # Define colors for each tier
    color_map = {
        "PLATINUM": "#E5E4E2",
        "GOLD": "#FFD700",
        "SILVER": "#C0C0C0",
        "BRONZE": "#CD7F32"
    }
    colors = [color_map.get(tier, "#CCCCCC") for tier in tier_counts["Opportunity Tier"]]

    fig = px.pie(
        tier_counts,
        values="Count",
        names="Opportunity Tier",
        title="Distribution of Opportunity Tiers",
        color_discrete_sequence=colors
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def create_score_distribution_chart(properties: List[Dict[str, Any]]) -> go.Figure:
    """Create a histogram showing distribution of total scores."""
    if not properties:
        return go.Figure()

    df = pd.DataFrame(properties)
    df = df[df["total_score"].notna()]
    
    if df.empty:
        return go.Figure()

    fig = px.histogram(
        df,
        x="total_score",
        nbins=30,
        title="Distribution of Investment Scores",
        labels={"total_score": "Total Score"},
        color_discrete_sequence=["#1f77b4"]
    )
    fig.update_layout(
        xaxis_title="Total Score",
        yaxis_title="Count",
        bargap=0.1
    )
    return fig


def create_top_opportunities_chart(opportunities: List[Dict[str, Any]]) -> go.Figure:
    """Create a bar chart showing top opportunities."""
    if not opportunities:
        return go.Figure()

    df = pd.DataFrame(opportunities)
    df = df[df["total_score"].notna()]
    
    if df.empty:
        return go.Figure()

    # Sort by total score and take top 15
    df = df.sort_values("total_score", ascending=True).tail(15)

    fig = px.bar(
        df,
        x="total_score",
        y="property_title",
        orientation="h",
        title="Top Investment Opportunities",
        labels={"total_score": "Total Score", "property_title": "Property"},
        color="total_score",
        color_continuous_scale="RdYlGn"
    )
    fig.update_layout(
        xaxis_title="Total Score",
        yaxis_title="Property",
        height=500
    )
    return fig


# ============================================================================
# UI Components
# ============================================================================


def render_sidebar():
    """Render the sidebar with filters."""
    st.sidebar.header("🔍 Filters")

    # Fetch markets for dropdown
    markets = fetch_markets()
    market_options = {m["name"]: m["id"] for m in markets}
    market_options["All Markets"] = None

    selected_market = st.sidebar.selectbox(
        "Market",
        options=list(market_options.keys()),
        index=0
    )
    market_id = market_options[selected_market]

    # Bedroom filters
    st.sidebar.subheader("Bedrooms")
    col1, col2 = st.sidebar.columns(2)
    min_bedrooms = col1.number_input("Min", min_value=0, max_value=20, value=0, step=1)
    max_bedrooms = col2.number_input("Max", min_value=0, max_value=20, value=20, step=1)

    # Revenue filters
    st.sidebar.subheader("Revenue ($)")
    col1, col2 = st.sidebar.columns(2)
    min_revenue = col1.number_input("Min", min_value=0.0, value=0.0, step=1000.0)
    max_revenue = col2.number_input("Max", min_value=0.0, value=1000000.0, step=1000.0)

    # Occupancy filters
    st.sidebar.subheader("Occupancy (%)")
    col1, col2 = st.sidebar.columns(2)
    min_occupancy = col1.number_input("Min", min_value=0.0, max_value=100.0, value=0.0, step=5.0)
    max_occupancy = col2.number_input("Max", min_value=0.0, max_value=100.0, value=100.0, step=5.0)

    # Rating filter
    min_rating = st.sidebar.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.1)

    # Boolean filters
    st.sidebar.subheader("Property Status")
    is_guest_favorite = st.sidebar.checkbox("Guest Favorite Only")
    is_reliable_data = st.sidebar.checkbox("Reliable Data Only", value=True)

    # Sorting
    st.sidebar.subheader("Sorting")
    sort_by = st.sidebar.selectbox(
        "Sort By",
        options=["title", "bedrooms", "bathrooms", "accommodates", "created_at"],
        index=0
    )
    sort_order = st.sidebar.radio("Order", options=["asc", "desc"], index=1)

    return {
        "market_id": market_id,
        "min_bedrooms": min_bedrooms if min_bedrooms > 0 else None,
        "max_bedrooms": max_bedrooms if max_bedrooms < 20 else None,
        "min_revenue": min_revenue if min_revenue > 0 else None,
        "max_revenue": max_revenue if max_revenue < 1000000 else None,
        "min_occupancy": min_occupancy if min_occupancy > 0 else None,
        "max_occupancy": max_occupancy if max_occupancy < 100 else None,
        "min_rating": min_rating if min_rating > 0 else None,
        "is_guest_favorite": is_guest_favorite if is_guest_favorite else None,
        "is_reliable_data": is_reliable_data if is_reliable_data else None,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


def render_property_card(property_data: Dict[str, Any]):
    """Render a property card with key information."""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 2])
        
        with col1:
            st.subheader(property_data.get("title", "Unknown Property"))
            st.caption(f"📍 {property_data.get('city_name', 'N/A')}, {property_data.get('zipcode', 'N/A')}")
        
        with col2:
            st.metric("Bedrooms", property_data.get("bedrooms", "N/A"))
            st.metric("Bathrooms", property_data.get("bathrooms", "N/A"))
        
        with col3:
            if property_data.get("revenue"):
                st.metric("Revenue", f"${property_data['revenue']:,.0f}")
            if property_data.get("occupancy"):
                st.metric("Occupancy", f"{property_data['occupancy']:.1f}%")
        
        st.divider()


def render_top_opportunities_section():
    """Render the top investment opportunities section."""
    st.header("🏆 Top Investment Opportunities")
    
    opportunities = fetch_top_opportunities(limit=15)
    
    if not opportunities:
        st.info("No top opportunities found. Run the pipeline to generate investment scores.")
        return
    
    # Display chart
    fig = create_top_opportunities_chart(opportunities)
    st.plotly_chart(fig, use_container_width=True)
    
    # Display table
    st.subheader("Detailed View")
    df = pd.DataFrame(opportunities)
    
    # Select columns to display
    display_columns = [
        "property_title",
        "property_bedrooms",
        "market_name",
        "property_revenue",
        "property_occupancy",
        "property_adr",
        "property_rating",
        "total_score",
        "opportunity_tier"
    ]
    
    df_display = df[display_columns].copy()
    df_display.columns = [
        "Property",
        "Bedrooms",
        "Market",
        "Revenue",
        "Occupancy",
        "ADR",
        "Rating",
        "Total Score",
        "Tier"
    ]
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def render_charts_section(filters: Dict[str, Any]):
    """Render the charts section with insights."""
    st.header("📊 Market Insights")
    
    # Fetch properties with scores for charts
    properties_with_scores = fetch_properties_with_scores(
        market_id=filters.get("market_id"),
        min_revenue=filters.get("min_revenue"),
        limit=500
    )
    
    if not properties_with_scores:
        st.info("No data available for charts. Run the pipeline to load data.")
        return
    
    # Create three columns for charts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Revenue by Bedrooms")
        fig1 = create_revenue_by_bedroom_chart(properties_with_scores)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("Opportunity Tiers")
        fig2 = create_opportunity_tier_chart(properties_with_scores)
        st.plotly_chart(fig2, use_container_width=True)
    
    with col3:
        st.subheader("Score Distribution")
        fig3 = create_score_distribution_chart(properties_with_scores)
        st.plotly_chart(fig3, use_container_width=True)


def render_properties_section(filters: Dict[str, Any]):
    """Render the properties section with filtering and pagination."""
    st.header("🏠 Properties")
    
    # Pagination
    page_size = st.selectbox("Properties per page", options=[10, 20, 50, 100], index=1)
    
    # Initialize session state for page
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    
    # Fetch properties
    result = fetch_properties(
        page=st.session_state.current_page,
        page_size=page_size,
        **filters
    )
    
    properties = result.get("data", [])
    total = result.get("total", 0)
    total_pages = result.get("total_pages", 1)
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Properties", total)
    col2.metric("Current Page", st.session_state.current_page)
    col3.metric("Total Pages", total_pages)
    
    st.divider()
    
    # Display properties
    if properties:
        for prop in properties:
            render_property_card(prop)
    else:
        st.info("No properties found matching your filters.")
    
    # Pagination controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_page <= 1):
            st.session_state.current_page -= 1
            st.rerun()
    with col2:
        st.write(f"Page {st.session_state.current_page} of {total_pages}")
    with col3:
        if st.button("Next ➡️", disabled=st.session_state.current_page >= total_pages):
            st.session_state.current_page += 1
            st.rerun()


# ============================================================================
# Main Application
# ============================================================================


def main():
    """Main application entry point."""
    st.title("🏠 Short-Term Rental Dashboard")
    st.markdown("Explore property data, investment opportunities, and market insights.")
    
    # Add tabs for different views
    tab1, tab2, tab3 = st.tabs(["🏠 Properties", "🏆 Top Opportunities", "📊 Insights"])
    
    # Render sidebar with filters
    filters = render_sidebar()
    
    with tab1:
        render_properties_section(filters)
    
    with tab2:
        render_top_opportunities_section()
    
    with tab3:
        render_charts_section(filters)


if __name__ == "__main__":
    main()
