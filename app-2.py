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


def calculate_trip_length(trip):
    """Calculate trip length with red-eye rule"""
    if not trip.get('days'):
        return 0
    
    # Base length from last day letter
    day_letters = ['A', 'B', 'C', 'D', 'E']
    last_day = trip['days'][-1]['day']
    base_length = day_letters.index(last_day) + 1
    
    # Check red-eye rule on last flight
    if trip.get('flights'):
        last_flight = trip['flights'][-1]
        dep_time = int(last_flight['departure_time'])
        arr_time = int(last_flight['arrival_time'])
        
        # Red-eye rule: departs >= 2000 AND arrives >= 0200
        if dep_time >= 2000 and arr_time >= 200:
            return base_length + 1
    
    return base_length


def get_base_last_day(trip):
    """Get the base last day letter (before red-eye adjustment)"""
    if not trip.get('days'):
        return None
    return trip['days'][-1]['day']
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


def parse_bidding_file(file_content, filename, month_name, year):
    """Parse the bidding data file and extract trip information with occurrence counting"""
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    lines = file_content.split('\n')
    
    # Month name to number
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    month_num = month_map.get(month_name, 1)
    
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
    
    # Day of week codes
    dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
    
    trips = []
    current_trip = None
    current_days = []
    first_departure_found = False
    current_day_letter = None
    
    for i, line in enumerate(lines):
        # Detect trip number and parse effective dates
        trip_match = re.search(r'^\s+#(\d+)\s+([A-Z\s]+?)\s+EFFECTIVE\s+(.+?)\s+CHECK-IN', line)
        if trip_match:
            # Save previous trip if exists
            if current_trip:
                current_trip['days'] = current_days
                trips.append(current_trip)
            
            # Parse trip header
            trip_number = trip_match.group(1)
            days_of_week_str = trip_match.group(2).strip()
            effective_dates = trip_match.group(3).strip()
            
            # Extract days of week
            days_of_week = []
            for dow_code in ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']:
                if dow_code in days_of_week_str:
                    days_of_week.append(dow_map[dow_code])
            
            # Start new trip
            current_trip = {
                'trip_number': trip_number,
                'days_of_week': days_of_week,
                'effective_dates': effective_dates,
                'except_dates': [],
                'occurrences': 0,  # Will be calculated
                'base': None,
                'filename': filename,
                'month': month_name,
                'year': year,
                'first_departure': None,
                'flights': []
            }
            current_days = []
            first_departure_found = False
            current_day_letter = None
            continue
        
        # Detect EXCEPT dates
        if current_trip and 'EXCEPT' in line:
            except_match = re.findall(r'([A-Z]{3}\s?\d+)', line)
            for date_str in except_match:
                current_trip['except_dates'].append(date_str.replace(' ', ''))
        
        # Detect day lines and flight information
        if current_trip:
            # Regular flight: A FLIGHT# DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            flight_match = re.search(r'^\s+([A-E])\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\*?\s+([A-Z]{3})\s+(\d{4})\*?', line)
            # Deadhead flight: A DH FLIGHT# DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            dh_match = re.search(r'^\s+([A-E])\s+DH\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\*?\s+([A-Z]{3})\s+(\d{4})\*?', line)
            # Continuation flight (no day letter): FLIGHT# DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            cont_match = re.search(r'^\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\*?\s+([A-Z]{3})\s+(\d{4})\*?', line) if current_day_letter else None
            # Continuation flight without flight number: DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            cont_no_num_match = re.search(r'^\s+([A-Z]{3})\s+(\d{4})\*?\s+([A-Z]{3})\s+(\d{4})\*?', line) if current_day_letter else None
            # Continuation DH flight
            cont_dh_match = re.search(r'^\s+DH\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\*?\s+([A-Z]{3})\s+(\d{4})\*?', line) if current_day_letter else None
            
            if flight_match:
                day_letter = flight_match.group(1)
                flight_num = flight_match.group(2)
                dep_airport = flight_match.group(3)
                dep_time = flight_match.group(4)
                arr_airport = flight_match.group(5)
                arr_time = flight_match.group(6)
                
                flight_info = {
                    'day': day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': False
                }
                
                current_trip['flights'].append(flight_info)
                
                # Determine base from first flight
                if not first_departure_found:
                    current_trip['first_departure'] = dep_airport
                    current_trip['base'] = airport_to_base.get(dep_airport, 'UNKNOWN')
                    first_departure_found = True
                
                # Track days
                if day_letter != current_day_letter:
                    current_day_letter = day_letter
                    if day_letter not in [d['day'] for d in current_days]:
                        current_days.append({'day': day_letter, 'flights': []})
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == day_letter:
                        day['flights'].append(flight_num)
                        break
            
            elif dh_match:
                day_letter = dh_match.group(1)
                flight_num = dh_match.group(2)
                dep_airport = dh_match.group(3)
                dep_time = dh_match.group(4)
                arr_airport = dh_match.group(5)
                arr_time = dh_match.group(6)
                
                flight_info = {
                    'day': day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': True
                }
                
                current_trip['flights'].append(flight_info)
                
                # Determine base from first flight (even if DH)
                if not first_departure_found:
                    current_trip['first_departure'] = dep_airport
                    current_trip['base'] = airport_to_base.get(dep_airport, 'UNKNOWN')
                    first_departure_found = True
                
                # Track days
                if day_letter != current_day_letter:
                    current_day_letter = day_letter
                    if day_letter not in [d['day'] for d in current_days]:
                        current_days.append({'day': day_letter, 'flights': []})
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == day_letter:
                        day['flights'].append(flight_num)
                        break
            
            elif cont_match:
                # Continuation flight - uses current_day_letter
                flight_num = cont_match.group(1)
                dep_airport = cont_match.group(2)
                dep_time = cont_match.group(3)
                arr_airport = cont_match.group(4)
                arr_time = cont_match.group(5)
                
                flight_info = {
                    'day': current_day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': False
                }
                
                current_trip['flights'].append(flight_info)
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == current_day_letter:
                        day['flights'].append(flight_num)
                        break
            
            elif cont_no_num_match:
                # Continuation flight without flight number - uses current_day_letter
                dep_airport = cont_no_num_match.group(1)
                dep_time = cont_no_num_match.group(2)
                arr_airport = cont_no_num_match.group(3)
                arr_time = cont_no_num_match.group(4)
                
                flight_info = {
                    'day': current_day_letter,
                    'flight_number': 'CONT',  # No flight number available
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': False
                }
                
                current_trip['flights'].append(flight_info)
                
                # Add to current day (using placeholder flight number)
                for day in current_days:
                    if day['day'] == current_day_letter:
                        day['flights'].append('CONT')
                        break
            
            elif cont_dh_match:
                # Continuation deadhead - uses current_day_letter
                flight_num = cont_dh_match.group(1)
                dep_airport = cont_dh_match.group(2)
                dep_time = cont_dh_match.group(3)
                arr_airport = cont_dh_match.group(4)
                arr_time = cont_dh_match.group(5)
                
                flight_info = {
                    'day': current_day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': True
                }
                
                current_trip['flights'].append(flight_info)
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == current_day_letter:
                        day['flights'].append(flight_num)
                        break
        
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
    
    # Calculate occurrences for each trip
    for trip in trips:
        trip['occurrences'] = calculate_occurrences(
            trip['days_of_week'],
            trip['effective_dates'],
            trip['except_dates'],
            month_num,
            year
        )
    
    return trips


