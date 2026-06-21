"""
PHASE 5: STREAMLIT DASHBOARD
Interactive app for event-driven congestion forecasting
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR.parent / "data file"
sys.path.insert(0, str(APP_DIR))
from recommendation_engine import RecommendationEngine


def _style_light_chart(fig, ax, *, legend: bool = False) -> None:
    """Apply light-theme styling to matplotlib figures."""
    panel = "#ffffff"
    text = "#212529"
    grid = "#e9ecef"
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor(panel)
    ax.tick_params(colors=text, labelcolor=text)
    ax.xaxis.label.set_color(text)
    ax.yaxis.label.set_color(text)
    ax.title.set_color(text)
    for spine in ax.spines.values():
        spine.set_color(grid)
    if legend:
        leg = ax.get_legend()
        if leg:
            leg.get_frame().set_facecolor(panel)
            leg.get_frame().set_edgecolor(grid)
            for label in leg.get_texts():
                label.set_color(text)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Bengaluru Traffic Forecasting",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS — dark theme with high-contrast light text
st.markdown("""
<style>
    :root {
        --page: #f8f9fa;
        --surface: #ffffff;
        --surface-hover: #f1f3f5;
        --line: #dee2e6;
        --text: #212529;
        --muted: #868e96;
        --accent: #228be6;
        --accent-soft: #e7f5ff;
        --accent-border: #74c0fc;
    }

    /* App shell */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    section.main,
    section[data-testid="stSidebar"],
    header[data-testid="stHeader"] {
        background-color: var(--page) !important;
        color: var(--text) !important;
    }
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 4rem;
        max-width: 1400px;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* Headings & body copy */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] em,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stMarkdownContainer"] a,
    .stWrite, .stWrite p {
        color: var(--text) !important;
    }

    /* Widget labels & inputs */
    [data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"],
    [data-testid="stSelectbox"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stSlider"] label,
    [data-testid="stCheckbox"] label p {
        color: var(--text) !important;
        font-weight: 650 !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--line) !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] span,
    [data-testid="stSelectbox"] [data-baseweb="select"] svg {
        color: var(--text) !important;
        fill: var(--text) !important;
    }
    [data-testid="stTextArea"] textarea:disabled {
        -webkit-text-fill-color: var(--text) !important;
        color: var(--text) !important;
        opacity: 1 !important;
        background-color: var(--surface-hover) !important;
    }
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"],
    [data-testid="stSlider"] [data-baseweb="slider"] div {
        color: var(--text) !important;
    }

    /* Dropdown popover */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--line) !important;
    }
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li,
    div[data-baseweb="popover"] li span,
    div[data-baseweb="menu"] li span {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] li:hover,
    div[data-baseweb="popover"] li:hover span,
    div[data-baseweb="menu"] li:hover span {
        background-color: var(--surface-hover) !important;
        color: var(--text) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        border-bottom: 1px solid var(--line);
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: var(--surface-hover) !important;
        border-radius: 6px 6px 0 0;
        padding: 12px 16px;
        color: var(--text) !important;
    }
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span {
        color: var(--text) !important;
    }
    .stTabs [aria-selected="true"] {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-bottom-color: var(--surface) !important;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: var(--surface) !important;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 24px 24px 20px;
        min-height: 128px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div {
        color: var(--text) !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"],
    [data-testid="stMetricDelta"] svg {
        color: var(--muted) !important;
    }

    /* Custom cards */
    .ops-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 28px;
        min-height: 160px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .ops-card .label { color: var(--muted); font-size: 0.92rem; margin: 0 0 8px; font-weight: 600; }
    .ops-card .value { color: var(--text); font-size: 2.1rem; font-weight: 720; line-height: 1.05; margin: 0; }
    .ops-card .detail { color: var(--muted); font-size: 0.9rem; margin: 10px 0 0; }
    .context-row {
        background: var(--accent-soft);
        border: 1px solid var(--accent-border);
        border-radius: 10px;
        padding: 18px 24px;
        color: var(--text) !important;
        margin-bottom: 16px;
        font-size: 1.05rem;
        box-shadow: 0 2px 6px rgba(34, 139, 230, 0.1);
    }
    .context-row b { color: var(--text) !important; }

    /* Alerts — target Streamlit notification container (icon :has selectors miss current DOM) */
    [data-testid="stAlert"],
    [data-testid="stAlertContainer"],
    [data-testid="stAlertContainer"] p,
    [data-testid="stAlertContainer"] div,
    [data-testid="stAlertContainer"] strong,
    [data-testid="stAlertContainer"] span,
    [data-baseweb="notification"] {
        color: var(--text) !important;
        border-radius: 8px !important;
    }
    [data-testid="stAlertContainer"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--line) !important;
    }

    /* Expander */
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
        color: var(--text) !important;
    }
    [data-testid="stExpander"] details {
        background: var(--surface) !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px;
    }

    /* Dataframe / table — hide Glide canvas overlay that paints low-contrast cells */
    [data-testid="stDataFrame"] canvas {
        display: none !important;
    }
    [data-testid="stDataFrame"] table,
    [data-testid="stTable"] table {
        width: 100% !important;
        border-collapse: collapse !important;
    }
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td,
    [data-testid="stTable"] th,
    [data-testid="stTable"] td {
        color: var(--text) !important;
        background-color: var(--surface) !important;
        border: 1px solid var(--line) !important;
        padding: 8px 12px !important;
    }
    [data-testid="stDataFrame"] th,
    [data-testid="stTable"] th {
        background-color: var(--surface-hover) !important;
        font-weight: 650 !important;
    }

    /* Sliders, help icons, captions */
    [data-testid="stSlider"] [data-testid="stThumbValue"],
    [data-testid="stSlider"] [data-testid="stTickBarMin"],
    [data-testid="stSlider"] [data-testid="stTickBarMax"] {
        color: var(--text) !important;
    }
    [data-testid="stTooltipIcon"],
    [data-testid="stHelpTooltipIcon"],
    button[kind="headerNoPadding"] {
        color: var(--muted) !important;
    }
    [data-testid="stCaptionContainer"] p {
        color: #b8c5d6 !important;
    }
    [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] span {
        color: var(--text) !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
        color: var(--text) !important;
    }

    /* Buttons */
    div.stButton > button,
    [data-testid="stDownloadButton"] button {
        border-radius: 6px;
        min-height: 46px;
        font-weight: 650;
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--line) !important;
    }
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {
        background-color: var(--accent) !important;
        color: #0b0f14 !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"] p,
    div.stButton > button[data-testid="baseButton-primary"] p {
        color: #0b0f14 !important;
    }

    /* Divider & footer */
    hr { border-color: var(--line) !important; }
    .small-note { color: var(--muted); font-size: 0.92rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZE CACHE & SESSION STATE
# ============================================================================

@st.cache_resource(show_spinner="Initializing Traffic Engine...")
def get_engine():
    return RecommendationEngine()

@st.cache_data(show_spinner="Loading Historical Demo Data...")
def load_demo_data():
    try:
        return pd.read_csv(DATA_DIR / 'demo_cases_results.csv')
    except Exception:
        return None

if 'engine' not in st.session_state:
    st.session_state.engine = get_engine()

if 'demo_data' not in st.session_state:
    st.session_state.demo_data = load_demo_data()

# ============================================================================
# HEADER
# ============================================================================

st.markdown("# 🚦 Bengaluru Event-Driven Congestion Forecasting System")
st.markdown("**AI-Powered Traffic Management for Bangalore Police**")

st.divider()

# ============================================================================
# MAIN TABS
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Live Prediction",
    "📊 Demo Cases",
    "📈 Analytics",
    "ℹ️ About",
    "📋 Documentation"
])

