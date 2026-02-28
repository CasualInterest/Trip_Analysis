"""
Core analysis engine for pilot trip data
Contains all the calculation logic from the original analysis
"""

from datetime import datetime, timedelta
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether
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

def get_effective_dates(trip_lines, bid_year=2026):
    """
    Parse EFFECTIVE date range, days of week, and EXCEPT dates
    Handles all months (JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC)
    """
    header_line = ""
    except_line = ""
    
    for line in trip_lines:
        if 'EFFECTIVE' in line:
            header_line = line
        elif 'EXCEPT' in line and 'EXCPT' not in line:
            except_line = line
    
    if not header_line:
        return [], None, None, 1
    
    # Month name to number mapping
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    # Extract days of week
    dow_pattern = r'\b(MO|TU|WE|TH|FR|SA|SU)\b'
    days_of_week = re.findall(dow_pattern, header_line)
    
    # Try "MMM## ONLY" pattern (any month)
    only_match = re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{1,2})\s+ONLY\b', header_line)
    if only_match:
        month_str = only_match.group(1)
        day = int(only_match.group(2))
        month_num = month_map[month_str]
        
        # Use the provided bid_year
        # For Oct-Dec, use bid_year (e.g., Oct 2025 is in 2025)
        # For Jan-Sep, could be bid_year or bid_year+1 depending on context
        # Default to bid_year for all months in the bid period
        if month_num >= 10:
            year = bid_year
        else:
            # Jan-Sep: use bid_year
            year = bid_year
        
        try:
            date = datetime(year, month_num, day)
        except ValueError:
            return days_of_week, None, None, 1
        
        # Verify day of week matches
        dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
        actual_dow = date.weekday()
        
        if days_of_week:
            for dow in days_of_week:
                if dow_map.get(dow) == actual_dow:
                    return days_of_week, date, date, 1
            return days_of_week, date, date, 0
        else:
            return days_of_week, date, date, 1
    
    # Try date range patterns
    # Pattern 1: MMM##-MMM. ## (e.g., FEB14-MAR. 01)
    range_match = re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{1,2})-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\.\s*(\d{1,2})\b', header_line)
    
    if not range_match:
        # Pattern 2: MMM##-## (same month, e.g., FEB02-FEB. 28 or JAN15-28)
        range_match = re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{1,2})-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\.\s*(\d{1,2})\b', header_line)
        if not range_match:
            range_match = re.search(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{1,2})-(\d{1,2})\b', header_line)
            if range_match:
                month_str = range_match.group(1)
                start_day = int(range_match.group(2))
                end_day = int(range_match.group(3))
                month_num = month_map[month_str]
                year = bid_year  # Use provided bid year
                
                try:
                    start_date = datetime(year, month_num, start_day)
                    end_date = datetime(year, month_num, end_day)
                except ValueError:
                    return days_of_week, None, None, 1
            else:
                return days_of_week, None, None, 1
    
    if range_match and len(range_match.groups()) == 4:
        # Cross-month range (e.g., FEB14-MAR. 01)
        start_month_str = range_match.group(1)
        start_day = int(range_match.group(2))
        end_month_str = range_match.group(3)
        end_day = int(range_match.group(4))
        
        start_month_num = month_map[start_month_str]
        end_month_num = month_map[end_month_str]
        
        # Use provided bid_year
        start_year = bid_year
        end_year = bid_year
        
        # Handle year rollover (e.g., DEC to JAN)
        if end_month_num < start_month_num:
            end_year = start_year + 1
        
        try:
            start_date = datetime(start_year, start_month_num, start_day)
            end_date = datetime(end_year, end_month_num, end_day)
        except ValueError:
            return days_of_week, None, None, 1
    elif not range_match:
        return days_of_week, None, None, 1
    
    # Count occurrences
    dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
    target_dows = [dow_map[dow] for dow in days_of_week if dow in dow_map]
    
    if not target_dows:
        # No specific days of week - every day in range
        occurrences = (end_date - start_date).days + 1
        return days_of_week, start_date, end_date, occurrences
    
    # Count occurrences of specified days of week
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
        # Find all month-day pairs in except line
        except_matches = re.findall(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\b', except_line)
        for month_str, day in except_matches:
            month_num = month_map[month_str]
            year = 2025 if month_num >= 10 else 2026
            
            try:
                except_date = datetime(year, month_num, int(day))
                if except_date in occurrence_dates:
                    occurrences -= 1
            except ValueError:
                pass
    
    return days_of_week, start_date, end_date, occurrences

def generate_staffing_heatmap(file_content, bid_month, bid_year, base_filter="All Bases"):
    """
    Generate daily staffing heat map data showing number of pilots working each day
    Returns dict with dates, pilot counts, and trip details
    """
    trips = parse_trips(file_content)
    
    # Month name to number mapping
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    month_num = month_map.get(bid_month, 1)
    
    # Dictionary to store: date -> list of (trip_number, duty_day)
    date_operations = {}
    
    for trip in trips:
        # Get trip number
        trip_number = None
        for line in trip:
            if line.strip().startswith('#'):
                match = re.search(r'#(\d+)', line)
                if match:
                    trip_number = match.group(1)
                    break
        
        if not trip_number:
            continue
        
        # Apply base filter
        first_airport = get_first_departure_airport(trip)
        if not first_airport:
            continue
        base = BASE_MAPPING.get(first_airport, 'UNKNOWN')
        if base_filter != "All Bases" and base != base_filter:
            continue
        
        # Get effective dates and EXCEPT dates
        header_line = ""
        except_line = ""
        for line in trip:
            if 'EFFECTIVE' in line:
                header_line = line
            elif 'EXCEPT' in line and 'EXCPT' not in line:
                except_line = line
        
        if not header_line:
            continue
        
        # Parse days of week
        dow_pattern = r'\b(MO|TU|WE|TH|FR|SA|SU)\b'
        days_of_week = re.findall(dow_pattern, header_line)
        
        # Get start and end dates
        days_of_week_parsed, start_date, end_date, _ = get_effective_dates(trip, bid_year)
        
        if not start_date or not end_date:
            continue
        
        # Get trip length (number of duty days A, B, C, D, etc.)
        duty_days = []
        for line in trip:
            match = re.match(r'\s+([A-Z])\s+\d+', line)
            if match:
                duty_day = match.group(1)
                if duty_day not in duty_days:
                    duty_days.append(duty_day)
        
        trip_length = len(duty_days)
        if trip_length == 0:
            continue
        
        # Get all dates this trip operates on
        dow_map = {'MO': 0, 'TU': 1, 'WE': 2, 'TH': 3, 'FR': 4, 'SA': 5, 'SU': 6}
        target_dows = [dow_map[dow] for dow in days_of_week_parsed if dow in dow_map]
        
        # Collect exception dates
        except_dates = set()
        if except_line:
            month_abbr_map = {
                'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
            }
            except_matches = re.findall(r'\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})\b', except_line)
            for month_str, day in except_matches:
                except_month_num = month_abbr_map[month_str]
                # Determine year based on month
                except_year = bid_year if except_month_num >= 10 else bid_year
                if except_month_num < month_num and month_num >= 10:
                    except_year = bid_year + 1
                try:
                    except_date = datetime(except_year, except_month_num, int(day))
                    except_dates.add(except_date)
                except ValueError:
                    pass
        
        # Find all occurrence dates
        occurrence_dates = []
        current = start_date
        while current <= end_date:
            if not target_dows or current.weekday() in target_dows:
                if current not in except_dates:
                    occurrence_dates.append(current)
            current += timedelta(days=1)
        
        # For each occurrence date, add all duty days
        for occ_date in occurrence_dates:
            for i, duty_day in enumerate(duty_days):
                duty_date = occ_date + timedelta(days=i)
                
                # Only include dates in the bid month
                if duty_date.month == month_num and duty_date.year == bid_year:
                    if duty_date not in date_operations:
                        date_operations[duty_date] = []
                    date_operations[duty_date].append({
                        'trip_number': trip_number,
                        'duty_day': duty_day,
                        'trip_length': trip_length
                    })
    
    # Get days in month
    import calendar
    days_in_month = calendar.monthrange(bid_year, month_num)[1]
    
    # Create arrays for heat map
    dates = []
    pilot_counts = []
    trip_details = []
    
    for day in range(1, days_in_month + 1):
        date = datetime(bid_year, month_num, day)
        dates.append(date)
        
        if date in date_operations:
            count = len(date_operations[date])
            pilot_counts.append(count)
            
            # Create detail string
            trip_nums = {}  # trip_number -> list of duty days
            for op in date_operations[date]:
                trip_num = op['trip_number']
                duty_day = op['duty_day']
                if trip_num not in trip_nums:
                    trip_nums[trip_num] = []
                trip_nums[trip_num].append(duty_day)
            
            detail_lines = []
            for trip_num in sorted(trip_nums.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                duty_days_str = ', '.join(sorted(set(trip_nums[trip_num])))
                detail_lines.append(f"#{trip_num} ({duty_days_str})")
            
            trip_details.append('<br>'.join(detail_lines[:10]))  # Limit to first 10 for readability
        else:
            pilot_counts.append(0)
            trip_details.append("No operations")
    
    return {
        'dates': dates,
        'pilot_counts': pilot_counts,
        'trip_details': trip_details,
        'month': bid_month,
        'year': bid_year
    }

def get_previous_month_abbr(bid_month):
    """Get the 3-letter abbreviation for the previous month"""
    prev_month_map = {
        'January': 'DEC', 'February': 'JAN', 'March': 'FEB',
        'April': 'MAR', 'May': 'APR', 'June': 'MAY',
        'July': 'JUN', 'August': 'JUL', 'September': 'AUG',
        'October': 'SEP', 'November': 'OCT', 'December': 'NOV'
    }
    return prev_month_map.get(bid_month, '')

def is_split_trip(trip_lines, bid_month):
    """
    Detect if this is a split trip:
    1. EFFECTIVE line contains previous month abbreviation
    2. Day sequence has repeating day letters
    """
    # Get EFFECTIVE line
    effective_line = ""
    for line in trip_lines:
        if 'EFFECTIVE' in line:
            effective_line = line
            break
    
    if not effective_line:
        return False
    
    # Check for previous month
    prev_month = get_previous_month_abbr(bid_month)
    if not prev_month or prev_month not in effective_line:
        return False
    
    # Check for repeating day letters
    day_letters = []
    for line in trip_lines:
        if len(line) > 3:
            day_col = line[1:4].strip()
            if day_col in ['A', 'B', 'C', 'D', 'E']:
                day_letters.append(day_col)
    
    # If any day letter appears more than once, it's a split
    from collections import Counter
    day_count = Counter(day_letters)
    has_repeat = any(count > 1 for count in day_count.values())
    
    return has_repeat

def split_trip_into_sections(trip_lines):
    """
    Split a trip into two sections at the point where day letters restart
    Section 1: Everything up to (but not including) the first repeated day + TOTAL CREDIT/PAY
    Section 2: From the repeated day onwards (no TOTAL CREDIT/PAY)
    
    Returns: (section1_lines, section2_lines, split_index)
    """
    day_letters = []
    day_line_indices = []
    
    for i, line in enumerate(trip_lines):
        if len(line) > 3:
            day_col = line[1:4].strip()
            if day_col in ['A', 'B', 'C', 'D', 'E']:
                day_letters.append(day_col)
                day_line_indices.append(i)
    
    if not day_letters:
        return trip_lines, [], -1
    
    # Find where first day repeats
    split_index = -1
    for i in range(1, len(day_letters)):
        if day_letters[i] in day_letters[:i]:
            split_index = day_line_indices[i]
            break
    
    if split_index == -1:
        return trip_lines, [], -1
    
    # Section 1: From start to split point
    section1 = trip_lines[:split_index]
    
    # Add TOTAL CREDIT and TOTAL PAY lines to section 1
    for line in trip_lines[split_index:]:
        if 'TOTAL CREDIT' in line or 'TOTAL PAY' in line:
            section1.append(line)
    
    # Section 2: From split point to TOTAL CREDIT (excluding it)
    section2_end = len(trip_lines)
    for i in range(split_index, len(trip_lines)):
        if 'TOTAL CREDIT' in trip_lines[i]:
            section2_end = i
            break
    
    # Section 2 needs ALL header lines (trip number, EFFECTIVE, DAY header, etc.)
    # Find where day letters start in the original trip
    first_day_line = day_line_indices[0] if day_line_indices else split_index
    header_lines = trip_lines[:first_day_line]
    
    section2 = header_lines + trip_lines[split_index:section2_end]
    
    return section1, section2, split_index

def calculate_credit_for_section(trip_lines):
    """
    Calculate credit for a trip section without TOTAL CREDIT line
    Credit = max(sum of BLK times, 5.15 * number of days)
    """
    # Get all BLK times
    block_times = get_flight_block_times(trip_lines)
    
    # Convert H.MM to decimal hours
    def hmm_to_decimal(hmm):
        hours = int(hmm)
        minutes = int(round((hmm - hours) * 100))
        return hours + (minutes / 60.0)
    
    total_blk = sum(hmm_to_decimal(blk) for blk in block_times)
    
    # Count unique days
    day_letters = []
    for line in trip_lines:
        if len(line) > 3:
            day_col = line[1:4].strip()
            if day_col in ['A', 'B', 'C', 'D', 'E'] and day_col not in day_letters:
                day_letters.append(day_col)
    
    num_days = len(day_letters)
    min_daily_credit = 5.15 * num_days
    
    # Return the higher value
    return max(total_blk, min_daily_credit)

def get_trip_number(trip_lines):
    """Extract trip number from trip header - can be numeric or alphanumeric (e.g., 4527 or L832)"""
    for line in trip_lines:
        if line.strip().startswith('#'):
            # Extract trip number after # - can include letters
            # Pattern: #L832 or #4527
            match = re.search(r'#([A-Z]?\d+)', line)
            if match:
                return match.group(1)
    return None

def get_total_pay(trip_lines):
    """
    Extract TOTAL PAY components - handles H:MM format and converts to decimal hours
    Returns dict with total_pay, sit, edp, hol, carve
    """
    pay_dict = {
        'total_pay': None,
        'sit': None,
        'edp': None,
        'hol': None,
        'carve': None
    }
    
    for line in trip_lines:
        if 'TOTAL PAY' in line:
            parts = line.split()
            
            # Find each component
            for i, part in enumerate(parts):
                if part == 'PAY' and i + 1 < len(parts):
                    pay_str = parts[i + 1]
                    if pay_str.endswith('TL'):
                        pay_str = pay_str[:-2]
                    pay_dict['total_pay'] = parse_time_to_decimal(pay_str)
                
                elif part.endswith('SIT') and i < len(parts):
                    sit_str = part[:-3]  # Remove 'SIT'
                    try:
                        pay_dict['sit'] = float(sit_str)
                    except ValueError:
                        pass
                
                elif part.endswith('EDP') and i < len(parts):
                    edp_str = part[:-3]  # Remove 'EDP'
                    try:
                        pay_dict['edp'] = float(edp_str)
                    except ValueError:
                        pass
                
                elif part.endswith('HOL') and i < len(parts):
                    hol_str = part[:-3]  # Remove 'HOL'
                    try:
                        pay_dict['hol'] = float(hol_str)
                    except ValueError:
                        pass
                
                elif part.endswith('CARVE'):
                    carve_str = part[:-5]  # Remove 'CARVE'
                    try:
                        pay_dict['carve'] = float(carve_str)
                    except ValueError:
                        pass
            break
    
    return pay_dict

def parse_time_to_decimal(time_str):
    """Convert H:MM format or decimal to decimal hours"""
    if ':' in time_str:
        try:
            time_parts = time_str.split(':')
            if len(time_parts) == 2:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                return hours + (minutes / 60.0)
        except ValueError:
            pass
    else:
        try:
            return float(time_str)
        except ValueError:
            pass
    return None

def get_flight_block_times(trip_lines):
    """
    Extract all flight block times (BLK column) - returns list in H.MM format
    Note: Format is H.MM (e.g., 2.37 = 2 hours 37 minutes, NOT 2.37 decimal hours)
    We keep them as-is since the format already represents H:MM with a period separator
    """
    block_times = []
    
    for line in trip_lines:
        if len(line) < 10:
            continue
        
        # Look for flight lines with departure/arrival pattern
        # Format: airport time airport time H.MM
        # The H.MM number after the second airport/time is the block time
        parts = line.split()
        
        for i in range(len(parts) - 1):
            # Look for pattern: AIRPORT(3 letters) TIME(4 digits) then a H.MM number
            if (i >= 2 and 
                len(parts[i-2]) == 3 and parts[i-2].isalpha() and  # departure airport
                len(parts[i-1]) == 4 and parts[i-1].isdigit() and  # departure time
                len(parts[i]) == 3 and parts[i].isalpha() and      # arrival airport
                i + 1 < len(parts)):
                
                # Next part should be arrival time (4 digits possibly with *)
                arr_time = parts[i+1].rstrip('*')
                if len(arr_time) == 4 and arr_time.isdigit():
                    # Look for block time in next few positions
                    # Block time is H.MM format like 2.37, 4.57, etc.
                    for j in range(i+2, min(i+5, len(parts))):
                        part = parts[j]
                        # Check if this is a H.MM number (block time)
                        if '.' in part:
                            try:
                                block_time = float(part)
                                # Block times are typically between 0.5 and 15 hours
                                # Note: these are stored as H.MM (e.g., 2.37) which we keep as-is
                                if 0.1 <= block_time <= 15.0:
                                    block_times.append(block_time)
                                    break
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
    
    # Get total credit and pay components
    total_credit = get_total_credit(trip_lines)
    pay_data = get_total_pay(trip_lines)
    
    # Get block times for longest/shortest leg (in H.MM format)
    block_times = get_flight_block_times(trip_lines)
    longest_leg = max(block_times) if block_times else 0  # H.MM format
    shortest_leg = min(block_times) if block_times else 0  # H.MM format
    
    # Convert H.MM format to HH:MM display format
    # Example: 2.37 means 2 hours 37 minutes
    def hmm_to_display(time_val):
        if time_val == 0:
            return "0:00"
        # Split the float: integer part is hours, decimal part is minutes
        hours = int(time_val)
        minutes = int(round((time_val - hours) * 100))  # .37 becomes 37 minutes
        return f"{hours}:{minutes:02d}"
    
    longest_leg_str = hmm_to_display(longest_leg)
    shortest_leg_str = hmm_to_display(shortest_leg)
    
    # Check if trip has red-eye
    has_redeye = has_redeye_flight(flight_legs)
    
    # Check if last leg is a deadhead
    last_leg_dh = get_last_leg_is_dh(trip_lines)
    
    # Get credit components (BL and CR)
    credit_components = get_credit_components(trip_lines)
    
    # Get days of week and effective dates
    days_of_week, start_date, end_date, occurrences = get_effective_dates(trip_lines)
    
    # Get raw trip text
    raw_text = '\n'.join(trip_lines)
    
    return {
        'trip_number': trip_number,
        'base': base,
        'length': length,
        'days_of_week': days_of_week,  # For AI and filtering
        'report_time': report_time_str,
        'report_time_minutes': report_time_minutes,  # For filtering
        'release_time': release_time_str,
        'release_time_minutes': release_time_minutes,  # For filtering
        'total_legs': len(flight_legs),
        'last_day_legs': last_day_legs,  # For filtering
        'longest_leg': longest_leg_str,
        'shortest_leg': shortest_leg_str,
        'total_credit': total_credit,
        'credit_minutes': credit_components['credit'],  # CR in minutes for filtering
        'block_hours': credit_components['block'],  # BL in hours for reference
        'has_redeye': has_redeye,  # For filtering
        'last_leg_dh': last_leg_dh,  # For filtering
        'total_pay': pay_data['total_pay'],
        'sit': pay_data['sit'],
        'edp': pay_data['edp'],
        'hol': pay_data['hol'],
        'carve': pay_data['carve'],
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

def get_credit_components(trip_lines):
    """
    Extract BL (block) and CR (credit) components from TOTAL CREDIT line
    Returns dict with 'block' and 'credit' values in decimal hours (for block) and minutes (for credit)
    
    Example line: TOTAL CREDIT 10.30TL   7.49BL    2.41CR
    """
    components = {'block': None, 'credit': None}
    
    for line in trip_lines:
        if 'TOTAL CREDIT' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part.endswith('BL'):
                    bl_str = part[:-2]
                    try:
                        components['block'] = float(bl_str)
                    except ValueError:
                        pass
                elif part.endswith('CR'):
                    cr_str = part[:-2]
                    try:
                        # Convert decimal hours to minutes for filtering
                        # 2.41 hours = 2 hours 41 minutes = 141 minutes
                        cr_hours = float(cr_str)
                        cr_whole_hours = int(cr_hours)
                        cr_decimal_minutes = int(round((cr_hours - cr_whole_hours) * 100))
                        components['credit'] = cr_whole_hours * 60 + cr_decimal_minutes
                    except ValueError:
                        pass
            break
    
    return components

def has_redeye_flight(flight_legs):
    """
    Check if ANY flight leg is a red-eye
    
    Red-eye definition: An OVERNIGHT flight that intrudes the pilot's WOCL 
    (Window of Circadian Low: 02:00-05:59) while in the air.
    
    Key: Must be an overnight flight (departs evening, arrives next morning).
    Early morning same-day departures (05:45, 06:00) are NOT red-eyes.
    """
    for dep_airport, dep_time, arr_airport, arr_time in flight_legs:
        try:
            # Parse times (handle * for next day arrival)
            dep_hour = int(dep_time[:2])
            dep_min = int(dep_time[2:4]) if len(dep_time) >= 4 else 0
            arr_time_clean = arr_time.rstrip('*')
            arr_hour = int(arr_time_clean[:2])
            arr_min = int(arr_time_clean[2:4]) if len(arr_time_clean) >= 4 else 0
            
            # Convert to minutes since midnight
            dep_minutes = dep_hour * 60 + dep_min
            arr_minutes = arr_hour * 60 + arr_min
            
            # WOCL window: 02:00 to 05:59
            wocl_start = 2 * 60  # 120 minutes (02:00)
            wocl_end = 5 * 60 + 59  # 359 minutes (05:59)
            
            # A red-eye MUST be an overnight flight
            # Overnight = has * OR departs after 18:00 with early morning arrival
            is_overnight = '*' in arr_time
            
            # Additional overnight check for flights without * marker
            if not is_overnight:
                # If departs evening (18:00+) and arrives early morning (before 12:00)
                if dep_minutes >= 18 * 60 and arr_minutes < 12 * 60:
                    is_overnight = True
            
            # Only check WOCL for overnight flights
            if is_overnight:
                # Red-eye if arrival is during WOCL (02:00-05:59)
                if wocl_start <= arr_minutes <= wocl_end:
                    return True
                # Also catches flights that depart late (20:00+) and arrive shortly after WOCL (06:00-08:00)
                # These still intrude WOCL while airborne
                if dep_minutes >= 20 * 60 and wocl_start <= arr_minutes <= 8 * 60:
                    return True
            
            # Explicitly ignore early morning same-day flights
            # (e.g., 05:45 departure is just an early start, not a red-eye)
                    
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

def analyze_file(file_content, base_filter, front_commute_minutes, back_commute_minutes, include_short_trips_commute=False, bid_year=2026):
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
        days_of_week, start, end, occurrences = get_effective_dates(trip, bid_year)
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
        
        # Commutability (only count trips 3+ days unless include_short_trips_commute is True)
        if flight_legs and (include_short_trips_commute or length >= 3):
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
    result['total_credit_hours'] = total_credit
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
    # Calculate the denominator: if short trips excluded, only count 3-5 day trips
    if include_short_trips_commute:
        commute_trip_total = total_trips
    else:
        commute_trip_total = sum(trip_counts[i] for i in range(3, 6))
    
    result['front_commute_pct'] = {
        length: (commute_front[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['front_commute_rate'] = sum(commute_front.values()) / commute_trip_total * 100 if commute_trip_total > 0 else 0
    
    result['back_commute_pct'] = {
        length: (commute_back[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['back_commute_rate'] = sum(commute_back.values()) / commute_trip_total * 100 if commute_trip_total > 0 else 0
    
    result['both_commute_pct'] = {
        length: (commute_both[length] / trip_counts[length] * 100) if trip_counts[length] > 0 else 0
        for length in range(1, 6)
    }
    result['both_commute_rate'] = sum(commute_both.values()) / commute_trip_total * 100 if commute_trip_total > 0 else 0
    
    return result

def get_detailed_trips(file_content, base_filter, bid_month, bid_year=2026):
    """
    Extract detailed information for all trips in a file
    Handles split trips (when EFFECTIVE contains previous month)
    Returns list of unique trip detail dicts with occurrence counts
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
        
        # Check if this is a split trip
        if is_split_trip(trip, bid_month):
            # Split into two sections
            section1, section2, split_idx = split_trip_into_sections(trip)
            
            if section1 and section2:
                # Get base from section 1 (the original/complete trip)
                # Section 2 might start with DH or incomplete data
                first_airport_s1 = get_first_departure_airport(section1)
                base_s1 = BASE_MAPPING.get(first_airport_s1, 'UNKNOWN') if first_airport_s1 else 'UNKNOWN'
                
                # SECTION 1: Uses file's TOTAL CREDIT/PAY, occurs on previous month date only (1 occurrence)
                trip_info1 = extract_detailed_trip_info(section1)
                # Override base with the one we determined
                trip_info1['base'] = base_s1
                # Include base in trip number for uniqueness
                trip_num = trip_info1['trip_number'] if trip_info1['trip_number'] else 'N/A'
                trip_info1['trip_number'] = f"{trip_num}-1 ({base_s1})" if base_s1 != 'UNKNOWN' else f"{trip_num}-1"
                trip_info1['occurrences'] = 1
                detailed_trips.append(trip_info1)
                
                # SECTION 2: Calculate credit manually, no pay, uses normal occurrence counting
                trip_info2 = extract_detailed_trip_info(section2)
                # Override base to match section 1
                trip_info2['base'] = base_s1
                trip_num = trip_info2['trip_number'] if trip_info2['trip_number'] else 'N/A'
                trip_info2['trip_number'] = f"{trip_num}-2 ({base_s1})" if base_s1 != 'UNKNOWN' else f"{trip_num}-2"
                
                # Override credit calculation for section 2
                calculated_credit = calculate_credit_for_section(section2)
                trip_info2['total_credit'] = calculated_credit
                trip_info2['total_pay'] = None  # No pay for section 2
                trip_info2['sit'] = None
                trip_info2['edp'] = None
                trip_info2['hol'] = None
                trip_info2['carve'] = None
                
                # Get occurrences for section 2 (subtract 1 for the first occurrence)
                days_of_week, start, end, total_occurrences = get_effective_dates(trip)
                section2_occurrences = max(total_occurrences - 1, 0)
                trip_info2['occurrences'] = section2_occurrences
                
                # Add section 2 as single entry with occurrence count
                detailed_trips.append(trip_info2)
        else:
            # Normal trip (not split)
            # Get occurrences for this trip
            days_of_week, start, end, occurrences = get_effective_dates(trip, bid_year)
            
            # Extract detailed info
            trip_info = extract_detailed_trip_info(trip)
            trip_info['occurrences'] = occurrences
            
            # Add as single entry with occurrence count
            detailed_trips.append(trip_info)
    
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
    available_width = 10*inch  # landscape letter minus margins
    
    if num_files == 1:
        col_widths = [2*inch] + [1.2*inch] * 6
    elif num_files == 2:
        col_widths = [1.8*inch] + [1.0*inch] * 6
    elif num_files <= 6:
        # For 3-6 files
        file_col_width = (available_width - 1.5*inch) / 6
        col_widths = [1.5*inch] + [file_col_width] * 6
    elif num_files <= 9:
        # For 7-9 files, make columns narrower
        file_col_width = (available_width - 1.2*inch) / 6
        col_widths = [1.2*inch] + [file_col_width] * 6
    else:
        # For 10+ files, make very narrow
        file_col_width = (available_width - 1.0*inch) / 6
        col_widths = [1.0*inch] + [file_col_width] * 6
    
    # Helper function to create table
    def create_table(data, title):
        # Calculate appropriate font size based on number of files
        if num_files <= 6:
            font_size = 7
        elif num_files <= 9:
            font_size = 6
        else:
            font_size = 5
        
        title_para = Paragraph(f"<b>{title}</b>", ParagraphStyle('Heading', fontSize=10, spaceAfter=0.05*inch))
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Use KeepTogether to prevent table from splitting across pages
        story.append(KeepTogether([title_para, t, Spacer(1, 0.05*inch)]))
    
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
    
    # 6. Red-Eye Trips
    data = [['File', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall']]
    for fname in sorted_files:
        result = analysis_results[fname]
        display_name = uploaded_files[fname]['display_name']
        row = [display_name]
        for length in range(1, 6):
            total = result['trip_counts'][length]
            redeye_count = int(total * result['redeye_pct'][length] / 100)
            pct = result['redeye_pct'][length]
            row.append(f"{redeye_count}\n({pct:.1f}%)")
        total_redeye = sum(result['trip_counts'][i] * result['redeye_pct'][i] / 100 for i in range(1, 6))
        overall_count = int(total_redeye)
        row.append(f"{overall_count}\n({result['redeye_rate']:.1f}%)")
        data.append(row)
    create_table(data, "6. Trips Containing Red-Eye Flight")
    
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


def get_last_leg_is_dh(trip_lines):
    """
    Return True if the last flight leg of the trip is a deadhead (DH).
    Scans every line with an airport-time-airport-time pattern and checks
    whether 'DH' appears among the tokens on that same line.
    """
    last_leg_dh = False
    for line in trip_lines:
        if len(line) < 10:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        for i in range(len(parts) - 3):
            p1 = parts[i]
            p2 = parts[i + 1].rstrip('*')
            p3 = parts[i + 2]
            p4 = parts[i + 3].rstrip('*')
            if (len(p1) == 3 and p1.isalpha() and p1.isupper() and
                    len(p2) == 4 and p2.isdigit() and
                    len(p3) == 3 and p3.isalpha() and p3.isupper() and
                    len(p4) == 4 and p4.isdigit()):
                last_leg_dh = 'DH' in parts
                break
    return last_leg_dh


def generate_selected_trips_pdf(selected_trips, display_name="", settings_text=""):
    """
    Generate a print-optimised PDF table of selected trips matching the
    on-screen Detailed Trip Table columns:
    Trip #, Base, Length, Days, Report, Release, Legs, Longest, Shortest,
    Credit, Pay, SIT, EDP, HOL, CARVE, Occurs
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Title ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'SelTitle', parent=styles['Title'], fontSize=14, spaceAfter=2
    )
    sub_style = ParagraphStyle(
        'SelSub', parent=styles['Normal'], fontSize=8,
        textColor=colors.HexColor('#555555'), spaceAfter=8
    )
    story.append(Paragraph(
        f"Selected Trips – {display_name}" if display_name else "Selected Trips",
        title_style
    ))
    if settings_text:
        story.append(Paragraph(settings_text, sub_style))
    story.append(Spacer(1, 0.05 * inch))

    # ── Column definitions ────────────────────────────────────────────────────
    # Total usable width in landscape letter minus margins = 10 - 0.8 = 9.2 inch
    col_defs = [
        ("Trip #",    0.52),
        ("Base",      0.35),
        ("Length",    0.42),
        ("Days",      0.60),
        ("Report",    0.45),
        ("Release",   0.45),
        ("Legs",      0.32),
        ("Longest",   0.45),
        ("Shortest",  0.45),
        ("Credit",    0.45),
        ("Pay",       0.45),
        ("SIT",       0.38),
        ("EDP",       0.38),
        ("HOL",       0.38),
        ("CARVE",     0.42),
        ("Occurs",    0.40),
    ]
    col_widths = [w * inch for _, w in col_defs]
    headers = [name for name, _ in col_defs]

    def fmt(val, decimals=2):
        if val is None:
            return ""
        try:
            f = float(val)
            return f"{f:.{decimals}f}"
        except (TypeError, ValueError):
            return str(val)

    # ── Rows ──────────────────────────────────────────────────────────────────
    rows = [headers]
    for t in selected_trips:
        days_str = '/'.join(t.get('days_of_week', [])) if t.get('days_of_week') else ''
        rows.append([
            str(t.get('trip_number') or 'N/A'),
            str(t.get('base') or ''),
            f"{t.get('length', '')}-day",
            days_str,
            str(t.get('report_time') or ''),
            str(t.get('release_time') or ''),
            str(t.get('total_legs') or ''),
            str(t.get('longest_leg') or ''),
            str(t.get('shortest_leg') or ''),
            fmt(t.get('total_credit')),
            fmt(t.get('total_pay')),
            fmt(t.get('sit')),
            fmt(t.get('edp')),
            fmt(t.get('hol')),
            fmt(t.get('carve')),
            str(t.get('occurrences', 1)),
        ])

    # ── Table style ───────────────────────────────────────────────────────────
    header_bg   = colors.HexColor('#1a3a6b')
    alt_row_bg  = colors.HexColor('#eef2f8')
    border_col  = colors.HexColor('#aaaaaa')

    tbl_style = TableStyle([
        # Header
        ('BACKGROUND',    (0, 0), (-1, 0),  header_bg),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  7),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  4),
        ('TOPPADDING',    (0, 0), (-1, 0),  4),
        # Data rows
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 7),
        ('TOPPADDING',    (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        # Alignment
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        # Grid
        ('GRID',          (0, 0), (-1, -1), 0.4, border_col),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.0, colors.white),
    ])

    # Alternating row colours
    for row_idx in range(1, len(rows)):
        if row_idx % 2 == 0:
            tbl_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), alt_row_bg)

    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(tbl_style)
    story.append(tbl)

    # ── Footer count ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.1 * inch))
    total_occ = sum(t.get('occurrences', 1) for t in selected_trips)
    story.append(Paragraph(
        f"{len(selected_trips)} unique trip pattern(s) · {total_occ} total occurrence(s)",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.grey)
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_selected_trips_txt(selected_trips):
    """Return plain text of selected trip raw blocks for download."""
    parts = []
    for trip in selected_trips:
        trip_num = trip.get('trip_number') or 'N/A'
        raw = trip.get('raw_text', '')
        parts.append(f"{'='*60}\nTRIP #{trip_num}\n{'='*60}\n{raw}\n")
    return '\n'.join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Comprehensive Base Report
# ─────────────────────────────────────────────────────────────────────────────

BASE_COLORS = {
    'ATL': '#2b7bba',
    'DTW': '#d94040',
    'LAX': '#e07b20',
    'MSP': '#9b59b6',
    'NYC': '#3a7cc2',
    'SEA': '#7b4fa6',
    'SLC': '#16a085',
    'BOS': '#1a3a6b',
    'All Bases': '#444444',
}


def get_all_flight_legs_with_block(trip_lines):
    """Extract all flight legs with their block times from trip lines."""
    legs = []
    for line in trip_lines:
        parts = line.split()
        i = 0
        while i < len(parts) - 3:
            p1 = parts[i]
            p2 = parts[i + 1].rstrip('*')
            p3 = parts[i + 2]
            p4 = parts[i + 3].rstrip('*')
            if (len(p1) == 3 and p1.isalpha() and p1.isupper() and
                    len(p2) == 4 and p2.isdigit() and
                    len(p3) == 3 and p3.isalpha() and p3.isupper() and
                    len(p4) == 4 and p4.isdigit()):
                block_val = None
                for j in range(i + 4, min(i + 8, len(parts))):
                    pj = parts[j]
                    if '.' in pj:
                        try:
                            bv = float(pj)
                            if 0.1 <= bv <= 15.0:
                                block_val = bv
                                break
                        except ValueError:
                            continue
                if block_val is not None:
                    h = int(block_val)
                    m = int(round((block_val - h) * 100))
                    legs.append((p1, p3, f"{h}:{m:02d}", h * 60 + m))
                i += 4
            else:
                i += 1
    return legs


def get_base_top20_legs(file_content, base, bid_year=2026):
    """
    Get top-20 legs sorted by frequency.
    For a specific base: all legs departing from that base's airports (anywhere in trip).
    For 'All Bases': all legs across the entire file.
    Returns dict with 'legs' list and summary stats.
    """
    if base == "All Bases":
        filter_airports = None
    else:
        filter_airports = {k for k, v in BASE_MAPPING.items() if v == base}

    trips = parse_trips(file_content)
    route_data = {}

    for trip in trips:
        fa = get_first_departure_airport(trip)
        if not fa:
            continue
        trip_base = BASE_MAPPING.get(fa, 'UNKNOWN')
        _, _, _, occurrences = get_effective_dates(trip, bid_year)
        if occurrences <= 0:
            continue
        legs = get_all_flight_legs_with_block(trip)
        for dep, arr, block_str, block_minutes in legs:
            if filter_airports is not None and dep not in filter_airports:
                continue
            route = f"{dep}-{arr}"
            if route not in route_data:
                route_data[route] = {
                    'block_minutes': block_minutes,
                    'block_str': block_str,
                    'total': 0,
                    'by_base': {},
                }
            # Keep the max block time seen for this route
            if block_minutes > route_data[route]['block_minutes']:
                route_data[route]['block_minutes'] = block_minutes
                route_data[route]['block_str'] = block_str
            route_data[route]['total'] += occurrences
            bd = route_data[route]['by_base']
            bd[trip_base] = bd.get(trip_base, 0) + occurrences

    top20 = sorted(route_data.items(), key=lambda x: x[1]['block_minutes'], reverse=True)[:25]

    legs_result = []
    total_top20 = 0
    base_top20 = 0

    for route, data in top20:
        total = data['total']
        total_top20 += total

        if base == "All Bases":
            if data['by_base']:
                top_b, top_cnt = max(data['by_base'].items(), key=lambda x: x[1])
                bp = int(round(top_cnt / total * 100))
                crew_dist = top_b
                base_top20 += top_cnt
            else:
                bp, crew_dist = 0, 'N/A'
        else:
            base_cnt = data['by_base'].get(base, 0)
            base_top20 += base_cnt
            bp = int(round(base_cnt / total * 100)) if total > 0 else 0
            top5 = sorted(data['by_base'].items(), key=lambda x: x[1], reverse=True)[:5]
            crew_dist = ', '.join(f"{b}:{c}" for b, c in top5)

        legs_result.append({
            'route': route,
            'block_str': data['block_str'],
            'total': total,
            'base_pct': bp,
            'crew_dist': crew_dist,
        })

    return {
        'legs': legs_result,
        'total_top20': total_top20,
        'base_top20': base_top20,
        'non_base_top20': total_top20 - base_top20,
        'base_pct_total': int(round(base_top20 / total_top20 * 100)) if total_top20 > 0 else 0,
    }


def _draw_mpl_table(ax, col_labels, cell_data, hdr_color, fontsize=6.5):
    """Draw a styled table filling the given axes."""
    n_rows = len(cell_data)
    n_cols = len(col_labels)
    cell_colors = [
        ['#eef2f8' if r % 2 == 0 else 'white'] * n_cols
        for r in range(n_rows)
    ]
    tbl = ax.table(
        cellText=cell_data,
        colLabels=col_labels,
        cellLoc='center',
        loc='center',
        bbox=[0, 0, 1, 1],
        cellColours=cell_colors,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    for j in range(n_cols):
        tbl[0, j].set_facecolor(hdr_color)
        tbl[0, j].set_text_props(color='white', fontweight='bold')
    for key, cell in tbl.get_celld().items():
        cell.set_edgecolor('#cccccc')
        cell.set_linewidth(0.3)
    return tbl


def _create_summary_fig(base, result, display_name, front_str, back_str):
    """Create landscape summary page figure for one base."""
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import matplotlib
    matplotlib.use('Agg')

    color = BASE_COLORS.get(base, '#444444')
    base_label = "All Bases" if base == "All Bases" else f"{base} Base"

    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor('white')

    # Standard print-safe margins: 0.5" on all sides
    # 0.5/11 = 0.0455 LR,  0.5/8.5 = 0.0588 TB
    MARGIN_LR = 0.046
    MARGIN_TB = 0.060

    # Title block (top)
    fig.text(0.5, 1.0 - MARGIN_TB, f"{base_label} - Trip Scheduling Analysis  |  {display_name}",
             ha='center', va='top', fontsize=13, fontweight='bold', color=color)
    fig.text(0.5, 1.0 - MARGIN_TB - 0.042,
             f"Front-End >= {front_str}  |  Back-End <= {back_str}",
             ha='center', va='top', fontsize=8, color='#555555')

    # Key metrics bar — spans ONLY the left table column width
    # so it never overlaps the chart area
    BAR_TOP = 1.0 - MARGIN_TB - 0.088
    BAR_H   = 0.055
    BAR_BOT = BAR_TOP - BAR_H
    bax = fig.add_axes([MARGIN_LR, BAR_BOT, 1 - 2 * MARGIN_LR, BAR_H])
    bax.set_facecolor(color)
    bax.axis('off')
    metrics = [
        ('Total Trips',   f"{result['total_trips']}"),
        ('Avg Length',    f"{result['avg_trip_length']:.2f} d"),
        ('Avg Cr/Trip',   f"{result['avg_credit_per_trip']:.2f} h"),
        ('Avg Cr/Day',    f"{result['avg_credit_per_day']:.2f} h"),
        ('Front Commute', f"{result['front_commute_rate']:.1f}%"),
        ('Back Commute',  f"{result['back_commute_rate']:.1f}%"),
        ('Both Ends',     f"{result['both_commute_rate']:.1f}%"),
    ]
    for i, (lbl, val) in enumerate(metrics):
        x = (i + 0.5) / len(metrics)
        bax.text(x, 0.68, val, ha='center', va='center', fontsize=9.5,
                 fontweight='bold', color='white', transform=bax.transAxes)
        bax.text(x, 0.18, lbl, ha='center', va='center', fontsize=6.5,
                 color='#cce0f5', transform=bax.transAxes)

    # Content area: starts below metrics bar, ends at bottom margin
    # Extra gap so charts never clip the bar
    AREA_TOP = BAR_BOT - 0.015
    AREA_BOT = MARGIN_TB
    AREA_H   = AREA_TOP - AREA_BOT

    # Left tables (55% of printable width)
    L_LEFT  = MARGIN_LR
    L_RIGHT = MARGIN_LR + (1.0 - 2 * MARGIN_LR) * 0.48
    L_W     = L_RIGHT - L_LEFT

    # Right charts start with a small gap after tables
    R_LEFT  = L_RIGHT + 0.06
    R_RIGHT = 1.0 - MARGIN_LR

    # Table specs (title, height_fraction, headers, row_fn)
    # Heights must sum to <= 1.0 accounting for gaps
    GAP     = 0.008          # gap between tables (figure fraction)
    T_LBL_H = 0.018          # height reserved for title label

    table_specs = [
        ('Trip Length Distribution',
         0.170,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Total'],
         lambda r: [[
             'Count (%)',
             *[f"{r['trip_counts'][i]}  ({r['trip_counts'][i]/max(r['total_trips'],1)*100:.0f}%)"
               for i in range(1, 6)],
             str(r['total_trips']),
         ]]),
        ('Single Leg on Last Day',
         0.115,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall'],
         lambda r: [['%',
                     *[f"{r['single_leg_pct'][i]:.1f}%" for i in range(1, 6)],
                     f"{sum(r['trip_counts'][i]*r['single_leg_pct'][i] for i in range(1,6)) / max(sum(r['trip_counts'][i] for i in range(1,6)),1):.1f}%"]]),
        ('Average Credit per Trip (hrs)',
         0.115,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall'],
         lambda r: [['Hrs',
                     *[f"{r['avg_credit_by_length'][i]:.2f}" for i in range(1, 6)],
                     f"{r['avg_credit_per_trip']:.2f}"]]),
        ('Average Credit per Day (hrs/day)',
         0.115,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall'],
         lambda r: [['Hrs/d',
                     *[f"{r['avg_credit_per_day_by_length'][i]:.2f}" for i in range(1, 6)],
                     f"{r['avg_credit_per_day']:.2f}"]]),
        ('Commutability',
         0.220,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall'],
         lambda r: [
             ['Front', *[f"{r['front_commute_pct'][i]:.1f}%" for i in range(1, 6)],
              f"{r['front_commute_rate']:.1f}%"],
             ['Back',  *[f"{r['back_commute_pct'][i]:.1f}%"  for i in range(1, 6)],
              f"{r['back_commute_rate']:.1f}%"],
             ['Both',  *[f"{r['both_commute_pct'][i]:.1f}%"  for i in range(1, 6)],
              f"{r['both_commute_rate']:.1f}%"],
         ]),
        ('Red-Eye Trips',
         0.115,
         ['', '1-day', '2-day', '3-day', '4-day', '5-day', 'Overall'],
         lambda r: [['%',
                     *[f"{r['redeye_pct'][i]:.1f}%" for i in range(1, 6)],
                     f"{r['redeye_rate']:.1f}%"]]),
    ]

    # Calculate heights in figure coordinates, top-to-bottom
    n_tables  = len(table_specs)
    total_gap = GAP * (n_tables - 1)
    total_lbl = T_LBL_H * n_tables
    avail_h   = AREA_H - total_gap - total_lbl
    # fracs must sum to 1
    frac_sum  = sum(s[1] for s in table_specs)

    cur_top = AREA_TOP   # start from top, walk downward
    for title, frac, headers, rows_fn in table_specs:
        tbl_h  = avail_h * (frac / frac_sum)
        # Title label
        fig.text(L_LEFT, cur_top - T_LBL_H * 0.3, title,
                 fontsize=7.5, fontweight='bold', color=color, va='top')
        # Table axes (just below title)
        ax_bot = cur_top - T_LBL_H - tbl_h
        ax = fig.add_axes([L_LEFT, ax_bot, L_W, tbl_h])
        ax.axis('off')
        _draw_mpl_table(ax, headers, rows_fn(result), color, fontsize=7.0)
        cur_top = ax_bot - GAP

    # ── Right side: 2x2 charts ────────────────────────────────────────────────
    # Shrink chart area: top pulled down 8%, bottom raised 2% vs table area
    # This ensures charts never bleed into the metrics bar regardless of rescaling
    CHART_TOP = AREA_TOP - 0.08
    CHART_BOT = AREA_BOT + 0.02
    gs = gridspec.GridSpec(2, 2, left=R_LEFT, right=R_RIGHT,
                            top=CHART_TOP, bottom=CHART_BOT,
                            wspace=0.40, hspace=0.60)

    lbl5 = ['1d', '2d', '3d', '4d', '5d']

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.bar(lbl5, [result['trip_counts'][i] for i in range(1, 6)], color=color, alpha=0.85)
    ax1.set_title('Trip Length Distribution', fontsize=7, fontweight='bold', pad=2)
    ax1.set_ylabel('Count', fontsize=6)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(lbl5, [result['single_leg_pct'][i] for i in range(1, 6)], color=color, alpha=0.85)
    ax2.set_title('Single Leg Last Day (%)', fontsize=7, fontweight='bold', pad=2)
    ax2.set_ylabel('%', fontsize=6)

    ax3 = fig.add_subplot(gs[1, 0])
    x = range(5)
    w = 0.25
    ax3.bar([xi - w for xi in x], [result['front_commute_pct'][i] for i in range(1, 6)],
            w, label='Front', color=color, alpha=0.9)
    ax3.bar(list(x), [result['back_commute_pct'][i] for i in range(1, 6)],
            w, label='Back', color=color, alpha=0.6)
    ax3.bar([xi + w for xi in x], [result['both_commute_pct'][i] for i in range(1, 6)],
            w, label='Both', color=color, alpha=0.3)
    ax3.set_title('Commutability (%)', fontsize=7, fontweight='bold', pad=2)
    ax3.set_xticks(list(x))
    ax3.set_xticklabels(lbl5, fontsize=6)
    ax3.legend(fontsize=5, loc='upper right')

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.bar(lbl5, [result['redeye_pct'][i] for i in range(1, 6)], color='#e74c3c', alpha=0.85)
    ax4.set_title('Red-Eye Trips (%)', fontsize=7, fontweight='bold', pad=2)
    ax4.set_ylabel('%', fontsize=6)

    for ax in [ax1, ax2, ax3, ax4]:
        ax.tick_params(labelsize=6)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.3, linewidth=0.5)

    return fig


def _create_top20_fig(base, legs_data, display_name):
    """Create landscape Top-25 page figure."""
    import matplotlib.pyplot as plt
    import matplotlib
    import numpy as np
    matplotlib.use('Agg')

    color = BASE_COLORS.get(base, '#444444')
    base_label = "All Bases" if base == "All Bases" else f"{base} BASE"
    is_all = (base == "All Bases")

    # Use tight margins for print (0.5" = safe for all printers)
    # 0.5/11 = 0.0455 LR,  0.5/8.5 = 0.0588 TB
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor('white')
    MARGIN_LR = 0.046
    MARGIN_TB = 0.060

    title_top = 1.0 - MARGIN_TB
    fig.text(0.5, title_top,
             f"{base_label} - Top 25 Longest Legs (Sorted by Block Time)  |  {display_name}",
             ha='center', va='top', fontsize=12, fontweight='bold', color='#333333')

    # Summary bar
    BAR_TOP = title_top - 0.075
    BAR_H   = 0.048
    bax = fig.add_axes([MARGIN_LR, BAR_TOP - BAR_H, 1 - 2*MARGIN_LR, BAR_H])
    bax.set_facecolor(color)
    bax.axis('off')
    total = legs_data['total_top20']
    base_n = legs_data['base_top20']
    non_n  = legs_data['non_base_top20']
    bpct   = legs_data['base_pct_total']
    if is_all:
        bar_txt = f"Total Legs (Top 25): {total:,}"
    else:
        bar_txt = (f"Total Legs (Top 25): {total:,}   |   "
                   f"{base} Crews: {base_n:,} ({bpct}%)   |   "
                   f"Non-{base} Crews: {non_n:,} ({100 - bpct}%)")
    bax.text(0.5, 0.5, bar_txt, ha='center', va='center', fontsize=9,
             fontweight='bold', color='white', transform=bax.transAxes)

    legs = legs_data['legs']
    if not legs:
        fig.text(0.5, 0.5, 'No leg data available', ha='center', va='center', fontsize=12)
        return fig

    if is_all:
        headers = ['Rank', 'Route', 'Block', 'Total', 'Top Base', 'Base%']
        rows = [[str(i + 1), l['route'], l['block_str'], str(l['total']),
                 l['crew_dist'], f"{l['base_pct']}%"] for i, l in enumerate(legs)]
        tbl_left  = MARGIN_LR
        tbl_right = 1 - MARGIN_LR
    else:
        headers = ['Rank', 'Route', 'Block', 'Total', f'{base}%', 'Crew Distribution']
        rows = [[str(i + 1), l['route'], l['block_str'], str(l['total']),
                 f"{l['base_pct']}%", l['crew_dist']] for i, l in enumerate(legs)]
        tbl_left  = MARGIN_LR
        tbl_right = 0.710   # leave room for pie

    n_rows = len(rows)
    n_cols = len(headers)

    CONTENT_TOP = BAR_TOP - BAR_H - 0.010
    CONTENT_BOT = MARGIN_TB
    tbl_h = CONTENT_TOP - CONTENT_BOT
    tbl_w = tbl_right - tbl_left

    ax = fig.add_axes([tbl_left, CONTENT_BOT, tbl_w, tbl_h])
    ax.axis('off')

    # Color-code base% column for base-specific report
    cell_colors = []
    for r in range(n_rows):
        row_c = ['#eef2f8' if r % 2 == 0 else 'white'] * n_cols
        if not is_all and n_cols > 4:
            pct = legs[r]['base_pct']
            row_c[4] = ('#c8e6c9' if pct >= 90 else
                        '#fff9c4' if pct >= 50 else '#ffccbc')
        cell_colors.append(row_c)

    # Font size: smaller to fit 25 rows
    font_sz = 6.8 if n_rows <= 20 else 6.2

    tbl = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc='center',
        loc='upper center',
        bbox=[0, 0, 1, 1],
        cellColours=cell_colors,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(font_sz)

    for j in range(n_cols):
        tbl[0, j].set_facecolor(color)
        tbl[0, j].set_text_props(color='white', fontweight='bold')
    for key, cell in tbl.get_celld().items():
        cell.set_edgecolor('#cccccc')
        cell.set_linewidth(0.3)

    # Proportional column widths (base-specific)
    if not is_all:
        col_widths = [0.05, 0.09, 0.07, 0.07, 0.07, 0.65]
        tw = sum(col_widths)
        for j, cw in enumerate(col_widths):
            for r in range(0, n_rows + 1):
                tbl[r, j].set_width(cw / tw)
        for r in range(1, n_rows + 1):
            tbl[r, 5]._text.set_ha('left')

    # Pie chart (base-specific only)
    if not is_all and total > 0:
        pie_left   = tbl_right + 0.015
        pie_bottom = CONTENT_BOT + tbl_h * 0.20
        pie_size   = min(1 - MARGIN_LR - pie_left, tbl_h * 0.65)
        pax = fig.add_axes([pie_left, pie_bottom, pie_size, pie_size])
        wedge_sizes = [max(base_n, 0), max(non_n, 0)]
        if sum(wedge_sizes) > 0:
            wedges, _ = pax.pie(
                wedge_sizes,
                colors=[color, '#dddddd'],
                startangle=90,
                counterclock=False,
                wedgeprops=dict(linewidth=0.5, edgecolor='white'),
            )
            pax.set_title(f'{base} vs Others', fontsize=9, fontweight='bold', pad=6)
            for wedge, txt, clr in zip(
                wedges,
                [f"{base}\n{bpct}%", f"Others\n{100 - bpct}%"],
                ['white', '#555555'],
            ):
                angle = np.radians((wedge.theta2 + wedge.theta1) / 2)
                xp = 0.52 * np.cos(angle)
                yp = 0.52 * np.sin(angle)
                pax.text(xp, yp, txt, ha='center', va='center',
                         fontsize=8, fontweight='bold', color=clr)

    return fig


def generate_comprehensive_base_report(file_content, fdata, selected_base,
                                        front_time_str, back_time_str):
    """
    Generate comprehensive base report PDF bytes (single file only).
    If 'All Bases': AllBases Summary + Top20, then each base with trips.
    If specific base: Base Summary + Base Top20.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    bid_year = fdata['year']
    display_name = fdata['display_name']

    def _t2m(s):
        h, m = map(int, s.split(':'))
        return h * 60 + m

    front_min = _t2m(front_time_str)
    back_min = _t2m(back_time_str)

    known_bases = ['ATL', 'BOS', 'DTW', 'LAX', 'MSP', 'NYC', 'SEA', 'SLC']

    if selected_base == "All Bases":
        bases = ["All Bases"] + known_bases
    else:
        bases = [selected_base]

    buf = BytesIO()
    with PdfPages(buf) as pdf:
        for base in bases:
            result = analyze_file(
                file_content, base, front_min, back_min, False, bid_year
            )
            if result['total_trips'] == 0 and base != "All Bases":
                continue

            fig = _create_summary_fig(
                base, result, display_name, front_time_str, back_time_str
            )
            pdf.savefig(fig, dpi=150)
            plt.close(fig)

            legs_data = get_base_top20_legs(file_content, base, bid_year)
            fig = _create_top20_fig(base, legs_data, display_name)
            pdf.savefig(fig, dpi=150)
            plt.close(fig)

    return buf.getvalue()