def calculate_occurrences(days_of_week, effective_dates, except_dates, month_num, year):
    """Calculate how many times a trip occurs based on date range and days of week"""
    from datetime import datetime, timedelta
    
    if not days_of_week:
        return 1  # Default to 1 if no days specified
    
    # Parse effective date range
    # Formats: "JAN01 ONLY", "JAN21-JAN. 28", "DEC31-JAN. 09"
    
    if 'ONLY' in effective_dates:
        # Single date
        date_match = re.search(r'([A-Z]{3})(\d+)', effective_dates)
        if date_match:
            month_str = date_match.group(1)
            day = int(date_match.group(2))
            
            # Convert month abbreviation
            month_abbr_map = {
                'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
            }
            month = month_abbr_map.get(month_str, month_num)
            
            # Check if this date's day of week is in the specified days
            try:
                date = datetime(year, month, day)
                if date.weekday() in days_of_week:
                    return 1
            except:
                pass
            return 0
    
    # Date range
    range_match = re.search(r'([A-Z]{3})(\d+)-([A-Z]{3})\.\s*(\d+)', effective_dates)
    if range_match:
        start_month_str = range_match.group(1)
        start_day = int(range_match.group(2))
        end_month_str = range_match.group(3)
        end_day = int(range_match.group(4))
        
        month_abbr_map = {
            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
        }
        
        start_month = month_abbr_map.get(start_month_str, month_num)
        end_month = month_abbr_map.get(end_month_str, month_num)
        
        # Handle year boundary crossing (e.g., DEC31-JAN09)
        start_year = year
        end_year = year
        if start_month > end_month:
            start_year = year - 1
        
        try:
            start_date = datetime(start_year, start_month, start_day)
            end_date = datetime(end_year, end_month, end_day)
            
            # Count occurrences
            count = 0
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in days_of_week:
                    # Check if this date is in except_dates
                    date_str = f"{current_date.strftime('%b').upper()}{current_date.day:02d}"
                    date_str_no_zero = f"{current_date.strftime('%b').upper()}{current_date.day}"
                    
                    if date_str not in except_dates and date_str_no_zero not in except_dates:
                        count += 1
                
                current_date += timedelta(days=1)
            
            return count
        except:
            pass
    
    return 1  # Default to 1 if parsing fails
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
    current_day_letter = None
    
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
                'base': None,
                'filename': filename,
                'first_departure': None,
                'flights': []  # Store all flight details
            }
            current_days = []
            first_departure_found = False
            current_day_letter = None
            continue
        
        # Detect day lines and flight information
        if current_trip:
            # Regular flight: A FLIGHT# DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            flight_match = re.search(r'^\s+([A-D])\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\s+([A-Z]{3})\s+(\d{4})', line)
            # Deadhead flight: A DH FLIGHT# DEPART_AIRPORT TIME ARRIVE_AIRPORT TIME
            dh_match = re.search(r'^\s+([A-D])\s+DH\s+(\d+)\s+([A-Z]{3})\s+(\d{4})\s+([A-Z]{3})\s+(\d{4})', line)
            
            if flight_match:
                day_letter = flight_match.group(1)
                flight_num = flight_match.group(2)
                dep_airport = flight_match.group(3)
                dep_time = flight_match.group(4)
                arr_airport = flight_match.group(5)
                arr_time = flight_match.group(6)
                
                flight_info = {
                    'day': day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': False
                }
                
                current_trip['flights'].append(flight_info)
                
                # Determine base from first flight
                if not first_departure_found:
                    current_trip['first_departure'] = dep_airport
                    current_trip['base'] = airport_to_base.get(dep_airport, 'UNKNOWN')
                    first_departure_found = True
                
                # Track days
                if day_letter != current_day_letter:
                    current_day_letter = day_letter
                    if day_letter not in [d['day'] for d in current_days]:
                        current_days.append({'day': day_letter, 'flights': []})
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == day_letter:
                        day['flights'].append(flight_num)
                        break
            
            elif dh_match:
                day_letter = dh_match.group(1)
                flight_num = dh_match.group(2)
                dep_airport = dh_match.group(3)
                dep_time = dh_match.group(4)
                arr_airport = dh_match.group(5)
                arr_time = dh_match.group(6)
                
                flight_info = {
                    'day': day_letter,
                    'flight_number': flight_num,
                    'departure_airport': dep_airport,
                    'departure_time': dep_time,
                    'arrival_airport': arr_airport,
                    'arrival_time': arr_time,
                    'is_deadhead': True
                }
                
                current_trip['flights'].append(flight_info)
                
                # Determine base from first flight (even if DH)
                if not first_departure_found:
                    current_trip['first_departure'] = dep_airport
                    current_trip['base'] = airport_to_base.get(dep_airport, 'UNKNOWN')
                    first_departure_found = True
                
                # Track days
                if day_letter != current_day_letter:
                    current_day_letter = day_letter
                    if day_letter not in [d['day'] for d in current_days]:
                        current_days.append({'day': day_letter, 'flights': []})
                
                # Add flight to current day
                for day in current_days:
                    if day['day'] == day_letter:
                        day['flights'].append(flight_num)
                        break
        
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