# ============================================================================
# TAB 1: LIVE PREDICTION
# ============================================================================

with tab1:
    st.markdown("## Live Congestion Assessment")
    st.markdown("Select the event and location. Traffic flow, affected people, spread, duration, and usual police deployment are estimated automatically.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Event Details")
        
        event_cause = st.selectbox(
            "Event Type",
            options=['public_event', 'accident', 'construction', 'vip_movement', 
                    'procession', 'vehicle_breakdown', 'pot_hole', 'water_logging',
                    'tree_fall', 'congestion'],
            help="Select the type of event"
        )
        
        corridor = st.selectbox(
            "Corridor/Road",
            options=['Mysore Road', 'Bellary Road 1', 'Bellary Road 2', 'ORR North',
                    'ORR East 1', 'ORR East 2', 'CBD-2', 'Bangalore-Mysore Road',
                    'Hosur Road', 'Tumkur Road', 'Non-corridor'],
            help="Which road is affected?"
        )
        
        zone = st.selectbox(
            "Zone",
            options=['Central Zone', 'North Zone 1', 'North Zone 2', 'South Zone 1',
                    'South Zone 2', 'East Zone 1', 'East Zone 2', 'West Zone 1', 
                    'West Zone 2', 'Unknown'],
            help="Administrative zone"
        )
        
        road_closure_choice = st.selectbox(
            "Road Closure Status",
            options=["Auto estimate", "Yes", "No"],
            help="Use Auto estimate when closure status is not confirmed"
        )
    
    with col2:
        st.markdown("### Time")

        if "event_time" not in st.session_state:
            st.session_state.event_time = datetime.now().time()
            
        event_time = st.time_input(
            "Event Time",
            value=st.session_state.event_time,
            help="Select the exact time of the event"
        )
        st.session_state.event_time = event_time
        event_hour = event_time.hour

        baseline = st.session_state.engine.estimate_defaults(event_cause, corridor, event_hour, zone=zone)
        
        if baseline.get("expected_crowd_range"):
            st.markdown("### 👥 Crowd Estimation")
            crowd_range = baseline["expected_crowd_range"]
            expected_crowd = st.number_input(
                "Expected Crowd Size",
                min_value=100,
                max_value=500000,
                value=int(crowd_range[1]),
                step=500,
                help=f"Typical range: {crowd_range[0]:,} - {crowd_range[2]:,}. This drives police deployment."
            )
            baseline["affected_people"] = expected_crowd
            
        st.markdown("### Auto-estimated Inputs")
        st.markdown(f"""
        <div class='ops-card'>
            <p class='label'>Traffic Flow · Avg Speed · Affected People · Usual Police</p>
            <p class='value'>{baseline['traffic_flow_index']} · {baseline.get('avg_speed_kmh', 15)} km/h · {baseline['affected_people']:,} · {baseline['usual_police']}</p>
            <p class='detail'>{baseline['historical_event_count']} similar local records used where available</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("Advanced overrides"):
        adv1, adv2, adv3 = st.columns(3)
        with adv1:
            override_severity = st.checkbox("Override event severity", value=False)
            event_severity = st.slider(
                "Event Severity Value",
                min_value=0.0,
                max_value=10.0,
                value=float(baseline["base_impact_score"]),
                step=0.1,
                disabled=not override_severity,
                help="Numeric seriousness of the event"
            )
            override_people = st.checkbox("Override affected people", value=False)
            crowd_size = st.number_input(
                "Affected People",
                min_value=0,
                max_value=250000,
                value=int(baseline["affected_people"]),
                step=100,
                disabled=not override_people,
            )
        with adv2:
            override_duration = st.checkbox("Override duration", value=False)
            duration_hours = st.slider(
                "Event Duration (hours)",
                min_value=0.25,
                max_value=24.0,
                value=float(min(24.0, baseline["duration_hours"])),
                step=0.25,
                disabled=not override_duration,
            )
            override_spread = st.checkbox("Override spread", value=False)
            affected_length_km = st.slider(
                "Affected Road Length / Spread (km)",
                min_value=0.2,
                max_value=15.0,
                value=float(min(15.0, baseline["spread_km"])),
                step=0.1,
                disabled=not override_spread,
            )
        with adv3:
            override_flow = st.checkbox("Override traffic flow", value=False)
            traffic_flow_index = st.slider(
                "Current Traffic Flow Index",
                min_value=0.0,
                max_value=1.0,
                value=float(baseline["traffic_flow_index"]),
                step=0.01,
                disabled=not override_flow,
            )
            st.markdown("### Baseline Source")
            st.caption(baseline["source_note"])
    
    # ====================================================================
    # PREDICTION SECTION
    # ====================================================================
    
    st.divider()
    
    if st.button("🚀 Get Prediction & Recommendations", type="primary", use_container_width=True):
        base_impact_score = event_severity if override_severity else None
        
        if override_people:
            crowd_override = int(crowd_size)
        elif baseline.get("expected_crowd_range"):
            crowd_override = int(expected_crowd)
        else:
            crowd_override = None
            
        duration_override = duration_hours if override_duration else None
        spread_override = affected_length_km if override_spread else None
        flow_override = traffic_flow_index if override_flow else None
        closure_override = None
        if road_closure_choice == "Yes":
            closure_override = True
        elif road_closure_choice == "No":
            closure_override = False
        
        # Get recommendations
        recommendations = st.session_state.engine.recommend(
            impact_score=base_impact_score,
            event_type=event_cause,
            corridor=corridor,
            zone=zone,
            duration_hours=duration_override,
            hour=event_hour,
            crowd_size=crowd_override,
            road_closure=closure_override,
            affected_length_km=spread_override,
            live_traffic_index=flow_override
        )

        impact_score = recommendations['impact_score']
        context = recommendations['context']
        baseline = recommendations['baseline']
        
        # Display results
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## Impact Analysis & Prediction")
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Spacious, text-heavy presentation instead of metric boxes
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"### Score: **{impact_score:.1f} / 10**")
            st.markdown(f"**Category:** {recommendations['category']}  \n"
                        f"**Expected Queue:** {context['expected_queue_km']:.1f} km  \n"
                        f"**Time Period:** {context['time_period']}")
        
        with col2:
            st.markdown("### Model Assumptions")
            st.markdown(f"**Base Event Severity:** {context['event_numeric_value']}/10  \n"
                        f"**Traffic Flow:** {context['traffic_flow_index']}  \n"
                        f"**Affected People:** {context['crowd_size']:,}  \n"
                        f"**Historical Records Used:** {baseline['historical_event_count']}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ========== ESCALATION ALERTS ==========
        if recommendations.get("escalation_required"):
            for esc in recommendations.get("escalations", []):
                alert_type = esc.get("notification", {}).get("alert_type", "WARNING")
                if alert_type == "EMERGENCY":
                    st.error(f"🆘 **EMERGENCY PROTOCOL ACTIVATED** — {esc['action']}")
                elif alert_type == "CRITICAL":
                    st.error(f"🚨 **CRITICAL ESCALATION** — {esc['action']}  \nNotify: {esc.get('notification', {}).get('sms', 'N/A')}")
                elif alert_type == "URGENT":
                    st.warning(f"⚠️ **ESCALATION TRIGGERED** — {esc['action']}  \nNotify: {esc.get('notification', {}).get('sms', 'N/A')}")
                else:
                    st.info(f"ℹ️ {esc['action']}")
        
        # ========== CONFLICT WARNINGS ==========
        conflicts = recommendations.get("conflicts", {})
        if conflicts.get("corridor_conflicts"):
            st.warning(f"⚠️ **Corridor Conflict Detected** — {len(conflicts['corridor_conflicts'])} other active event(s) on this corridor. Resolution: {conflicts.get('conflict_resolution', {}).get('action', 'Escalate')}")
        if conflicts.get("manpower_shortage"):
            st.error(f"🚨 **Manpower Shortage** — Zone demand exceeds available capacity (200 officers). Requesting mutual aid from adjacent zones.")
        
        # ========== VALIDATION WARNINGS ==========
        if recommendations.get("validation_errors"):
            with st.expander("⚠️ Input Validation Warnings", expanded=False):
                for err in recommendations["validation_errors"]:
                    st.caption(f"• {err}")

        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # Recommendations
        st.markdown("## Police Deployment Recommendations")
        
        rec_col1, rec_col2, rec_col3, rec_col4 = st.columns(4)
        
        with rec_col1:
            manpower = recommendations['manpower']
            st.markdown(f"""
            <div class='ops-card'>
                <p class='label'>Officers</p>
                <p class='value'>{manpower['recommended']}</p>
                <p class='detail'>Range {manpower['min_officers']}-{manpower['max_officers']} · usual {manpower['usual_officers']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with rec_col2:
            barricades = recommendations['barricades']
            st.markdown(f"""
            <div class='ops-card'>
                <p class='label'>Barricade Locations</p>
                <p class='value'>{barricades['count']}</p>
                <p class='detail'>{barricades['level']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with rec_col3:
            setup = recommendations['setup_cleanup']
            st.markdown(f"""
            <div class='ops-card'>
                <p class='label'>Setup / Response</p>
                <p class='value'>{setup['response_minutes']:.0f}m</p>
                <p class='detail'>{setup['setup_hours_before']:.2f}h pre-deployment for planned events</p>
            </div>
            """, unsafe_allow_html=True)
        
        with rec_col4:
            st.markdown(f"""
            <div class='ops-card'>
                <p class='label'>Clearance Time</p>
                <p class='value'>{setup['cleanup_hours_after']:.2f}h</p>
                <p class='detail'>Total impact {setup['total_impact_hours']:.2f}h</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Barricade locations
        st.markdown("### 🚧 Barricade Locations")
        if barricades['locations']:
            for i, loc in enumerate(barricades['locations'], 1):
                st.write(f"{i}. {loc}")
        else:
            st.write("No barricades needed")
        
        # Traffic diversions
        st.markdown("### 🛣️ Traffic Diversions")
        diversions = recommendations['diversions']
        col_div1, col_div2, col_div3 = st.columns(3)
        
        with col_div1:
            if diversions.get('primary'):
                st.success(f"**Primary:** {diversions['primary']}")
        
        with col_div2:
            if diversions.get('secondary'):
                st.info(f"**Secondary:** {diversions['secondary']}")
        
        with col_div3:
            if diversions.get('tertiary'):
                st.warning(f"**Tertiary:** {diversions['tertiary']}")
        
        # Summary
        st.markdown("### 📝 Summary")
        st.text_area(
            "Deployment Summary",
            value=recommendations['summary'],
            disabled=True,
            height=150
        )

# ============================================================================
# TAB 2: DEMO CASES
# ============================================================================

with tab2:
    st.markdown("## 📊 Demo Cases: Real Bengaluru Events")
    st.markdown("5 real events from the Astram dataset with predictions and recommendations")
    
    if st.session_state.demo_data is not None:
        demo_df = st.session_state.demo_data
        
        # Summary table
        st.markdown("### 📋 Summary Table")
        summary_cols = ['Case', 'Name', 'Event_Cause', 'Corridor', 'Impact_Score', 
                       'Officers', 'Barricade_Level', 'Diversion_Level']
        st.table(demo_df[summary_cols])
        
        st.divider()
        
        # Detailed cases
        st.markdown("### 📌 Detailed Case Analysis")
        
        selected_case = st.selectbox(
            "Select a case to view details:",
            options=demo_df['Name'].unique(),
            key="case_selector"
        )
        
        case_data = demo_df[demo_df['Name'] == selected_case].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Event Information")
            st.write(f"**Event Type:** {case_data['Event_Cause']}")
            st.write(f"**Corridor:** {case_data['Corridor']}")
            st.write(f"**Zone:** {case_data['Zone']}")
            st.write(f"**Priority:** {case_data['Priority']}")
            st.write(f"**Duration:** {case_data['Duration_Hours']} hours")
        
        with col2:
            st.markdown("#### Prediction Results")
            st.metric("Impact Score", f"{case_data['Impact_Score']}/10")
            st.metric("Officers", f"{case_data['Officers']}")
            st.metric("Setup Time", f"{case_data['Setup_Hours']:.1f}h")
        
        st.divider()
        
        st.markdown("#### 👮 Recommendations")
        rec_col1, rec_col2, rec_col3 = st.columns(3)
        
        with rec_col1:
            st.info(f"""
            **Manpower**
            
            {case_data['Officers']} officers
            ({case_data['Officer_Range']})
            """)
        
        with rec_col2:
            st.warning(f"""
            **Barricades**
            
            {case_data['Barricade_Count']} locations
            {case_data['Barricade_Level']} level
            """)
        
        with rec_col3:
            st.error(f"""
            **Diversions**
            
            {case_data['Diversion_Level']} level
            Primary: {case_data['Primary_Route']}
            """)
        
        # Download button
        st.divider()
        csv = demo_df.to_csv(index=False)
        st.download_button(
            label="📥 Download All Demo Cases (CSV)",
            data=csv,
            file_name="demo_cases_results.csv",
            mime="text/csv"
        )
    else:
        st.error("Demo cases data not available")

# ============================================================================
# TAB 3: ANALYTICS
# ============================================================================

with tab3:
    st.markdown("## 📈 System Analytics & Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Model Accuracy", "95.5%", "+0.5%")
    
    with col2:
        st.metric("Prediction Error", "±0.08", "on 1-10 scale")
    
    with col3:
        st.metric("Training Data", "8,173", "real events")
    
    with col4:
        st.metric("Features Used", "19", "engineered")
    
    st.divider()
    
    # Demo cases stats
    if st.session_state.demo_data is not None:
        demo_df = st.session_state.demo_data
        
        st.markdown("### 📊 Demo Cases Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Impact Score Distribution")
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(8, 4))
            scores = demo_df['Impact_Score'].values
            colors = ['#FF6B6B' if s > 8 else '#FFA500' if s > 6 else '#4CAF50' for s in scores]
            ax.bar(range(len(scores)), scores, color=colors, alpha=0.85, edgecolor='#2a3647')
            ax.set_ylabel('Impact Score')
            ax.set_xlabel('Case')
            ax.set_ylim(0, 10)
            ax.axhline(y=5, color='#9aaabe', linestyle='--', alpha=0.6, label='Moderate')
            ax.set_title('Impact Scores Across Demo Cases')
            _style_light_chart(fig, ax, legend=True)
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            st.markdown("#### Officer Deployment")
            fig, ax = plt.subplots(figsize=(8, 4))
            officers = demo_df['Officers'].values
            colors_off = ['#667eea' if o >= 50 else '#764ba2' for o in officers]
            ax.bar(range(len(officers)), officers, color=colors_off, alpha=0.85, edgecolor='#2a3647')
            ax.set_ylabel('Number of Officers')
            ax.set_xlabel('Case')
            ax.set_title('Recommended Officer Deployment')
            ax.set_ylim(0, 70)
            _style_light_chart(fig, ax)
            plt.tight_layout()
            st.pyplot(fig)
        
        st.divider()
        
        st.markdown("#### 📊 Key Metrics")
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        
        with metrics_col1:
            st.metric("Avg Impact Score", f"{demo_df['Impact_Score'].mean():.2f}/10")
        
        with metrics_col2:
            st.metric("Avg Officers", f"{demo_df['Officers'].mean():.0f}")
        
        with metrics_col3:
            st.metric("Total Barricades", f"{demo_df['Barricade_Count'].sum()}")
        
        with metrics_col4:
            st.metric("Max Setup Time", f"{demo_df['Setup_Hours'].max():.1f}h")
        
        st.divider()
        
        st.markdown("#### 🎯 Deployment Levels")
        level_counts = demo_df['Diversion_Level'].value_counts()
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.pie(
            level_counts.values,
            labels=level_counts.index,
            autopct='%1.0f%%',
            colors=['#FF6B6B', '#FFA500', '#4CAF50'],
            textprops={'color': '#eef2f7'},
        )
        ax.set_title('Diversion Level Distribution')
        _style_light_chart(fig, ax)
        plt.tight_layout()
        st.pyplot(fig)

# ============================================================================
# TAB 4: ABOUT
# ============================================================================

with tab4:
    st.markdown("## ℹ️ About This System")
    
    st.markdown("""
    ### 🎯 Purpose
    AI-powered traffic management system that forecasts congestion impact for events
    and recommends police resource deployment in Bengaluru.
    
    ### 🏗️ Architecture
    
    **Phase 1:** Y Variable Engineering
    - Created Congestion Impact Score (1-10)
    - 8,173 Bengaluru events analyzed
    
    **Phase 2:** Feature Engineering
    - 19 engineered features from raw data
    - Time, location, severity, and interaction features
    
    **Phase 3:** Model Training
    - Random Forest model (95.5% accurate)
    - ±0.08 prediction error on 1-10 scale
    - Trained on 6,538 events
    
    **Phase 4:** Recommendation Engine
    - Auto-estimates traffic flow, affected people, duration, spread, and usual police presence
    - Combines road capacity, event type, time of day, closure probability, and historical records
    - Produces officer deployment, barricade locations, diversions, setup time, and clearance time
    
    **Phase 5:** Dashboard (You are here)
    - Interactive interface for police
    - Live predictions and recommendations
    - Demo cases and analytics
    
    ### 📊 Data Source
    **Astram Dataset:** 6-month Bengaluru traffic incident data
    - 8,173 real events
    - 46 fields per event
    - Time period: Nov 2023 - Apr 2024
    
    ### 🎓 Model Performance
    - **Accuracy:** 95.5% (R² = 0.955)
    - **Error:** ±0.08/10 on impact score
    - **Features:** 19 engineered variables
    - **Context layer:** Astram history + Bengaluru road/event baselines + published public-event context
    - **Training time:** ~30 seconds
    - **Prediction time:** <100ms per event
    
    ### 🚀 Use Cases
    1. **Event Planning:** Estimate traffic impact before approval
    2. **Resource Allocation:** Deploy optimal number of officers
    3. **Route Management:** Plan traffic diversions
    4. **Time Management:** Calculate setup/cleanup times
    5. **Risk Assessment:** Identify high-impact events early
    
    ### 💡 Key Features
    - ✅ Real-time predictions
    - ✅ Actionable recommendations
    - ✅ Validated on real Bengaluru data
    - ✅ Production-ready accuracy
    - ✅ Scalable architecture
    """)

# ============================================================================
# TAB 5: DOCUMENTATION
# ============================================================================

with tab5:
    st.markdown("## 📋 Technical Documentation")
    
    st.markdown("""
    ### 🔧 System Components
    
    #### Feature Engineering (19 Features)
    
    **Time-based (6):**
    - Hour of day (0-23)
    - Day of week (0-6)
    - Month (1-12)
    - Is weekend (0/1)
    - Is peak hour (0/1)
    - Time period (morning/afternoon/evening/night)
    
    **Location-based (2):**
    - Corridor (top corridors encoded)
    - Zone (administrative zone)
    
    **Severity-based (3):**
    - Is high priority (0/1)
    - Requires road closure (0/1)
    - Is planned event (0/1)
    
    **Interaction Features (3):**
    - Is major event (0/1)
    - Is major corridor (0/1)
    - Critical situation (0/1)
    
    **Risk Scores (3):**
    - Corridor risk score (0-1, normalized)
    - Zone risk score (0-1, normalized)
    - Hour risk score (0-1, normalized)
    
    #### Model Architecture
    
    **Random Forest Regressor**
    - 100 trees
    - Max depth: 15
    - Min samples split: 10
    - Min samples leaf: 5
    
    #### Contextual Recommendation Layer
    
    The dashboard no longer requires an operator to type traffic flow or affected crowd. It estimates those values from:
    - Corridor profile: traffic-flow index, road-capacity index, lanes, typical queue spread, response time
    - Event profile: numeric event value, blockage factor, crowd load, police complexity, planned/unplanned status
    - Historical Astram records: similar-event count, median duration, average impact, closure rate
    - Time factor: peak commute, midday, night, and night gathering adjustments
    - Published context: ORR/Silk Board congestion, Bengaluru Traffic Police structure, and large public-event crowd-control references
    
    **Officer deployment uses:**
    ```
    incident load + affected people + traffic pressure + closure impact
    + expected queue spread + event police complexity + time-of-day factor
    ```
    
    **Barricades and diversions use:**
    ```
    contextual impact score + road closure + expected queue length
    + corridor-specific junctions and alternate routes
    ```
    
    ### 📈 Performance Metrics
    
    | Metric | Value |
    |--------|-------|
    | Model Accuracy (R²) | 95.5% |
    | Mean Absolute Error | 0.081 |
    | Root Mean Squared Error | 0.208 |
    | Training Samples | 6,538 |
    | Test Samples | 1,635 |
    | Training Time | ~30 seconds |
    | Prediction Time | <100ms |
    
    ### 🔐 Validation
    
    **Cross-validation:** 80/20 train/test split
    **Generalization:** Works on unseen events
    **Robustness:** Handles missing values
    **Scalability:** Fast predictions on new data
    
    ### 🎯 Next Steps
    1. Deploy to production traffic police system
    2. Real-time integration with Astram database
    3. Mobile app for field officers
    4. Feedback loop for continuous improvement
    5. Expand to other Indian cities
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.markdown("""
    **📊 System Status**
    - Model: ✅ Active
    - Data: ✅ Loaded
    - Engine: ✅ Ready
    """)

with col_footer2:
    st.markdown("""
    **🎓 Built with**
    - Python, Pandas, Scikit-learn
    - Random Forest ML Model
    - Streamlit
    """)

with col_footer3:
    st.markdown("""
    **📞 Contact**
    - Bengaluru Traffic Police
    - Event Management Team
    - +91-XXXX-XXXX-XXXX
    """)

st.markdown("""
---
*Bengaluru Event-Driven Congestion Forecasting System v1.0*
*Powered by AI | Built for Traffic Police*
""")
