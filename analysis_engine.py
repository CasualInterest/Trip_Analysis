"""
Core analysis engine for pilot trip data
Contains all the calculation logic from the original analysis
"""

from datetime import datetime, timedelta
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

# Base mapping
BASE_MAPPING = {
    'ATL': 'ATL',
    'BOS': 'BOS',
    'JFK': 'NYC', 'LGA': 'NYC', 'EWR': 'NYC',
    'DTW': 'DTW',
    'SLC': 'SLC',
    'MSP': 'MSP',
    'SEA': 'SEA',
    'LAX': 'LAX', 'LGB': 'LAX', 'ONT': 'LAX'
}

def parse_trips(file_content):
    """Parse the trip file content"""
    trips = []
    current_trip = []
    in_trip = False
    
    lines = file_content.split('\n')
    for line in lines:
        if 'EFFECTIVE' in line:
            in_trip = True
            current_trip = [line]
        elif in_trip:
            current_trip.append(line)
            if line.strip().startswith('---'):
                trips.append(current_trip)
                current_trip = []
                in_trip = False
    
    return trips

def get_effective_dates(trip_lines):
    """Parse EFFECTIVE date range, days of week, and EXCEPT dates"""
    header_line = ""
    except_line = ""
    
    for line in trip_lines:
        if 'EFFECTIVE' in line:
            header_line = line
        elif 'EXCEPT' in line:
            except_line = line
    
    if not header_line:
        return [], None, None, 1
    
    # Extract days of week
    dow_pattern = r'\b(MO|TU|WE|TH|FR|SA|SU)\b'
    days_of_week = re.findall(dow_pattern, header_line)
    
    # Try "JAN## ONLY" pattern
    only_match = re.search(r'(JAN|DEC)(\d{1,2})\s+ONLY', header_line)
    if only_match:
        month = only_match.group(1)
        day = int(only_match.group(2))
        year = 2025 if month == 'DEC' else 2026
        
        date = datetime(year, 12 if month == 'DEC' else 1, day)
        
        dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
        actual_dow = date.weekday()
        
        for dow in days_of_week:
            if dow_map[dow] == actual_dow:
                return days_of_week, date, date, 1
        
        return days_of_week, date, date, 0
    
    # Try date range patterns
    range_match = re.search(r'(DEC|JAN)(\d{1,2})-(JAN|DEC)\.\s*(\d{1,2})', header_line)
    if not range_match:
        range_match = re.search(r'(JAN)(\d{1,2})-(\d{1,2})', header_line)
        if range_match:
            start_day = int(range_match.group(2))
            end_day = int(range_match.group(3))
            start_date = datetime(2026, 1, start_day)
            end_date = datetime(2026, 1, end_day)
        else:
            return days_of_week, None, None, 1
    else:
        start_month = range_match.group(1)
        start_day = int(range_match.group(2))
        end_month = range_match.group(3)
        end_day = int(range_match.group(4))
        
        start_year = 2025 if start_month == 'DEC' else 2026
        end_year = 2025 if end_month == 'DEC' else 2026
        
        start_date = datetime(start_year, 12 if start_month == 'DEC' else 1, start_day)
        end_date = datetime(end_year, 12 if end_month == 'DEC' else 1, end_day)
    
    # Count occurrences
    dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
    target_dows = [dow_map[dow] for dow in days_of_week if dow in dow_map]
    
    if not target_dows:
        occurrences = (end_date - start_date).days + 1
        return days_of_week, start_date, end_date, occurrences
    
    occurrence_dates = []
    current = start_date
    while current <= end_date:
        if current.weekday() in target_dows:
            occurrence_dates.append(current)
        current += timedelta(days=1)
    
    occurrences = len(occurrence_dates)
    
    # Handle EXCEPT dates
    if except_line:
        except_dates = []
        except_matches = re.findall(r'(JAN|DEC)\s+(\d{1,2})', except_line)
        for month, day in except_matches:
            year = 2025 if month == 'DEC' else 2026
            except_date = datetime(year, 12 if month == 'DEC' else 1, int(day))
            if except_date in occurrence_dates:
                occurrences -= 1
    
    return days_of_week, start_date, end_date, occurrences

