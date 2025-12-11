# Major Analysis Update - Version 2.0

## 🎯 Overview

The app has been completely updated to follow professional pilot trip scheduling analysis rules, including occurrence counting, red-eye adjustments, and proper commutability calculations.

---

## ✨ New Features

### 1. **Month/Year Selection for Each File**

When you upload a file, you'll now be prompted to select:
- **Month**: January through December
- **Year**: 2020-2030 (default: 2026)

This is critical for:
- Calculating trip occurrences from date ranges
- Properly labeling charts and reports
- Handling year boundary crossings (e.g., DEC31-JAN09)

**How it works:**
1. Upload a file
2. Expand to see month/year selectors
3. Click "Process [filename]" button
4. File is parsed with correct date context

---

### 2. **Occurrence Counting**

Trips are now counted based on how many times they actually operate, not just as single instances.

**Example:**
```
#4467 WE FR EFFECTIVE JAN21-JAN. 28
```

This expands to:
- Wednesdays in range: Jan 21, Jan 28 = 2 occurrences
- Fridays in range: Jan 23 = 1 occurrence
- **Total: 3 occurrences**

**EXCEPT Handling:**
```
EXCEPT JAN 02 JAN 07
```
Specific dates are subtracted from the count.

**Formats Supported:**
- Single date: `JAN01 ONLY`
- Date range: `JAN21-JAN. 28`
- Year crossing: `DEC31-JAN. 09`

---

### 3. **Trip Length with Red-Eye Rule**

Trip length is now calculated correctly:

**Base Length:**
- Last day = A → 1-day trip
- Last day = B → 2-day trip
- Last day = C → 3-day trip
- Last day = D → 4-day trip
- Last day = E → 5-day trip

**Red-Eye Adjustment (+1 day):**
If the LAST flight leg:
- Departs ≥ 20:00 (8:00 PM) AND
- Arrives ≥ 02:00 (2:00 AM)
→ Add 1 day to base length

**Example:**
```
Trip with days A, B, C, D (base = 4 days)
Last flight: ONT 2229 → ATL 0539
→ Departs 22:29 (≥20:00) ✓
→ Arrives 05:39 (≥02:00) ✓
→ Final length = 5 days
```

---

### 4. **Enhanced Red-Eye Detection**

Red-eyes are now detected on ANY flight leg (not just the last):

**Criteria:**
- Departure ≥ 20:00 (8:00 PM) AND
- Arrival ≥ 02:00 (2:00 AM)

**Both conditions must be true** for a single leg.

The app checks every flight in the trip and counts the trip as containing a red-eye if any leg meets the criteria.

---

### 5. **Professional Commutability Calculation**

Commutability now uses industry-standard calculations:

**Front-End (Report Time):**
```
Report Time = First Departure - 60 minutes
Trip is front-commutable if Report Time ≥ Threshold
```

**Example:**
```
First departure: 11:30
Report time: 11:30 - 60 = 10:30
Threshold: 10:30
Result: Commutable ✓
```

**Back-End (Release Time):**
```
Release Time = Last Base Arrival + 45 minutes
Trip is back-commutable if Release Time ≤ Threshold
```

**Example:**
```
Last ATL arrival: 16:08
Release time: 16:08 + 45 = 16:53 (4:53 PM)
Threshold: 18:00 (6:00 PM)
Result: Commutable ✓
```

**Time Wraparound:**
- Subtraction < 0: Add 24 hours
- Addition > 23:59: Subtract 24 hours

**Custom Thresholds:**
You can still adjust the time selectors to fine-tune what you consider "commutable":
- Default front: 10:30
- Default back: 18:00

---

### 6. **Weighted Metrics**

All metrics are now occurrence-weighted:

**Before:** Each trip counted as 1
**Now:** Each trip counted by its occurrences

**Example:**
```
Trip A: 10 hours credit, 3 occurrences = 30 total credit hours
Trip B: 15 hours credit, 1 occurrence = 15 total credit hours
Average: (30 + 15) / (3 + 1) = 11.25 hours per trip
```

This gives accurate fleet-wide statistics.

---

### 7. **Credit Per Day Calculation**

Now properly divides by actual trip length (after red-eye adjustment):

```
15.87 credit hours ÷ 3-day trip = 5.29 hours/day
```

---

## 📊 Updated Display

### Trip Length Distribution
- Shows occurrences (not just unique trips)
- Includes percentages
- Totals at bottom

### Single Leg on Last Day
- Checks base last day (before red-eye)
- Shows count and percentage

### Commutability Metrics
- Front, Back, and Both commutable
- Red-eye count
- All with counts and percentages

