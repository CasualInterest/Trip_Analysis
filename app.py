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
                
                # Check if this exact file (by content) is already uploaded
                already_exists = False
                for existing_name, existing_data in st.session_state.uploaded_files.items():
                    if get_file_hash(existing_data['content']) == file_hash:
                        already_exists = True
                        st.warning(f"⚠️ File '{uploaded_file.name}' already uploaded as '{existing_name}'")
                        break
                
                if not already_exists and uploaded_file.name not in st.session_state.uploaded_files:
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
                            # Add to uploaded files
                            st.session_state.uploaded_files[uploaded_file.name] = {
                                'content': content,
                                'month': month,
                                'year': year,
                                'display_name': f"{month} {year} - {uploaded_file.name}"
                            }
                            st.session_state.file_counter += 1
                            st.success(f"✅ Added {uploaded_file.name}")
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
        # Single file - show detailed analysis
        fname = list(st.session_state.analysis_results.keys())[0]
        result = st.session_state.analysis_results[fname]
        fdata = st.session_state.uploaded_files[fname]
        
        st.subheader(f"Analysis: {fdata['display_name']}")
        
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
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Red-Eye Rate", f"{result['redeye_rate']:.1f}%")
        with col2:
            st.metric("Front-End Commute", f"{result['front_commute_rate']:.1f}%")
        with col3:
            st.metric("Back-End Commute", f"{result['back_commute_rate']:.1f}%")
        with col4:
            st.metric("Both Ends Commute", f"{result['both_commute_rate']:.1f}%")
        
        # Charts in tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Trip Length", "Single Leg Last Day", "Credit/Trip", 
            "Credit/Day", "Red-Eyes", "Commutability"
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
                'Length': [f"{i}-day" for i in range(1, 6)],
                'Percentage': [result['redeye_pct'][i] for i in range(1, 6)]
            })
            fig = px.bar(data, x='Length', y='Percentage',
                        title='Red-Eye Rate by Trip Length (%)')
            st.plotly_chart(fig, use_container_width=True)
        
        with tab6:
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
        # Multiple files - show comparison
        st.subheader("📈 Comparison Analysis")
        
        # Summary comparison table
        summary_data = []
        for fname, result in st.session_state.analysis_results.items():
            display_name = st.session_state.uploaded_files[fname]['display_name']
            summary_data.append({
                'File': display_name,
                'Total Trips': result['total_trips'],
                'Avg Length (days)': f"{result['avg_trip_length']:.2f}",
                'Avg Credit/Trip (hrs)': f"{result['avg_credit_per_trip']:.2f}",
                'Avg Credit/Day (hrs)': f"{result['avg_credit_per_day']:.2f}",
                'Red-Eye %': f"{result['redeye_rate']:.1f}%",
                'Front Commute %': f"{result['front_commute_rate']:.1f}%",
                'Back Commute %': f"{result['back_commute_rate']:.1f}%"
            })
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
        
        # Comparison charts
        tab1, tab2, tab3 = st.tabs(["Trip Distribution", "Credit Metrics", "Rates"])
        
        with tab1:
            data = []
            for fname, result in st.session_state.analysis_results.items():
                display_name = st.session_state.uploaded_files[fname]['display_name']
                for length in range(1, 6):
                    pct = result['trip_counts'][length] / result['total_trips'] * 100
                    data.append({
                        'File': display_name,
                        'Length': f"{length}-day",
                        'Percentage': pct
                    })
            df = pd.DataFrame(data)
            fig = px.bar(df, x='Length', y='Percentage', color='File',
                        barmode='group', title='Trip Length Distribution Comparison')
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                data = []
                for fname, result in st.session_state.analysis_results.items():
                    display_name = st.session_state.uploaded_files[fname]['display_name']
                    for length in range(1, 6):
                        data.append({
                            'File': display_name,
                            'Length': f"{length}-day",
                            'Hours': result['avg_credit_by_length'][length]
                        })
                df = pd.DataFrame(data)
                fig = px.line(df, x='Length', y='Hours', color='File',
                            title='Avg Credit per Trip', markers=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                data = []
                for fname, result in st.session_state.analysis_results.items():
                    display_name = st.session_state.uploaded_files[fname]['display_name']
                    for length in range(1, 6):
                        data.append({
                            'File': display_name,
                            'Length': f"{length}-day",
                            'Hours/Day': result['avg_credit_per_day_by_length'][length]
                        })
                df = pd.DataFrame(data)
                fig = px.line(df, x='Length', y='Hours/Day', color='File',
                            title='Avg Credit per Day', markers=True)
                st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            col1, col2, col3 = st.columns(3)
            with col1:
                data = []
                for fname, result in st.session_state.analysis_results.items():
                    display_name = st.session_state.uploaded_files[fname]['display_name']
                    data.append({'File': display_name, 'Red-Eye %': result['redeye_rate']})
                df = pd.DataFrame(data)
                fig = px.bar(df, x='File', y='Red-Eye %', title='Red-Eye Rate')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                data = []
                for fname, result in st.session_state.analysis_results.items():
                    display_name = st.session_state.uploaded_files[fname]['display_name']
                    data.append({'File': display_name, 'Front %': result['front_commute_rate']})
                df = pd.DataFrame(data)
                fig = px.bar(df, x='File', y='Front %', title='Front-End Commute')
                st.plotly_chart(fig, use_container_width=True)
            
            with col3:
                data = []
                for fname, result in st.session_state.analysis_results.items():
                    display_name = st.session_state.uploaded_files[fname]['display_name']
                    data.append({'File': display_name, 'Back %': result['back_commute_rate']})
                df = pd.DataFrame(data)
                fig = px.bar(df, x='File', y='Back %', title='Back-End Commute')
                st.plotly_chart(fig, use_container_width=True)
    
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
