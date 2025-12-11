# Flight Bidding Data Analyzer

A Streamlit web application for analyzing flight crew bidding data across multiple fleet types and bases.

## Features

- **Upload Multiple Files**: Analyze up to 12 bidding data files simultaneously
- **Base Filtering**: Filter analysis by specific crew bases (ATL, SEA, MSP, DTW, NYC, SLC, LAX)
- **Comprehensive Metrics**:
  - Trip day length distribution
  - Trips with one leg on last day
  - Average credit per trip
  - Average credit per day
  - Red-eye flight detection
  - Commutability analysis (front, back, both)
- **Comparison Mode**: Compare metrics across multiple files
- **Visual Analytics**: Interactive charts and graphs using Plotly
- **PDF Export**: Generate downloadable PDF reports
- **Clear Data**: One-click data clearing for privacy

## Supported Fleet Types

- 320 (A320 family)
- 737/738/73N (Boeing 737 variants)
- 7ER (Boeing 777ER)
- 220 (Airbus A220)
- 330 (Airbus A330)
- 350 (Airbus A350)
- 717 (Boeing 717)
- 765 (Boeing 767-500)

## Base Determination

Bases are automatically detected from the first departure airport of each trip:
- **ATL** - Atlanta (ATL)
- **BOS** - Boston (BOS)
- **NYC** - New York (JFK, LGA, EWR)
- **DTW** - Detroit (DTW)
- **SLC** - Salt Lake City (SLC)
- **MSP** - Minneapolis (MSP)
- **SEA** - Seattle (SEA)
- **LAX** - Los Angeles (LAX, LGB, ONT)

## Installation

### Local Development

1. Clone this repository:
```bash
git clone <your-repo-url>
cd flight-bidding-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run app.py
```

4. Open your browser to `http://localhost:8501`

## Deployment to Streamlit Cloud

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))

### Steps

1. **Push to GitHub**:
   - Create a new repository on GitHub
   - Push your code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository
   - Set the main file path to `app.py`
   - Click "Deploy"

3. **Configuration** (optional):
   - You can create a `.streamlit/config.toml` file for custom settings
   - Set memory limits if needed for large files

## Usage

1. **Upload Files**: Use the sidebar to upload 1-12 bidding data text files
2. **Filter by Base**: Select a specific base or "All" to view all bases
3. **View Analysis**: 
   - Single file: Detailed metrics and visualizations
   - Multiple files: Comparison tables and charts
4. **Export Report**: Click "Download PDF Report" to save analysis results
5. **Clear Data**: Use "Clear All Data" button to remove all uploaded files

## File Format

The app expects text files in the standard bidding format with:
- Base headers (e.g., "ATL BASE")
- Trip numbers (e.g., "#4426")
- Day designations (A, B, C, D)
- Total credit and TAFB information

## Limitations

### File Size
- Individual files up to ~10MB recommended
- With 12 files, total upload should stay under 100MB for optimal performance
- Your uploaded file (6.2MB) is well within limits

### Processing Notes
- Parsing 80,000+ lines per file is efficient with pandas
- Initial load time: 2-5 seconds per file
- Filtering and recalculation: Near-instant
- PDF generation: 1-2 seconds

### Memory Considerations
- Streamlit Cloud free tier: 1GB RAM
- Estimated memory usage:
  - Each 6MB file ≈ 50-100MB RAM when parsed
  - 12 files ≈ 600-1200MB RAM total
- Recommendation: Test with 6-8 files initially on free tier

## Advanced Features (Planned)

- Detailed commutability scoring based on actual flight times
- Red-eye detection with configurable time windows
- Reserve day analysis
- Calendar view of trips
- Historical trend analysis

## Troubleshooting

### "File too large" error
- Files over 200MB may timeout
- Split large files by base or date range

### Memory errors on Streamlit Cloud
- Reduce number of simultaneous files
- Use base filtering to reduce dataset size

### Parse errors
- Ensure files match the expected format
- Check for encoding issues (use UTF-8)

## Contributing

Suggestions for improvements:
- Enhanced commutability algorithms
- Additional metrics
- Export to Excel
- Database storage for historical analysis

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License - feel free to modify and use for your needs.
