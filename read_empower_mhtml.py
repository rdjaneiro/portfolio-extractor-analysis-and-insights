"""
Empower Portfolio MHTML Extractor
Copyright (C) 2025 Rodrigo Loureiro

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Empower Portfolio MHTML Extractor
# -----------------------------------------------------------------------------
#
# OVERVIEW:
# This script extracts portfolio holdings data from Empower retirement account
# MHTML files (.mhtml, .mht) and converts them to both human-readable text and CSV format.
# It can process the entire MHTML content or specifically extract just
# the portfolio holdings section with ticker symbols, share counts, prices, etc.
#
# INPUT:
# - .mhtml/.mht files (MIME HTML archive format used by Chrome/Edge/Firefox)
# - The script looks for portfolio data in a specific format with sections showing:
#   Ticker, Name, Shares, Price, Change, Day percentage, Day dollar change, and Value
#
# OUTPUT:
# - CSV file with structured portfolio data (default)
# - Text file with extracted content (optional)
#
# USAGE:
# Basic usage (default: extract portfolio to CSV, interactive file selection):
#   python read_empower_mhtml.py
#
# Specify input file:
#   python read_empower_mhtml.py portfolio.mhtml
#
# Extract full text content:
#   python read_empower_mhtml.py portfolio.mhtml --full-text
#
# Custom output name:
#   python read_empower_mhtml.py portfolio.mhtml -o my_portfolio
#
# Extract portfolio as formatted text (no CSV):
#   python read_empower_mhtml.py portfolio.mhtml --portfolio --no-csv
#
# DEPENDENCIES:
# - BeautifulSoup4 (bs4): For HTML parsing
# - email: For parsing MHTML format
# - argparse: For command-line argument handling
# -----------------------------------------------------------------------------

import bs4
import argparse
import os
import sys
import glob
import re
import csv
import email
from email import policy
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_mhtml_text(file_path):
    """Extract text content from an MHTML file."""
    try:
        # Read the MHTML file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            mhtml_content = file.read()

        # Parse the MHTML content using email parser
        message = email.message_from_string(mhtml_content, policy=policy.default)

        # Extract HTML content from MHTML
        html_content = None

        # Iterate through parts to find HTML content
        for part in message.walk():
            content_type = part.get_content_type()

            if content_type == 'text/html':
                html_content = part.get_content()
                break

        if not html_content:
            return "Error: No HTML content found in MHTML file."

        # Parse HTML with BeautifulSoup
        soup = bs4.BeautifulSoup(html_content, "html.parser")

        # Extract visible text
        extracted_text = soup.get_text(separator="\n")

        return extracted_text
    except Exception as e:
        logger.error(f"Error reading MHTML file: {e}", exc_info=True)
        return f"Error reading MHTML file: {e}"

def extract_grand_totals(text_content):
    """
    Extract the grand total values (Day_Dollar and Value) from the raw text.
    Returns a tuple of (day_dollar_total, value_total) or None if not found.
    """
    grand_total_pattern = r'Grand total\s+([+-]?\$[\d,]+\.\d+)\s+\$([\d,]+\.\d+)'
    match = re.search(grand_total_pattern, text_content)

    if match:
        day_dollar_total = match.group(1)  # This includes the $ sign
        value_total = match.group(2)       # This doesn't include the $ sign

        # Clean the values for numeric comparison
        day_dollar_numeric = float(day_dollar_total.replace('$', '').replace(',', ''))
        value_numeric = float(value_total.replace(',', ''))

        return {
            'day_dollar_total': day_dollar_total,
            'value_total': f"${value_total}",
            'day_dollar_numeric': day_dollar_numeric,
            'value_numeric': value_numeric
        }

    return None

def extract_portfolio_holdings(text_content):
    """
    Extract portfolio holdings from the text content in the format:
    Ticker
    Company Name
    Shares
    Price
    Change
    1 Day %
    1 day $
    Value
    """
    # Look for the holdings section headers pattern
    holdings_pattern = r"Holding\s+Shares\s+Price\s+Change\s+1 Day %\s+1 day \$\s+Value"
    if not re.search(holdings_pattern, text_content):
        return "Could not find portfolio holdings section in the file."

    # Split the content at the heading line
    sections = re.split(holdings_pattern, text_content)
    if len(sections) < 2:
        return "Could not parse portfolio holdings section."

    # Extract the holdings section (should be after the heading)
    holdings_section = sections[1]

    # Extract grand total values for integrity check
    grand_totals = extract_grand_totals(text_content)

    # Find where the holdings section ends (typically at "Grand total")
    end_marker = "Grand total"
    if end_marker in holdings_section:
        holdings_section = holdings_section.split(end_marker)[0]

    # Process the holdings data
    # Look for patterns like ticker symbol followed by company name, shares, etc.
    holdings_data = []

    # Use regex to find holdings entries
    # Look for patterns that include standard stock format, cash, and crypto formats
    entries = []  # Initialize the entries list here
    # Track unique tickers to prevent duplicates
    processed_tickers = set()

    # Standard Entries Pattern : Standard entries for stocks - more flexible pattern
    standard_entries = re.findall(r'([A-Z0-9\.\-]+)(?:\s+([^\n]+?))\s+(\d+(?:\.\d+)?)\s+\$(\d+(?:\.\d+)?)\s+\$?([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?%)\s+([-+]?\$\d+(?:,\d+)*(?:\.\d+)?)\s+\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in standard_entries:
        ticker = entry[0]
        # Only add if this ticker hasn't been processed yet
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            logger.info(f"Added standard entry: {ticker}")

    # Alternative stock pattern for different spacing or formatting
    alt_stock_entries = re.findall(r'([A-Z0-9\.\-]+)\s+([^\n]+?)\s+(\d+(?:\.\d+)?)\s+\$(\d+(?:\.\d+)?(?:,\d+)*)\s+([-+]?[^\s]+)\s+([-+]\d+(?:\.\d+)?%)\s+([-+]\$\d+(?:,\d+)*(?:\.\d+)?)\s+\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in alt_stock_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            logger.info(f"Added alternative stock entry: {ticker}")

    # Cash entries pattern
    cash_entries = re.findall(r'Cash\s+(\d+(?:\.\d+)?)\s+\$(\d+(?:\.\d+)?)\s+\$?([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?%)\s+([-+]?\$\d+(?:,\d+)*(?:\.\d+)?)\s+\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in cash_entries:
        shares, price, change, day_percent, day_dollar, value = entry
        if "CASH" not in processed_tickers:
            entries.append(("CASH", "Cash", shares, price, change, day_percent, day_dollar, value))
            processed_tickers.add("CASH")

    # Generic cryptocurrency pattern - more flexible to catch various crypto formats
    crypto_entries = re.findall(r'([A-Z0-9]+\.COIN|[A-Z]{3,5})[^\n]*?\s+([A-Z0-9]+|[^\n]+?)\s+(\d+\.\d+)\s+\$([0-9,.]+)\s+([-+]?\$?[0-9,.]+)\s+([-+][0-9.]+%)\s+([-+]\$[0-9,.]+)\s+\$([0-9,.]+)', holdings_section)

    for entry in crypto_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            # Clean up the change value to remove any extra $ if present
            change = entry[4].replace('$', '')
            entries.append((ticker, entry[1], entry[2], entry[3].replace(',', ''), change, entry[5], entry[6], entry[7]))
            processed_tickers.add(ticker)
            logger.info(f"Added crypto entry: {ticker}")

    # Add a catch-all pattern for any remaining entries with standard format
    catchall_entries = re.findall(r'([A-Z0-9\.\-]+)[^\n]*?\n([^\n]+?)\n(\d+(?:\.\d+)?)\n\$(\d+(?:\.\d+)?)\n\$?([-+]?\d+(?:\.\d+)?)\n([-+]?\d+(?:\.\d+)?%)\n([-+]?\$\d+(?:,\d+)*(?:\.\d+)?)\n\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in catchall_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            logger.info(f"Added catchall entry: {ticker}")

    # MHTML Specific Pattern: Try to find entries that might have different formatting in MHTML files
    mhtml_entries = re.findall(r'([A-Z0-9\.\-]+)\s+([^\n]+?)\s+(\d+(?:\.\d+)?)\s+\$([\d,.]+)\s+([-+]?\$?[\d,.]+)\s+([-+][\d,.]+%)\s+([-+]\$[\d,.]+)\s+\$([\d,.]+)', holdings_section)

    for entry in mhtml_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            logger.info(f"Added MHTML-specific entry: {ticker}")

    # Debug info with more details
    logger.info(f"Total entries found: {len(entries)}")
    logger.info(f"Unique tickers: {len(processed_tickers)}")
    logger.info(f"Tickers found: {', '.join(sorted(processed_tickers))}")

    # Process all found entries
    for entry in entries:
        ticker, name, shares, price, change, day_percent, day_dollar, value = entry

        # If name is empty or None (which can happen for crypto), use ticker as name
        if not name or name.strip() == "":
            name = ticker

        # Check for potential false positives where part of the name was captured as a ticker
        # Common patterns: "ETF Shares" being split into "ETF" as ticker and "Shares" as name
        if ticker == "ETF" and "Shares" in name:
            # Skip this entry as it's likely part of another entry
            continue

        # Detect duplicate entries by comparing values
        # If we already have an entry with same share count and value, skip this one
        duplicate = False
        for existing_holding in holdings_data:
            if (existing_holding["Shares"] == shares and
                existing_holding["Value"] == value.replace('$', '').replace(',', '') and
                ticker != existing_holding["Ticker"]):
                logger.info(f"Skipping duplicate entry for {ticker} (likely part of {existing_holding['Ticker']})")
                duplicate = True
                break

        if duplicate:
            continue

        # Strip currency symbol from day_dollar but keep track of negative/positive
        day_dollar_clean = day_dollar.replace('$', '').replace(',', '')
        is_negative = '-' in day_dollar_clean
        day_dollar_clean = day_dollar_clean.replace('-', '')
        if is_negative and not day_dollar_clean.startswith('-'):
            day_dollar_clean = '-' + day_dollar_clean

        # Clean the value field by removing $ and commas
        value_clean = value.replace('$', '').replace(',', '')
        # Clean price field by removing commas
        price_clean = price.replace(',', '')

        holdings_data.append({
            "Ticker": ticker,
            "Name": name.strip(),
            "Shares": shares,
            "Price": price_clean,  # Use cleaned price value
            "Change": change,
            "Day_Percent": day_percent,
            "Day_Dollar": day_dollar_clean,  # Cleaned for CSV
            "Day_Dollar_Original": day_dollar,  # Keep original for text formatting
            "Value": value_clean,  # Cleaned for CSV
            "Value_Original": value  # Keep original for text formatting
        })

    # Sort holdings by value in descending order
    holdings_data = sorted(holdings_data, key=lambda x: float(x['Value']), reverse=True)

    # Perform integrity check if grand totals were found
    if grand_totals:
        # Calculate totals from processed data
        calculated_day_dollar = sum(float(holding['Day_Dollar']) for holding in holdings_data)
        calculated_value = sum(float(holding['Value']) for holding in holdings_data)

        # Format calculated values for display
        formatted_day_dollar = "${:,.2f}".format(calculated_day_dollar)
        formatted_value = "${:,.2f}".format(calculated_value)

        # Set tolerance for floating point comparison (0.5%)
        day_dollar_tolerance = abs(grand_totals['day_dollar_numeric'] * 0.005)
        value_tolerance = abs(grand_totals['value_numeric'] * 0.005)

        # Check if the values match within tolerance
        day_dollar_match = abs(calculated_day_dollar - grand_totals['day_dollar_numeric']) <= day_dollar_tolerance
        value_match = abs(calculated_value - grand_totals['value_numeric']) <= value_tolerance

        # Display integrity check results
        logger.info("\nIntegrity Check:")
        logger.info(f"Raw Grand Total (Day $): {grand_totals['day_dollar_total']} | Calculated: {formatted_day_dollar} | {'✓ Match' if day_dollar_match else '✗ Mismatch'}")
        logger.info(f"Raw Grand Total (Value): {grand_totals['value_total']} | Calculated: {formatted_value} | {'✓ Match' if value_match else '✗ Mismatch'}")

        # Store grand totals in the return data for use in reporting
        return {
            'holdings': holdings_data,
            'grand_totals': {
                'raw_day_dollar': grand_totals['day_dollar_total'],
                'raw_value': grand_totals['value_total'],
                'calculated_day_dollar': formatted_day_dollar,
                'calculated_value': formatted_value,
                'day_dollar_match': day_dollar_match,
                'value_match': value_match
            }
        }

    # If no grand totals found, just return the holdings data
    return holdings_data

def save_holdings_to_csv(holdings_data, output_file):
    """Save the holdings data to a CSV file"""
    # Check if we have the new format with grand_totals
    if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
        actual_holdings = holdings_data['holdings']
    else:
        actual_holdings = holdings_data

    # Define CSV headers with Name before Ticker
    fieldnames = ["Name", "Ticker", "Shares", "Price", "Change", "Day_Percent", "Day_Dollar", "Value"]

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            # Write rows but exclude the _Original fields not meant for CSV
            for row in actual_holdings:
                csv_row = {k: v for k, v in row.items() if not k.endswith('_Original')}
                writer.writerow(csv_row)
        return True
    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        return False

def format_holdings_as_text(holdings_data):
    """Format holdings data as formatted text"""
    # Check if we have the new format with grand_totals
    if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
        actual_holdings = holdings_data['holdings']
        grand_totals = holdings_data.get('grand_totals')
    else:
        actual_holdings = holdings_data
        grand_totals = None

    formatted_text = []
    for holding in actual_holdings:
        formatted_text.append(f"{holding['Ticker']}\n"
                             f"{holding['Name']}\n"
                             f"{holding['Shares']}\n"
                             f"${holding['Price']}\n"
                             f"${holding['Change']}\n"
                             f"{holding['Day_Percent']}\n"
                             f"{holding['Day_Dollar_Original']}\n"  # Use the original format with $ symbol
                             f"{holding['Value_Original']}")  # Use the original format with $ symbol

    # Add grand totals if available
    if grand_totals:
        formatted_text.append("\nGrand total\n"
                             f"{grand_totals['raw_day_dollar']}\n"
                             f"{grand_totals['raw_value']}")

    return "\n\n".join(formatted_text)

def list_mhtml_files():
    """Find and list all .mhtml and .mht files in the current directory"""
    mhtml_files = glob.glob("*.mhtml") + glob.glob("*.mht")
    if not mhtml_files:
        logger.error("No .mhtml or .mht files found in the current directory.")
        sys.exit(1)

    print("Available MHTML files:")
    for i, file in enumerate(mhtml_files, 1):
        print(f"{i}. {file}")

    # Let user choose a file
    while True:
        try:
            choice = input("\nEnter the number of the file to process (or 'q' to quit): ")
            if choice.lower() == 'q':
                sys.exit(0)

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(mhtml_files):
                return mhtml_files[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(mhtml_files)}")
        except ValueError:
            print("Please enter a valid number")

def display_csv_as_table(csv_file, holdings_data=None):
    """Read CSV file and display its contents as a formatted table"""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                print("No data found in CSV file.")
                return

            # Get headers from the first row
            headers = list(rows[0].keys())

            # Calculate column widths (minimum width is the header length)
            col_widths = {header: len(header) for header in headers}
            for row in rows:
                for header in headers:
                    col_widths[header] = max(col_widths[header], len(row[header]))

            # Set Name column width to 40 characters
            if "Name" in col_widths:
                col_widths["Name"] = 40

            # Print header row
            header_row = " | ".join(header.ljust(col_widths[header]) for header in headers)
            print(header_row)
            print("-" * len(header_row))

            # Print data rows
            for row in rows:
                data_row = " | ".join(row[header].ljust(col_widths[header]) for header in headers)
                print(data_row)

            # Calculate total portfolio value
            total_value = 0.0
            total_day_dollar = 0.0
            for row in rows:
                if "Value" in row and row["Value"]:
                    try:
                        total_value += float(row["Value"].replace(',', ''))
                    except ValueError:
                        # Skip non-numeric values
                        pass
                if "Day_Dollar" in row and row["Day_Dollar"]:
                    try:
                        total_day_dollar += float(row["Day_Dollar"].replace(',', ''))
                    except ValueError:
                        # Skip non-numeric values
                        pass

            # Format total values as currency with commas
            formatted_total_value = "${:,.2f}".format(total_value)
            formatted_total_day_dollar = "${:,.2f}".format(total_day_dollar)

            print(f"\nTotal: {len(rows)} holdings")
            print(f"Total Day $ Change: {formatted_total_day_dollar}")
            print(f"Total Portfolio Value: {formatted_total_value}")

            # Display integrity check results if available
            if holdings_data and isinstance(holdings_data, dict) and 'grand_totals' in holdings_data:
                gt = holdings_data['grand_totals']
                print("\nIntegrity Check:")
                print(f"Raw Grand Total (Day $): {gt['raw_day_dollar']} | Calculated: {gt['calculated_day_dollar']} | {'✓ Match' if gt['day_dollar_match'] else '✗ Mismatch'}")
                print(f"Raw Grand Total (Value): {gt['raw_value']} | Calculated: {gt['calculated_value']} | {'✓ Match' if gt['value_match'] else '✗ Mismatch'}")

    except Exception as e:
        print(f"Error displaying CSV data: {e}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Extract data from MHTML files")
    parser.add_argument("input_file", nargs='?', help="Path to the .mhtml/.mht file")
    parser.add_argument("-o", "--output", help="Output file base name (without extension)")
    parser.add_argument("--portfolio", action="store_true", help="Extract portfolio holdings information only")
    parser.add_argument("--csv", action="store_true", help="Save portfolio holdings as CSV file")
    parser.add_argument("--full-text", action="store_true", help="Extract full text content (default is portfolio+csv)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)

    # Set defaults if no specific options provided
    if not (args.portfolio or args.csv or args.full_text):
        # Default behavior: extract portfolio and save as CSV
        args.portfolio = True
        args.csv = True

    # If no input file provided, list available MHTML files
    if not args.input_file:
        args.input_file = list_mhtml_files()

    # Validate input file
    if not os.path.exists(args.input_file):
        logger.error(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)

    # Determine output filename
    if args.output:
        output_file_base = os.path.splitext(args.output)[0]
    else:
        output_file_base = os.path.splitext(args.input_file)[0]

    output_txt = f"{output_file_base}.txt"
    output_csv = f"{output_file_base}.csv"

    # Extract text content
    logger.info(f"Extracting text from '{args.input_file}'...")
    extracted_text = extract_mhtml_text(args.input_file)

    # Save raw text for debugging if debug mode enabled
    if args.debug:
        debug_txt = f"{output_file_base}_raw.txt"
        with open(debug_txt, "w", encoding="utf-8") as file:
            file.write(extracted_text)
        logger.debug(f"Raw extracted text saved to '{debug_txt}'")

    if extracted_text and not extracted_text.startswith("Error"):
        # Process for portfolio holdings if requested
        if args.portfolio or args.csv:
            holdings_data = extract_portfolio_holdings(extracted_text)
            if isinstance(holdings_data, str) and holdings_data.startswith("Could not"):
                logger.error(holdings_data)
                sys.exit(1)

            # Save as CSV if requested
            if args.csv:
                if save_holdings_to_csv(holdings_data, output_csv):
                    logger.info(f"Portfolio holdings saved as CSV to '{output_csv}'")
                    # Display the CSV contents as a table
                    print("\nPortfolio Holdings Table:")
                    display_csv_as_table(output_csv, holdings_data)

            # Format holdings as text for text output
            if args.portfolio:
                formatted_text = format_holdings_as_text(holdings_data)
                with open(output_txt, "w", encoding="utf-8") as file:
                    file.write(formatted_text)
                logger.info(f"Portfolio holdings text saved to '{output_txt}'")
                return

        # Save extracted text to file (unless we're only creating CSV)
        if args.full_text or args.portfolio:
            with open(output_txt, "w", encoding="utf-8") as file:
                file.write(extracted_text)
            logger.info(f"Extraction complete. Text saved to '{output_txt}'")
    else:
        logger.error(extracted_text or "Extraction failed: No content extracted")

if __name__ == "__main__":
    main()
