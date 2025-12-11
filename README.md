# ✈️ Pilot Trip Scheduling Analysis App

A Streamlit web application for analyzing airline pilot trip scheduling data.

## Features

- 📁 Upload up to 12 trip schedule files
- 📊 Comprehensive analysis of 6 key metrics:
  - Trip length distribution
  - Single leg on last day
  - Average credit per trip
  - Average credit per day
  - Red-eye flight analysis
  - Commutability (front-end, back-end, both ends)
- 🔍 Base filtering (ATL, BOS, NYC, DTW, SLC, MSP, SEA, LAX)
- ⏰ Customizable commutability time thresholds
- 📈 Interactive charts and visualizations
- 📄 PDF export for reports
- 🔄 Compare up to 12 different schedules

## Deployment to Streamlit Cloud

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at share.streamlit.io)

### Steps

1. **Create a new GitHub repository**
   - Go to GitHub and create a new repository
   - Name it something like `pilot-trip-analysis`
   - Make it public or private

2. **Upload files to repository**
   Upload these files to your GitHub repo:
   ```
   pilot-trip-analysis/
   ├── app.py
   ├── analysis_engine.py
   └── requirements.txt
   ```

3. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Select your GitHub repository
   - Set main file path to: `app.py`
   - Click "Deploy"

4. **Your app will be live!**
   - Streamlit Cloud will automatically install dependencies
   - App will be available at: `https://[your-app-name].streamlit.app`

## Local Development

To run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. **Upload Files**: Upload trip schedule .txt files (max 12)
2. **Set Date**: For each file, specify the month and year
3. **Configure Settings**:
   - Select base filter
   - Adjust commutability times
4. **Analyze**: Click "Analyze Data" to process
5. **View Results**: Explore charts and metrics
6. **Export**: Download PDF report

## File Format

The app expects trip schedule files in the standard format with:
- EFFECTIVE date headers
- Day markers (A, B, C, D, E)
- Flight segments (AIRPORT TIME AIRPORT TIME)
- TOTAL CREDIT lines

## Base Codes

- ATL: Atlanta
- BOS: Boston
- NYC: New York (JFK, LGA, EWR)
- DTW: Detroit
- SLC: Salt Lake City
- MSP: Minneapolis
- SEA: Seattle
- LAX: Los Angeles (LAX, LGB, ONT)

## Metrics Explained

### Trip Length Distribution
Shows percentage of trips by length (1-5 days). Trip length is determined by the last day letter, with red-eye rule adding an extra day if the last flight departs ≥20:00 and arrives ≥02:00.

### Single Leg on Last Day
Percentage of trips where the last day contains only one flight leg.

### Average Credit Per Trip
Average credit hours earned per trip, broken down by trip length.

### Average Credit Per Day
Average credit hours per day of trip, calculated as total credit ÷ trip length.

### Red-Eye Analysis
Percentage of trips containing any flight leg that departs ≥20:00 and arrives ≥02:00.

### Commutability
- **Front-End**: Report time (1st departure - 60 min) meets threshold
- **Back-End**: Release time (last arrival + 45 min) meets threshold
- **Both Ends**: Meets both front and back-end criteria

## Technical Notes

### File Size Limitations
- Streamlit Cloud has a 200MB file upload limit per file
- The app can handle large files efficiently through streaming
- If you encounter memory issues with very large files, consider:
  - Splitting files by base before upload
  - Using the base filter to process subsets

### Performance
- Analysis typically completes in 5-30 seconds depending on file size
- Multiple file comparison may take longer but should complete within 2 minutes

### Date Handling
- Files are assumed to be for January 2026 by default
- The app handles date ranges that cross year boundaries (e.g., DEC31-JAN09)
- EXCEPT dates are properly subtracted from occurrence counts

## Troubleshooting

**App is slow or timing out:**
- Try analyzing fewer files at once
- Use base filters to reduce dataset size
- Ensure files are in the correct format

**Charts not displaying:**
- Check that analysis completed successfully
- Verify files contain valid trip data
- Try refreshing the page

**PDF export fails:**
- This may occur with very large datasets
- Try exporting with fewer files loaded

## Support

For issues or questions, please create an issue in the GitHub repository.

## License

This tool is provided as-is for internal use.
