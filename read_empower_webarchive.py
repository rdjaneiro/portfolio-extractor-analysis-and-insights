"""
Empower Portfolio WebArchive Extractor
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
# Empower Portfolio WebArchive Extractor
# -----------------------------------------------------------------------------
#
# OVERVIEW:
# This script extracts portfolio holdings data from Empower webarchive files
# (.webarchive) and converts them to both human-readable text and CSV format.
# It can process the entire webarchive content or specifically extract just
# the portfolio holdings section with ticker symbols, share counts, prices, etc.
#
# INPUT:
# - .webarchive files (Safari's saved webpage format containing binary plist data)
# - The script looks for portfolio data in a specific format with sections showing:
#   Ticker, Name, Shares, Price, Change, Day percentage, Day dollar change, and Value
#
# OUTPUT:
# - CSV file with structured portfolio data (default)
# - Text file with extracted content (optional)
#
# USAGE:
# Basic usage (default: extract portfolio to CSV, interactive file selection):
#   python read_empower_webarchive.py
#
# Specify input file:
#   python read_empower_webarchive.py portfolio.webarchive
#
# Extract full text content:
#   python read_empower_webarchive.py portfolio.webarchive --full-text
#
# Custom output name:
#   python read_empower_webarchive.py portfolio.webarchive -o my_portfolio
#
# Extract portfolio as formatted text (no CSV):
#   python read_empower_webarchive.py portfolio.webarchive --portfolio --no-csv
#
# DEPENDENCIES:
# - plistlib: For parsing webarchive plist data
# - BeautifulSoup4 (bs4): For HTML parsing
# - argparse: For command-line argument handling
# -----------------------------------------------------------------------------

import plistlib
import bs4
import argparse
import os
import sys
import glob
import re
import csv

def extract_webarchive_text(file_path):
    try:
        # Load the binary plist (property list) file
        with open(file_path, "rb") as file:
            plist_data = plistlib.load(file)

        # Extract main web content
        if "WebMainResource" in plist_data:
            web_resource = plist_data["WebMainResource"]
            if "WebResourceData" in web_resource:
                html_content = web_resource["WebResourceData"].decode("utf-8", errors="ignore")

                # Parse HTML with BeautifulSoup
                soup = bs4.BeautifulSoup(html_content, "html.parser")

                # Extract visible text
                extracted_text = soup.get_text(separator="\n")

                return extracted_text
    except Exception as e:
        return f"Error reading webarchive: {e}"

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
            print(f"Added standard entry: {ticker}")

    # Alternative stock pattern for different spacing or formatting
    alt_stock_entries = re.findall(r'([A-Z0-9\.\-]+)\s+([^\n]+?)\s+(\d+(?:\.\d+)?)\s+\$(\d+(?:\.\d+)?(?:,\d+)*)\s+([-+]?[^\s]+)\s+([-+]\d+(?:\.\d+)?%)\s+([-+]\$\d+(?:,\d+)*(?:\.\d+)?)\s+\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in alt_stock_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            print(f"Added alternative stock entry: {ticker}")

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
            print(f"Added crypto entry: {ticker}")

    # Add a catch-all pattern for any remaining entries with standard format
    catchall_entries = re.findall(r'([A-Z0-9\.\-]+)[^\n]*?\n([^\n]+?)\n(\d+(?:\.\d+)?)\n\$(\d+(?:\.\d+)?)\n\$?([-+]?\d+(?:\.\d+)?)\n([-+]?\d+(?:\.\d+)?%)\n([-+]?\$\d+(?:,\d+)*(?:\.\d+)?)\n\$(\d+(?:,\d+)*(?:\.\d+)?)', holdings_section)

    for entry in catchall_entries:
        ticker = entry[0]
        if ticker not in processed_tickers:
            entries.append(entry)
            processed_tickers.add(ticker)
            print(f"Added catchall entry: {ticker}")

    # Debug info with more details
    print(f"Total entries found: {len(entries)}")
    print(f"Unique tickers: {len(processed_tickers)}")
    print(f"Tickers found: {', '.join(sorted(processed_tickers))}")

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
                print(f"Skipping duplicate entry for {ticker} (likely part of {existing_holding['Ticker']})")
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
        print("\nIntegrity Check:")
        print(f"Raw Grand Total (Day $): {grand_totals['day_dollar_total']} | Calculated: {formatted_day_dollar} | {'✓ Match' if day_dollar_match else '✗ Mismatch'}")
        print(f"Raw Grand Total (Value): {grand_totals['value_total']} | Calculated: {formatted_value} | {'✓ Match' if value_match else '✗ Mismatch'}")

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
        print(f"Error saving CSV file: {e}")
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

def list_webarchive_files():
    """Find and list all .webarchive files in the current directory"""
    webarchive_files = glob.glob("*.webarchive")
    if not webarchive_files:
        print("No .webarchive files found in the current directory.")
        sys.exit(1)

    print("Available .webarchive files:")
    for i, file in enumerate(webarchive_files, 1):
        print(f"{i}. {file}")

    # Let user choose a file
    while True:
        try:
            choice = input("\nEnter the number of the file to process (or 'q' to quit): ")
            if choice.lower() == 'q':
                sys.exit(0)

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(webarchive_files):
                return webarchive_files[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(webarchive_files)}")
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

def extract_net_worth_data(text_content):
    """Extract net worth data from the text content using proper group structure"""
    if not text_content:
        return "Could not extract net worth data: No text content provided"

    # Look for patterns that indicate this is net worth data
    if "Net worth" not in text_content and "Net Worth" not in text_content and "ALL ACCOUNTS" not in text_content:
        return "Could not extract net worth data: No net worth indicators found"

    accounts = []
    lines = text_content.split('\n')

    # Define the group structure and their expected patterns
    groups = {
        'Cash': 'Cash',
        'Investment': 'Investment',
        'Credit': 'Credit',
        'Loan': 'Loan',
        'Mortgage': 'Mortgage',
        'Other Asset': 'Other Asset'
    }

    # Find the section that contains the structured account data (around line 8500+)
    # Look for the pattern: Account\nType\nBalance\nCash
    structured_section_start = -1
    for i, line in enumerate(lines):
        if (line.strip() == "Account" and
            i + 1 < len(lines) and lines[i + 1].strip() == "Type" and
            i + 2 < len(lines) and lines[i + 2].strip() == "Balance"):
            structured_section_start = i + 3
            break

    if structured_section_start == -1:
        return "Could not extract net worth data: Structured section not found"

    # Process the structured section
    current_group = None
    current_group_total = None
    i = structured_section_start

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this line is a group header with total
        if line in groups:
            current_group = line
            # Look for the group total on the next few lines
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                if next_line.startswith('$') or next_line.startswith('-$'):
                    current_group_total = next_line
                    break
                j += 1
            i = j + 1
            continue

        # Check if this is a provider name (looking for known providers)
        if any(provider in line for provider in [
            'Apple Federal Credit Union', 'Charles Schwab', 'Fidelity', 'Morgan Stanley', 'M1 Finance',
            'Manual Investment Holdings', 'Wells Fargo', 'Chase', 'American Express', 'Brex',
            'E*TRADE', 'T-RowePrice Manual Holdings', 'Bluevine', 'Webull', 'Coinbase', 'Truist',
            'MorganStanley', 'Manual', 'Cyber Connective Corporation'
        ]):
            provider = line

            # Look ahead for account details
            j = i + 1
            account_name = None
            account_type = None
            balance = None
            date = None

            # Parse the next several lines for account details
            while j < len(lines) and j < i + 15:
                next_line = lines[j].strip()

                if not next_line:
                    j += 1
                    continue

                # Check for account name pattern (contains "Ending in" or looks like account name)
                # Exclude lines that start with currency symbols to avoid capturing balances as account names
                if (not account_name and
                    ("Ending in" in next_line or "-" in next_line or
                    any(keyword in next_line.lower() for keyword in [
                        'checking', 'savings', 'brokerage', 'ira', '401', 'credit', 'card',
                        'investment', 'trust', 'loan', 'mortgage', 'line', 'cash', 'apple',
                        'advantage', 'afcu', 'cyber', 'schwab', 'rltq', 'sep', 'individual',
                        'lei', 'ai', 'growth', 'crypto', 'aaa', 'consulting', 'platinum',
                        'select', 'uma', 'hilton', 'marriott', 'bonvoy', 'business', 'preferred',
                        'blue', 'equity', 'ready', 'advtge'
                    ])) and not next_line.startswith('$') and not next_line.startswith('-$') and
                    next_line not in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                                    '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                                    'Line Of Credit', 'Cryptocurrency']):
                    account_name = next_line
                    j += 1
                    continue

                # Check for account type (common types) - only if we don't already have one
                if (not account_type and next_line in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                               '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                               'Line Of Credit', 'Cryptocurrency']):
                    account_type = next_line
                    j += 1
                    continue

                # Check for balance (multiple formats: $123.45, -$123.45, -123.45)
                if ((next_line.startswith('$') or next_line.startswith('-$') or next_line.startswith('-')) and
                    any(c.isdigit() for c in next_line) and
                    ('.' in next_line or next_line.replace('$', '').replace('-', '').replace(',', '').isdigit())):
                    balance = next_line
                    j += 1
                    continue

                # Check for date pattern (contains / and time info)
                if ('/' in next_line and ('AM' in next_line or 'PM' in next_line or 'ago' in next_line)):
                    date = next_line
                    break

                j += 1

            # If we found account details, add to accounts
            if account_name and balance:
                # Don't use account type as account name if we have a better name
                if account_name in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                                  '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                                  'Line Of Credit', 'Cryptocurrency']:
                    # This means we captured the type as the name, try to use provider info instead
                    account_name = f"{provider} {account_name}" if provider != account_name else account_name

                # Clean up balance for numeric conversion while preserving sign
                # Handle various negative formats: -$123.45, -123.45
                is_negative = balance.startswith('-$') or balance.startswith('-')
                balance_clean = balance.replace('$', '').replace(',', '')

                # Remove the negative sign for processing, we'll add it back if needed
                if is_negative:
                    balance_clean = balance_clean.lstrip('-')

                # Determine category based on account type and current group
                account_type_lower = (account_type or 'Unknown').lower()

                # First check if we're in a specific group context
                if current_group == 'Other Asset':
                    category = 'Other'
                elif account_type_lower in ['checking', 'savings']:
                    category = 'Cash'
                elif account_type_lower == 'investment':
                    category = 'Investment Brokerage'
                elif account_type_lower == 'cryptocurrency':
                    category = 'Investment Brokerage'  # Treat crypto as investment brokerage
                elif '401k' in account_type_lower or 'ira' in account_type_lower:
                    category = 'Investment Retirement'
                elif account_type_lower == 'personal':
                    category = 'Credit'
                elif account_type_lower == 'line of credit':
                    category = 'Loan'
                elif account_type_lower == 'mortgage':
                    category = 'Mortgage'
                elif account_type_lower in ['assets', 'property']:
                    category = 'Other'
                else:
                    # Check if account name suggests it's a property/real estate asset
                    account_name_lower = (account_name or '').lower()
                    if any(keyword in account_name_lower for keyword in ['home', 'house', 'property', 'real estate', 'land', 'zestimate']):
                        category = 'Other'
                    else:
                        category = 'Other'

                # Keep the full account name including "Ending in" details
                # Don't modify account names that contain full descriptive information

                # Fix account names that look like dates/times by using provider instead
                import re
                if (account_name and provider and
                    (re.match(r'^\d{1,2}/\d{1,2}/\d{4}', account_name) or  # Date pattern like 2/15/2022
                     re.match(r'^\d{1,2}:\d{2}[AP]M$', account_name))):    # Time pattern like 2:43PM
                    account_name = provider

                accounts.append({
                    'Account': account_name,
                    'Type': account_type or 'Unknown',
                    'Balance': f"-{balance_clean}" if is_negative else balance_clean,
                    'Category': category,
                    'Provider': provider,
                    'Date': date or 'Unknown'
                })

            i = j
        else:
            i += 1

    # Special handling for "Other Asset" section which has a different format
    # Look for the "Other Asset" header and parse the property details that follow
    other_asset_line = -1
    for i, line in enumerate(lines):
        if line.strip() == "Other Asset":
            other_asset_line = i
            break

    if other_asset_line != -1:
        # Parse the Other Asset section for property details
        # The format is: "Other Asset" -> total amount -> property details
        i = other_asset_line + 1
        section_end = min(len(lines), other_asset_line + 500)  # Search reasonable range

        current_property = {}
        looking_for_amount = False
        looking_for_address = False

        while i < section_end:
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Look for property type indicators
            if line.startswith('Home') or 'Zestimate' in line:
                if current_property:
                    # Save previous property if we have enough data
                    if 'amount' in current_property and 'name' in current_property:
                        accounts.append({
                            'Account': current_property['name'],
                            'Type': 'Property',
                            'Balance': current_property['amount'],
                            'Category': 'Other',
                            'Provider': 'Empower Manual',
                            'Date': current_property.get('date', 'Unknown')
                        })

                # Start new property
                current_property = {'name': line, 'type': 'Property'}
                looking_for_amount = True
                looking_for_address = False

            # Look for dollar amounts (property values)
            elif looking_for_amount and line.startswith('$') and ',' in line and '.' in line:
                current_property['amount'] = line.replace('$', '').replace(',', '')
                looking_for_amount = False
                looking_for_address = True

            # Look for property address (specific street address pattern)
            elif looking_for_address and any(word in line for word in ['Ct', 'St', 'Ave', 'Dr', 'Ln', 'Rd', 'Way']) and any(c.isdigit() for c in line):
                current_property['name'] = f"{current_property.get('name', '')} - {line}".strip(' -')
                looking_for_address = False

            # Look for dates
            elif '/' in line and ('2024' in line or '2025' in line):
                current_property['date'] = line

            # Stop if we hit the structured section or another major section
            elif line in ['Account', 'Type', 'Balance'] or (line in ['Cash', 'Investment', 'Credit', 'Loan', 'Mortgage']):
                break

            i += 1

        # Save the last property if we have data
        if current_property and 'amount' in current_property and 'name' in current_property:
            accounts.append({
                'Account': current_property['name'],
                'Type': 'Property',
                'Balance': current_property['amount'],
                'Category': 'Other',
                'Provider': 'Empower Manual',
                'Date': current_property.get('date', 'Unknown')
            })

    # Find the actual total net worth from the text (more accurate than summing individual accounts)
    actual_total = None
    total_pattern = r'\$([0-9,]+\.?\d*)'

    # Look for the net worth total in the text - it appears near "ALL ACCOUNTS" section
    lines_text = '\n'.join(lines)

    # Search for patterns like "$10,359,346.21" that appear as the main total
    import re
    matches = re.findall(r'\$([0-9,]+\.[0-9]{2})', lines_text)

    # Find the largest amount which is likely the total net worth
    largest_amount = 0
    for match in matches:
        try:
            amount = float(match.replace(',', ''))
            if amount > largest_amount and amount > 1000000:  # Must be > 1M to be total net worth
                largest_amount = amount
                actual_total = amount
        except:
            continue

    # Use actual total if found, otherwise calculate from accounts
    if actual_total:
        total_net_worth = actual_total
    else:
        total_net_worth = 0
        for account in accounts:
            try:
                balance_val = float(account['Balance'].replace(',', ''))
                total_net_worth += balance_val
            except:
                pass

    # Add the total as a summary row
    if total_net_worth != 0:
        accounts.append({
            'Account': 'TOTAL NET WORTH',
            'Type': 'Total',
            'Balance': f"{total_net_worth:.2f}",
            'Category': 'Total',
            'Provider': 'Summary',
            'Date': 'Calculated'
        })

    # Second pass: Look for accounts in alternative format (provider on separate line)
    # This catches accounts like Brex Card Account that appear later in the file
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for standalone provider names (exact match, case-sensitive)
        if line in ['Brex', 'Chase', 'American Express', 'Wells Fargo', 'Fidelity', 'Morgan Stanley', 'Bluevine', 'Webull', 'Coinbase', 'Apple Federal Credit Union']:
            provider = line

            # Look ahead for account details in the next few lines
            j = i + 1
            account_name = None
            account_type = None
            balance = None
            date = None

            while j < len(lines) and j < i + 15:  # Increased range to 15 lines
                current_line = lines[j]
                next_line = current_line.strip()

                if not next_line:
                    j += 1
                    continue

                # Look for indented account name (has significant leading spaces)
                if (len(current_line) > len(next_line) and len(current_line) >= 14 and
                    current_line.startswith('              ') and next_line and
                    not next_line.startswith('$') and not next_line.startswith('-$') and
                    next_line not in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                                    '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                                    'Cryptocurrency']):
                    account_name = next_line
                    j += 1
                    continue

                # Look for account type
                if (not account_type and next_line in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                               '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                               'Cryptocurrency']):
                    account_type = next_line
                    j += 1
                    continue

                # Look for balance (including negative balances)
                if ((next_line.startswith('$') or next_line.startswith('-$') or next_line.startswith('-')) and
                    any(c.isdigit() for c in next_line) and
                    ('.' in next_line or next_line.replace('$', '').replace('-', '').replace(',', '').isdigit())):
                    balance = next_line
                    j += 1
                    continue

                # Look for date/time
                if ('/' in next_line and ('AM' in next_line or 'PM' in next_line)):
                    date = next_line
                    break

                j += 1

            # If we found an account, add it
            if account_name and balance:
                # Clean up balance for numeric conversion while preserving sign
                is_negative = balance.startswith('-$') or balance.startswith('-')
                balance_clean = balance.replace('$', '').replace(',', '')

                if is_negative:
                    balance_clean = balance_clean.lstrip('-')

                # Determine category based on account type
                account_type_lower = (account_type or 'Unknown').lower()
                if account_type_lower in ['checking', 'savings']:
                    category = 'Cash'
                elif account_type_lower == 'investment':
                    category = 'Investment Brokerage'
                elif account_type_lower == 'cryptocurrency':
                    category = 'Investment Brokerage'  # Treat crypto as investment brokerage
                elif '401k' in account_type_lower or 'ira' in account_type_lower:
                    category = 'Investment Retirement'
                elif account_type_lower == 'personal':
                    category = 'Credit'
                elif account_type_lower == 'line of credit':
                    category = 'Loan'
                elif account_type_lower == 'mortgage':
                    category = 'Mortgage'
                elif account_type_lower in ['assets', 'property']:
                    category = 'Other'
                else:
                    category = 'Other'

                accounts.append({
                    'Account': account_name,
                    'Type': account_type or 'Unknown',
                    'Balance': f"-{balance_clean}" if is_negative else balance_clean,
                    'Category': category,
                    'Provider': provider,
                    'Date': date or 'Unknown'
                })

            i = j
        else:
            i += 1

    # Third pass: Look for accounts where account name comes first, then indented provider
    # This catches accounts like "Manual Loan" followed by indented "MorganStanley-LAL"
    # and "Webull Investment Holdings" followed by indented "Webull"
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for potential account names that might be followed by indented provider
        # Be more specific to avoid section headers like "Loan", "Mortgage", etc.
        # Also exclude date/time patterns
        import re
        is_date_time = (re.match(r'^\d{1,2}/\d{1,2}/\d{4}', line) or  # Date pattern like 2/15/2022
                       re.match(r'^\d{1,2}:\d{2}[AP]M$', line))      # Time pattern like 2:43PM

        if (line and not line.startswith('$') and not line.startswith('-$') and
            line not in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                        '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                        'Loan', 'Credit', 'Cryptocurrency'] and  # Exclude section headers
            len(line) > 4 and  # Must be longer than simple section headers
            not is_date_time and  # Exclude date/time patterns
            (any(keyword in line.lower() for keyword in ['manual loan', 'mortgage loan', 'credit card', 'line of credit']) or
             any(pattern in line for pattern in ['Investment Holdings', 'Crypto', 'Manual']) or  # Investment-related patterns
             (len(line) > 8 and any(char.isupper() for char in line) and ' ' in line))):  # Generic account name pattern

            potential_account_name = line

            # Look ahead for indented provider and account details
            j = i + 1
            provider = None
            account_type = None
            balance = None
            date = None

            while j < len(lines) and j < i + 20:
                current_line = lines[j]
                next_line = current_line.strip()

                if not next_line:
                    j += 1
                    continue

                # Look for indented provider (starts with significant spaces and contains known provider patterns)
                if (len(current_line) > len(next_line) and len(current_line) >= 14 and
                    current_line.startswith('              ') and next_line and
                    (any(prov in next_line for prov in ['MorganStanley', 'Apple Federal', 'Wells Fargo', 'Chase', 'Fidelity']) or
                     len(next_line) > 3 and next_line.replace(' ', '').isalpha())):  # Any alphabetic provider name
                    provider = next_line
                    j += 1
                    continue

                # Look for account type
                if (not account_type and next_line in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                               '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                               'Cryptocurrency']):
                    account_type = next_line
                    j += 1
                    continue

                # Look for balance
                if ((next_line.startswith('$') or next_line.startswith('-$') or next_line.startswith('-')) and
                    any(c.isdigit() for c in next_line) and
                    ('.' in next_line or next_line.replace('$', '').replace('-', '').replace(',', '').isdigit())):
                    balance = next_line
                    j += 1
                    continue

                # Look for date/time
                if ('/' in next_line or ('AM' in next_line or 'PM' in next_line)):
                    date = next_line
                    break

                j += 1

            # If we found provider and balance, add the account
            if provider and balance:
                # Clean up balance for numeric conversion while preserving sign
                is_negative = balance.startswith('-$') or balance.startswith('-')
                balance_clean = balance.replace('$', '').replace(',', '')

                if is_negative:
                    balance_clean = balance_clean.lstrip('-')

                # Determine category based on account type
                account_type_lower = (account_type or 'Unknown').lower()
                if account_type_lower in ['checking', 'savings']:
                    category = 'Cash'
                elif account_type_lower == 'investment':
                    category = 'Investment Brokerage'
                elif account_type_lower == 'cryptocurrency':
                    category = 'Investment Brokerage'  # Treat crypto as investment brokerage
                elif '401k' in account_type_lower or 'ira' in account_type_lower:
                    category = 'Investment Retirement'
                elif account_type_lower == 'personal':
                    category = 'Credit'
                elif account_type_lower == 'line of credit':
                    category = 'Loan'
                elif account_type_lower == 'mortgage':
                    category = 'Mortgage'
                elif account_type_lower == 'assets':
                    category = 'Assets'
                else:
                    # For unknown types, check account name for clues
                    account_name_lower = (potential_account_name or '').lower()
                    if 'crypto' in account_name_lower or 'coinbase' in account_name_lower or 'webull' in account_name_lower:
                        category = 'Investment'
                    else:
                        category = 'Other'

                # Fix account names that look like dates/times by using provider instead
                if (potential_account_name and provider and
                    (re.match(r'^\d{1,2}/\d{1,2}/\d{4}', potential_account_name) or  # Date pattern like 2/15/2022
                     re.match(r'^\d{1,2}:\d{2}[AP]M$', potential_account_name))):    # Time pattern like 2:43PM
                    potential_account_name = provider

                accounts.append({
                    'Account': potential_account_name,
                    'Type': account_type or 'Unknown',
                    'Balance': f"-{balance_clean}" if is_negative else balance_clean,
                    'Category': category,
                    'Provider': provider,
                    'Date': date or 'Unknown'
                })

            i = j
        else:
            i += 1

    # Find the actual total net worth from the text (more accurate than summing individual accounts)
    actual_total = None
    total_pattern = r'\$([0-9,]+\.?\d*)'

    # Look for the net worth total in the text - it appears near "ALL ACCOUNTS" section
    lines_text = '\n'.join(lines)

    # Search for patterns like "$10,359,346.21" that appear as the main total
    import re
    matches = re.findall(r'\$([0-9,]+\.[0-9]{2})', lines_text)

    # Find the largest amount which is likely the total net worth
    largest_amount = 0
    for match in matches:
        try:
            amount = float(match.replace(',', ''))
            if amount > largest_amount and amount > 1000000:  # Must be > 1M to be total net worth
                largest_amount = amount
                actual_total = amount
        except:
            continue

    # Use actual total if found, otherwise calculate from accounts
    if actual_total:
        total_net_worth = actual_total
    else:
        total_net_worth = 0
        for account in accounts:
            try:
                balance_val = float(account['Balance'].replace(',', ''))
                total_net_worth += balance_val
            except:
                pass

    # Add the total as a summary row
    if total_net_worth != 0:
        accounts.append({
            'Account': 'TOTAL NET WORTH',
            'Type': 'Total',
            'Balance': f"{total_net_worth:.2f}",
            'Category': 'Total',
            'Provider': 'Summary',
            'Date': 'Calculated'
        })

    # Remove duplicates while preserving order
    # First pass: exact duplicates (same account, balance, provider)
    seen = set()
    filtered_accounts = []
    for account in accounts:
        key = (account['Account'], account['Balance'], account['Provider'])
        if key not in seen:
            seen.add(key)
            filtered_accounts.append(account)

    # Second pass: remove duplicates based on same balance and similar account names
    unique_accounts = []
    balance_groups = {}

    # Group accounts by balance
    for account in filtered_accounts:
        balance = account['Balance']
        if balance not in balance_groups:
            balance_groups[balance] = []
        balance_groups[balance].append(account)

    # For each balance group, keep only unique accounts
    for balance, account_list in balance_groups.items():
        if len(account_list) == 1:
            # Only one account with this balance, keep it
            unique_accounts.extend(account_list)
        else:
            # Multiple accounts with same balance, need to deduplicate
            # Look for patterns that indicate same account with different names
            accounts_to_keep = []
            skip_indices = set()

            for i, account in enumerate(account_list):
                if i in skip_indices:
                    continue

                account_name = account['Account'].lower()
                is_duplicate = False

                # Check against other accounts in this balance group
                for j, other_account in enumerate(account_list):
                    if i != j and j not in skip_indices:
                        other_name = other_account['Account'].lower()

                        # Check if accounts are likely the same based on similar names or providers
                        if (
                            # Same provider and similar account types (crypto accounts)
                            ('coinbase' in account['Provider'].lower() and 'coinbase' in other_account['Provider'].lower() and
                             ('crypto' in account_name or 'crypto' in other_name)) or
                            # One account name is contained in the other
                            (account_name in other_name or other_name in account_name) or
                            # Both contain the same provider name in account name
                            (account['Provider'].lower() in account_name and
                             account['Provider'].lower() in other_name) or
                            # Special case: "Cryptocurrency" + "Coinbase" provider vs "Coinbase Crypto" + "Coinbase" provider
                            ((account_name == 'cryptocurrency' and 'coinbase' in account['Provider'].lower()) and
                             ('coinbase' in other_name and 'coinbase' in other_account['Provider'].lower()))
                        ):
                            # Keep the more descriptive account name (longer usually better)
                            if len(account['Account']) >= len(other_account['Account']):
                                skip_indices.add(j)
                            else:
                                is_duplicate = True
                                break

                if not is_duplicate:
                    accounts_to_keep.append(account)

            unique_accounts.extend(accounts_to_keep)

    if not unique_accounts:
        return "Could not extract net worth data: No account information found in the expected format"

    return unique_accounts

def save_networth_to_csv(networth_data, output_file):
    """Save net worth data to CSV file"""
    if not networth_data or isinstance(networth_data, str):
        return False

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if networth_data:
                fieldnames = ['Account', 'Type', 'Balance', 'Category', 'Provider', 'Date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for account in networth_data:
                    writer.writerow(account)

                return True
    except Exception as e:
        print(f"Error saving net worth to CSV: {e}")
        return False

def format_networth_as_text(networth_data):
    """Format net worth data as human-readable text"""
    if not networth_data or isinstance(networth_data, str):
        return "No net worth data available."

    # Build formatted text
    lines = []
    lines.append("NET WORTH SUMMARY")
    lines.append("=" * 50)
    lines.append("")

    # Group by category
    categories = {}
    total_found = False

    for account in networth_data:
        category = account.get('Category', 'Unknown')
        if category == 'Total':
            total_found = True
            continue
        if category not in categories:
            categories[category] = []
        categories[category].append(account)

    # Display by category
    for category, accounts in categories.items():
        lines.append(f"{category.upper()}:")
        lines.append("-" * (len(category) + 1))

        for account in accounts:
            lines.append(f"  Account:      {account.get('Account', 'N/A')}")
            lines.append(f"  Type:         {account.get('Type', 'N/A')}")
            lines.append(f"  Balance:      ${account.get('Balance', 'N/A')}")
            lines.append("")
        lines.append("")

    # Add total if found
    for account in networth_data:
        if account.get('Category') == 'Total':
            lines.append("TOTAL NET WORTH:")
            lines.append("=" * 16)
            lines.append(f"${account.get('Balance', 'N/A')}")
            break

    if not total_found:
        lines.append(f"Total Accounts: {len(networth_data)}")

    return "\n".join(lines)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Extract text from WebArchive files")
    parser.add_argument("input_file", nargs='?', help="Path to the .webarchive file")
    parser.add_argument("-o", "--output", help="Output file base name (without extension)")
    parser.add_argument("--portfolio", action="store_true", help="Extract portfolio holdings information only")
    parser.add_argument("--net-worth", action="store_true", help="Extract net worth information only")
    parser.add_argument("--csv", action="store_true", help="Save portfolio holdings as CSV file")
    parser.add_argument("--full-text", action="store_true", help="Extract full text content (default is portfolio+csv)")
    args = parser.parse_args()

    # Set defaults if no specific options provided
    if not (args.portfolio or args.net_worth or args.csv or args.full_text):
        # Default behavior: extract portfolio and save as CSV
        args.portfolio = True
        args.csv = True

    # If no input file provided, list available .webarchive files
    if not args.input_file:
        args.input_file = list_webarchive_files()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' not found.")
        sys.exit(1)

    # Determine output filename
    if args.output:
        output_file_base = os.path.splitext(args.output)[0]
    else:
        output_file_base = os.path.splitext(args.input_file)[0]

    output_txt = f"{output_file_base}.txt"
    output_csv = f"{output_file_base}.csv"

    # Extract text content
    print(f"Extracting text from '{args.input_file}'...")
    extracted_text = extract_webarchive_text(args.input_file)

    if extracted_text and not extracted_text.startswith("Error"):
        # Process for net worth if requested
        if args.net_worth:
            networth_data = extract_net_worth_data(extracted_text)
            if isinstance(networth_data, str) and networth_data.startswith("Could not"):
                print(networth_data)
                sys.exit(1)

            # Save as CSV if requested
            if args.csv:
                if save_networth_to_csv(networth_data, output_csv):
                    print(f"Net worth data saved as CSV to '{output_csv}'")
                    # Display the CSV contents as a table
                    print("\nNet Worth Table:")
                    display_csv_as_table(output_csv, networth_data)

            # Format net worth as text for text output
            formatted_text = format_networth_as_text(networth_data)
            with open(output_txt, "w", encoding="utf-8") as file:
                file.write(formatted_text)
            print(f"Net worth text saved to '{output_txt}'")
            return

        # Process for portfolio holdings if requested
        if args.portfolio or args.csv:
            holdings_data = extract_portfolio_holdings(extracted_text)
            if isinstance(holdings_data, str) and holdings_data.startswith("Could not"):
                print(holdings_data)
                sys.exit(1)

            # Save as CSV if requested
            if args.csv:
                if save_holdings_to_csv(holdings_data, output_csv):
                    print(f"Portfolio holdings saved as CSV to '{output_csv}'")
                    # Display the CSV contents as a table
                    print("\nPortfolio Holdings Table:")
                    display_csv_as_table(output_csv, holdings_data)

            # Format holdings as text for text output
            if args.portfolio:
                formatted_text = format_holdings_as_text(holdings_data)
                with open(output_txt, "w", encoding="utf-8") as file:
                    file.write(formatted_text)
                print(f"Portfolio holdings text saved to '{output_txt}'")
                return

        # Save extracted text to file (unless we're only creating CSV)
        if args.full_text or args.portfolio:
            with open(output_txt, "w", encoding="utf-8") as file:
                file.write(extracted_text)
            print(f"Extraction complete. Text saved to '{output_txt}'")
    else:
        print(extracted_text or "Extraction failed: No content extracted")

if __name__ == "__main__":
    main()
