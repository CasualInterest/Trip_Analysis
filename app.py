"""
Pilot Trip Scheduling Analysis - Streamlit App
Analyzes trip scheduling data for airline pilot bids
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import analysis_engine
import hashlib

# Page config
st.set_page_config(
    page_title="Pilot Trip Analysis",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'file_counter' not in st.session_state:
    st.session_state.file_counter = 0

def get_file_hash(content):
    """Generate unique hash for file content"""
    return hashlib.md5(content.encode()).hexdigest()[:8]

# Sidebar
st.sidebar.title("✈️ Trip Analysis Settings")

# Time selectors
st.sidebar.subheader("Commutability Settings")
time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]]
time_to_minutes = {t: int(t[:2])*60 + int(t[3:]) for t in time_options}

front_end_time = st.sidebar.selectbox(
    "Front End Commutable (Report ≥)",
    time_options,
    index=time_options.index("10:30"),
    key='sidebar_front_time'
)

back_end_time = st.sidebar.selectbox(
    "Back End Commutable (Release ≤)",
    time_options,
    index=time_options.index("18:00"),
    key='sidebar_back_time'
)

# Base filter
st.sidebar.subheader("Base Filter")
base_options = ["All Bases", "ATL", "BOS", "NYC", "DTW", "SLC", "MSP", "SEA", "LAX"]
selected_base = st.sidebar.selectbox("Select Base", base_options, key='sidebar_base')

# Update Analysis button
st.sidebar.markdown("---")
if st.session_state.uploaded_files and st.sidebar.button("🔄 Update Analysis", type="secondary", key='sidebar_update'):
    with st.spinner("Updating analysis with new settings..."):
        st.session_state.analysis_results = {}
        st.session_state.detailed_trips = {}  # Clear detailed trips cache too
        
        front_minutes = time_to_minutes[front_end_time]
        back_minutes = time_to_minutes[back_end_time]
        
        for fname, fdata in st.session_state.uploaded_files.items():
            result = analysis_engine.analyze_file(
                fdata['content'],
                selected_base,
                front_minutes,
                back_minutes
            )
            st.session_state.analysis_results[fname] = result
        
        st.success("✅ Analysis updated!")
        st.rerun()

# Clear button
if st.sidebar.button("🗑️ Clear All Data", type="primary", key='sidebar_clear'):
    st.session_state.uploaded_files = {}
    st.session_state.analysis_results = {}
    st.session_state.file_counter = 0
    st.rerun()

# Main title
st.title("✈️ Pilot Trip Scheduling Analysis")
st.markdown("Upload trip schedule files to analyze metrics including trip length, credit hours, red-eyes, and commutability.")

# File upload section
st.header("📁 Upload Schedule Files")

# Show current file count
col1, col2 = st.columns([3, 1])
with col2:
    st.metric("Files Loaded", len(st.session_state.uploaded_files))
    if len(st.session_state.uploaded_files) >= 12:
        st.warning("⚠️ Maximum 12 files")

# File uploader with form to avoid key conflicts
with col1:
    if len(st.session_state.uploaded_files) < 12:
        uploaded_files = st.file_uploader(
            "Upload trip schedule files (.txt)",
            type=['txt'],
            accept_multiple_files=True,
            key=f'file_uploader_{st.session_state.file_counter}'
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Read content immediately
                content = uploaded_file.read().decode('utf-8')
                file_hash = get_file_hash(content)
                
                # Check if this exact file content is already uploaded
                already_exists = False
                for existing_name, existing_data in st.session_state.uploaded_files.items():
                    if get_file_hash(existing_data['content']) == file_hash:
                        already_exists = True
                        st.warning(f"⚠️ File '{uploaded_file.name}' (same content) already uploaded as '{existing_name}'")
                        break
                
                # Also check if there's a pending form for this exact content
                if not already_exists:
                    # Show date selection form
                    with st.form(key=f'date_form_{file_hash}'):
                        st.subheader(f"📅 Set Date for: {uploaded_file.name}")
                        
                        col_m, col_y = st.columns(2)
                        with col_m:
                            month = st.selectbox(
                                "Month",
                                ["January", "February", "March", "April", "May", "June",
                                 "July", "August", "September", "October", "November", "December"],
                                index=0
                            )
                        with col_y:
                            year = st.number_input(
                                "Year",
                                min_value=2020,
                                max_value=2030,
                                value=2026
                            )
                        
                        # Fleet field (optional)
                        fleet = st.text_input(
                            "Fleet (optional)",
                            placeholder="e.g., 320, 737, A220",
                            help="Add a fleet identifier to differentiate files for the same month"
                        )
                        
                        submitted = st.form_submit_button("✅ Add File")
                        
                        if submitted:
                            # Create unique filename based on date and optional fleet
                            # Extract base name without extension
                            base_name = uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name
                            extension = uploaded_file.name.rsplit('.', 1)[1] if '.' in uploaded_file.name else 'txt'
                            
                            # Create new filename: basename_MMYYYY_fleet.ext or basename_MMYYYY.ext
                            month_num = {
                                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                                'September': '09', 'October': '10', 'November': '11', 'December': '12'
                            }[month]
                            
                            if fleet:
                                new_filename = f"{base_name}_{month_num}{year}_{fleet}.{extension}"
                                display_name = f"{month} {year} ({fleet})"
                            else:
                                new_filename = f"{base_name}_{month_num}{year}.{extension}"
                                display_name = f"{month} {year}"
                            
                            # Add to uploaded files with new filename
                            st.session_state.uploaded_files[new_filename] = {
                                'content': content,
                                'month': month,
                                'year': year,
                                'fleet': fleet if fleet else None,
                                'display_name': display_name,
                                'original_name': uploaded_file.name
                            }
                            st.session_state.file_counter += 1
                            st.success(f"✅ Added '{uploaded_file.name}' as '{new_filename}'")
                            st.rerun()
    else:
        st.info("Maximum of 12 files reached. Remove files to add more.")

# Display loaded files
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

# Run analysis button
if st.session_state.uploaded_files:
    if st.button("🔍 Analyze Data", type="primary", key='analyze_button'):
        with st.spinner("Analyzing trip data..."):
            st.session_state.analysis_results = {}
            
            front_minutes = time_to_minutes[front_end_time]
            back_minutes = time_to_minutes[back_end_time]
            
            for fname, fdata in st.session_state.uploaded_files.items():
                result = analysis_engine.analyze_file(
                    fdata['content'],
                    selected_base,
                    front_minutes,
                    back_minutes
                )
                st.session_state.analysis_results[fname] = result
            
            st.success("✅ Analysis complete!")
            st.rerun()

# Display results
if st.session_state.analysis_results:
    st.header("📊 Analysis Results")
    
    if len(st.session_state.analysis_results) == 1:
        # Single file - show summary or detailed view based on toggle
        fname = list(st.session_state.analysis_results.keys())[0]
        result = st.session_state.analysis_results[fname]
        fdata = st.session_state.uploaded_files[fname]
        
        st.subheader(f"Analysis: {fdata['display_name']}")
        
        # View toggle
        view_mode = st.radio(
            "View Mode",
            ["Summary", "Detailed Trip Table"],
            horizontal=True,
            key='view_mode_toggle'
        )
        
        if view_mode == "Summary":
            # AI Chat Section for Summary View
            with st.expander("💬 Ask AI About This Analysis", expanded=False):
                st.markdown("Ask questions about the summary statistics and metrics!")
                st.markdown("*Examples: 'What does this data tell me?', 'Are 3-days or 4-days better for credit?'*")
                
                # Try to get API key from secrets, then from session state, then from user input
                api_key_summary = None
                if "ANTHROPIC_API_KEY" in st.secrets:
                    api_key_summary = st.secrets["ANTHROPIC_API_KEY"]
                    st.success("✅ Using API key from Streamlit secrets")
                else:
                    # API Key input
                    api_key_summary = st.text_input(
                        "Anthropic API Key",
                        type="password",
                        help="Get your API key at https://console.anthropic.com, or save it in Settings > Secrets as ANTHROPIC_API_KEY",
                        key="anthropic_api_key_summary",
                        value=st.session_state.get('saved_api_key', '')
                    )
                    
                    if api_key_summary and api_key_summary != st.session_state.get('saved_api_key', ''):
                        st.session_state.saved_api_key = api_key_summary
                        st.info("💡 API key saved for this session. To save permanently, add it to Streamlit Settings > Secrets")
                
                # Question input
                user_question_summary = st.text_area(
                    "Your Question",
                    placeholder="e.g., What's the best trip length for maximizing credit per day?",
                    height=80,
                    key="ai_question_summary"
                )
                
                if st.button("Ask AI", type="primary", key="ask_ai_summary"):
                    if not api_key_summary:
                        st.error("Please enter your Anthropic API key first")
                    elif not user_question_summary:
                        st.error("Please enter a question")
                    else:
                        with st.spinner("Analyzing..."):
                            try:
                                import anthropic
                                
                                # Prepare summary data for AI
                                summary_data = {
                                    'file': fdata['display_name'],
                                    'total_trips': result['total_trips'],
                                    'avg_trip_length': result['avg_trip_length'],
                                    'avg_credit_per_trip': result['avg_credit_per_trip'],
                                    'avg_credit_per_day': result['avg_credit_per_day'],
                                    'trip_counts_by_length': result['trip_counts'],
                                    'avg_credit_by_length': result['avg_credit_by_length'],
                                    'avg_credit_per_day_by_length': result['avg_credit_per_day_by_length'],
                                    'single_leg_last_day_pct': result['single_leg_pct'],
                                    'redeye_pct': result['redeye_pct'],
                                    'front_end_commutable_pct': result['front_commute_pct'],
                                    'back_end_commutable_pct': result['back_commute_pct']
                                }
                                
                                # Call Claude API
                                client = anthropic.Anthropic(api_key=api_key_summary)
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=2000,
                                    messages=[{
                                        "role": "user",
                                        "content": f"""You are analyzing pilot trip scheduling data. Here is the summary statistics:

{summary_data}

The user's question is: {user_question_summary}

Please provide a helpful, concise answer based on this data. Explain patterns and provide actionable insights."""
                                    }]
                                )
                                
                                # Display response
                                st.success("✨ AI Analysis:")
                                st.markdown(message.content[0].text)
                                
                            except ImportError:
                                st.error("❌ Anthropic library not installed. Run: `pip install anthropic`")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            
            # SUMMARY VIEW (existing code)
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Trips", result['total_trips'])
            with col2:
                st.metric("Avg Trip Length", f"{result['avg_trip_length']:.2f} days")
            with col3:
                st.metric("Avg Credit/Trip", f"{result['avg_credit_per_trip']:.2f} hrs")
            with col4:
                st.metric("Avg Credit/Day", f"{result['avg_credit_per_day']:.2f} hrs")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Front-End Commute", f"{result['front_commute_rate']:.1f}%")
            with col2:
                st.metric("Back-End Commute", f"{result['back_commute_rate']:.1f}%")
            with col3:
                st.metric("Both Ends Commute", f"{result['both_commute_rate']:.1f}%")
            
            # Charts in tabs
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Trip Length", "Single Leg Last Day", "Credit/Trip", 
                "Credit/Day", "Commutability", "Red-Eye Trips"
            ])
            
            with tab1:
                # Calculate percentages for each trip length
                total_trips = result['total_trips']
                trip_counts = [result['trip_counts'][i] for i in range(1, 6)]
                trip_percentages = [(count / total_trips * 100) if total_trips > 0 else 0 for count in trip_counts]
                
                # Create bar chart with count and percentage
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)],
                    'Count': trip_counts,
                    'Percentage': trip_percentages
                })
                
                fig = px.bar(
                    data,
                    x='Length',
                    y='Count',
                    labels={'Length': 'Trip Length', 'Count': 'Number of Trips'},
                    title='Trip Length Distribution',
                    text=[f"{count}<br>({pct:.1f}%)" for count, pct in zip(trip_counts, trip_percentages)]
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)],
                    'Percentage': [result['single_leg_pct'][i] for i in range(1, 6)]
                })
                fig = px.bar(data, x='Length', y='Percentage',
                            title='Trips with Single Leg on Last Day (%)')
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)],
                    'Hours': [result['avg_credit_by_length'][i] for i in range(1, 6)]
                })
                fig = px.bar(data, x='Length', y='Hours',
                            title='Average Credit Hours per Trip')
                st.plotly_chart(fig, use_container_width=True)
            
            with tab4:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)],
                    'Hours/Day': [result['avg_credit_per_day_by_length'][i] for i in range(1, 6)]
                })
                fig = px.bar(data, x='Length', y='Hours/Day',
                            title='Average Credit Hours per Day')
                st.plotly_chart(fig, use_container_width=True)
            
            with tab5:
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)] * 3,
                    'Percentage': [result['front_commute_pct'][i] for i in range(1, 6)] +
                                 [result['back_commute_pct'][i] for i in range(1, 6)] +
                                 [result['both_commute_pct'][i] for i in range(1, 6)],
                    'Type': ['Front End']*5 + ['Back End']*5 + ['Both Ends']*5
                })
                fig = px.bar(data, x='Length', y='Percentage', color='Type',
                            barmode='group', title='Commutability by Trip Length (%)')
                st.plotly_chart(fig, use_container_width=True)
            
            with tab6:
                # Calculate red-eye counts and percentages by trip length
                trip_counts = [result['trip_counts'][i] for i in range(1, 6)]
                redeye_pcts = [result['redeye_pct'][i] for i in range(1, 6)]
                redeye_counts = [int(trip_counts[i-1] * redeye_pcts[i-1] / 100) for i in range(1, 6)]
                
                # Create bar chart with count and percentage
                data = pd.DataFrame({
                    'Length': [f"{i}-day" for i in range(1, 6)],
                    'Count': redeye_counts,
                    'Percentage': redeye_pcts
                })
                
                fig = px.bar(
                    data,
                    x='Length',
                    y='Count',
                    labels={'Length': 'Trip Length', 'Count': 'Number of Trips with Red-Eye'},
                    title='Trips Containing Red-Eye Flight by Trip Length',
                    text=[f"{count}<br>({pct:.1f}%)" for count, pct in zip(redeye_counts, redeye_pcts)]
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            # DETAILED TRIP TABLE VIEW
            # Get detailed trip data
            if 'detailed_trips' not in st.session_state:
                st.session_state.detailed_trips = {}
            
            if fname not in st.session_state.detailed_trips:
                with st.spinner("Loading detailed trip data..."):
                    # Get bid month from uploaded file data
                    bid_month = fdata['month']
                    
                    detailed_trips = analysis_engine.get_detailed_trips(
                        fdata['content'],
                        selected_base,
                        bid_month
                    )
                    st.session_state.detailed_trips[fname] = detailed_trips
            
            trips = st.session_state.detailed_trips[fname]
            
            # Initialize filter state
            if 'trip_filters' not in st.session_state:
                st.session_state.trip_filters = {
                    'trip_length': 'All',
                    'report_start': '00:00',
                    'report_end': '23:59',
                    'release_start': '00:00',
                    'release_end': '23:59',
                    'search_term': '',
                    'sort_column': None,
                    'sort_ascending': True
                }
            
            # Filters section
            st.markdown("### Filters")
            
            # Create filter columns
            filter_col1, filter_col2, filter_col3, filter_col4, filter_col5, filter_col6, filter_col7 = st.columns([1, 1.5, 1.5, 1, 1, 1, 0.5])
            
            with filter_col1:
                trip_length_filter = st.selectbox(
                    "Trip Length",
                    ['All', '1-day', '2-day', '3-day', '4-day', '5-day'],
                    key='filter_trip_length'
                )
            
            with filter_col2:
                # Time options: 00:00 to 23:59 in 30-min increments, plus 23:59
                time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]]
                time_options.append("23:59")
                
                col_a, col_b = st.columns(2)
                with col_a:
                    report_start = st.selectbox("Report Start", time_options, index=0, key='filter_report_start')
                with col_b:
                    report_end = st.selectbox("Report End", time_options, index=len(time_options)-1, key='filter_report_end')
            
            with filter_col3:
                col_a, col_b = st.columns(2)
                with col_a:
                    release_start = st.selectbox("Release Start", time_options, index=0, key='filter_release_start')
                with col_b:
                    release_end = st.selectbox("Release End", time_options, index=len(time_options)-1, key='filter_release_end')
            
            with filter_col4:
                search_term = st.text_input("Search Trip #", key='filter_search', placeholder="e.g., 44")
            
            with filter_col5:
                num_legs_filter = st.selectbox(
                    "Number of Legs",
                    ['All', '2', '3', '4', '5', '6', '7', '8', '9', '10+'],
                    key='filter_num_legs'
                )
            
            with filter_col6:
                credit_filter = st.selectbox(
                    "Credit",
                    ['All', 'Hard Block', '<15 minutes', '15-30 minutes', '30-60 minutes', '>60 minutes'],
                    key='filter_credit'
                )
            
            with filter_col7:
                st.write("")  # Spacer
                st.write("")  # Spacer
                if st.button("🔄 Clear", key='clear_filters'):
                    # Clear detailed trips cache to force reload with unchecked boxes
                    if fname in st.session_state.detailed_trips:
                        del st.session_state.detailed_trips[fname]
                    # Delete all filter widget keys - they'll reset to defaults on rerun
                    keys_to_delete = ['filter_trip_length', 'filter_report_start', 'filter_report_end', 
                                     'filter_release_start', 'filter_release_end', 'filter_search', 'filter_num_legs', 'filter_credit',
                                     'filter_one_leg_home', 'filter_has_sit', 'filter_has_edp', 
                                     'filter_has_hol', 'filter_has_carve', 'filter_has_redeye']
                    for key in keys_to_delete:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            # Checkbox filters row
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
            
            # Apply filters
            filtered_trips = trips.copy()
            
            # Trip length filter
            if trip_length_filter != 'All':
                length = int(trip_length_filter.split('-')[0])
                filtered_trips = [t for t in filtered_trips if t['length'] == length]
            
            # Report time filter
            def time_to_minutes(time_str):
                h, m = map(int, time_str.split(':'))
                return h * 60 + m
            
            report_start_min = time_to_minutes(report_start)
            report_end_min = time_to_minutes(report_end)
            filtered_trips = [t for t in filtered_trips 
                            if t['report_time_minutes'] is not None 
                            and report_start_min <= t['report_time_minutes'] <= report_end_min]
            
            # Release time filter
            release_start_min = time_to_minutes(release_start)
            release_end_min = time_to_minutes(release_end)
            filtered_trips = [t for t in filtered_trips 
                            if t['release_time_minutes'] is not None 
                            and release_start_min <= t['release_time_minutes'] <= release_end_min]
            
            # Search filter - match partial trip number (including suffix like -1, -2)
            if search_term:
                filtered_trips = [t for t in filtered_trips 
                                if t['trip_number'] and search_term in str(t['trip_number'])]
            
            # Number of legs filter
            if num_legs_filter != 'All':
                if num_legs_filter == '10+':
                    filtered_trips = [t for t in filtered_trips if t['total_legs'] >= 10]
                else:
                    num_legs = int(num_legs_filter)
                    filtered_trips = [t for t in filtered_trips if t['total_legs'] == num_legs]
            
            # Credit filter (CR time in minutes)
            if credit_filter != 'All':
                if credit_filter == 'Hard Block':
                    # CR = 0 minutes (hard block, no credit beyond block time)
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and t.get('credit_minutes') == 0]
                elif credit_filter == '<15 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 0 < t.get('credit_minutes') < 15]
                elif credit_filter == '15-30 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 15 <= t.get('credit_minutes') <= 30]
                elif credit_filter == '30-60 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and 30 < t.get('credit_minutes') <= 60]
                elif credit_filter == '>60 minutes':
                    filtered_trips = [t for t in filtered_trips if t.get('credit_minutes') is not None and t.get('credit_minutes') > 60]
            
            # Checkbox filters
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
            
            # Display trip count (sum of all occurrences)
            total_occurrences = sum(trip.get('occurrences', 1) for trip in filtered_trips)
            st.markdown(f"**Showing {total_occurrences} trips** *({len(filtered_trips)} unique patterns)*")
            
            # AI Chat Section (above the table)
            with st.expander("💬 Ask AI About Your Trips", expanded=False):
                st.markdown("Ask questions about the filtered trips in natural language!")
                st.markdown("*Examples: 'Which trips have the best credit ratio?', 'Show me commutable 3-days with high pay'*")
                
                # Try to get API key from secrets, then from session state, then from user input
                api_key = None
                if "ANTHROPIC_API_KEY" in st.secrets:
                    api_key = st.secrets["ANTHROPIC_API_KEY"]
                    st.success("✅ Using API key from Streamlit secrets")
                else:
                    # API Key input
                    api_key = st.text_input(
                        "Anthropic API Key",
                        type="password",
                        help="Get your API key at https://console.anthropic.com, or save it in Settings > Secrets as ANTHROPIC_API_KEY",
                        key="anthropic_api_key",
                        value=st.session_state.get('saved_api_key', '')
                    )
                    
                    if api_key and api_key != st.session_state.get('saved_api_key', ''):
                        st.session_state.saved_api_key = api_key
                        st.info("💡 API key saved for this session. To save permanently, add it to Streamlit Settings > Secrets")
                
                # Question input
                user_question = st.text_area(
                    "Your Question",
                    placeholder="e.g., What are the top 5 trips by credit per day?",
                    height=80,
                    key="ai_question"
                )
                
                if st.button("Ask AI", type="primary"):
                    if not api_key:
                        st.error("Please enter your Anthropic API key first")
                    elif not user_question:
                        st.error("Please enter a question")
                    elif len(filtered_trips) == 0:
                        st.warning("No trips to analyze. Adjust your filters.")
                    else:
                        with st.spinner("Analyzing trips..."):
                            try:
                                # Prepare trip data for AI
                                import anthropic
                                
                                # Create a summary of the filtered trips
                                trip_summary = []
                                
                                # Get current commutability thresholds from sidebar
                                def parse_time_to_minutes(time_str):
                                    """Convert HH:MM to minutes, returns None if invalid"""
                                    if not time_str or time_str == 'N/A':
                                        return None
                                    try:
                                        parts = time_str.split(':')
                                        return int(parts[0]) * 60 + int(parts[1])
                                    except:
                                        return None
                                
                                front_threshold = parse_time_to_minutes(front_end_time)
                                back_threshold = parse_time_to_minutes(back_end_time)
                                
                                for trip in filtered_trips[:500]:  # Increased to 500 to capture more trips
                                    # Calculate commutability flags by parsing time strings
                                    report_minutes = parse_time_to_minutes(trip.get('report_time'))
                                    release_minutes = parse_time_to_minutes(trip.get('release_time'))
                                    
                                    front_commutable = report_minutes is not None and front_threshold is not None and report_minutes >= front_threshold
                                    back_commutable = release_minutes is not None and back_threshold is not None and release_minutes <= back_threshold
                                    both_ends_commutable = front_commutable and back_commutable
                                    
                                    trip_summary.append({
                                        'trip_number': trip.get('trip_number', 'N/A'),
                                        'base': trip['base'],
                                        'length': f"{trip['length']}-day",
                                        'days_of_week': trip.get('days_of_week', []),
                                        'occurrences': trip.get('occurrences', 1),
                                        'report': trip.get('report_time'),
                                        'release': trip.get('release_time'),
                                        'front_end_commutable': front_commutable,
                                        'back_end_commutable': back_commutable,
                                        'both_ends_commutable': both_ends_commutable,
                                        'legs': trip['total_legs'],
                                        'longest_leg': trip.get('longest_leg'),
                                        'shortest_leg': trip.get('shortest_leg'),
                                        'credit': trip.get('total_credit'),
                                        'pay': trip.get('total_pay'),
                                        'sit': trip.get('sit'),
                                        'edp': trip.get('edp'),
                                        'hol': trip.get('hol'),
                                        'carve': trip.get('carve'),
                                        'credit_per_day': trip.get('total_credit', 0) / trip['length'] if trip['length'] > 0 else 0,
                                        'last_day_legs': trip.get('last_day_legs')
                                    })
                                
                                # Call Claude API
                                client = anthropic.Anthropic(api_key=api_key)
                                message = client.messages.create(
                                    model="claude-sonnet-4-20250514",
                                    max_tokens=4000,  # Increased from 2000
                                    messages=[{
                                        "role": "user",
                                        "content": f"""You are analyzing pilot trip scheduling data. Here is the current filtered dataset (showing first 500 of {len(filtered_trips)} trips):