def get_base_last_day(trip):
    """Get the base last day letter (before red-eye adjustment)"""
    if not trip.get('days'):
        return None
    return trip['days'][-1]['day']


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


def analyze_trips(trips_data, front_commute_time='1000', back_commute_time='2000'):
    """Analyze trip data and calculate metrics with proper occurrence counting"""
    if not trips_data:
        return None
    
    df = pd.DataFrame(trips_data)
    
    # Ensure occurrences field exists (for backwards compatibility)
    if 'occurrences' not in df.columns:
        df['occurrences'] = 1
    
    # Calculate trip lengths with red-eye rule
    df['trip_length'] = df.apply(calculate_trip_length, axis=1)
    df['base_last_day'] = df.apply(get_base_last_day, axis=1)
    df['credit_minutes'] = df['total_credit'].apply(parse_time_to_minutes)
    df['tafb_minutes'] = df['tafb'].apply(parse_time_to_minutes)
    df['occurrences'] = df['occurrences'].fillna(1).astype(int)
    
    # Calculate metrics
    metrics = {}
    
    # Trip day length distribution (weighted by occurrences)
    trip_length_counts = {}
    for _, trip in df.iterrows():
        length = trip['trip_length']
        occurrences = trip['occurrences']
        trip_length_counts[length] = trip_length_counts.get(length, 0) + occurrences
    
    metrics['trip_day_length'] = trip_length_counts
    
    # Trips with one leg on last day - count if the last day letter has exactly ONE flight leg total
    one_leg_last_day_counts = {}
    for _, trip in df.iterrows():
        if trip['days'] and len(trip['days']) > 0 and trip.get('flights'):
            # Get the base last day letter (before red-eye adjustment)
            last_day_letter = trip['days'][-1]['day']
            
            # Count total flights on the last day (any flights, not just to base)
            flights_on_last_day = 0
            for flight in trip['flights']:
                if flight['day'] == last_day_letter:
                    flights_on_last_day += 1
            
            # Only count if exactly 1 flight leg on last day
            if flights_on_last_day == 1:
                length = trip['trip_length']
                occurrences = trip['occurrences']
                one_leg_last_day_counts[length] = one_leg_last_day_counts.get(length, 0) + occurrences
    
    metrics['one_leg_last_day'] = one_leg_last_day_counts
    
    # Average credit per trip (by trip length, weighted by occurrences)
    credit_by_length = {}
    count_by_length = {}
    
    for _, trip in df.iterrows():
        length = trip['trip_length']
        credit = trip['credit_minutes']
        occurrences = trip['occurrences']
        
        if length not in credit_by_length:
            credit_by_length[length] = 0
            count_by_length[length] = 0
        
        credit_by_length[length] += credit * occurrences
        count_by_length[length] += occurrences
    
    avg_credit_per_trip = {}
    for length in credit_by_length:
        if count_by_length[length] > 0:
            avg_credit_per_trip[length] = credit_by_length[length] / count_by_length[length] / 60  # Convert to hours
    
    metrics['avg_credit_per_trip'] = avg_credit_per_trip
    
    # Overall average credit per trip
    total_credit = sum(credit_by_length.values())
    total_count = sum(count_by_length.values())
    metrics['avg_credit_per_trip_overall'] = (total_credit / total_count / 60) if total_count > 0 else 0
    
    # Average credit per day (credit / trip_length, weighted by occurrences)
    credit_per_day_by_length = {}
    
    for _, trip in df.iterrows():
        length = trip['trip_length']
        if length == 0:
            continue
        
        credit = trip['credit_minutes']
        occurrences = trip['occurrences']
        credit_per_day = credit / length
        
        if length not in credit_per_day_by_length:
            credit_per_day_by_length[length] = []
        
        for _ in range(occurrences):
            credit_per_day_by_length[length].append(credit_per_day)
    
    avg_credit_per_day = {}
    for length in credit_per_day_by_length:
        avg_credit_per_day[length] = sum(credit_per_day_by_length[length]) / len(credit_per_day_by_length[length]) / 60  # Convert to hours
    
    metrics['avg_credit_per_day'] = avg_credit_per_day
    
    # Overall average credit per day
    all_credit_per_day = []
    for length_list in credit_per_day_by_length.values():
        all_credit_per_day.extend(length_list)
    metrics['avg_credit_per_day_overall'] = (sum(all_credit_per_day) / len(all_credit_per_day) / 60) if all_credit_per_day else 0
    
    # Red-eye analysis (ANY leg meets criteria, weighted by occurrences)
    red_eye_by_length = {}
    
    for _, trip in df.iterrows():
        length = trip['trip_length']
        occurrences = trip['occurrences']
        has_red_eye_flight = has_red_eye_updated(trip)
        
        if length not in red_eye_by_length:
            red_eye_by_length[length] = {'with_red_eye': 0, 'total': 0}
        
        red_eye_by_length[length]['total'] += occurrences
        if has_red_eye_flight:
            red_eye_by_length[length]['with_red_eye'] += occurrences
    
    metrics['red_eye_by_length'] = red_eye_by_length
    
    # Commutability analysis with custom times
    commute_by_length = {}
    
    for _, trip in df.iterrows():
        length = trip['trip_length']
        occurrences = trip['occurrences']
        base = trip.get('base')
        
        if length not in commute_by_length:
            commute_by_length[length] = {
                'front': 0, 'back': 0, 'both': 0, 'total': 0
            }
        
        commute_by_length[length]['total'] += occurrences
        
        # Calculate report time (first departure - 60 minutes)
        report_time = calculate_report_time(trip)
        is_front_commutable = report_time >= int(front_commute_time) if report_time else False
        
        # Calculate release time (last ATL arrival + 45 minutes)
        release_time = calculate_release_time(trip, base)
        is_back_commutable = release_time <= int(back_commute_time) if release_time else False
        
        if is_front_commutable:
            commute_by_length[length]['front'] += occurrences
        if is_back_commutable:
            commute_by_length[length]['back'] += occurrences
        if is_front_commutable and is_back_commutable:
            commute_by_length[length]['both'] += occurrences
    
    metrics['commute_by_length'] = commute_by_length
    
    # Overall totals
    metrics['total_trips'] = total_count
    metrics['total_occurrences'] = total_count
    metrics['avg_tafb'] = (df['tafb_minutes'] * df['occurrences']).sum() / total_count / 60 if total_count > 0 else 0
    
    return metrics, df
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
    
    # Commutability analysis - parse flight times from the raw data
    commute_front = 0
    commute_back = 0
    commute_both = 0
    
    for _, trip in df.iterrows():
        base = trip.get('base')
        if not base or not trip.get('days'):
            continue
        
        # Get first and last day
        days = trip['days']
        if not days:
            continue
            
        first_day = days[0]
        last_day = days[-1]
        
        # Extract first departure time from first day
        first_departure_time = extract_first_flight_time(trip, first_day, base)
        
        # Extract last arrival time from last day
        last_arrival_time = extract_last_flight_time(trip, last_day, base)
        
        # Check commutability
        is_front_commutable = first_departure_time >= front_commute_time if first_departure_time else False
        is_back_commutable = last_arrival_time <= back_commute_time if last_arrival_time else False
        
        if is_front_commutable:
            commute_front += 1
        if is_back_commutable:
            commute_back += 1
        if is_front_commutable and is_back_commutable:
            commute_both += 1
    
    metrics['commute_front'] = commute_front
    metrics['commute_back'] = commute_back
    metrics['commute_both'] = commute_both
    
    # Red-eye detection (flights departing after 2200 or arriving before 0600)
    red_eye_count = 0
    for _, trip in df.iterrows():
        if has_red_eye(trip):
            red_eye_count += 1
    
    metrics['red_eye_count'] = red_eye_count
    
    # Additional useful metrics
    metrics['total_trips'] = len(df)
    metrics['avg_tafb'] = df['tafb_minutes'].mean() / 60  # Hours
    
    return metrics, df



