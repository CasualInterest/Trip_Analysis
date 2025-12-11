import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
import re
from datetime import datetime, time
import plotly.graph_objects as go
import plotly.express as px
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

# Page configuration
st.set_page_config(
    page_title="Flight Bidding Data Analyzer",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 5px;
    }
    h1 {
        color: #1f77b4;
    }
    .uploadedFile {
        background-color: #e8f4f8;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def parse_time_to_minutes(time_str):
    """Convert time string (HH.MM or HH:MM) to minutes"""
    if pd.isna(time_str) or time_str == '':
        return 0
    
    time_str = str(time_str).strip()
    # Handle both . and : separators
    if '.' in time_str:
        parts = time_str.split('.')
    elif ':' in time_str:
        parts = time_str.split(':')
    else:
        return 0
    
    try:
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return hours * 60 + minutes
    except:
        return 0


def parse_bidding_file(file_content, filename):
    """Parse the bidding data file and extract trip information"""
    lines = file_content.split('\n')
    
    # Base determination from airport codes
    airport_to_base = {
        'ATL': 'ATL',
        'BOS': 'BOS',
        'JFK': 'NYC', 'LGA': 'NYC', 'EWR': 'NYC',
        'DTW': 'DTW',
        'SLC': 'SLC',
        'MSP': 'MSP',
        'SEA': 'SEA',
        'LAX': 'LAX', 'LGB': 'LAX', 'ONT': 'LAX'
    }
    
    trips = []
    current_trip = None
    current_days = []
    first_departure_found = False
    
    for i, line in enumerate(lines):
        # Detect trip number
        trip_match = re.search(r'^\s+#(\d+)\s+([A-Z]{2})', line)
        if trip_match:
            # Save previous trip if exists
            if current_trip:
                current_trip['days'] = current_days
                trips.append(current_trip)
            
            # Start new trip
            current_trip = {
                'trip_number': trip_match.group(1),
                'trip_type': trip_match.group(2),
                'base': None,  # Will be determined from first departure
                'filename': filename,
                'first_departure': None
            }
            current_days = []
            first_departure_found = False
            continue
        
        # Detect first flight leg (Day A) to determine base - handles both regular and DH flights
        if not first_departure_found and current_trip:
            # Regular flight: A FLIGHT# AIRPORT TIME
            flight_match = re.search(r'^\s+A\s+\d+\s+([A-Z]{3})\s+\d{4}', line)
            # Deadhead flight: A DH FLIGHT# AIRPORT TIME
            dh_match = re.search(r'^\s+A\s+DH\s+\d+\s+([A-Z]{3})\s+\d{4}', line)
            
            if flight_match:
                airport = flight_match.group(1)
                current_trip['first_departure'] = airport
                current_trip['base'] = airport_to_base.get(airport, 'UNKNOWN')
                first_departure_found = True
            elif dh_match:
                airport = dh_match.group(1)
                current_trip['first_departure'] = airport
                current_trip['base'] = airport_to_base.get(airport, 'UNKNOWN')
                first_departure_found = True
        
        # Detect day lines (A, B, C, D, etc.) and count flights
        day_match = re.search(r'^\s+([A-D])\s+(\d+)', line)
        if day_match and current_trip:
            day_letter = day_match.group(1)
            # Check if this day already exists
            existing_day = next((d for d in current_days if d['day'] == day_letter), None)
            if existing_day:
                existing_day['flights'].append(day_match.group(2))
            else:
                current_days.append({'day': day_letter, 'flights': [day_match.group(2)]})
        
        # Detect TOTAL CREDIT line
        if 'TOTAL CREDIT' in line and current_trip:
            credit_match = re.search(r'TOTAL CREDIT\s+([\d:.]+)TL', line)
            tafb_match = re.search(r'TAFB\s+([\d:.]+)', line)
            
            if credit_match:
                current_trip['total_credit'] = credit_match.group(1)
            if tafb_match:
                current_trip['tafb'] = tafb_match.group(1)
    
    # Add last trip
    if current_trip:
        current_trip['days'] = current_days
        trips.append(current_trip)
    
    return trips


def analyze_trips(trips_data):
    """Analyze trip data and calculate metrics"""
    if not trips_data:
        return None
    
    df = pd.DataFrame(trips_data)
    df['num_days'] = df['days'].apply(len)
    df['credit_minutes'] = df['total_credit'].apply(parse_time_to_minutes)
    df['tafb_minutes'] = df['tafb'].apply(parse_time_to_minutes)
    
    # Calculate metrics
    metrics = {}
    
    # Trip day length distribution
    metrics['trip_day_length'] = df['num_days'].value_counts().sort_index().to_dict()
    
    # Trips with one leg on last day
    one_leg_last_day = []
    for _, trip in df.iterrows():
        if trip['days'] and len(trip['days']) > 0:
            last_day = trip['days'][-1]
            if len(last_day.get('flights', [])) == 1:
                one_leg_last_day.append(trip['num_days'])
    
    if one_leg_last_day:
        metrics['one_leg_last_day'] = pd.Series(one_leg_last_day).value_counts().sort_index().to_dict()
    else:
        metrics['one_leg_last_day'] = {}
    
    # Average credit per trip
    metrics['avg_credit_per_trip'] = df['credit_minutes'].mean() / 60  # Convert to hours
    
    # Average credit per day
    total_days = df['num_days'].sum()
    total_credit = df['credit_minutes'].sum()
    metrics['avg_credit_per_day'] = (total_credit / total_days / 60) if total_days > 0 else 0
    
    # Red-eye detection (flights departing after 10 PM or arriving before 6 AM)
    # For this simplified version, we'll estimate based on TAFB and credit
    metrics['red_eye_count'] = 0  # Placeholder - would need flight time parsing
    
    # Commutability metrics (simplified - would need detailed flight time analysis)
    metrics['commute_front'] = "Analysis requires detailed flight times"
    metrics['commute_back'] = "Analysis requires detailed flight times"
    metrics['commute_both'] = "Analysis requires detailed flight times"
    
    # Additional useful metrics
    metrics['total_trips'] = len(df)
    metrics['avg_tafb'] = df['tafb_minutes'].mean() / 60  # Hours
    
    return metrics, df


def create_comparison_table(all_metrics, file_names):
    """Create a comparison table for multiple files"""
    comparison_data = []
    
    for file_name, metrics in zip(file_names, all_metrics):
        row = {
            'File': file_name,
            'Total Trips': metrics.get('total_trips', 0),
            'Avg Credit/Trip (hrs)': f"{metrics.get('avg_credit_per_trip', 0):.2f}",
            'Avg Credit/Day (hrs)': f"{metrics.get('avg_credit_per_day', 0):.2f}",
            'Avg TAFB (hrs)': f"{metrics.get('avg_tafb', 0):.2f}",
        }
        comparison_data.append(row)
    
    return pd.DataFrame(comparison_data)


def generate_pdf_report(metrics_list, file_names, base_filter="All"):
    """Generate PDF report of the analysis"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    story.append(Paragraph("Flight Bidding Data Analysis Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Metadata
    meta_style = styles['Normal']
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
    story.append(Paragraph(f"<b>Base Filter:</b> {base_filter}", meta_style))
    story.append(Paragraph(f"<b>Number of Files:</b> {len(file_names)}", meta_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary for each file
    for file_name, metrics in zip(file_names, metrics_list):
        story.append(Paragraph(f"<b>File: {file_name}</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        # Metrics table
        data = [
            ['Metric', 'Value'],
            ['Total Trips', str(metrics.get('total_trips', 0))],
            ['Avg Credit per Trip', f"{metrics.get('avg_credit_per_trip', 0):.2f} hours"],
            ['Avg Credit per Day', f"{metrics.get('avg_credit_per_day', 0):.2f} hours"],
            ['Avg TAFB', f"{metrics.get('avg_tafb', 0):.2f} hours"],
        ]
        
        # Trip day length distribution
        trip_lengths = metrics.get('trip_day_length', {})
        for days, count in sorted(trip_lengths.items()):
            data.append([f'{days}-Day Trips', str(count)])
        
        table = Table(data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def main():
    st.title("✈️ Flight Bidding Data Analyzer")
    st.markdown("Upload and analyze flight bidding data files (320, 737/738/73N, 7ER, 220, 330, 350, 717, 765)")
    
    # Initialize session state
    if 'uploaded_files_data' not in st.session_state:
        st.session_state.uploaded_files_data = {}
    if 'parsed_data' not in st.session_state:
        st.session_state.parsed_data = {}
    
    # Sidebar
    with st.sidebar:
        st.header("📁 File Upload")
        st.markdown("Upload 1-12 bidding data files")
        
        uploaded_files = st.file_uploader(
            "Choose text files",
            type=['txt'],
            accept_multiple_files=True,
            key='file_uploader'
        )
        
        if uploaded_files:
            if len(uploaded_files) > 12:
                st.error("⚠️ Maximum 12 files allowed. Please remove some files.")
            else:
                # Process uploaded files
                for uploaded_file in uploaded_files:
                    if uploaded_file.name not in st.session_state.uploaded_files_data:
                        file_content = uploaded_file.getvalue().decode('utf-8')
                        st.session_state.uploaded_files_data[uploaded_file.name] = file_content
                        
                        # Parse the file
                        trips = parse_bidding_file(file_content, uploaded_file.name)
                        st.session_state.parsed_data[uploaded_file.name] = trips
                
                st.success(f"✅ {len(uploaded_files)} file(s) loaded")
                
                # Show uploaded files
                st.markdown("### Uploaded Files:")
                for fname in st.session_state.uploaded_files_data.keys():
                    st.markdown(f"- {fname}")
        
        st.markdown("---")
        
        # Base filter
        st.header("🔍 Filters")
        
        # Extract all bases from parsed data
        all_bases = set()
        for trips in st.session_state.parsed_data.values():
            for trip in trips:
                if trip.get('base'):
                    all_bases.add(trip['base'])
        
        # Define base order
        base_order = ['ATL', 'BOS', 'NYC', 'DTW', 'SLC', 'MSP', 'SEA', 'LAX']
        ordered_bases = [b for b in base_order if b in all_bases]
        other_bases = sorted([b for b in all_bases if b not in base_order])
        
        base_options = ['All'] + ordered_bases + other_bases
        selected_base = st.selectbox("Select Base", base_options)
        
        st.markdown("---")
        
        # Clear button
        if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
            st.session_state.uploaded_files_data = {}
            st.session_state.parsed_data = {}
            st.rerun()
    
    # Main content
    if not st.session_state.parsed_data:
        st.info("👆 Please upload one or more bidding data files to begin analysis")
        
        # Show example metrics
        st.markdown("### 📊 Metrics That Will Be Analyzed:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            - **Trip Day Length**: Distribution of 1-day, 2-day, 3-day, 4-day trips
            - **One Leg Last Day**: Trips ending with single leg by trip length
            - **Average Credit per Trip**: Mean credit hours across all trips
            - **Average Credit per Day**: Mean credit per duty day
            """)
        with col2:
            st.markdown("""
            - **Red-eye Flights**: Late night/early morning flights
            - **Commutability - Front**: Front-end commutable trips
            - **Commutability - Back**: Back-end commutable trips
            - **Commutability - Both**: Fully commutable trips
            """)
    
    else:
        # Filter data by base
        filtered_data = {}
        for fname, trips in st.session_state.parsed_data.items():
            if selected_base == 'All':
                filtered_data[fname] = trips
            else:
                filtered_data[fname] = [t for t in trips if t.get('base') == selected_base]
        
        # Analyze each file
        all_metrics = []
        all_dfs = []
        
        for fname, trips in filtered_data.items():
            if trips:
                metrics, df = analyze_trips(trips)
                all_metrics.append(metrics)
                all_dfs.append(df)
            else:
                st.warning(f"No trips found for {fname} with base filter: {selected_base}")
        
        if not all_metrics:
            st.warning("No data available for the selected base filter")
            return
        
        # Display analysis
        if len(filtered_data) == 1:
            # Single file analysis
            fname = list(filtered_data.keys())[0]
            metrics = all_metrics[0]
            df = all_dfs[0]
            
            st.header(f"📈 Analysis: {fname}")
            st.markdown(f"**Base:** {selected_base} | **Total Trips:** {metrics['total_trips']}")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Credit/Trip", f"{metrics['avg_credit_per_trip']:.2f} hrs")
            with col2:
                st.metric("Avg Credit/Day", f"{metrics['avg_credit_per_day']:.2f} hrs")
            with col3:
                st.metric("Avg TAFB", f"{metrics['avg_tafb']:.2f} hrs")
            with col4:
                st.metric("Total Trips", metrics['total_trips'])
            
            st.markdown("---")
            
            # Trip length distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📅 Trip Day Length Distribution")
                trip_length_data = metrics['trip_day_length']
                if trip_length_data:
                    fig = px.bar(
                        x=list(trip_length_data.keys()),
                        y=list(trip_length_data.values()),
                        labels={'x': 'Number of Days', 'y': 'Number of Trips'},
                        title="Trips by Length"
                    )
                    fig.update_traces(marker_color='#1f77b4')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show table
                    df_display = pd.DataFrame({
                        'Trip Length': [f"{k}-Day" for k in trip_length_data.keys()],
                        'Count': list(trip_length_data.values())
                    })
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            with col2:
                st.subheader("🛬 One Leg on Last Day")
                one_leg_data = metrics['one_leg_last_day']
                if one_leg_data:
                    fig = px.bar(
                        x=list(one_leg_data.keys()),
                        y=list(one_leg_data.values()),
                        labels={'x': 'Trip Length (Days)', 'y': 'Count'},
                        title="Trips with One Leg on Last Day"
                    )
                    fig.update_traces(marker_color='#ff7f0e')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    df_display = pd.DataFrame({
                        'Trip Length': [f"{k}-Day" for k in one_leg_data.keys()],
                        'Count': list(one_leg_data.values())
                    })
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No trips with one leg on last day found")
            
            # Commutability section (placeholder)
            st.markdown("---")
            st.subheader("🏠 Commutability Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info("**Front Commutability**\n\nRequires detailed flight time analysis")
            with col2:
                st.info("**Back Commutability**\n\nRequires detailed flight time analysis")
            with col3:
                st.info("**Both Commutable**\n\nRequires detailed flight time analysis")
        
        else:
            # Multiple file comparison
            st.header(f"📊 Comparison Analysis ({len(filtered_data)} files)")
            st.markdown(f"**Base Filter:** {selected_base}")
            
            # Comparison table
            comparison_df = create_comparison_table(all_metrics, list(filtered_data.keys()))
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Comparison charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Avg Credit per Trip Comparison")
                fig = px.bar(
                    comparison_df,
                    x='File',
                    y='Avg Credit/Trip (hrs)',
                    title="Average Credit per Trip"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Avg Credit per Day Comparison")
                fig = px.bar(
                    comparison_df,
                    x='File',
                    y='Avg Credit/Day (hrs)',
                    title="Average Credit per Day"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Trip length distribution comparison
            st.markdown("---")
            st.subheader("📅 Trip Length Distribution Comparison")
            
            # Prepare data for grouped bar chart
            trip_length_comparison = []
            for fname, metrics in zip(filtered_data.keys(), all_metrics):
                for days, count in metrics['trip_day_length'].items():
                    trip_length_comparison.append({
                        'File': fname,
                        'Days': f"{days}-Day",
                        'Count': count
                    })
            
            if trip_length_comparison:
                df_trip_comp = pd.DataFrame(trip_length_comparison)
                fig = px.bar(
                    df_trip_comp,
                    x='Days',
                    y='Count',
                    color='File',
                    barmode='group',
                    title="Trip Length Distribution by File"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Export button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            pdf_buffer = generate_pdf_report(
                all_metrics,
                list(filtered_data.keys()),
                selected_base
            )
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_buffer,
                file_name=f"bidding_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )


if __name__ == "__main__":
    main()