def get_trip_number(trip_lines):
    """Extract trip number from trip header"""
    for line in trip_lines:
        if line.strip().startswith('#'):
            # Extract number after #
            match = re.search(r'#(\d+)', line)
            if match:
                return match.group(1)
    return None

def get_total_pay(trip_lines):
    """Extract TOTAL PAY value"""
    for line in trip_lines:
        if 'TOTAL PAY' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'PAY' and i + 1 < len(parts):
                    pay_str = parts[i + 1]
                    if pay_str.endswith('TL'):
                        try:
                            return float(pay_str[:-2])
                        except ValueError:
                            pass
    return None

def get_flight_block_times(trip_lines):
    """Extract all flight block times (BLK column)"""
    block_times = []
    
    for line in trip_lines:
        if len(line) < 10:
            continue
        
        # Look for BLK. column pattern - time followed by decimal
        # Pattern: number.number (e.g., "4.57", "2.18")
        parts = line.split()
        for i, part in enumerate(parts):
            # Check if this looks like a block time (X.XX format)
            if '.' in part and i + 1 < len(parts):
                try:
                    # Try to parse as float
                    block_time = float(part)
                    # Also check if next part might be a turn time (also has decimal)
                    # Block times are typically between 0.5 and 15 hours
                    if 0.1 <= block_time <= 15.0:
                        # Convert to minutes for easier comparison
                        block_minutes = int(block_time * 60)
                        block_times.append(block_minutes)
                except ValueError:
                    continue
    
    return block_times

def extract_detailed_trip_info(trip_lines):
    """
    Extract all information needed for detailed trip table view
    Returns dict with trip details
    """
    trip_number = get_trip_number(trip_lines)
    first_airport = get_first_departure_airport(trip_lines)
    base = BASE_MAPPING.get(first_airport, 'UNKNOWN') if first_airport else 'UNKNOWN'
    
    # Get trip length and flight legs
    length, last_day_legs, flight_legs = determine_trip_length_with_details(trip_lines)
    
    # Calculate report and release times
    report_time_minutes = None
    release_time_minutes = None
    if flight_legs:
        first_dep_time = flight_legs[0][1]
        last_arr_time = flight_legs[-1][3]
        report_time_minutes = calculate_report_time(first_dep_time)
        release_time_minutes = calculate_release_time(last_arr_time)
    
    # Convert minutes to HH:MM format for display
    def minutes_to_time(minutes):
        if minutes is None:
            return None
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    report_time_str = minutes_to_time(report_time_minutes)
    release_time_str = minutes_to_time(release_time_minutes)
    
    # Get total credit and pay
    total_credit = get_total_credit(trip_lines)
    total_pay = get_total_pay(trip_lines)
    
    # Get block times for longest/shortest leg
    block_times = get_flight_block_times(trip_lines)
    longest_leg = max(block_times) if block_times else 0
    shortest_leg = min(block_times) if block_times else 0
    
    # Get raw trip text
    raw_text = '\n'.join(trip_lines)
    
    return {
        'trip_number': trip_number,
        'base': base,
        'length': length,
        'report_time': report_time_str,
        'report_time_minutes': report_time_minutes,  # For filtering
        'release_time': release_time_str,
        'release_time_minutes': release_time_minutes,  # For filtering
        'total_legs': len(flight_legs),
        'longest_leg': longest_leg,
        'shortest_leg': shortest_leg,
        'total_credit': total_credit,
        'total_pay': total_pay,
        'raw_text': raw_text
    }

def get_first_departure_airport(trip_lines):
    """Get the departure airport of the first flight"""
    for line in trip_lines:
        if len(line) < 10:
            continue
        day_col = line[1:4].strip()
        if day_col in ['A', 'B', 'C', 'D', 'E']:
            parts = line.split()
            for part in parts:
                if len(part) == 3 and part.isalpha() and part.isupper():
                    return part
    return None