### Average Credit
- By trip length
- Overall average
- Weighted by occurrences

---

## 🔍 Analysis Workflow

### For Single File:

1. **Upload** your bidding file
2. **Select** month and year
3. **Click** "Process [filename]"
4. **Filter** by base (optional)
5. **Adjust** commute times if needed
6. **Review** all metrics
7. **Export** PDF report

### For Multiple Files (Comparison):

1. **Upload** multiple files (e.g., TEST and ACTUAL)
2. **Set** month/year for each
3. **Process** each file
4. **Use same** base filter
5. **Compare** metrics side-by-side
6. **Export** comparison report

---

## 🎯 Key Metrics Explained

### Trip Length Distribution
Shows how trips are distributed across 1-5 day lengths (after red-eye adjustment).

**What it means:**
- High 1-2 day %: More turns, less time away
- High 3-4 day %: Balanced schedule
- High 5 day %: Longer trips, less frequency

### Average Credit Per Trip
Total credit hours divided by trip occurrences.

**What it means:**
- Higher = More productive trips
- Compare across trip lengths
- Compare TEST vs ACTUAL

### Average Credit Per Day
Credit divided by trip length in days.

**What it means:**
- Industry standard: ~5.3 hours/day
- Lower = More spread out schedule
- Higher = More compressed flying

### Red-Eye Percentage
Trips containing at least one red-eye flight.

**What it means:**
- Higher = More overnight/early morning
- Affects fatigue and commutability
- Industry typical: 8-10%

### Commutability
Percentage of trips that fit within your schedule.

**Front Commutable:**
- Can arrive at airport with reasonable time
- Based on first departure

**Back Commutable:**
- Can get home at reasonable hour
- Based on last base arrival

**Both Commutable:**
- The "sweet spot" trips
- Neither early start nor late finish

---

## 📋 File Requirements

### Format
- Text files (.txt)
- Standard bidding format
- Trip boundaries marked with dashed lines
- EFFECTIVE dates required

### Size
- Individual files: Up to 10MB
- Multiple files: Up to 12 files total

### Date Ranges
Must include date information:
- Single: `JAN01 ONLY`
- Range: `JAN21-JAN. 28`
- Can cross years: `DEC31-JAN. 09`

---

## 🔧 Troubleshooting

### "No occurrences found"
- Check that EFFECTIVE dates are present
- Verify month/year selection is correct
- Ensure days of week are specified

### "Trip length seems wrong"
- Check for red-eye rule application
- Last flight departing after 8 PM and arriving after 2 AM adds a day

### "Commutability numbers don't match my calculation"
- Remember: Report time = first departure - 60 min
- Remember: Release time = last base arrival + 45 min
- Check if multi-airport base (NYC, LAX)

### "Metrics seem low"
- Check base filter - are you filtering correctly?
- Verify month/year matches your file
- Check if TEST file (already filtered) vs ACTUAL (needs filtering)

---

## 💡 Tips for Best Analysis

### Comparing TEST vs ACTUAL:

1. **Use same month/year** for both files
2. **Filter both for same base** (e.g., ATL)
3. **Use same commute times** for fair comparison
4. **Look for differences** in:
   - Trip length distribution
   - Credit per trip/day
   - Commutability percentages

### Finding Your Ideal Schedule:

1. **Start with default times** (10:30 / 18:00)
2. **Adjust based on your commute**:
   - Live far? Increase front threshold
   - Want more home time? Decrease back threshold
3. **Check "Both Commutable" percentage**
4. **Balance with credit hours** - higher commutability may mean lower credit

### Analyzing Fleet Changes:

1. **Upload old and new files**
2. **Compare trip lengths** - shifting to longer or shorter?
3. **Compare credit** - increasing or decreasing productivity?
4. **Check red-eyes** - more or fewer overnight trips?

---

## 📈 Expected Results (Validation)

For ATL base in January 2026:

| Metric | Expected Range |
|--------|----------------|
| Total trips | 2,250-2,300 |
| Avg credit/day | 5.3-5.4 hours |
| Red-eye rate | 8-10% |
| Front commutable | 45-48% |
| Back commutable | 85-90% |
| Both commutable | 40-45% |

If your numbers are significantly different, review:
- Base filter settings
- Month/year selection
- File format and parsing

---

## 🚀 What's Next

Future enhancements may include:
- Automated TEST vs ACTUAL comparison mode
- Historical trend analysis across multiple months
- Reserve day analysis
- Custom metric definitions
- Advanced filtering options

---

**Version**: 2.0 - Professional Analysis Rules  
**Date**: December 11, 2025  
**Status**: Production Ready

