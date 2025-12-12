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
                        
                        submitted = st.form_submit_button("✅ Add File")
                        
                        if submitted:
                            # Create unique filename based on date and original name
                            # Extract base name without extension
                            base_name = uploaded_file.name.rsplit('.', 1)[0] if '.' in uploaded_file.name else uploaded_file.name
                            extension = uploaded_file.name.rsplit('.', 1)[1] if '.' in uploaded_file.name else 'txt'
                            
                            # Create new filename: basename_MMYYYY.ext
                            month_num = {
                                'January': '01', 'February': '02', 'March': '03', 'April': '04',
                                'May': '05', 'June': '06', 'July': '07', 'August': '08',
                                'September': '09', 'October': '10', 'November': '11', 'December': '12'
                            }[month]
                            
                            new_filename = f"{base_name}_{month_num}{year}.{extension}"
                            
                            # Add to uploaded files with new filename
                            st.session_state.uploaded_files[new_filename] = {
                                'content': content,
                                'month': month,
                                'year': year,
                                'display_name': f"{month} {year}",
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
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "Trip Length", "Single Leg Last Day", "Credit/Trip", 
                "Credit/Day", "Commutability"
            ])
            
            with tab1:
                fig = px.bar(
                    x=[f"{i}-day" for i in range(1, 6)],
                    y=[result['trip_counts'][i] for i in range(1, 6)],
                    labels={'x': 'Trip Length', 'y': 'Number of Trips'},
                    title='Trip Length Distribution'
                )
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
        
        else:
            # DETAILED TRIP TABLE VIEW
            # Get detailed trip data
            if 'detailed_trips' not in st.session_state:
                st.session_state.detailed_trips = {}
            
            if fname not in st.session_state.detailed_trips:
                with st.spinner("Loading detailed trip data..."):
                    detailed_trips = analysis_engine.get_detailed_trips(
                        fdata['content'],
                        selected_base
                    )
                    st.session_state.detailed_trips[fname] = detailed_trips
            
            trips = st.session_state.detailed_trips[fname]
            
            # Initialize filter state
            if 'trip_filters' not in st.session_state:
                st.session_state.trip_filters = {
                    'trip_length': 'All',
                    'report_start': '00:00',
                    'report_end': '23:30',
                    'release_start': '00:00',
                    'release_end': '23:30',
                    'search_term': '',
                    'sort_column': None,
                    'sort_ascending': True
                }
            
            # Filters section
            st.markdown("### Filters")
            
            # Create filter columns
            filter_col1, filter_col2, filter_col3, filter_col4, filter_col5 = st.columns([1, 1.5, 1.5, 1, 0.5])
            
            with filter_col1:
                trip_length_filter = st.selectbox(
                    "Trip Length",
                    ['All', '1-day', '2-day', '3-day', '4-day', '5-day'],
                    key='filter_trip_length'
                )
            
            with filter_col2:
                time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in [0, 30]]
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
                st.write("")  # Spacer
                st.write("")  # Spacer
                if st.button("🔄 Clear", key='clear_filters'):
                    st.session_state.trip_filters = {
                        'trip_length': 'All',
                        'report_start': '00:00',
                        'report_end': '23:30',
                        'release_start': '00:00',
                        'release_end': '23:30',
                        'search_term': '',
                        'sort_column': None,
                        'sort_ascending': True
                    }
                    st.rerun()
            
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
            
            # Search filter
            if search_term:
                filtered_trips = [t for t in filtered_trips 
                                if t['trip_number'] and search_term in t['trip_number']]
            
            # Display trip count
            st.markdown(f"**Showing {len(filtered_trips)} trips**")
            
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
                        'Credit': f"{trip['total_credit']:.2f}" if trip['total_credit'] else 'N/A',
                        'Pay': f"{trip['total_pay']:.2f}" if trip['total_pay'] else 'N/A'
                    })
                
                df = pd.DataFrame(df_data)
                
                # Use data_editor for selection capability
                edited_df = st.data_editor(
                    df,
                    column_config={
                        'Select': st.column_config.CheckboxColumn(
                            'Select',
                            help='Click to view trip details',
                            default=False,
                            width='small'
                        ),
                        'Trip #': st.column_config.TextColumn('Trip #', width='small'),
                        'Base': st.column_config.TextColumn('Base', width='small'),
                        'Length': st.column_config.TextColumn('Length', width='small'),
                        'Report': st.column_config.TextColumn('Report', width='small'),
                        'Release': st.column_config.TextColumn('Release', width='small'),
                        'Legs': st.column_config.NumberColumn('Legs', width='small'),
                        'Longest': st.column_config.TextColumn('Longest', width='small'),
                        'Shortest': st.column_config.TextColumn('Shortest', width='small'),
                        'Credit': st.column_config.TextColumn('Credit', width='small'),
                        'Pay': st.column_config.TextColumn('Pay', width='small')
                    },
                    disabled=['Trip #', 'Base', 'Length', 'Report', 'Release', 'Legs', 'Longest', 'Shortest', 'Credit', 'Pay'],
                    hide_index=True,
                    use_container_width=True,
                    height=600
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