def determine_trip_length_with_details(trip_lines):
    """Determine trip length, legs on last day, all flight legs"""
    last_day_letter = None
    current_day_letter = None
    legs_by_day = {}
    flight_legs = []
    
    for line in trip_lines:
        if len(line) < 10:
            continue
        
        day_col = line[1:4].strip()
        if day_col in ['A', 'B', 'C', 'D', 'E']:
            last_day_letter = day_col
            current_day_letter = day_col
            if current_day_letter not in legs_by_day:
                legs_by_day[current_day_letter] = 0
        
        if len(line) > 30:
            parts = line.split()
            i = 0
            while i < len(parts) - 3:
                part1 = parts[i]
                part2 = parts[i+1].rstrip('*')
                part3 = parts[i+2]
                part4 = parts[i+3].rstrip('*')
                
                if (len(part1) == 3 and part1.isalpha() and
                    len(part2) == 4 and part2.isdigit() and
                    len(part3) == 3 and part3.isalpha() and
                    len(part4) == 4 and part4.isdigit()):
                    
                    dep_time = part2
                    arr_time = part4
                    flight_legs.append((part1, dep_time, part3, arr_time))
                    if current_day_letter:
                        legs_by_day[current_day_letter] += 1
                    i += 4
                else:
                    i += 1
    
    day_to_length = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
    num_days = day_to_length.get(last_day_letter, 0)
    last_day_legs = legs_by_day.get(last_day_letter, 0)
    
    # Check for red-eye on last leg
    if flight_legs:
        last_dep, last_arr = flight_legs[-1][1], flight_legs[-1][3]
        try:
            dep_hour = int(last_dep[:2])
            arr_hour = int(last_arr[:2])
            if dep_hour >= 20 and arr_hour >= 2:
                num_days += 1
        except (ValueError, IndexError):
            pass
    
    return num_days, last_day_legs, flight_legs

def get_total_credit(trip_lines):
    """Extract TOTAL CREDIT value"""
    for line in trip_lines:
        if 'TOTAL CREDIT' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'CREDIT' and i + 1 < len(parts):
                    credit_str = parts[i + 1]
                    if credit_str.endswith('TL'):
                        try:
                            return float(credit_str[:-2])
                        except ValueError:
                            pass
    return None

def has_redeye_flight(flight_legs):
    """Check if ANY flight leg is a red-eye"""
    for dep_airport, dep_time, arr_airport, arr_time in flight_legs:
        try:
            dep_hour = int(dep_time[:2])
            arr_hour = int(arr_time[:2])
            if dep_hour >= 20 and arr_hour >= 2:
                return True
        except (ValueError, IndexError):
            continue
    return False

def calculate_report_time(first_dep_time):
    """Calculate report time = first departure - 60 minutes"""
    try:
        hour = int(first_dep_time[:2])
        minute = int(first_dep_time[2:4])
        total_minutes = hour * 60 + minute - 60
        if total_minutes < 0:
            total_minutes += 1440
        return total_minutes
    except (ValueError, IndexError):
        return None

def calculate_release_time(last_arr_time):
    """Calculate release time = last arrival + 45 minutes"""
    try:
        hour = int(last_arr_time[:2])
        minute = int(last_arr_time[2:4])
        total_minutes = hour * 60 + minute + 45
        if total_minutes >= 1440:
            total_minutes -= 1440
        return total_minutes
    except (ValueError, IndexError):
        return None