def has_red_eye_updated(trip):
    """Check if trip contains a red-eye flight (ANY leg: departs >=2000 AND arrives >=0200)"""
    if not trip.get('flights'):
        return False
    
    for flight in trip['flights']:
        try:
            dep_time = int(flight.get('departure_time', '0000'))
            arr_time = int(flight.get('arrival_time', '0000'))
            
            # Check if departure >= 2000 AND arrival >= 0200
            if dep_time >= 2000 and arr_time >= 200:
                return True
        except:
            continue
    
    return False


def calculate_report_time(trip):
    """Calculate report time: first departure - 60 minutes"""
    if not trip.get('flights'):
        return None
    
    try:
        first_dep_time = int(trip['flights'][0]['departure_time'])
        
        # Convert to minutes
        hours = first_dep_time // 100
        minutes = first_dep_time % 100
        total_minutes = hours * 60 + minutes
        
        # Subtract 60 minutes
        report_minutes = total_minutes - 60
        
        # Handle wraparound
        if report_minutes < 0:
            report_minutes += 1440  # Add 24 hours
        
        # Convert back to HHMM format
        report_hours = report_minutes // 60
        report_mins = report_minutes % 60
        return report_hours * 100 + report_mins
    except:
        return None


def calculate_release_time(trip, base):
    """Calculate release time: last arrival at base + 45 minutes"""
    if not trip.get('flights') or not base:
        return None
    
    # Get base airports
    base_airports = {
        'ATL': ['ATL'],
        'BOS': ['BOS'],
        'NYC': ['JFK', 'LGA', 'EWR'],
        'DTW': ['DTW'],
        'SLC': ['SLC'],
        'MSP': ['MSP'],
        'SEA': ['SEA'],
        'LAX': ['LAX', 'LGB', 'ONT']
    }
    
    airports = base_airports.get(base, [])
    
    # Find last arrival at base
    last_arrival_time = None
    for flight in reversed(trip['flights']):
        if flight['arrival_airport'] in airports:
            last_arrival_time = flight['arrival_time']
            break
    
    if not last_arrival_time:
        return None
    
    try:
        arr_time = int(last_arrival_time)
        
        # Convert to minutes
        hours = arr_time // 100
        minutes = arr_time % 100
        total_minutes = hours * 60 + minutes
        
        # Add 45 minutes
        release_minutes = total_minutes + 45
        
        # Handle wraparound
        if release_minutes >= 1440:
            release_minutes -= 1440  # Subtract 24 hours
        
        # Convert back to HHMM format
        release_hours = release_minutes // 60
        release_mins = release_minutes % 60
        return release_hours * 100 + release_mins
    except:
        return None


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
            ['Avg Credit per Trip', f"{metrics.get('avg_credit_per_trip_overall', 0):.2f} hours"],
            ['Avg Credit per Day', f"{metrics.get('avg_credit_per_day_overall', 0):.2f} hours"],
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
    if 'file_metadata' not in st.session_state:
        st.session_state.file_metadata = {}  # Store month/year for each file
    
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
                new_files = []
                for uploaded_file in uploaded_files:
                    if uploaded_file.name not in st.session_state.uploaded_files_data:
                        new_files.append(uploaded_file)
                
                # If there are new files, prompt for month/year
                if new_files:
                    st.markdown("### 📅 Set Date for New Files")
                    
                    for uploaded_file in new_files:
                        with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                month = st.selectbox(
                                    "Month",
                                    options=['January', 'February', 'March', 'April', 'May', 'June',
                                            'July', 'August', 'September', 'October', 'November', 'December'],
                                    key=f"month_{uploaded_file.name}"
                                )
                            
                            with col2:
                                year = st.number_input(
                                    "Year",
                                    min_value=2020,
                                    max_value=2030,
                                    value=2026,
                                    step=1,
                                    key=f"year_{uploaded_file.name}"
                                )
                            
                            if st.button(f"Process {uploaded_file.name}", key=f"process_{uploaded_file.name}"):
                                file_content = uploaded_file.getvalue().decode('utf-8')
                                st.session_state.uploaded_files_data[uploaded_file.name] = file_content
                                
                                # Store metadata
                                st.session_state.file_metadata[uploaded_file.name] = {
                                    'month': month,
                                    'year': year
                                }
                                
                                # Parse the file
                                trips = parse_bidding_file(file_content, uploaded_file.name, month, year)
                                st.session_state.parsed_data[uploaded_file.name] = trips
                                
                                st.success(f"✅ {uploaded_file.name} processed for {month} {year}")
                                st.rerun()
                
                # Show already processed files
                if st.session_state.uploaded_files_data:
                    st.markdown("### Uploaded Files:")
                    for fname in st.session_state.uploaded_files_data.keys():
                        metadata = st.session_state.file_metadata.get(fname, {})
                        month = metadata.get('month', 'Unknown')
                        year = metadata.get('year', 'Unknown')
                        st.markdown(f"- {fname} ({month} {year})")
        
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
        
        # Commutability time selectors
        st.header("⏰ Commutability Times")
        st.markdown("Set time windows for commutable trips")
        
        # Generate 24-hour time options in 30-minute intervals
        time_options = []
        for hour in range(24):
            for minute in ['00', '30']:
                time_options.append(f"{hour:02d}{minute}")
        
        # Front end commutability
        front_commute_time = st.selectbox(
            "Front-End Commutable After",
            options=time_options,
            index=time_options.index('1000'),  # Default 10:00
            help="First departure must be at or after this time"
        )
        
        # Back end commutability
        back_commute_time = st.selectbox(
            "Back-End Commutable Before",
            options=time_options,
            index=time_options.index('2000'),  # Default 20:00
            help="Last arrival must be at or before this time"
        )
        
        # Display selected times in readable format
        front_hour = int(front_commute_time[:2])
        front_min = front_commute_time[2:]
        back_hour = int(back_commute_time[:2])
        back_min = back_commute_time[2:]
        
        st.caption(f"✈️ Front: After {front_hour:02d}:{front_min}")
        st.caption(f"🏠 Back: Before {back_hour:02d}:{back_min}")
        
        st.markdown("---")
        
        # Clear button
        if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
            st.session_state.uploaded_files_data = {}
            st.session_state.parsed_data = {}
            st.session_state.file_metadata = {}
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
                metrics, df = analyze_trips(trips, front_commute_time, back_commute_time)
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
            
            # Get file metadata
            file_meta = st.session_state.file_metadata.get(fname, {})
            month_year = f"{file_meta.get('month', 'Unknown')} {file_meta.get('year', '')}" if file_meta else "Unknown"
            
            st.markdown(f"**Base:** {selected_base} | **Period:** {month_year} | **Total Trips:** {metrics['total_trips']}")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Avg Credit/Trip", f"{metrics.get('avg_credit_per_trip_overall', 0):.2f} hrs")
            with col2:
                st.metric("Avg Credit/Day", f"{metrics.get('avg_credit_per_day_overall', 0):.2f} hrs")
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
                total_trips = metrics['total_trips']
                
                if trip_length_data:
                    fig = px.bar(
                        x=list(trip_length_data.keys()),
                        y=list(trip_length_data.values()),
                        labels={'x': 'Number of Days', 'y': 'Number of Trips'},
                        title="Trips by Length"
                    )
                    fig.update_traces(marker_color='#1f77b4')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show table with percentages
                    df_display = pd.DataFrame({
                        'Trip Length': [f"{k}-Day" for k in trip_length_data.keys()],
                        'Count': list(trip_length_data.values()),
                        'Percentage': [f"{(v/total_trips*100):.1f}%" for v in trip_length_data.values()]
                    })
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    st.caption(f"**Total: {total_trips} trips**")
            
            with col2:
                st.subheader("🛬 One Leg on Last Day")
                one_leg_data = metrics['one_leg_last_day']
                if one_leg_data:
                    one_leg_total = sum(one_leg_data.values())
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
                        'Count': list(one_leg_data.values()),
                        'Percentage': [f"{(v/total_trips*100):.1f}%" for v in one_leg_data.values()]
                    })
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    st.caption(f"**Total: {one_leg_total} trips ({one_leg_total/total_trips*100:.1f}% of all trips)**")
                else:
                    st.info("No trips with one leg on last day found")
            
            # Commutability section
            st.markdown("---")
            st.subheader("🏠 Commutability Analysis")
            
            # Display selected times
            front_hour = int(front_commute_time[:2])
            front_min = front_commute_time[2:]
            back_hour = int(back_commute_time[:2])
            back_min = back_commute_time[2:]
            
            st.caption(f"Report time threshold: {front_hour:02d}:{front_min} (First departure - 60 min) | " +
                      f"Release time threshold: {back_hour:02d}:{back_min} (Last base arrival + 45 min)")
            
            # Calculate totals from commute_by_length
            commute_by_length = metrics.get('commute_by_length', {})
            total_front = sum(data['front'] for data in commute_by_length.values())
            total_back = sum(data['back'] for data in commute_by_length.values())
            total_both = sum(data['both'] for data in commute_by_length.values())
            
            # Calculate total red-eyes
            red_eye_by_length = metrics.get('red_eye_by_length', {})
            total_red_eye = sum(data['with_red_eye'] for data in red_eye_by_length.values())
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                front_pct = (total_front / total_trips * 100) if total_trips > 0 else 0
                st.metric("Front Commutable", f"{total_front}", f"{front_pct:.1f}%")
            
            with col2:
                back_pct = (total_back / total_trips * 100) if total_trips > 0 else 0
                st.metric("Back Commutable", f"{total_back}", f"{back_pct:.1f}%")
            
            with col3:
                both_pct = (total_both / total_trips * 100) if total_trips > 0 else 0
                st.metric("Both Commutable", f"{total_both}", f"{both_pct:.1f}%")
            
            with col4:
                red_eye_pct = (total_red_eye / total_trips * 100) if total_trips > 0 else 0
                st.metric("Red-Eye Trips", f"{total_red_eye}", f"{red_eye_pct:.1f}%")
            
            # Detailed metrics by trip length
            st.markdown("---")
            st.subheader("📋 Detailed Metrics by Trip Length")
            
            # Build detailed table
            detailed_data = []
            for length in sorted(metrics.get('trip_day_length', {}).keys()):
                trip_count = metrics['trip_day_length'].get(length, 0)
                
                # Credit metrics
                avg_credit_trip = metrics.get('avg_credit_per_trip', {}).get(length, 0)
                avg_credit_day = metrics.get('avg_credit_per_day', {}).get(length, 0)
                
                # Red-eye
                red_eye_data = metrics.get('red_eye_by_length', {}).get(length, {'with_red_eye': 0, 'total': 0})
                red_eye_pct = (red_eye_data['with_red_eye'] / red_eye_data['total'] * 100) if red_eye_data['total'] > 0 else 0
                
                # Commutability
                commute_data = metrics.get('commute_by_length', {}).get(length, {'front': 0, 'back': 0, 'both': 0, 'total': 0})
                front_pct = (commute_data['front'] / commute_data['total'] * 100) if commute_data['total'] > 0 else 0
                back_pct = (commute_data['back'] / commute_data['total'] * 100) if commute_data['total'] > 0 else 0
                both_pct = (commute_data['both'] / commute_data['total'] * 100) if commute_data['total'] > 0 else 0
                
                detailed_data.append({
                    'Trip Length': f"{length}-Day",
                    'Count': trip_count,
                    '% of Total': f"{(trip_count/total_trips*100):.1f}%",
                    'Avg Credit/Trip': f"{avg_credit_trip:.2f}h",
                    'Avg Credit/Day': f"{avg_credit_day:.2f}h",
                    'Red-Eye %': f"{red_eye_pct:.1f}%",
                    'Front Commute %': f"{front_pct:.1f}%",
                    'Back Commute %': f"{back_pct:.1f}%",
                    'Both Commute %': f"{both_pct:.1f}%"
                })
            
            if detailed_data:
                df_detailed = pd.DataFrame(detailed_data)
                st.dataframe(df_detailed, use_container_width=True, hide_index=True)
        
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