{trip_summary}

Each trip includes:
- days_of_week: Which days of the week this trip operates (e.g., ['MO', 'TU', 'WE', 'TH', 'FR'] means Monday-Friday only, ['SA', 'SU'] means weekends only)
- occurrences: How many times this trip pattern operates during the bid period
- report/release: Time strings (HH:MM format)
- front_end_commutable: True if report_minutes >= front_threshold (630 = 10:30)
- back_end_commutable: True if release_minutes <= back_threshold (1080 = 18:00)
- both_ends_commutable: True if BOTH front and back are commutable

CRITICAL FILTERING RULES:
- "Monday-Friday only" means days_of_week must contain ONLY weekday codes (MO, TU, WE, TH, FR)
- If days_of_week contains 'SA' or 'SU', the trip is NOT Monday-Friday only
- Example: ['SA'] = Saturday trip = NOT Monday-Friday
- Example: ['MO'] = Monday trip = Monday-Friday only ✓
- Example: ['MO', 'SA'] = Monday and Saturday = NOT Monday-Friday only

Common day patterns:
- Monday-Friday only: days_of_week contains only ['MO', 'TU', 'WE', 'TH', 'FR'] or subset (no SA or SU)
- Weekends only: days_of_week contains only ['SA', 'SU']
- Every day: days_of_week is empty or contains all 7 days

