# Version 64 - Red-Eye Analysis Enhancement

## New Feature: Total Red-Eyes Column in Comparison Analysis

### Changes Made:

#### 1. Sequential Mode Comparison (Multi-file)
- ✅ **Added Section 6: Trips Containing Red-Eye Flight**
  - Shows red-eye trip counts and percentages by trip length (1-5 days)
  - Shows overall red-eye statistics
  - **NEW**: "Total Red-Eyes" column showing absolute count of red-eye trips
  - Includes difference calculations when comparing exactly 2 files
  
#### 2. Year-over-Year Mode Comparison
- ✅ **Enhanced existing Section 6**
  - **NEW**: "Total Red-Eyes" column added to show absolute count of red-eye trips per year
  - Maintains existing percentage displays by trip length

### What This Means:

When comparing multiple bid packs, users can now see:
- **Percentage view**: What % of trips contain red-eyes (by length and overall)
- **Absolute count**: Exactly how many trips contain red-eyes
- **Differences**: When comparing 2 files, see the change in both percentages and absolute counts

### Example Output:

**Sequential Mode - Section 6:**
```
File          | 1-day        | 2-day        | ... | Overall     | Total Red-Eyes
--------------|--------------|--------------|-----|-------------|---------------
Jan 2025 320  | 15 (2.50%)   | 45 (7.20%)  | ... | 150 (5.5%) | 150
Feb 2025 320  | 18 (3.00%)   | 52 (8.30%)  | ... | 175 (6.2%) | 175
```

**Difference Row (when 2 files):**
```
Metric                      | 1-day       | 2-day       | ... | Overall    | Total Red-Eyes
----------------------------|-------------|-------------|-----|------------|---------------
Percentage Point Difference | +0.50 points| +1.10 points| ... | +0.70 points| +25
```

### Files Modified:
- `app.py`: Lines 1510-1563 (Sequential mode section 6 added)
- `app.py`: Lines 1272-1285 (Year-over-Year mode enhanced)

### Version: v64
### Date: 2026-01-29
