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
from reportlab.lib.styles import getSampleStyleSheet
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

def generate_pdf_report(analysis_results, uploaded_files, base_filter, front_time, back_time):
    """Generate PDF report of analysis results"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = styles['Title']
    story.append(Paragraph("Pilot Trip Scheduling Analysis Report", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Settings
    settings_text = f"<b>Settings:</b> Base Filter: {base_filter} | Front-End: ≥{front_time} | Back-End: ≤{back_time}"
    story.append(Paragraph(settings_text, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary table for each file
    for fname, result in analysis_results.items():
        display_name = uploaded_files[fname]['display_name']
        
        story.append(Paragraph(f"<b>{display_name}</b>", styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        
        # Summary metrics
        data = [
            ['Metric', 'Value'],
            ['Total Trips', str(result['total_trips'])],
            ['Avg Trip Length', f"{result['avg_trip_length']:.2f} days"],
            ['Avg Credit/Trip', f"{result['avg_credit_per_trip']:.2f} hrs"],
            ['Avg Credit/Day', f"{result['avg_credit_per_day']:.2f} hrs/day"],
            ['Red-Eye Rate', f"{result['redeye_rate']:.1f}%"],
            ['Front-End Commute', f"{result['front_commute_rate']:.1f}%"],
            ['Back-End Commute', f"{result['back_commute_rate']:.1f}%"],
            ['Both Ends Commute', f"{result['both_commute_rate']:.1f}%"],
        ]
        
        t = Table(data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*inch))
        
        # Trip length distribution
        data = [['Length', 'Count', 'Percentage']]
        for length in range(1, 6):
            count = result['trip_counts'][length]
            pct = count / result['total_trips'] * 100 if result['total_trips'] > 0 else 0
            data.append([f"{length}-day", str(count), f"{pct:.1f}%"])
        
        t = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(Paragraph("<b>Trip Length Distribution</b>", styles['Heading3']))
        story.append(t)
        
        story.append(PageBreak())
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