The user's question is: {user_question}

When counting trips, remember to sum the 'occurrences' field to get total trips. Format your response clearly with bullet points or tables where appropriate."""
                                    }]
                                )
                                
                                # Display response
                                st.success("✨ AI Analysis:")
                                st.markdown(message.content[0].text)
                                
                            except ImportError:
                                st.error("❌ Anthropic library not installed. Run: `pip install anthropic`")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            
            # Create dataframe for display
            if filtered_trips:
                # Initialize selected trip in session state
                if 'selected_trip_index' not in st.session_state:
                    st.session_state.selected_trip_index = None
                
                df_data = []
                for i, trip in enumerate(filtered_trips):
                    df_data.append({
                        'Select': False,
                        'Trip #': trip['trip_number'] or 'N/A',
                        'Base': trip['base'],
                        'Length': f"{trip['length']}-day",
                        'Report': trip['report_time'] or 'N/A',
                        'Release': trip['release_time'] or 'N/A',
                        'Legs': trip['total_legs'],
                        'Longest': trip['longest_leg'],
                        'Shortest': trip['shortest_leg'],
                        'Credit': trip['total_credit'] if trip['total_credit'] is not None else None,
                        'Pay': trip['total_pay'] if trip['total_pay'] is not None else None,
                        'SIT': trip.get('sit'),
                        'EDP': trip.get('edp'),
                        'HOL': trip.get('hol'),
                        'CARVE': trip.get('carve'),
                        'Occurs': trip['occurrences']
                    })
                
                df = pd.DataFrame(df_data)
                
                # Use data_editor for selection capability with column sorting enabled
                edited_df = st.data_editor(
                    df,
                    column_config={
                        'Select': st.column_config.CheckboxColumn(
                            'Select',
                            help='Click to view trip details',
                            default=False,
                            width='small'
                        ),
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
                        'Occurs': st.column_config.NumberColumn('Occurs', width='small', help='Number of times this trip operates')
                    },
                    disabled=['Trip #', 'Base', 'Length', 'Report', 'Release', 'Legs', 'Longest', 'Shortest', 'Credit', 'Pay', 'SIT', 'EDP', 'HOL', 'CARVE', 'Occurs'],
                    hide_index=True,
                    use_container_width=True,
                    height=600,
                    key='trip_table'
                )
                
                # Check which trips are selected
                selected_indices = edited_df[edited_df['Select']].index.tolist()
                
                # Display details for selected trips
                if selected_indices:
                    st.markdown("---")
                    st.markdown("### Selected Trip Details")
                    
                    for idx in selected_indices:
                        trip = filtered_trips[idx]
                        trip_num = trip['trip_number']
                        
                        with st.expander(f"Trip #{trip_num} - Full Details", expanded=True):
                            st.code(trip['raw_text'], language=None)
            else:
                st.info("No trips match the current filters.")
    
    else:
        # Multiple files - show detailed comparison tables
        st.subheader("📈 Detailed Comparison Analysis")
        
        # AI Chat Section for Comparison View
        with st.expander("💬 Ask AI About This Comparison", expanded=False):
            st.markdown("Ask questions comparing the different bid packs!")
            st.markdown("*Examples: 'Which month has better 3-day trips?', 'How do November and December compare for commutability?'*")
            
            # Try to get API key from secrets, then from session state, then from user input
            api_key_comparison = None
            if "ANTHROPIC_API_KEY" in st.secrets:
                api_key_comparison = st.secrets["ANTHROPIC_API_KEY"]
                st.success("✅ Using API key from Streamlit secrets")
            else:
                # API Key input
                api_key_comparison = st.text_input(
                    "Anthropic API Key",
                    type="password",
                    help="Get your API key at https://console.anthropic.com, or save it in Settings > Secrets as ANTHROPIC_API_KEY",
                    key="anthropic_api_key_comparison",
                    value=st.session_state.get('saved_api_key', '')
                )
                
                if api_key_comparison and api_key_comparison != st.session_state.get('saved_api_key', ''):
                    st.session_state.saved_api_key = api_key_comparison
                    st.info("💡 API key saved for this session. To save permanently, add it to Streamlit Settings > Secrets")
            
            # Question input
            user_question_comparison = st.text_area(
                "Your Question",
                placeholder="e.g., Which month should I bid for to maximize credit per day?",
                height=80,
                key="ai_question_comparison"
            )
            
            if st.button("Ask AI", type="primary", key="ask_ai_comparison"):
                if not api_key_comparison:
                    st.error("Please enter your Anthropic API key first")
                elif not user_question_comparison:
                    st.error("Please enter a question")
                else:
                    with st.spinner("Analyzing comparison data..."):
                        try:
                            import anthropic
                            
                            # Prepare comparison data for AI
                            comparison_data = {}
                            for fname in st.session_state.analysis_results.keys():
                                fdata = st.session_state.uploaded_files[fname]
                                result = st.session_state.analysis_results[fname]
                                
                                comparison_data[fdata['display_name']] = {
                                    'total_trips': result['total_trips'],
                                    'avg_trip_length': result['avg_trip_length'],
                                    'avg_credit_per_trip': result['avg_credit_per_trip'],
                                    'avg_credit_per_day': result['avg_credit_per_day'],
                                    'trip_counts_by_length': result['trip_counts'],
                                    'avg_credit_by_length': result['avg_credit_by_length'],
                                    'avg_credit_per_day_by_length': result['avg_credit_per_day_by_length'],
                                    'single_leg_last_day_pct': result['single_leg_pct'],
                                    'redeye_pct': result['redeye_pct'],
                                    'front_end_commutable_pct': result['front_commute_pct'],
                                    'back_end_commutable_pct': result['back_commute_pct']
                                }
                            
                            # Call Claude API
                            client = anthropic.Anthropic(api_key=api_key_comparison)
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=2000,
                                messages=[{
                                    "role": "user",
                                    "content": f"""You are analyzing pilot trip scheduling data comparing multiple bid packs. Here is the comparison data:

{comparison_data}

The user's question is: {user_question_comparison}

Please provide a helpful, detailed comparison highlighting key differences and providing actionable recommendations."""
                                }]
                            )
                            
                            # Display response
                            st.success("✨ AI Comparison Analysis:")
                            st.markdown(message.content[0].text)
                            
                        except ImportError:
                            st.error("❌ Anthropic library not installed. Run: `pip install anthropic`")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
        
        # Sort files by date (month/year)
        month_order = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        sorted_files = sorted(
            st.session_state.analysis_results.keys(),
            key=lambda f: (
                st.session_state.uploaded_files[f]['year'],
                month_order[st.session_state.uploaded_files[f]['month']]
            )
        )
        
        num_files = len(sorted_files)
        show_differences = (num_files == 2)
        
        # 1. TRIP LENGTH DISTRIBUTION
        st.markdown("### 1️⃣ Trip Length Distribution")
        trip_dist_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                count = result['trip_counts'][length]
                pct = (count / result['total_trips'] * 100) if result['total_trips'] > 0 else 0
                row[f'{length}-day'] = f"{count} ({pct:.2f}%)"
            row['Total'] = f"{result['total_trips']} (100.00%)"
            trip_dist_data.append(row)
        st.dataframe(pd.DataFrame(trip_dist_data), use_container_width=True, hide_index=True)
        
        # Show differences only if exactly 2 files
        if show_differences:
            st.markdown("**Change (Newer - Older):**")
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Percentage Point Difference'}
            for length in range(1, 6):
                pct1 = (r1['trip_counts'][length] / r1['total_trips'] * 100) if r1['total_trips'] > 0 else 0
                pct2 = (r2['trip_counts'][length] / r2['total_trips'] * 100) if r2['total_trips'] > 0 else 0
                diff = pct2 - pct1
                row[f'{length}-day'] = f"{diff:+.2f} points"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 2. SINGLE LEG ON LAST DAY
        st.markdown("### 2️⃣ Trips with Single Leg on Last Day")
        single_leg_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                total = result['trip_counts'][length]
                single_count = int(total * result['single_leg_pct'][length] / 100)
                pct = result['single_leg_pct'][length]
                row[f'{length}-day'] = f"{single_count} ({pct:.2f}%)"
            # Overall
            total_single = sum(result['trip_counts'][i] * result['single_leg_pct'][i] / 100 for i in range(1, 6))
            overall_pct = (total_single / result['total_trips'] * 100) if result['total_trips'] > 0 else 0
            overall_count = int(total_single)
            row['Overall'] = f"{overall_count} ({overall_pct:.2f}%)"
            single_leg_data.append(row)
        st.dataframe(pd.DataFrame(single_leg_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            st.markdown("**Change (Newer - Older):**")
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Percentage Point Difference'}
            for length in range(1, 6):
                diff = r2['single_leg_pct'][length] - r1['single_leg_pct'][length]
                row[f'{length}-day'] = f"{diff:+.2f} points"
            # Overall difference
            total_single1 = sum(r1['trip_counts'][i] * r1['single_leg_pct'][i] / 100 for i in range(1, 6))
            overall_pct1 = (total_single1 / r1['total_trips'] * 100) if r1['total_trips'] > 0 else 0
            total_single2 = sum(r2['trip_counts'][i] * r2['single_leg_pct'][i] / 100 for i in range(1, 6))
            overall_pct2 = (total_single2 / r2['total_trips'] * 100) if r2['total_trips'] > 0 else 0
            row['Overall'] = f"{overall_pct2 - overall_pct1:+.2f} points"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 3. AVERAGE CREDIT PER TRIP
        st.markdown("### 3️⃣ Average Credit per Trip (hours)")
        credit_trip_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                row[f'{length}-day'] = f"{result['avg_credit_by_length'][length]:.2f} hrs"
            row['Overall'] = f"{result['avg_credit_per_trip']:.2f} hrs"
            credit_trip_data.append(row)
        st.dataframe(pd.DataFrame(credit_trip_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            st.markdown("**Change (Newer - Older):**")
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Hour Difference'}
            for length in range(1, 6):
                diff = r2['avg_credit_by_length'][length] - r1['avg_credit_by_length'][length]
                row[f'{length}-day'] = f"{diff:+.2f} hrs"
            overall_diff = r2['avg_credit_per_trip'] - r1['avg_credit_per_trip']
            row['Overall'] = f"{overall_diff:+.2f} hrs"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 4. AVERAGE CREDIT PER DAY
        st.markdown("### 4️⃣ Average Credit per Day (hours/day)")
        credit_day_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                row[f'{length}-day'] = f"{result['avg_credit_per_day_by_length'][length]:.2f} hrs/day"
            row['Overall'] = f"{result['avg_credit_per_day']:.2f} hrs/day"
            credit_day_data.append(row)
        st.dataframe(pd.DataFrame(credit_day_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            st.markdown("**Change (Newer - Older):**")
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Hours/Day Difference'}
            for length in range(1, 6):
                diff = r2['avg_credit_per_day_by_length'][length] - r1['avg_credit_per_day_by_length'][length]
                row[f'{length}-day'] = f"{diff:+.2f} hrs/day"
            overall_diff = r2['avg_credit_per_day'] - r1['avg_credit_per_day']
            row['Overall'] = f"{overall_diff:+.2f} hrs/day"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 5. COMMUTABILITY
        st.markdown("### 5️⃣ Commutability")
        
        st.markdown("**Front-End Commutable (Report ≥ threshold):**")
        front_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                total = result['trip_counts'][length]
                commute_count = int(total * result['front_commute_pct'][length] / 100)
                pct = result['front_commute_pct'][length]
                row[f'{length}-day'] = f"{commute_count} ({pct:.2f}%)"
            # Overall
            total_commute = sum(result['trip_counts'][i] * result['front_commute_pct'][i] / 100 for i in range(1, 6))
            overall_count = int(total_commute)
            row['Overall'] = f"{overall_count} ({result['front_commute_rate']:.2f}%)"
            front_data.append(row)
        st.dataframe(pd.DataFrame(front_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Difference'}
            for length in range(1, 6):
                diff = r2['front_commute_pct'][length] - r1['front_commute_pct'][length]
                row[f'{length}-day'] = f"{diff:+.2f} points"
            overall_diff = r2['front_commute_rate'] - r1['front_commute_rate']
            row['Overall'] = f"{overall_diff:+.2f} points"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("**Back-End Commutable (Release ≤ threshold):**")
        back_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                total = result['trip_counts'][length]
                commute_count = int(total * result['back_commute_pct'][length] / 100)
                pct = result['back_commute_pct'][length]
                row[f'{length}-day'] = f"{commute_count} ({pct:.2f}%)"
            # Overall
            total_commute = sum(result['trip_counts'][i] * result['back_commute_pct'][i] / 100 for i in range(1, 6))
            overall_count = int(total_commute)
            row['Overall'] = f"{overall_count} ({result['back_commute_rate']:.2f}%)"
            back_data.append(row)
        st.dataframe(pd.DataFrame(back_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Difference'}
            for length in range(1, 6):
                diff = r2['back_commute_pct'][length] - r1['back_commute_pct'][length]
                row[f'{length}-day'] = f"{diff:+.2f} points"
            overall_diff = r2['back_commute_rate'] - r1['back_commute_rate']
            row['Overall'] = f"{overall_diff:+.2f} points"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
        
        st.markdown("**Both Ends Commutable:**")
        both_data = []
        for fname in sorted_files:
            result = st.session_state.analysis_results[fname]
            display_name = st.session_state.uploaded_files[fname]['display_name']
            row = {'File': display_name}
            for length in range(1, 6):
                total = result['trip_counts'][length]
                commute_count = int(total * result['both_commute_pct'][length] / 100)
                pct = result['both_commute_pct'][length]
                row[f'{length}-day'] = f"{commute_count} ({pct:.2f}%)"
            # Overall
            total_commute = sum(result['trip_counts'][i] * result['both_commute_pct'][i] / 100 for i in range(1, 6))
            overall_count = int(total_commute)
            row['Overall'] = f"{overall_count} ({result['both_commute_rate']:.2f}%)"
            both_data.append(row)
        st.dataframe(pd.DataFrame(both_data), use_container_width=True, hide_index=True)
        
        if show_differences:
            diff_data = []
            r1 = st.session_state.analysis_results[sorted_files[0]]
            r2 = st.session_state.analysis_results[sorted_files[1]]
            row = {'Metric': 'Difference'}
            for length in range(1, 6):
                diff = r2['both_commute_pct'][length] - r1['both_commute_pct'][length]
                row[f'{length}-day'] = f"{diff:+.2f} points"
            overall_diff = r2['both_commute_rate'] - r1['both_commute_rate']
            row['Overall'] = f"{overall_diff:+.2f} points"
            diff_data.append(row)
            st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)
    
    # Export PDF button
    if st.button("📄 Export PDF Report", key='pdf_export'):
        with st.spinner("Generating PDF..."):
            pdf_bytes = analysis_engine.generate_pdf_report(
                st.session_state.analysis_results,
                st.session_state.uploaded_files,
                selected_base,
                front_end_time,
                back_end_time
            )
            
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"trip_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                key='pdf_download'
            )

# Footer
st.markdown("---")
st.markdown("✈️ Pilot Trip Scheduling Analysis Tool | Upload up to 12 files for comparison")
