"""
Pilot Trip Scheduling Analysis - Streamlit App
Analyzes trip scheduling data for airline pilot bids
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime
import analysis_engine
import rps_parser
import hashlib

# Page config
st.set_page_config(
    page_title="Pilot Trip Analysis",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Password Protection
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        if "APP_PASSWORD" in st.secrets:
            correct_password = st.secrets["APP_PASSWORD"]
        else:
            correct_password = "pilot2026"
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("# 🔒 Pilot Trip Scheduling Analysis")
        st.markdown("### Please enter the password to access the application")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.info("💡 Contact your administrator for the access password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("# 🔒 Pilot Trip Scheduling Analysis")
        st.markdown("### Please enter the password to access the application")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect. Please try again.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ── Dark / Light mode CSS injection ──────────────────────────────────────────
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown("""
    <style>
    .stApp, .stApp > header, [data-testid="stAppViewContainer"] {
        background-color: #0e1117 !important; color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: #161b27 !important; color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] .stMarkdown {
        color: #c0c8d8 !important;
    }
    [data-testid="stSelectbox"] > div > div, [data-baseweb="select"] > div {
        background-color: #1e2433 !important; border-color: #3a4560 !important; color: #e0e0e0 !important;
    }
    [data-baseweb="select"] span, [data-baseweb="select"] div {
        color: #e0e0e0 !important; background-color: transparent !important;
    }
    [data-baseweb="popover"] ul, [data-baseweb="menu"] {
        background-color: #1e2433 !important; border-color: #3a4560 !important;
    }
    [data-baseweb="menu"] li { background-color: #1e2433 !important; color: #e0e0e0 !important; }
    [data-baseweb="menu"] li:hover { background-color: #2a3550 !important; }
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea,
    input[type="text"], input[type="password"], textarea {
        background-color: #1e2433 !important; color: #e0e0e0 !important; border-color: #3a4560 !important;
    }
    [data-baseweb="input"], [data-baseweb="textarea"] {
        background-color: #1e2433 !important; border-color: #3a4560 !important;
    }
    [data-testid="stNumberInput"] input {
        background-color: #1e2433 !important; color: #e0e0e0 !important; border-color: #3a4560 !important;
    }
    [data-testid="metric-container"] {
        background-color: #1a2035 !important; border-radius: 8px !important; padding: 12px !important;
    }
    [data-testid="metric-container"] label,
    [data-testid="metric-container"] [data-testid="stMetricLabel"] p { color: #8899bb !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e8eeff !important; }
    [data-testid="stExpander"] { background-color: #161b27 !important; border-color: #2a3550 !important; }
    [data-testid="stExpander"] summary { color: #c0c8d8 !important; }
    [data-baseweb="tab-list"] { background-color: #161b27 !important; }
    [data-baseweb="tab"] { color: #8899bb !important; }
    [aria-selected="true"][data-baseweb="tab"] { color: #4da6ff !important; border-bottom-color: #4da6ff !important; }
    [data-testid="stDataFrame"] iframe { filter: invert(0.88) hue-rotate(180deg); }
    p, h1, h2, h3, h4, label, .stMarkdown { color: #e0e0e0 !important; }
    [data-baseweb="checkbox"] span { border-color: #4da6ff !important; background-color: #1e2433 !important; }
    [data-testid="stAlert"] { background-color: #1a2035 !important; color: #e0e0e0 !important; }
    [data-testid="stForm"] { background-color: #161b27 !important; border-color: #2a3550 !important; }
    [data-testid="stRadio"] label { color: #c0c8d8 !important; }
    [data-testid="stCode"], code, pre { background-color: #0d1117 !important; color: #79c0ff !important; }
    hr { border-color: #2a3550 !important; }
    </style>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def build_export_filename(prefix, fdata_list, ext="pdf"):
    if len(fdata_list) == 1:
        fd = fdata_list[0]
        parts = [prefix, fd.get('month', 'Unknown'), str(fd.get('year', ''))]
        if fd.get('fleet'):
            parts.append(fd['fleet'].replace(' ', '_'))
        return '_'.join(parts) + f'.{ext}'
    return f"{prefix}_MultiFile_{datetime.now().strftime('%Y%m%d')}.{ext}"

def get_file_hash(content):
    return hashlib.md5(content.encode()).hexdigest()[:8]

def get_rps_data(fleet, base_filter):
    """Return best matching RPS data for the given fleet/base, or None."""
    rps_files = st.session_state.get('rps_files', {})
    if not rps_files:
        return None
    return rps_parser.get_rps_data_for_context(rps_files, fleet, base_filter)

def max_trip_len(results_dict):
    """Find the highest trip length with trips across all result dicts."""
    ml = 5
    for r in results_dict.values():
        for l, c in r['trip_counts'].items():
            if c > 0:
                ml = max(ml, l)
    return ml

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'file_counter' not in st.session_state:
    st.session_state.file_counter = 0

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("✈️ Trip Analysis Settings")

_mode_label = "☀️ Switch to Light Mode" if st.session_state.dark_mode else "🌙 Switch to Dark Mode"
if st.sidebar.button(_mode_label, key='dark_mode_toggle'):
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()
st.sidebar.markdown("---")

time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]]
time_to_minutes = {t: int(t[:2])*60 + int(t[3:]) for t in time_options}

front_end_time = st.sidebar.selectbox(
    "Front End Commutable (Report ≥)", time_options,
    index=time_options.index("10:30"), key='sidebar_front_time'
)
back_end_time = st.sidebar.selectbox(
    "Back End Commutable (Release ≤)", time_options,
    index=time_options.index("18:00"), key='sidebar_back_time'
)
include_short_commute = st.sidebar.checkbox(
    "Include 1-2 Day Trips in Commutability", value=False, key='include_short_commute',
    help="By default, commutability analysis only includes trips 3+ days."
)

st.sidebar.subheader("Base Filter")
base_options = ["All Bases", "ATL", "BOS", "NYC", "DTW", "SLC", "MSP", "SEA", "LAX"]
selected_base = st.sidebar.selectbox("Select Base", base_options, key='sidebar_base')

# ── RPS Comparison ────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("RPS Comparison")
compare_rps = st.sidebar.checkbox(
    "Compare RPS", value=False, key='compare_rps',
    help="Overlay Rotation Preference Survey targets on trip length and commutability data"
)

if compare_rps:
    rps_uploads = st.sidebar.file_uploader(
        "Upload RPS File(s) (.pdf)", type=['pdf'], accept_multiple_files=True,
        key='rps_uploader',
        help="e.g. 202603_320_NoComments.pdf  or  202603_LAX320_NoComments.pdf"
    )
    if rps_uploads:
        if 'rps_files' not in st.session_state:
            st.session_state.rps_files = {}
        for rps_file in rps_uploads:
            if rps_file.name not in st.session_state.rps_files:
                try:
                    parsed = rps_parser.parse_rps_file(rps_file.read(), rps_file.name)
                    st.session_state.rps_files[rps_file.name] = parsed
                    base_label = parsed['base'] or 'All Bases'
                    st.sidebar.success(
                        f"✓ {rps_file.name}\n"
                        f"Fleet: {parsed['fleet']} | Base: {base_label} | "
                        f"Commutable: {parsed['commutable_pct']}%"
                    )
                except Exception as e:
                    st.sidebar.error(f"Parse error: {rps_file.name}\n{e}")

    loaded_rps = st.session_state.get('rps_files', {})
    if loaded_rps:
        st.sidebar.caption(f"{len(loaded_rps)} RPS file(s) loaded")
        if st.sidebar.button("Clear RPS Files", key='clear_rps'):
            st.session_state.rps_files = {}
            st.rerun()

st.sidebar.markdown("---")
if st.session_state.uploaded_files and st.sidebar.button("🔄 Update Analysis", type="secondary", key='sidebar_update'):
    with st.spinner("Updating analysis with new settings..."):
        st.session_state.analysis_results = {}
        st.session_state.detailed_trips = {}
        front_minutes = time_to_minutes[front_end_time]
        back_minutes = time_to_minutes[back_end_time]
        for fname, fdata in st.session_state.uploaded_files.items():
            result = analysis_engine.analyze_file(
                fdata['content'], selected_base, front_minutes, back_minutes,
                include_short_commute, fdata['year']
            )
            st.session_state.analysis_results[fname] = result
        st.success("✅ Analysis updated!")
        st.rerun()

if st.sidebar.button("🗑️ Clear All Data", type="primary", key='sidebar_clear'):
    st.session_state.uploaded_files = {}
    st.session_state.analysis_results = {}
    st.session_state.file_counter = 0
    st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("✈️ Pilot Trip Scheduling Analysis")
st.markdown("Upload trip schedule files to analyze metrics including trip length, credit hours, red-eyes, and commutability.")

st.header("📁 Upload Schedule Files")
col1, col2 = st.columns([3, 1])
with col2:
    st.metric("Files Loaded", len(st.session_state.uploaded_files))
    if len(st.session_state.uploaded_files) >= 12:
        st.warning("⚠️ Maximum 12 files")

with col1:
    if len(st.session_state.uploaded_files) < 12:
        uploaded_files = st.file_uploader(
            "Upload trip schedule files (.txt)", type=['txt'], accept_multiple_files=True,
            key=f'file_uploader_{st.session_state.file_counter}'
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                content = uploaded_file.read().decode('utf-8')
                file_hash = get_file_hash(content)
                already_exists = False
                for existing_name, existing_data in st.session_state.uploaded_files.items():
                    if get_file_hash(existing_data['content']) == file_hash:
                        already_exists = True
                        st.warning(f"⚠️ File '{uploaded_file.name}' (same content) already uploaded as '{existing_name}'")
                        break
                if not already_exists:
                    with st.form(key=f'date_form_{file_hash}'):
                        st.subheader(f"📅 Set Date for: {uploaded_file.name}")
                        col_m, col_y = st.columns(2)
                        with col_m:
                            month = st.selectbox("Month", [
                                "January","February","March","April","May","June",
                                "July","August","September","October","November","December"
                            ], index=0)
                        with col_y:
                            year = st.number_input("Year", min_value=2020, max_value=2030, value=2026)
                        fleet = st.text_input("Fleet (optional)", placeholder="e.g., 320, 737, A220",
                                              help="Add a fleet identifier to differentiate files for the same month")
                        submitted = st.form_submit_button("✅ Add File")
                        if submitted:
                            base_name = uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name
                            extension = uploaded_file.name.rsplit('.', 1)[1] if '.' in uploaded_file.name else 'txt'
                            month_num = {
                                'January':'01','February':'02','March':'03','April':'04',
                                'May':'05','June':'06','July':'07','August':'08',
                                'September':'09','October':'10','November':'11','December':'12'
                            }[month]
                            if fleet:
                                new_filename = f"{base_name}_{month_num}{year}_{fleet}.{extension}"
                                display_name = f"{month} {year} ({fleet})"
                            else:
                                new_filename = f"{base_name}_{month_num}{year}.{extension}"
                                display_name = f"{month} {year}"
                            st.session_state.uploaded_files[new_filename] = {
                                'content': content, 'month': month, 'year': year,
                                'fleet': fleet if fleet else None,
                                'display_name': display_name, 'original_name': uploaded_file.name
                            }
                            st.session_state.file_counter += 1
                            st.success(f"✅ Added '{uploaded_file.name}' as '{new_filename}'")
                            st.rerun()
    else:
        st.info("Maximum of 12 files reached. Remove files to add more.")

if st.session_state.uploaded_files:
    st.subheader("📋 Loaded Files")
    for fname, fdata in st.session_state.uploaded_files.items():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.text(fdata['display_name'])
        with col2:
            st.text(f"Base: {selected_base}")
        with col3:
            if st.button("❌ Remove", key=f"remove_{fname}_{get_file_hash(fdata['content'])}"):
                del st.session_state.uploaded_files[fname]
                if fname in st.session_state.analysis_results:
                    del st.session_state.analysis_results[fname]
                st.rerun()

if st.session_state.uploaded_files:
    if st.button("🔍 Analyze Data", type="primary", key='analyze_button'):
        with st.spinner("Analyzing trip data..."):
            st.session_state.analysis_results = {}
            front_minutes = time_to_minutes[front_end_time]
            back_minutes = time_to_minutes[back_end_time]
            for fname, fdata in st.session_state.uploaded_files.items():
                result = analysis_engine.analyze_file(
                    fdata['content'], selected_base, front_minutes, back_minutes,
                    include_short_commute, fdata['year']
                )
                st.session_state.analysis_results[fname] = result
            st.success("✅ Analysis complete!")
            st.rerun()

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.analysis_results:
    st.header("📊 Analysis Results")

    if len(st.session_state.analysis_results) == 1:
        fname = list(st.session_state.analysis_results.keys())[0]
        result = st.session_state.analysis_results[fname]
        fdata = st.session_state.uploaded_files[fname]

        st.subheader(f"Analysis: {fdata['display_name']}")
        view_mode = st.radio("View Mode", ["Summary", "Detailed Trip Table"],
                             horizontal=True, key='view_mode_toggle')

        if view_mode == "Summary":
            # AI Chat
            with st.expander("💬 Ask AI About This Analysis", expanded=False):
                st.markdown("Ask questions about the summary statistics and metrics!")
                api_key_summary = None
                if "ANTHROPIC_API_KEY" in st.secrets:
                    api_key_summary = st.secrets["ANTHROPIC_API_KEY"]
                    st.success("✅ Using API key from Streamlit secrets")
                else:
                    api_key_summary = st.text_input(
                        "Anthropic API Key", type="password",
                        key="anthropic_api_key_summary", value=st.session_state.get('saved_api_key', '')
                    )
                    if api_key_summary and api_key_summary != st.session_state.get('saved_api_key', ''):
                        st.session_state.saved_api_key = api_key_summary
                user_question_summary = st.text_area("Your Question",
                    placeholder="e.g., What's the best trip length for maximizing credit per day?",
                    height=80, key="ai_question_summary")
                if st.button("Ask AI", type="primary", key="ask_ai_summary"):
                    if not api_key_summary:
                        st.error("Please enter your Anthropic API key first")
                    elif not user_question_summary:
                        st.error("Please enter a question")
                    else:
                        with st.spinner("Analyzing..."):
                            try:
                                import anthropic
                                summary_data = {
                                    'file': fdata['display_name'],
                                    'total_trips': result['total_trips'],
                                    'avg_trip_length': result['avg_trip_length'],
                                    'avg_credit_per_trip': result['avg_credit_per_trip'],
                                    'avg_credit_per_day': result['avg_credit_per_day'],
                                    'trip_counts_by_length': result['trip_counts'],
                                    'avg_credit_by_length': result['avg_credit_by_length'],
                                    'single_leg_last_day_pct': result['single_leg_pct'],
                                    'redeye_pct': result['redeye_pct'],
                                    'front_end_commutable_pct': result['front_commute_pct'],
                                    'back_end_commutable_pct': result['back_commute_pct']
                                }
                                client = anthropic.Anthropic(api_key=api_key_summary)
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=2000,
                                    messages=[{"role": "user", "content":
                                        f"You are analyzing pilot trip scheduling data.\n\n{summary_data}\n\nQuestion: {user_question_summary}\n\nProvide a helpful, concise answer."}]
                                )
                                st.success("✨ AI Analysis:")
                                st.markdown(message.content[0].text)
                            except ImportError:
                                st.error("❌ Anthropic library not installed.")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

            # ── Metrics row 1 ─────────────────────────────────────────────
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Trips", result['total_trips'])
            with col2:
                st.metric("Avg Trip Length", f"{result['avg_trip_length']:.2f} days")
            with col3:
                st.metric("Avg Credit/Trip", f"{result['avg_credit_per_trip']:.2f} hrs")
            with col4:
                st.metric("Avg Credit/Day", f"{result['avg_credit_per_day']:.2f} hrs")

            # ── Metrics row 2 (Both Ends gets RPS delta if enabled) ───────
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Front-End Commute", f"{result['front_commute_rate']:.1f}%")
            with col2:
                st.metric("Back-End Commute", f"{result['back_commute_rate']:.1f}%")
            with col3:
                both_rate = result['both_commute_rate']
                _rps_m = get_rps_data(fdata.get('fleet'), selected_base) if compare_rps else None
                if _rps_m and _rps_m.get('commutable_pct') is not None:
                    rps_val = _rps_m['commutable_pct']
                    delta = both_rate - rps_val
                    st.metric("Both Ends Commute", f"{both_rate:.1f}%",
                              delta=f"{delta:+.1f}pp vs {rps_val}% RPS",
                              delta_color="normal")
                else:
                    st.metric("Both Ends Commute", f"{both_rate:.1f}%")
            with col4:
                total_cr = result.get('total_credit_hours', 0)
                st.metric("Total Credit (hrs)", f"{total_cr:,.1f}")

            # ── Charts ────────────────────────────────────────────────────
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                "Trip Length", "Single Leg Last Day", "Credit/Trip",
                "Credit/Day", "Commutability", "Red-Eye Trips", "Staffing Heat Map"
            ])

            # Determine max trip length to display
            _ml = max((l for l, c in result['trip_counts'].items() if c > 0), default=5)
            _ml = max(_ml, 5)

            with tab1:
                total_trips_t1 = result['total_trips']
                _trip_counts = [result['trip_counts'].get(i, 0) for i in range(1, _ml + 1)]
                _trip_pcts   = [(c / total_trips_t1 * 100) if total_trips_t1 > 0 else 0 for c in _trip_counts]
                _xlabels     = [f"{i}-day" for i in range(1, _ml + 1)]

                _rps_t1 = get_rps_data(fdata.get('fleet'), selected_base) if compare_rps else None

                if _rps_t1 and _rps_t1.get('trip_length_pct'):
                    _colors, _texts = [], []
                    for _i, (_cnt, _pct) in enumerate(zip(_trip_counts, _trip_pcts)):
                        _day = _i + 1
                        _rv = _rps_t1['trip_length_pct'].get(_day)
                        if _rv is not None:
                            _colors.append('#d62728' if _pct < _rv else '#2ca02c')
                            _texts.append(f"{_cnt}<br>({_pct:.1f}%)<br>({_rv:.2f}% RPS)")
                        else:
                            _colors.append('#1f77b4')
                            _texts.append(f"{_cnt}<br>({_pct:.1f}%)")
                    fig = go.Figure(go.Bar(
                        x=_xlabels, y=_trip_counts, text=_texts,
                        marker_color=_colors, textposition='outside'
                    ))
                    fig.update_layout(
                        title='Trip Length Distribution  (🟢 ≥ RPS target  |  🔴 < RPS target)',
                        xaxis_title='Trip Length', yaxis_title='Number of Trips'
                    )
                else:
                    data = pd.DataFrame({'Length': _xlabels, 'Count': _trip_counts, 'Percentage': _trip_pcts})
                    fig = px.bar(data, x='Length', y='Count',
                                 labels={'Length': 'Trip Length', 'Count': 'Number of Trips'},
                                 title='Trip Length Distribution',
                                 text=[f"{c}<br>({p:.1f}%)" for c, p in zip(_trip_counts, _trip_pcts)])
                    fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, _ml + 1)],
                    'Percentage': [result['single_leg_pct'].get(i, 0) for i in range(1, _ml + 1)]
                })
                fig = px.bar(data, x='Length', y='Percentage', title='Trips with Single Leg on Last Day (%)')
                st.plotly_chart(fig, use_container_width=True)

            with tab3:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, _ml + 1)],
                    'Hours': [result['avg_credit_by_length'].get(i, 0) for i in range(1, _ml + 1)]
                })
                fig = px.bar(data, x='Length', y='Hours', title='Average Credit Hours per Trip')
                st.plotly_chart(fig, use_container_width=True)

            with tab4:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, _ml + 1)],
                    'Hours/Day': [result['avg_credit_per_day_by_length'].get(i, 0) for i in range(1, _ml + 1)]
                })
                fig = px.bar(data, x='Length', y='Hours/Day', title='Average Credit Hours per Day')
                st.plotly_chart(fig, use_container_width=True)

            with tab5:
                _lbls = [f"{i}-day" for i in range(1, _ml + 1)]
                data = pd.DataFrame({
                    'Length': _lbls * 3,
                    'Percentage': (
                        [result['front_commute_pct'].get(i, 0) for i in range(1, _ml + 1)] +
                        [result['back_commute_pct'].get(i, 0)  for i in range(1, _ml + 1)] +
                        [result['both_commute_pct'].get(i, 0)  for i in range(1, _ml + 1)]
                    ),
                    'Type': ['Front End'] * _ml + ['Back End'] * _ml + ['Both Ends'] * _ml
                })
                fig = px.bar(data, x='Length', y='Percentage', color='Type',
                             barmode='group', title='Commutability by Trip Length (%)')
                _rps_t5 = get_rps_data(fdata.get('fleet'), selected_base) if compare_rps else None
                if _rps_t5 and _rps_t5.get('commutable_pct') is not None:
                    _rv5 = _rps_t5['commutable_pct']
                    fig.add_hline(y=_rv5, line_dash='dash', line_color='red',
                                  annotation_text=f"RPS: {_rv5}% prefer commutable",
                                  annotation_position='top right')
                st.plotly_chart(fig, use_container_width=True)

            with tab6:
                _tc6 = [result['trip_counts'].get(i, 0) for i in range(1, _ml + 1)]
                _rp6 = [result['redeye_pct'].get(i, 0) for i in range(1, _ml + 1)]
                _rc6 = [int(_tc6[i] * _rp6[i] / 100) for i in range(_ml)]
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, _ml + 1)],
                    'Count': _rc6, 'Percentage': _rp6
                })
                fig = px.bar(data, x='Length', y='Count',
                             labels={'Length': 'Trip Length', 'Count': 'Number of Trips with Red-Eye'},
                             title='Trips Containing Red-Eye Flight by Trip Length',
                             text=[f"{c}<br>({p:.1f}%)" for c, p in zip(_rc6, _rp6)])
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with tab7:
                st.markdown("### 📅 Daily Staffing Heat Map")
                st.caption("Shows the number of pilots working each day of the month based on trip operations")
                with st.spinner("Generating staffing heat map..."):
                    heatmap_data = analysis_engine.generate_staffing_heatmap(
                        fdata['content'], fdata['month'], fdata['year'], selected_base
                    )
                dates = heatmap_data['dates']
                pilot_counts = heatmap_data['pilot_counts']
                trip_details = heatmap_data['trip_details']
                day_names = [d.strftime('%a') for d in dates]
                day_numbers = [d.day for d in dates]
                x_labels = [f"{day}<br>{dow}" for day, dow in zip(day_numbers, day_names)]
                cell_text = [[str(count) if count > 0 else "" for count in pilot_counts]]

                import numpy as np
                non_zero_counts = [c for c in pilot_counts if c > 0]
                color_max = int(np.percentile(non_zero_counts, 95)) if non_zero_counts else 1

                fig = go.Figure(data=go.Heatmap(
                    z=[pilot_counts], x=x_labels, y=['Pilots Working'],
                    text=cell_text, texttemplate='<b>%{text}</b>',
                    textfont={"size": 14, "color": "white"},
                    hovertemplate='<b>Day %{customdata[0]}</b><br>Pilots: %{z}<br><br>%{customdata[1]}<extra></extra>',
                    colorscale='Blues', zmin=0, zmax=color_max,
                    colorbar=dict(title="Pilot<br>Count"),
                    customdata=[[f"{day_numbers[i]} ({day_names[i]})", trip_details[i]] for i in range(len(dates))]
                ))
                fig.update_layout(
                    title=f"Daily Pilot Operations - {heatmap_data['month']} {heatmap_data['year']}",
                    xaxis_title="", yaxis_title="", height=300,
                    xaxis=dict(tickmode='array', tickvals=list(range(len(x_labels))),
                               ticktext=x_labels, tickangle=0, side='bottom'),
                    yaxis=dict(showticklabels=False)
                )
                st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Peak Day", f"{max(pilot_counts)} pilots" if pilot_counts else "N/A")
                with col2:
                    avg_pilots = sum(pilot_counts) / len(pilot_counts) if pilot_counts else 0
                    st.metric("Avg Daily", f"{avg_pilots:.1f} pilots")
                with col3:
                    days_with_ops = sum(1 for c in pilot_counts if c > 0)
                    st.metric("Days with Ops", f"{days_with_ops}/{len(pilot_counts)}")
                with col4:
                    st.metric("Total Pilot-Days", sum(pilot_counts))

                if pilot_counts:
                    max_idx = pilot_counts.index(max(pilot_counts))
                    peak_date = dates[max_idx]
                    st.info(f"📊 **Peak Operations:** {peak_date.strftime('%A, %B %d, %Y')} with {pilot_counts[max_idx]} pilots working")

                st.markdown("---")
                st.markdown("### 📊 Reserve vs Operations Correlation Analysis")
                st.caption("Compare required reserve levels with daily pilot operations to identify staffing patterns")
                with st.expander("📥 Enter Reserve Data for Correlation Analysis", expanded=False):
                    st.markdown("**Instructions:** Enter the required reserve count for each day.\n\nFormat: `03FEB,39` (one per line)")
                    bulk_input = st.text_area("Paste reserve data",
                        placeholder="Example:\n03FEB,39\n04FEB,40\n05FEB,42",
                        height=150, key='reserve_bulk_input')
                    if st.button("📊 Analyze Reserve Correlation", type="primary"):
                        if bulk_input.strip():
                            try:
                                reserve_data = {}
                                month_abbr_map = {
                                    'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,
                                    'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12
                                }
                                month_map = {
                                    'January':1,'February':2,'March':3,'April':4,
                                    'May':5,'June':6,'July':7,'August':8,
                                    'September':9,'October':10,'November':11,'December':12
                                }
                                for line in bulk_input.strip().split('\n'):
                                    line = line.strip()
                                    if not line or ',' not in line:
                                        continue
                                    parts = line.split(',')
                                    if len(parts) >= 2:
                                        date_str = parts[0].strip().upper()
                                        required = int(parts[1].strip())
                                        match = re.match(r'(\d{1,2})([A-Z]{3})', date_str)
                                        if match:
                                            day = int(match.group(1))
                                            month_abbr = match.group(2)
                                            month_num = month_abbr_map.get(month_abbr)
                                            if month_num == month_map.get(fdata['month']):
                                                reserve_data[datetime(fdata['year'], month_num, day)] = required
                                if reserve_data:
                                    matched_dates, reserve_required, pilots_on_duty = [], [], []
                                    for date in dates:
                                        if date in reserve_data:
                                            matched_dates.append(date)
                                            reserve_required.append(reserve_data[date])
                                            pilots_on_duty.append(pilot_counts[dates.index(date)])
                                    if len(matched_dates) >= 3:
                                        correlation = np.corrcoef(reserve_required, pilots_on_duty)[0, 1]
                                        st.success(f"✅ Analysis complete! Found {len(matched_dates)} matching dates.")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Correlation Coefficient", f"{correlation:.3f}")
                                        with col2:
                                            strength = "Strong" if abs(correlation) > 0.7 else "Moderate" if abs(correlation) > 0.4 else "Weak"
                                            st.metric("Relationship Strength", strength)
                                        with col3:
                                            st.metric("Direction", "Positive" if correlation > 0 else "Negative")
                                        scatter_df = pd.DataFrame({
                                            'Pilots on Duty': pilots_on_duty,
                                            'Reserves Required': reserve_required,
                                            'Date': [d.strftime('%b %d') for d in matched_dates],
                                            'Day of Week': [d.strftime('%a') for d in matched_dates]
                                        })
                                        fig = px.scatter(scatter_df, x='Pilots on Duty', y='Reserves Required',
                                                         hover_data=['Date','Day of Week'],
                                                         title='Reserve Requirements vs Pilot Operations',
                                                         trendline='ols')
                                        fig.update_traces(marker=dict(size=10))
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.warning(f"⚠️ Only found {len(matched_dates)} matching dates. Need at least 3.")
                                else:
                                    st.error("❌ No valid reserve data found.")
                            except Exception as e:
                                st.error(f"❌ Error parsing reserve data: {str(e)}")
                        else:
                            st.warning("⚠️ Please enter reserve data to analyze.")

        else:
            # DETAILED TRIP TABLE VIEW
            if 'detailed_trips' not in st.session_state:
                st.session_state.detailed_trips = {}
            if fname not in st.session_state.detailed_trips:
                with st.spinner("Loading detailed trip data..."):
                    detailed_trips = analysis_engine.get_detailed_trips(
                        fdata['content'], selected_base, fdata['month'], fdata['year']
                    )
                    st.session_state.detailed_trips[fname] = detailed_trips
            trips = st.session_state.detailed_trips[fname]

            if 'trip_filters' not in st.session_state:
                st.session_state.trip_filters = {
                    'trip_length': 'All', 'report_start': '00:00', 'report_end': '23:59',
                    'release_start': '00:00', 'release_end': '23:59', 'search_term': '',
                    'sort_column': None, 'sort_ascending': True
                }

            st.markdown("### Filters")
            filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6, filter_col7 = st.columns([1, 1.5, 1.5, 1, 1, 1, 0.5])
            with filter_col1:
                trip_length_filter = st.selectbox("Trip Length",
                    ['All','1-day','2-day','3-day','4-day','5-day','6-day','7-day'],
                    key='filter_trip_length')
            with filter_col2:
                time_options_f = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]]
                time_options_f.append("23:59")
                col_a, col_b = st.columns(2)
                with col_a:
                    report_start = st.selectbox("Report Start", time_options_f, index=0, key='filter_report_start')
                with col_b:
                    report_end = st.selectbox("Report End", time_options_f, index=len(time_options_f)-1, key='filter_report_end')
            with filter_col3:
                col_a, col_b = st.columns(2)
                with col_a:
                    release_start = st.selectbox("Release Start", time_options_f, index=0, key='filter_release_start')
                with col_b:
                    release_end = st.selectbox("Release End", time_options_f, index=len(time_options_f)-1, key='filter_release_end')
            with filter_col4:
                search_term = st.text_input("Search Trip #", key='filter_search', placeholder="e.g., 44")
            with filter_col5:
                num_legs_filter = st.selectbox("Number of Legs",
                    ['All','2','3','4','5','6','7','8','9','10+'], key='filter_num_legs')
            with filter_col6:
                credit_filter = st.selectbox("Credit",
                    ['All','Hard Block','<15 minutes','15-30 minutes','30-60 minutes','>60 minutes'],
                    key='filter_credit')
            with filter_col7:
                st.write("")
                st.write("")
                if st.button("🔄 Clear", key='clear_filters'):
                    if fname in st.session_state.detailed_trips:
                        del st.session_state.detailed_trips[fname]
                    keys_to_delete = [
                        'filter_trip_length','filter_report_start','filter_report_end',
                        'filter_release_start','filter_release_end','filter_search',
                        'filter_num_legs','filter_credit','filter_one_leg_home',
                        'filter_has_sit','filter_has_edp','filter_has_hol',
                        'filter_has_carve','filter_has_redeye','filter_last_leg_dh',
                        'filter_mid_rotation_redeye','trip_select_all'
                    ]
                    for key in keys_to_delete:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

            st.markdown("#### Additional Filters")
            checkbox_col1, checkbox_col2, checkbox_col3, checkbox_col4, checkbox_col5, checkbox_col6 = st.columns(6)
            with checkbox_col1:
                one_leg_home = st.checkbox("One Leg Home Last Day", key='filter_one_leg_home')
            with checkbox_col2:
                has_sit = st.checkbox("Has SIT Pay", key='filter_has_sit')
            with checkbox_col3:
                has_edp = st.checkbox("Has EDP", key='filter_has_edp')
            with checkbox_col4:
                has_hol = st.checkbox("Has Holiday Pay", key='filter_has_hol')
            with checkbox_col5:
                has_carve = st.checkbox("Has CARVE Pay", key='filter_has_carve')
            with checkbox_col6:
                has_redeye = st.checkbox("Has Red-Eye", key='filter_has_redeye')

            dh_col1, dh_col2 = st.columns(6)[:2]
            with dh_col1:
                last_leg_dh_filter = st.checkbox("Last Leg DH", key='filter_last_leg_dh',
                    help="Show only trips where the final flight leg is a Deadhead (DH)")
            with dh_col2:
                mid_rotation_redeye_filter = st.checkbox("First/Mid-Rotation Red-Eye",
                    key='filter_mid_rotation_redeye',
                    help="Show only trips with a red-eye flight NOT on the last day")

            # Apply filters
            filtered_trips = trips.copy()
            if trip_length_filter != 'All':
                length = int(trip_length_filter.split('-')[0])
                filtered_trips = [t for t in filtered_trips if t['length'] == length]

            def time_to_minutes_local(time_str):
                h, m = map(int, time_str.split(':'))
                return h * 60 + m

            report_start_min = time_to_minutes_local(report_start)
            report_end_min   = time_to_minutes_local(report_end)
            filtered_trips = [t for t in filtered_trips
                              if t['report_time_minutes'] is not None
                              and report_start_min <= t['report_time_minutes'] <= report_end_min]

            release_start_min = time_to_minutes_local(release_start)
            release_end_min   = time_to_minutes_local(release_end)
            filtered_trips = [t for t in filtered_trips
                              if t['release_time_minutes'] is not None
                              and release_start_min <= t['release_time_minutes'] <= release_end_min]

            if search_term:
                filtered_trips = [t for t in filtered_trips
                                  if t['trip_number'] and search_term in str(t['trip_number'])]
            if num_legs_filter != 'All':
                if num_legs_filter == '10+':
                    filtered_trips = [t for t in filtered_trips if t['total_legs'] >= 10]
                else:
                    filtered_trips = [t for t in filtered_trips if t['total_legs'] == int(num_legs_filter)]
            if credit_filter != 'All':
                if credit_filter == 'Hard Block':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and t.get('credit_minutes') == 0]
                elif credit_filter == '<15 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 0 < t.get('credit_minutes') < 15]
                elif credit_filter == '15-30 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 15 <= t.get('credit_minutes') <= 30]
                elif credit_filter == '30-60 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 30 < t.get('credit_minutes') <= 60]
                elif credit_filter == '>60 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and t.get('credit_minutes') > 60]
            if one_leg_home:
                filtered_trips = [t for t in filtered_trips if t.get('last_day_legs') == 1]
            if has_sit:
                filtered_trips = [t for t in filtered_trips if t.get('sit') is not None and t.get('sit') > 0]
            if has_edp:
                filtered_trips = [t for t in filtered_trips if t.get('edp') is not None and t.get('edp') > 0]
            if has_hol:
                filtered_trips = [t for t in filtered_trips if t.get('hol') is not None and t.get('hol') > 0]
            if has_carve:
                filtered_trips = [t for t in filtered_trips if t.get('carve') is not None and t.get('carve') > 0]
            if has_redeye:
                filtered_trips = [t for t in filtered_trips if t.get('has_redeye') == True]
            if last_leg_dh_filter:
                filtered_trips = [t for t in filtered_trips if t.get('last_leg_dh') == True]
            if mid_rotation_redeye_filter:
                filtered_trips = [t for t in filtered_trips if t.get('mid_rotation_redeye') == True]

            total_occurrences = sum(trip.get('occurrences', 1) for trip in filtered_trips)
            st.markdown(f"**Showing {total_occurrences} trips** *({len(filtered_trips)} unique patterns)*")

            # AI Chat
            with st.expander("💬 Ask AI About Your Trips", expanded=False):
                st.markdown("Ask questions about the filtered trips in natural language!")
                api_key = None
                if "ANTHROPIC_API_KEY" in st.secrets:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                    st.success("✅ Using API key from Streamlit secrets")
                else:
                    api_key = st.text_input("Anthropic API Key", type="password",
                        key="anthropic_api_key", value=st.session_state.get('saved_api_key', ''))
                    if api_key and api_key != st.session_state.get('saved_api_key', ''):
                        st.session_state.saved_api_key = api_key
                user_question = st.text_area("Your Question",
                    placeholder="e.g., What are the top 5 trips by credit per day?",
                    height=80, key="ai_question")
                col1, col2 = st.columns(2)
                with col1:
                    ask_ai_btn = st.button("Ask AI", type="primary", use_container_width=True)
                with col2:
                    quick_calc_btn = st.button("⚡ Quick Calculate", use_container_width=True)

                if quick_calc_btn:
                    question_lower = user_question.lower()
                    asking_commutable = any(w in question_lower for w in ['commutable','commute','both ends','both-ends'])
                    asking_weekday_only = any(p in question_lower for p in ['monday-friday','weekday','no weekend','mon-fri','m-f','weekdays only'])
                    if not (asking_commutable and asking_weekday_only):
                        st.warning("Quick Calculate works best for: 'How many trips are both-ends commutable and operate Monday-Friday only?'")
                    else:
                        with st.spinner("Calculating..."):
                            def parse_t(ts):
                                if not ts or ts == 'N/A':
                                    return None
                                try:
                                    p = ts.split(':')
                                    return int(p[0]) * 60 + int(p[1])
                                except:
                                    return None
                            ft = parse_t(front_end_time)
                            bt = parse_t(back_end_time)
                            matching = []
                            for trip in filtered_trips:
                                rm  = parse_t(trip.get('report_time'))
                                rlm = parse_t(trip.get('release_time'))
                                days = trip.get('days_of_week', [])
                                if (rm is not None and ft is not None and rm >= ft and
                                    rlm is not None and bt is not None and rlm <= bt and
                                    'SA' not in days and 'SU' not in days and len(days) > 0):
                                    matching.append(trip)
                            total_occ = sum(t.get('occurrences', 1) for t in matching)
                            by_length = {}
                            for trip in matching:
                                l = trip['length']
                                by_length[l] = by_length.get(l, 0) + trip.get('occurrences', 1)
                            st.success("✨ Quick Answer:")
                            st.markdown(f"**Found {len(matching)} unique patterns ({total_occ} total occurrences)** — both-ends commutable, Monday-Friday only")
                            for l in sorted(by_length.keys()):
                                st.markdown(f"- **{l}-day:** {by_length[l]} occurrences")

                if ask_ai_btn:
                    if not api_key:
                        st.error("Please enter your Anthropic API key first")
                    elif not user_question:
                        st.error("Please enter a question")
                    elif len(filtered_trips) == 0:
                        st.warning("No trips to analyze.")
                    elif len(filtered_trips) > 500:
                        question_key = f"ai_question_{user_question.strip().lower()}"
                        if not st.session_state.get(question_key, False):
                            st.warning(f"⚠️ **{len(filtered_trips)} trips** — AI processes first 500. Filter down or use ⚡ Quick Calculate, then click Ask AI again to proceed.")
                            st.session_state[question_key] = True
                            st.stop()
                    if not (len(filtered_trips) > 500 and not st.session_state.get(f"ai_question_{user_question.strip().lower()}", False)):
                        with st.spinner("Analyzing trips..."):
                            try:
                                import anthropic
                                def parse_t(ts):
                                    if not ts or ts == 'N/A':
                                        return None
                                    try:
                                        p = ts.split(':')
                                        return int(p[0]) * 60 + int(p[1])
                                    except:
                                        return None
                                ft = parse_t(front_end_time)
                                bt = parse_t(back_end_time)
                                trip_summary = []
                                for trip in filtered_trips[:500]:
                                    rm  = parse_t(trip.get('report_time'))
                                    rlm = parse_t(trip.get('release_time'))
                                    trip_summary.append({
                                        'trip_number': trip.get('trip_number','N/A'),
                                        'base': trip['base'], 'length': f"{trip['length']}-day",
                                        'days_of_week': trip.get('days_of_week',[]),
                                        'occurrences': trip.get('occurrences',1),
                                        'report': trip.get('report_time'), 'release': trip.get('release_time'),
                                        'front_end_commutable': rm is not None and ft is not None and rm >= ft,
                                        'back_end_commutable': rlm is not None and bt is not None and rlm <= bt,
                                        'both_ends_commutable': (rm is not None and ft is not None and rm >= ft and
                                                                  rlm is not None and bt is not None and rlm <= bt),
                                        'legs': trip['total_legs'],
                                        'longest_leg': trip.get('longest_leg'), 'shortest_leg': trip.get('shortest_leg'),
                                        'credit': trip.get('total_credit'), 'pay': trip.get('total_pay'),
                                        'sit': trip.get('sit'), 'edp': trip.get('edp'),
                                        'hol': trip.get('hol'), 'carve': trip.get('carve'),
                                        'credit_per_day': trip.get('total_credit',0)/trip['length'] if trip['length']>0 else 0,
                                        'last_day_legs': trip.get('last_day_legs')
                                    })
                                client = anthropic.Anthropic(api_key=api_key)
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514", max_tokens=4000,
                                    messages=[{"role": "user", "content":
                                        f"Pilot trip data (first 500 of {len(filtered_trips)}):\n\n{trip_summary}\n\n"
                                        f"MO=Monday,TU=Tuesday,WE=Wednesday,TH=Thursday,FR=Friday,SA=Saturday,SU=Sunday\n"
                                        f"Sum 'occurrences' for totals.\n\nQuestion: {user_question}"}]
                                )
                                st.success("✨ AI Analysis:")
                                st.markdown(message.content[0].text)
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

            # Trip table
            if filtered_trips:
                if 'selected_trip_index' not in st.session_state:
                    st.session_state.selected_trip_index = None
                if 'trip_select_all' not in st.session_state:
                    st.session_state.trip_select_all = False

                sel_col1, sel_col2, sel_col3 = st.columns([1, 1, 8])
                with sel_col1:
                    if st.button("☑️ Select All", key='btn_select_all'):
                        st.session_state.trip_select_all = True
                        st.rerun()
                with sel_col2:
                    if st.button("☐ Deselect All", key='btn_deselect_all'):
                        st.session_state.trip_select_all = False
                        st.rerun()

                df_data = []
                for i, trip in enumerate(filtered_trips):
                    df_data.append({
                        'Select': st.session_state.trip_select_all,
                        'Trip #': trip['trip_number'] or 'N/A',
                        'Base': trip['base'], 'Length': f"{trip['length']}-day",
                        'Report': trip['report_time'] or 'N/A',
                        'Release': trip['release_time'] or 'N/A',
                        'Legs': trip['total_legs'],
                        'Longest': trip['longest_leg'], 'Shortest': trip['shortest_leg'],
                        'Credit': trip['total_credit'] if trip['total_credit'] is not None else None,
                        'Pay': trip['total_pay'] if trip['total_pay'] is not None else None,
                        'SIT': trip.get('sit'), 'EDP': trip.get('edp'),
                        'HOL': trip.get('hol'), 'CARVE': trip.get('carve'),
                        'Occurs': trip['occurrences']
                    })

                df = pd.DataFrame(df_data)
                edited_df = st.data_editor(
                    df,
                    column_config={
                        'Select': st.column_config.CheckboxColumn('Select', default=False, width='small'),
                        'Trip #': st.column_config.TextColumn('Trip #', width='medium'),
                        'Base': st.column_config.TextColumn('Base', width='small'),
                        'Length': st.column_config.TextColumn('Length', width='small'),
                        'Report': st.column_config.TextColumn('Report', width='small'),
                        'Release': st.column_config.TextColumn('Release', width='small'),
                        'Legs': st.column_config.NumberColumn('Legs', width='small'),
                        'Longest': st.column_config.TextColumn('Longest', width='small'),
                        'Shortest': st.column_config.TextColumn('Shortest', width='small'),
                        'Credit': st.column_config.NumberColumn('Credit', width='small', format="%.2f"),
                        'Pay': st.column_config.NumberColumn('Pay', width='small', format="%.2f"),
                        'SIT': st.column_config.NumberColumn('SIT', width='small', format="%.2f"),
                        'EDP': st.column_config.NumberColumn('EDP', width='small', format="%.2f"),
                        'HOL': st.column_config.NumberColumn('HOL', width='small', format="%.2f"),
                        'CARVE': st.column_config.NumberColumn('CARVE', width='small', format="%.2f"),
                        'Occurs': st.column_config.NumberColumn('Occurs', width='small'),
                    },
                    disabled=['Trip #','Base','Length','Report','Release','Legs','Longest',
                              'Shortest','Credit','Pay','SIT','EDP','HOL','CARVE','Occurs'],
                    hide_index=True, use_container_width=True, height=600, key='trip_table'
                )

                selected_indices = edited_df[edited_df['Select']].index.tolist()
                if selected_indices:
                    st.markdown("---")
                    selected_trip_objects = [filtered_trips[idx] for idx in selected_indices]
                    pdf_settings = (f"Base: {selected_base}  |  Front-End: ≥{front_end_time}  |  "
                                    f"Back-End: ≤{back_end_time}  |  {fdata.get('display_name', '')}")
                    hdr_col1, hdr_col2, hdr_col3 = st.columns([3, 1, 1])
                    with hdr_col1:
                        total_sel_occ = sum(t.get('occurrences', 1) for t in selected_trip_objects)
                        st.markdown(
                            f"### ✈️ Selected Trip Details &nbsp;"
                            f"<span style='font-size:0.85rem;color:grey'>"
                            f"({len(selected_indices)} pattern{'s' if len(selected_indices)!=1 else ''}, "
                            f"{total_sel_occ} occurrence{'s' if total_sel_occ!=1 else ''})</span>",
                            unsafe_allow_html=True
                        )
                    with hdr_col2:
                        try:
                            pdf_bytes = analysis_engine.generate_selected_trips_pdf(
                                selected_trip_objects, display_name=fdata.get('display_name',''),
                                settings_text=pdf_settings
                            )
                            st.download_button(
                                label="📄 Print / Save PDF", data=pdf_bytes,
                                file_name=f"selected_trips_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf", use_container_width=True, key='export_selected_pdf'
                            )
                        except Exception as e:
                            st.error(f"PDF error: {e}")
                    with hdr_col3:
                        txt_content = analysis_engine.generate_selected_trips_txt(selected_trip_objects)
                        st.download_button(
                            label="📋 Export Raw TXT", data=txt_content.encode('utf-8'),
                            file_name=f"selected_trips_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain", use_container_width=True, key='export_selected_txt'
                        )
                    for idx in selected_indices:
                        trip = filtered_trips[idx]
                        with st.expander(f"Trip #{trip['trip_number']} - Full Details", expanded=True):
                            st.code(trip['raw_text'], language=None)
            else:
                st.info("No trips match the current filters.")

    else:
        # ── MULTI-FILE VIEW ───────────────────────────────────────────────────
        st.subheader("📈 Detailed Comparison Analysis")

        month_order_sort = {
            'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
            'July':7,'August':8,'September':9,'October':10,'November':11,'December':12
        }
        sorted_files_metrics = sorted(
            st.session_state.analysis_results.keys(),
            key=lambda f: (st.session_state.uploaded_files[f]['year'],
                           month_order_sort[st.session_state.uploaded_files[f]['month']])
        )
        metric_cols = st.columns(len(sorted_files_metrics))
        for i, fn in enumerate(sorted_files_metrics):
            r  = st.session_state.analysis_results[fn]
            fd = st.session_state.uploaded_files[fn]
            with metric_cols[i]:
                st.markdown(f"**{fd['display_name']}**")
                st.metric("Total Trips", f"{r['total_trips']:,}")
                st.metric("Total Credit (hrs)", f"{r.get('total_credit_hours',0):,.1f}")
        st.markdown("---")

        grouping_mode = st.radio("Display Mode",
            ["Sequential (by date)", "Year-over-Year (by month)"], horizontal=True)

        # AI Chat
        with st.expander("💬 Ask AI About This Comparison", expanded=False):
            api_key_comparison = None
            if "ANTHROPIC_API_KEY" in st.secrets:
                api_key_comparison = st.secrets["ANTHROPIC_API_KEY"]
                st.success("✅ Using API key from Streamlit secrets")
            else:
                api_key_comparison = st.text_input("Anthropic API Key", type="password",
                    key="anthropic_api_key_comparison", value=st.session_state.get('saved_api_key',''))
            user_question_comparison = st.text_area("Your Question",
                placeholder="e.g., Which month should I bid to maximize credit per day?",
                height=80, key="ai_question_comparison")
            if st.button("Ask AI", type="primary", key="ask_ai_comparison"):
                if not api_key_comparison or not user_question_comparison:
                    st.error("Please enter API key and question.")
                else:
                    with st.spinner("Analyzing..."):
                        try:
                            import anthropic
                            comparison_data = {}
                            for fn in st.session_state.analysis_results:
                                fd = st.session_state.uploaded_files[fn]
                                r  = st.session_state.analysis_results[fn]
                                comparison_data[fd['display_name']] = {
                                    'total_trips': r['total_trips'],
                                    'total_credit_hours': r.get('total_credit_hours',0),
                                    'avg_trip_length': r['avg_trip_length'],
                                    'avg_credit_per_trip': r['avg_credit_per_trip'],
                                    'avg_credit_per_day': r['avg_credit_per_day'],
                                    'trip_counts_by_length': r['trip_counts'],
                                    'avg_credit_by_length': r['avg_credit_by_length'],
                                    'redeye_pct': r['redeye_pct'],
                                    'front_end_commutable_pct': r['front_commute_pct'],
                                    'back_end_commutable_pct': r['back_commute_pct']
                                }
                            client = anthropic.Anthropic(api_key=api_key_comparison)
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514", max_tokens=2000,
                                messages=[{"role": "user", "content":
                                    f"Pilot scheduling comparison:\n\n{comparison_data}\n\nQuestion: {user_question_comparison}"}]
                            )
                            st.success("✨ AI Comparison Analysis:")
                            st.markdown(message.content[0].text)
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

        month_order = {
            'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
            'July':7,'August':8,'September':9,'October':10,'November':11,'December':12
        }
        sorted_files = sorted(
            st.session_state.analysis_results.keys(),
            key=lambda f: (st.session_state.uploaded_files[f]['year'],
                           month_order[st.session_state.uploaded_files[f]['month']])
        )
        num_files = len(sorted_files)
        show_differences = (num_files == 2)

        # Determine max trip length across all loaded files
        _global_ml = max_trip_len(st.session_state.analysis_results)

        # Shared RPS lookup helper for multi-file (uses first file's fleet)
        def _multi_rps():
            if not compare_rps or not sorted_files:
                return None
            _fd0 = st.session_state.uploaded_files[sorted_files[0]]
            return get_rps_data(_fd0.get('fleet'), selected_base)

        # Styler for trip-length tables with RPS coloring
        def _apply_rps_style(df, rps_d, ml):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            if rps_d is None or not rps_d.get('trip_length_pct'):
                return styles
            for d in range(1, ml + 1):
                col = f'{d}-day'
                if col not in df.columns:
                    continue
                rv = rps_d['trip_length_pct'].get(d)
                if rv is None:
                    continue
                for i, val in enumerate(df[col]):
                    m = re.search(r'\((\d+\.?\d*)%\)', str(val))
                    if m:
                        actual = float(m.group(1))
                        styles.at[i, col] = 'color: red' if actual < rv else 'color: green'
            return styles

        # ── YEAR-OVER-YEAR MODE ───────────────────────────────────────────
        if grouping_mode == "Year-over-Year (by month)":
            files_by_month = {}
            for fname in sorted_files:
                month = st.session_state.uploaded_files[fname]['month']
                if month not in files_by_month:
                    files_by_month[month] = []
                files_by_month[month].append(fname)

            multi_year_months = {m: fs for m, fs in files_by_month.items()
                                  if isinstance(fs, list) and len(fs) > 1}

            if not multi_year_months:
                st.warning("⚠️ No months with multiple years found.")

            for month in ['January','February','March','April','May','June',
                          'July','August','September','October','November','December']:
                if month not in multi_year_months:
                    continue
                st.markdown(f"## 📅 {month}")
                month_files = multi_year_months[month]

                # Determine max length for this month's files
                _yoy_ml = max(
                    (l for fn in month_files
                     for l, c in st.session_state.analysis_results[fn]['trip_counts'].items() if c > 0),
                    default=5
                )
                _yoy_ml = max(_yoy_ml, 5)

                # RPS for this group
                _yoy_rps = None
                if compare_rps and month_files:
                    _fd0 = st.session_state.uploaded_files[month_files[0]]
                    _yoy_rps = get_rps_data(_fd0.get('fleet'), selected_base)

                # 1. Trip Length
                st.markdown("### 1️⃣ Trip Length Distribution")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        cnt = r['trip_counts'].get(l, 0)
                        pct = (cnt / r['total_trips'] * 100) if r['total_trips'] > 0 else 0
                        if _yoy_rps and l in _yoy_rps.get('trip_length_pct', {}):
                            rps_p = _yoy_rps['trip_length_pct'][l]
                            row[f'{l}-day'] = f"{cnt} ({pct:.2f}%) [{rps_p:.2f}% RPS]"
                        else:
                            row[f'{l}-day'] = f"{cnt} ({pct:.2f}%)"
                    row['Total'] = f"{r['total_trips']} (100%)"
                    data.append(row)
                _df_yoy = pd.DataFrame(data)
                if _yoy_rps and _yoy_rps.get('trip_length_pct'):
                    st.dataframe(_df_yoy.style.apply(lambda df: _apply_rps_style(df, _yoy_rps, _yoy_ml), axis=None),
                                 use_container_width=True, hide_index=True)
                else:
                    st.dataframe(_df_yoy, use_container_width=True, hide_index=True)

                # 2. Single Leg
                st.markdown("### 2️⃣ Single Leg on Last Day")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        row[f'{l}-day'] = f"{r['single_leg_pct'].get(l,0):.2f}%"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                # 3. Credit/Trip
                st.markdown("### 3️⃣ Average Credit per Trip")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        row[f'{l}-day'] = f"{r['avg_credit_by_length'].get(l,0):.2f}"
                    row['Overall'] = f"{r['avg_credit_per_trip']:.2f}"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                # 4. Credit/Day
                st.markdown("### 4️⃣ Average Credit per Day")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        row[f'{l}-day'] = f"{r['avg_credit_per_day_by_length'].get(l,0):.2f}"
                    row['Overall'] = f"{r['avg_credit_per_day']:.2f}"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                # 5. Commutability (Both Ends) with RPS Target column
                st.markdown("### 5️⃣ Commutability (Both Ends)")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        row[f'{l}-day'] = f"{r['both_commute_pct'].get(l,0):.2f}%"
                    row['Overall'] = f"{r['both_commute_rate']:.2f}%"
                    if _yoy_rps and _yoy_rps.get('commutable_pct') is not None:
                        row['RPS Target'] = f"{_yoy_rps['commutable_pct']}%"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                # 6. Red-Eye
                st.markdown("### 6️⃣ Trips Containing Red-Eye Flight")
                data = []
                for fn in month_files:
                    r = st.session_state.analysis_results[fn]
                    row = {'Year': st.session_state.uploaded_files[fn]['display_name']}
                    for l in range(1, _yoy_ml + 1):
                        row[f'{l}-day'] = f"{r['redeye_pct'].get(l,0):.2f}%"
                    row['Overall'] = f"{r['redeye_rate']:.2f}%"
                    total_redeye = sum(r['trip_counts'].get(i,0)*r['redeye_pct'].get(i,0)/100 for i in range(1,_yoy_ml+1))
                    row['Total Red-Eyes'] = f"{int(total_redeye)}"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                st.markdown("---")

        # ── SEQUENTIAL MODE ───────────────────────────────────────────────
        else:
            _rps_seq = _multi_rps()

            # 1. Trip Length Distribution
            st.markdown("### 1️⃣ Trip Length Distribution")
            data = []
            for fname in sorted_files:
                r  = st.session_state.analysis_results[fname]
                row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                for l in range(1, _global_ml + 1):
                    cnt = r['trip_counts'].get(l, 0)
                    pct = (cnt / r['total_trips'] * 100) if r['total_trips'] > 0 else 0
                    if _rps_seq and l in _rps_seq.get('trip_length_pct', {}):
                        rps_p = _rps_seq['trip_length_pct'][l]
                        row[f'{l}-day'] = f"{cnt} ({pct:.2f}%) [{rps_p:.2f}% RPS]"
                    else:
                        row[f'{l}-day'] = f"{cnt} ({pct:.2f}%)"
                row['Total'] = f"{r['total_trips']} (100.00%)"
                data.append(row)
            _df_seq = pd.DataFrame(data)
            if _rps_seq and _rps_seq.get('trip_length_pct'):
                st.dataframe(_df_seq.style.apply(lambda df: _apply_rps_style(df, _rps_seq, _global_ml), axis=None),
                             use_container_width=True, hide_index=True)
            else:
                st.dataframe(_df_seq, use_container_width=True, hide_index=True)

            if show_differences:
                r1 = st.session_state.analysis_results[sorted_files[0]]
                r2 = st.session_state.analysis_results[sorted_files[1]]
                diff = {'Metric': 'Pct Point Diff'}
                for l in range(1, _global_ml + 1):
                    p1 = r1['trip_counts'].get(l,0)/r1['total_trips']*100 if r1['total_trips']>0 else 0
                    p2 = r2['trip_counts'].get(l,0)/r2['total_trips']*100 if r2['total_trips']>0 else 0
                    diff[f'{l}-day'] = f"{p2-p1:+.2f} pts"
                st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)
            st.markdown("---")

            # 2. Single Leg on Last Day
            st.markdown("### 2️⃣ Trips with Single Leg on Last Day")
            data = []
            for fname in sorted_files:
                r  = st.session_state.analysis_results[fname]
                row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                for l in range(1, _global_ml + 1):
                    total = r['trip_counts'].get(l, 0)
                    pct   = r['single_leg_pct'].get(l, 0)
                    cnt   = int(total * pct / 100)
                    row[f'{l}-day'] = f"{cnt} ({pct:.2f}%)"
                total_single = sum(r['trip_counts'].get(i,0)*r['single_leg_pct'].get(i,0)/100 for i in range(1,_global_ml+1))
                overall_pct  = (total_single/r['total_trips']*100) if r['total_trips']>0 else 0
                row['Overall'] = f"{int(total_single)} ({overall_pct:.2f}%)"
                data.append(row)
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            if show_differences:
                r1 = st.session_state.analysis_results[sorted_files[0]]
                r2 = st.session_state.analysis_results[sorted_files[1]]
                diff = {'Metric': 'Difference'}
                for l in range(1, _global_ml + 1):
                    diff[f'{l}-day'] = f"{r2['single_leg_pct'].get(l,0)-r1['single_leg_pct'].get(l,0):+.2f} pts"
                st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)
            st.markdown("---")

            # 3. Average Credit per Trip
            st.markdown("### 3️⃣ Average Credit per Trip (hours)")
            data = []
            for fname in sorted_files:
                r  = st.session_state.analysis_results[fname]
                row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                for l in range(1, _global_ml + 1):
                    row[f'{l}-day'] = f"{r['avg_credit_by_length'].get(l,0):.2f} hrs"
                row['Overall'] = f"{r['avg_credit_per_trip']:.2f} hrs"
                data.append(row)
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            if show_differences:
                r1 = st.session_state.analysis_results[sorted_files[0]]
                r2 = st.session_state.analysis_results[sorted_files[1]]
                diff = {'Metric': 'Difference'}
                for l in range(1, _global_ml + 1):
                    diff[f'{l}-day'] = f"{r2['avg_credit_by_length'].get(l,0)-r1['avg_credit_by_length'].get(l,0):+.2f}"
                diff['Overall'] = f"{r2['avg_credit_per_trip']-r1['avg_credit_per_trip']:+.2f}"
                st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)
            st.markdown("---")

            # 4. Average Credit per Day
            st.markdown("### 4️⃣ Average Credit per Day (hours/day)")
            data = []
            for fname in sorted_files:
                r  = st.session_state.analysis_results[fname]
                row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                for l in range(1, _global_ml + 1):
                    row[f'{l}-day'] = f"{r['avg_credit_per_day_by_length'].get(l,0):.2f}"
                row['Overall'] = f"{r['avg_credit_per_day']:.2f}"
                data.append(row)
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            if show_differences:
                r1 = st.session_state.analysis_results[sorted_files[0]]
                r2 = st.session_state.analysis_results[sorted_files[1]]
                diff = {'Metric': 'Difference'}
                for l in range(1, _global_ml + 1):
                    diff[f'{l}-day'] = f"{r2['avg_credit_per_day_by_length'].get(l,0)-r1['avg_credit_per_day_by_length'].get(l,0):+.2f}"
                diff['Overall'] = f"{r2['avg_credit_per_day']-r1['avg_credit_per_day']:+.2f}"
                st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)
            st.markdown("---")

            # 5. Commutability
            st.markdown("### 5️⃣ Commutability")
            for label, pct_key, rate_key in [
                ("**Front-End:**",  'front_commute_pct', 'front_commute_rate'),
                ("**Back-End:**",   'back_commute_pct',  'back_commute_rate'),
                ("**Both Ends:**",  'both_commute_pct',  'both_commute_rate'),
            ]:
                st.markdown(label)
                data = []
                for fname in sorted_files:
                    r   = st.session_state.analysis_results[fname]
                    row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                    for l in range(1, _global_ml + 1):
                        cnt = int(r['trip_counts'].get(l,0) * r[pct_key].get(l,0) / 100)
                        row[f'{l}-day'] = f"{cnt} ({r[pct_key].get(l,0):.2f}%)"
                    total_c = sum(r['trip_counts'].get(i,0)*r[pct_key].get(i,0)/100 for i in range(1,_global_ml+1))
                    row['Overall'] = f"{int(total_c)} ({r[rate_key]:.2f}%)"
                    # Add RPS Target column only for Both Ends
                    if pct_key == 'both_commute_pct' and _rps_seq and _rps_seq.get('commutable_pct') is not None:
                        row['RPS Target'] = f"{_rps_seq['commutable_pct']}%"
                    data.append(row)
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
                if show_differences:
                    r1 = st.session_state.analysis_results[sorted_files[0]]
                    r2 = st.session_state.analysis_results[sorted_files[1]]
                    diff = {'Metric': 'Difference'}
                    for l in range(1, _global_ml + 1):
                        diff[f'{l}-day'] = f"{r2[pct_key].get(l,0)-r1[pct_key].get(l,0):+.2f} pts"
                    diff['Overall'] = f"{r2[rate_key]-r1[rate_key]:+.2f} pts"
                    st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)
            st.markdown("---")

            # 6. Red-Eye Trips
            st.markdown("### 6️⃣ Trips Containing Red-Eye Flight")
            data = []
            for fname in sorted_files:
                r   = st.session_state.analysis_results[fname]
                row = {'File': st.session_state.uploaded_files[fname]['display_name']}
                for l in range(1, _global_ml + 1):
                    cnt = int(r['trip_counts'].get(l,0) * r['redeye_pct'].get(l,0) / 100)
                    row[f'{l}-day'] = f"{cnt} ({r['redeye_pct'].get(l,0):.2f}%)"
                total_re = int(sum(r['trip_counts'].get(i,0)*r['redeye_pct'].get(i,0)/100 for i in range(1,_global_ml+1)))
                row['Overall'] = f"{total_re} ({r['redeye_rate']:.2f}%)"
                data.append(row)
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            if show_differences:
                r1 = st.session_state.analysis_results[sorted_files[0]]
                r2 = st.session_state.analysis_results[sorted_files[1]]
                diff = {'Metric': 'Difference'}
                for l in range(1, _global_ml + 1):
                    diff[f'{l}-day'] = f"{r2['redeye_pct'].get(l,0)-r1['redeye_pct'].get(l,0):+.2f} pts"
                diff['Overall'] = f"{r2['redeye_rate']-r1['redeye_rate']:+.2f} pts"
                st.dataframe(pd.DataFrame([diff]), use_container_width=True, hide_index=True)

    # ── Export buttons ────────────────────────────────────────────────────────
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("📊 Export Summary/Comparison PDF Report", key='pdf_export'):
            with st.spinner("Generating PDF..."):
                pdf_bytes = analysis_engine.generate_pdf_report(
                    st.session_state.analysis_results, st.session_state.uploaded_files,
                    selected_base, front_end_time, back_end_time
                )
                all_fdata = list(st.session_state.uploaded_files.values())
                summary_filename = build_export_filename("Summary", all_fdata)
                st.download_button(
                    label="⬇️ Download Summary/Comparison PDF", data=pdf_bytes,
                    file_name=summary_filename, mime="application/pdf", key='pdf_download'
                )
    with btn_col2:
        single_file_available = len(st.session_state.uploaded_files) == 1
        if not single_file_available:
            st.info("📋 Comprehensive Base Report available for single-file analysis only.")
        else:
            if st.button("📋 Export Comprehensive Base Report", key='comprehensive_export'):
                with st.spinner("Generating comprehensive report..."):
                    fname = list(st.session_state.uploaded_files.keys())[0]
                    fdata = st.session_state.uploaded_files[fname]
                    pdf_bytes = analysis_engine.generate_comprehensive_base_report(
                        fdata['content'], fdata, selected_base, front_end_time, back_end_time
                    )
                    comp_filename = build_export_filename("Comprehensive", [fdata])
                    st.download_button(
                        label="⬇️ Download Comprehensive Base Report", data=pdf_bytes,
                        file_name=comp_filename, mime="application/pdf", key='comprehensive_download'
                    )

# Footer
st.markdown("---")
st.markdown("✈️ Pilot Trip Scheduling Analysis Tool | Upload up to 12 files for comparison")
st.caption("Version: 67.0 - RPS Comparison | 7-Day Trip Support | 2026-03-31")