def analyze_file(file_content, base_filter, front_commute_minutes, back_commute_minutes):
    """
    Main analysis function
    Returns dict with all metrics
    """
    trips = parse_trips(file_content)
    
    # Initialize counters
    total_trips = 0
    trip_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    single_leg_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_credit_by_length = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
    redeye_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    commute_front = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    commute_back = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    commute_both = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    
    for trip in trips:
        first_airport = get_first_departure_airport(trip)
        if not first_airport:
            continue
        
        # Apply base filter
        base = BASE_MAPPING.get(first_airport, 'UNKNOWN')
        if base_filter != "All Bases" and base != base_filter:
            continue
        
        # Get occurrences
        days_of_week, start, end, occurrences = get_effective_dates(trip)
        length, last_day_legs, flight_legs = determine_trip_length_with_details(trip)
        credit = get_total_credit(trip)
        
        if length not in trip_counts:
            continue
        
        total_trips += occurrences
        trip_counts[length] += occurrences
        
        # Single leg on last day
        if last_day_legs == 1:
            single_leg_counts[length] += occurrences
        
        # Credit
        if credit is not None:
            total_credit_by_length[length] += (credit * occurrences)
        
        # Red-eye
        if has_redeye_flight(flight_legs):
            redeye_counts[length] += occurrences
        
        # Commutability
        if flight_legs:
            first_dep_time = flight_legs[0][1]
            last_arr_time = flight_legs[-1][3]
            
            report_minutes = calculate_report_time(first_dep_time)
            release_minutes = calculate_release_time(last_arr_time)
            
            front_ok = report_minutes is not None and report_minutes >= front_commute_minutes
            back_ok = release_minutes is not None and release_minutes <= back_commute_minutes
            
            if front_ok:
                commute_front[length] += occurrences
            if back_ok:
                commute_back[length] += occurrences
            if front_ok and back_ok:
                commute_both[length] += occurrences
    
    # Calculate percentages and averages
    result = {
        'total_trips': total_trips,
        'trip_counts': trip_counts,
        'avg_trip_length': sum(l * c for l, c in trip_counts.items()) / total_trips if total_trips > 0 else 0,
    }
    
    # Single leg percentages
    result['single_leg_pct'] = {
        length: (single_leg_counts[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    
    # Credit averages
    result['avg_credit_by_length'] = {
        length: (total_credit_by_length[length] / trip_counts[length]) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    
    total_credit = sum(total_credit_by_length.values())
    result['avg_credit_per_trip'] = total_credit / total_trips if total_trips > 0 else 0
    
    result['avg_credit_per_day_by_length'] = {
        length: (result['avg_credit_by_length'][length] / length) if result['avg_credit_by_length'][length] > 0 else 0
        for length in range(1, 6)
    }
    
    total_days = sum(length * count for length, count in trip_counts.items())
    result['avg_credit_per_day'] = total_credit / total_days if total_days > 0 else 0
    
    # Red-eye percentages
    result['redeye_pct'] = {
        length: (redeye_counts[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['redeye_rate'] = sum(redeye_counts.values()) / total_trips * 100 if total_trips > 0 else 0
    
    # Commutability percentages
    result['front_commute_pct'] = {
        length: (commute_front[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['front_commute_rate'] = sum(commute_front.values()) / total_trips * 100 if total_trips > 0 else 0
    
    result['back_commute_pct'] = {
        length: (commute_back[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['back_commute_rate'] = sum(commute_back.values()) / total_trips * 100 if total_trips > 0 else 0
    
    result['both_commute_pct'] = {
        length: (commute_both[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['both_commute_rate'] = sum(commute_both.values()) / total_trips * 100 if total_trips > 0 else 0
    
    return result

def get_detailed_trips(file_content, base_filter):
    """
    Extract detailed information for all trips in a file
    Returns list of trip detail dicts
    """
    trips = parse_trips(file_content)
    detailed_trips = []
    
    for trip in trips:
        first_airport = get_first_departure_airport(trip)
        if not first_airport:
            continue
        
        # Apply base filter
        base = BASE_MAPPING.get(first_airport, 'UNKNOWN')
        if base_filter != "All Bases" and base != base_filter:
            continue
        
        # Get occurrences for this trip
        days_of_week, start, end, occurrences = get_effective_dates(trip)
        
        # Extract detailed info
        trip_info = extract_detailed_trip_info(trip)
        trip_info['occurrences'] = occurrences
        
        # Add one entry per occurrence
        for _ in range(occurrences):
            detailed_trips.append(trip_info.copy())
    
    return detailed_trips

def generate_pdf_report(analysis_results, uploaded_files, base_filter, front_time, back_time):
    """Generate PDF report with tables on page 1 and trend graphs on page 2+"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Sort files by date
    month_order = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    sorted_files = sorted(
        analysis_results.keys(),
        key=lambda f: (uploaded_files[f]['year'], month_order[uploaded_files[f]['month']])
    )
    
    num_files = len(sorted_files)
    
    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=16, spaceAfter=0.1*inch)
    story.append(Paragraph("Pilot Trip Scheduling Analysis Report", title_style))
    
    # Settings
    settings_text = f"<b>Base:</b> {base_filter} | <b>Front-End:</b> ≥{front_time} | <b>Back-End:</b> ≤{back_time}"
    story.append(Paragraph(settings_text, styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    # Calculate column widths based on number of files
    if num_files == 1:
        col_widths = [2*inch] + [1.2*inch] * 6
    elif num_files == 2:
        col_widths = [1.8*inch] + [1.0*inch] * 6
    else:
        # For 3+ files, make columns narrower
        available_width = 10*inch  # landscape letter minus margins
        file_col_width = (available_width - 1.5*inch) / 6  # 6 columns (1-day through Overall)
        col_widths = [1.5*inch] + [file_col_width] * 6
    
    # Helper function to create table
    def create_table(data, title):
        story.append(Paragraph(f"<b>{title}</b>", ParagraphStyle('Heading', fontSize=10, spaceAfter=0.05*inch)))
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.05*inch))
    
    # 1. Trip Length Distribution
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Total']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            count = result['trip_counts'][length]
            pct = (count / result['total_trips'] * 100) if result['total_trips'] > 0 else 0
            row.append(f"{count}\n({pct:.1f}%)")
        row.append(f"{result['total_trips']}\n(100%)")
        data.append(row)
    create_table(data, "1. Trip Length Distribution")
    
    # 2. Single Leg on Last Day
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            total = result['trip_counts'][length]
            single_count = int(total * result['single_leg_pct'][length] / 100)
            pct = result['single_leg_pct'][length]
            row.append(f"{single_count}\n({pct:.1f}%)")
        total_single = sum(result['trip_counts'][i] * result['single_leg_pct'][i] / 100 for i in range(1, 6))
        overall_pct = (total_single / result['total_trips'] * 100) if result['total_trips'] > 0 else 0
        overall_count = int(total_single)
        row.append(f"{overall_count}\n({overall_pct:.1f}%)")
        data.append(row)
    create_table(data, "2. Single Leg on Last Day")
    
    # 3. Average Credit per Trip
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            row.append(f"{result['avg_credit_by_length'][length]:.2f}\nhrs")
        row.append(f"{result['avg_credit_per_trip']:.2f}\nhrs")
        data.append(row)
    create_table(data, "3. Average Credit per Trip")
    
    # 4. Average Credit per Day
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            row.append(f"{result['avg_credit_per_day_by_length'][length]:.2f}\nhrs/day")
        row.append(f"{result['avg_credit_per_day']:.2f}\nhrs/day")
        data.append(row)
    create_table(data, "4. Average Credit per Day")
    
    # 5. Commutability - Front End
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            total = result['trip_counts'][length]
            commute_count = int(total * result['front_commute_pct'][length] / 100)
            pct = result['front_commute_pct'][length]
            row.append(f"{commute_count}\n({pct:.1f}%)")
        total_commute = sum(result['trip_counts'][i] * result['front_commute_pct'][i] / 100 for i in range(1, 6))
        overall_count = int(total_commute)
        row.append(f"{overall_count}\n({result['front_commute_rate']:.1f}%)")
        data.append(row)
    create_table(data, "5a. Front-End Commutability")
    
    # 5b. Commutability - Back End
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            total = result['trip_counts'][length]
            commute_count = int(total * result['back_commute_pct'][length] / 100)
            pct = result['back_commute_pct'][length]
            row.append(f"{commute_count}\n({pct:.1f}%)")
        total_commute = sum(result['trip_counts'][i] * result['back_commute_pct'][i] / 100 for i in range(1, 6))
        overall_count = int(total_commute)
        row.append(f"{overall_count}\n({result['back_commute_rate']:.1f}%)")
        data.append(row)
    create_table(data, "5b. Back-End Commutability")
    
    # 5c. Commutability - Both Ends
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            total = result['trip_counts'][length]
            commute_count = int(total * result['both_commute_pct'][length] / 100)
            pct = result['both_commute_pct'][length]
            row.append(f"{commute_count}\n({pct:.1f}%)")
        total_commute = sum(result['trip_counts'][i] * result['both_commute_pct'][i] / 100 for i in range(1, 6))
        overall_count = int(total_commute)
        row.append(f"{overall_count}\n({result['both_commute_rate']:.1f}%)")
        data.append(row)
    create_table(data, "5c. Both Ends Commutability")
    
    # Add page break before graphs if multiple files
    if num_files >= 2:
        story.append(PageBreak())
        
        # PAGE 2+: TREND GRAPHS
        story.append(Paragraph("<b>Trend Analysis</b>", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Import matplotlib for graphs
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')
        from io import BytesIO as ImgBuffer
        from reportlab.platypus import Image
        
        # Prepare data for graphs
        file_labels = [uploaded_files[f]['display_name'] for f in sorted_files]
        
        # Graph 1: Trip Length Distribution (by percentage)
        fig, ax = plt.subplots(figsize=(10, 4))
        x = range(len(file_labels))
        width = 0.15
        
        for i, length in enumerate(range(1, 6)):
            percentages = []
            for fname in sorted_files:
                result = analysis_results[fname]
                pct = (result['trip_counts'][length] / result['total_trips'] * 100) if result['total_trips'] > 0 else 0
                percentages.append(pct)
            ax.bar([xi + width*i for xi in x], percentages, width, label=f'{length}-day')
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Percentage (%)')
        ax.set_title('Trip Length Distribution Over Time')
        ax.set_xticks([xi + width*2 for xi in x])
        ax.set_xticklabels(file_labels, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        img_buffer = ImgBuffer()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        story.append(Image(img_buffer, width=7*inch, height=2.8*inch))
        plt.close()
        story.append(Spacer(1, 0.2*inch))
        
        # Graph 2: Average Credit per Trip
        fig, ax = plt.subplots(figsize=(10, 4))
        for length in range(1, 6):
            credits = [analysis_results[f]['avg_credit_by_length'][length] for f in sorted_files]
            ax.plot(file_labels, credits, marker='o', label=f'{length}-day', linewidth=2)
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Average Credit (hours)')
        ax.set_title('Average Credit per Trip Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        img_buffer = ImgBuffer()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        story.append(Image(img_buffer, width=7*inch, height=2.8*inch))
        plt.close()
        story.append(Spacer(1, 0.2*inch))
        
        # Graph 3: Commutability Trends
        fig, ax = plt.subplots(figsize=(10, 4))
        
        front_rates = [analysis_results[f]['front_commute_rate'] for f in sorted_files]
        back_rates = [analysis_results[f]['back_commute_rate'] for f in sorted_files]
        both_rates = [analysis_results[f]['both_commute_rate'] for f in sorted_files]
        
        ax.plot(file_labels, front_rates, marker='o', label='Front-End', linewidth=2)
        ax.plot(file_labels, back_rates, marker='s', label='Back-End', linewidth=2)
        ax.plot(file_labels, both_rates, marker='^', label='Both Ends', linewidth=2)
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Commutability (%)')
        ax.set_title('Commutability Trends Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        img_buffer = ImgBuffer()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        story.append(Image(img_buffer, width=7*inch, height=2.8*inch))
        plt.close()
        
        # Page 3 if needed
        story.append(PageBreak())
        
        # Graph 4: Average Credit per Day
        fig, ax = plt.subplots(figsize=(10, 4))
        for length in range(1, 6):
            credits = [analysis_results[f]['avg_credit_per_day_by_length'][length] for f in sorted_files]
            ax.plot(file_labels, credits, marker='o', label=f'{length}-day', linewidth=2)
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Average Credit per Day (hrs/day)')
        ax.set_title('Average Credit per Day Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        img_buffer = ImgBuffer()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        story.append(Image(img_buffer, width=7*inch, height=2.8*inch))
        plt.close()
        story.append(Spacer(1, 0.2*inch))
        
        # Graph 5: Single Leg Last Day Trends
        fig, ax = plt.subplots(figsize=(10, 4))
        for length in range(1, 6):
            percentages = [analysis_results[f]['single_leg_pct'][length] for f in sorted_files]
            ax.plot(file_labels, percentages, marker='o', label=f'{length}-day', linewidth=2)
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Single Leg Last Day (%)')
        ax.set_title('Single Leg on Last Day Trends Over Time')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        img_buffer = ImgBuffer()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        story.append(Image(img_buffer, width=7*inch, height=2.8*inch))
        plt.close()
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
