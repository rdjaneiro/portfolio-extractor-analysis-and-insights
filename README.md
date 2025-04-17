# Empower Portfolio WebArchive Extractor

A Streamlit web application that extracts portfolio holdings data from Empower retirement account webarchive files and converts them to both human-readable text and CSV format for further analysis.

## Features

- **WebArchive Processing**: Extract text content from .webarchive files from Empower retirement accounts
- **Portfolio Data Extraction**: Parse and structure portfolio holdings data
- **CSV Export**: Generate downloadable CSV files containing portfolio data
- **User-Friendly Interface**: Easy-to-use web interface powered by Streamlit
- **Flexible Input Options**: Upload files or process existing files in the directory

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/empower-portfolio-extractor.git
   cd empower-portfolio-extractor
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Dependencies

- Python 3.6+
- streamlit
- pandas
- BeautifulSoup4 (for webarchive parsing)

## Usage

1. Launch the application:
   ```bash
   streamlit run finTools_app.py --server.port=8505 --server.address=0.0.0.0
   ```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Select your input method:
   - Upload a .webarchive file
   - Choose from available files in the current directory

4. Configure extraction options:
   - Extract Portfolio Holdings: Parse and structure the portfolio data
   - Generate CSV File: Save the extracted data as a CSV file
   - Show Full Extracted Text: Display the raw text content of the webarchive

5. Click "Process WebArchive File" to start the extraction

6. View the results and download the CSV file if needed

## File Structure

- `finTools_app.py`: Main Streamlit application
- `read_empower_webarchive.py`: Module containing functions for processing webarchive files
- `requirements.txt`: List of Python dependencies

## How to Generate WebArchive Files

1. Log in to your Empower retirement account
2. Navigate to the portfolio/holdings page
3. In Safari browser:
   - Go to File > Save As
   - Select "Web Archive" format
   - Save the file to your computer

## Output Format

The extracted portfolio data includes:
- Fund names
- Asset classes
- Allocation percentages
- Current values
- Share quantities
- Price per share

## Troubleshooting

If you encounter issues with extraction:
1. Ensure your webarchive file contains portfolio data (extracted from the portfolio page)
2. Check the "Show Full Extracted Text" option to view the raw content
3. Make sure the webarchive format is compatible (Safari-generated)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
