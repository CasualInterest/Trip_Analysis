"""
rps_parser.py
Parses RPS (Rotation Preference Survey) files.
RPS files are ZIP archives disguised as PDFs, containing JPEG images and .txt files.
"""

import zipfile
import io
import re


# Known base codes that prefix fleet in RPS filenames
_BASES = ['ATL', 'DTW', 'INS', 'LAX', 'MSP', 'NYC', 'SEA', 'SLC', 'BOS']


def parse_rps_file(file_bytes, filename):
    """
    Parse an RPS file and return structured survey data.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the RPS file (ZIP archive)
    filename : str
        Original filename, e.g. '202603_320_NoComments.pdf'
        or '202603_LAX320_NoComments.pdf'

    Returns
    -------
    dict with keys:
        fleet          : str  e.g. '320'
        base           : str or None  e.g. 'LAX', or None = all bases
        yyyymm         : str  e.g. '202603'
        commutable_pct : int or None  % who prefer commutable rotations
        trip_length_pct: dict {1: float, 2: float, ...}  weighted %
        raw_text       : str  full extracted text for debugging
    """
    fleet, base, yyyymm = _parse_filename(filename)
    all_text = _extract_text(file_bytes)

    commutable_pct = _parse_commutable(all_text)
    trip_length_pct = _parse_trip_length(all_text)

    return {
        'fleet': fleet,
        'base': base,
        'yyyymm': yyyymm,
        'commutable_pct': commutable_pct,
        'trip_length_pct': trip_length_pct,
        'raw_text': all_text,
    }


def _parse_filename(filename):
    """
    Extract yyyymm, fleet, and base from RPS filename.

    Patterns:
        202603_320_NoComments.pdf          → fleet='320', base=None
        202603_LAX320_NoComments.pdf       → fleet='320', base='LAX'
        202603_ATL320_NoComments.pdf       → fleet='320', base='ATL'
    """
    name = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE)
    parts = name.split('_')

    yyyymm = parts[0] if parts else None

    fleet = None
    base = None

    if len(parts) >= 2:
        identifier = parts[1]
        for b in _BASES:
            if identifier.upper().startswith(b):
                base = b
                fleet = identifier[len(b):]
                break
        if fleet is None:
            fleet = identifier  # all-bases file, identifier IS the fleet

    return fleet, base, yyyymm


def _extract_text(file_bytes):
    """Extract all .txt pages from the ZIP and concatenate them."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            txt_names = sorted(
                [n for n in z.namelist() if n.endswith('.txt')],
                key=lambda x: int(re.sub(r'\D', '', x) or '0')
            )
            parts = []
            for name in txt_names:
                parts.append(z.read(name).decode('utf-8', errors='replace'))
            return '\n'.join(parts)
    except Exception:
        return ''


def _parse_commutable(text):
    """
    Extract the Yes % from the 'Prefer commutable rotations' section.

    In the source data this appears as:
        Commuter Rotation Responses
        Yes 709 64%
        No  233 21%
        ...
    """
    # Look for the section header followed by Yes line
    m = re.search(
        r'Commuter Rotation[^\n]*\n\s*Yes\s+\d+\s+(\d+)%',
        text,
        re.IGNORECASE
    )
    if m:
        return int(m.group(1))

    # Fallback: find Yes / No / Sometimes triple near a commuter heading
    m = re.search(
        r'Yes\s+(\d+)\s+(\d+)%\s*[\r\n]+\s*No\s+\d+\s+\d+%\s*[\r\n]+\s*Sometimes',
        text,
        re.IGNORECASE
    )
    if m:
        return int(m.group(2))

    return None


def _parse_trip_length(text):
    """
    Extract weighted-% for each trip length from the Rank Preferred Trip Length table.

    Source data format (spaces may vary):
        1 Day 262 84 215 261 578 3391 15.05% 206.4
        2 Day 187 505 298 487  20 4843 21.49% 147.4
        ...
    Pattern: <N> Day <5 ranking counts> <weighted sum> <weighted %>  <total>
    """
    result = {}
    for day in range(1, 8):
        # 6 numbers after "N Day" then the percentage
        pattern = rf'\b{day}\s+Day\s+(?:\d+\s+){{6}}(\d+\.\d+)%'
        m = re.search(pattern, text)
        if m:
            result[day] = float(m.group(1))
    return result


def get_rps_data_for_context(rps_files_dict, fleet, base_filter):
    """
    Given the session state rps_files dict, return the best matching RPS data
    for the given fleet and base_filter.

    Priority:
        1. Exact match: fleet + base
        2. All-bases fallback: fleet + base=None
        3. First available (single-file fallback)

    Parameters
    ----------
    rps_files_dict : dict  {filename: parsed_rps_dict}
    fleet          : str or None  e.g. '320'
    base_filter    : str  e.g. 'LAX' or 'All Bases'
    """
    if not rps_files_dict:
        return None

    fleet_norm = (fleet or '').strip().upper()
    target_base = None if base_filter == 'All Bases' else base_filter

    # Pass 1: exact fleet + base match
    for data in rps_files_dict.values():
        rps_fleet = (data.get('fleet') or '').strip().upper()
        if rps_fleet == fleet_norm and data.get('base') == target_base:
            return data

    # Pass 2: fleet + all-bases (base=None) fallback
    if target_base is not None:
        for data in rps_files_dict.values():
            rps_fleet = (data.get('fleet') or '').strip().upper()
            if rps_fleet == fleet_norm and data.get('base') is None:
                return data

    # Pass 3: any fleet match (base ignored)
    for data in rps_files_dict.values():
        rps_fleet = (data.get('fleet') or '').strip().upper()
        if rps_fleet == fleet_norm:
            return data

    # Pass 4: single loaded file, use it regardless
    if len(rps_files_dict) == 1:
        return list(rps_files_dict.values())[0]

    return None
