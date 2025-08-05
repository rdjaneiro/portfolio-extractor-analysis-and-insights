#!/usr/bin/env python3
"""
Empower Portfolio Extractor
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

# Empower Portfolio Extractor
=======================================

## Overview
This Streamlit app extracts portfolio holdings data from Empower retirement account
files (.webarchive or .mhtml/.mht format) and converts them to both human-readable text
and CSV format for further analysis.

## Inputs
- .webarchive or .mhtml/.mht files containing Empower retirement account portfolio information
- Files can be either uploaded by the user or selected from available files in the current directory

## Outputs
- Structured portfolio holdings data displayed as a table
- CSV file containing portfolio holdings information
- Raw extracted text (optional)

## Usage Instructions
1. Launch the app by running `streamlit run finTools_app.py`
2. Upload your .webarchive or .mhtml file
3. Click Process and view the results
4. Download your processed data in various formats

## Dependencies
- streamlit: Web interface
- pandas: Data manipulation
- read_empower_webarchive: Custom module for webarchive processing
- read_empower_mhtml: Custom module for mhtml processing

"""

# First, import streamlit
import streamlit as st

# Set page config must be the first Streamlit command
st.set_page_config(page_title="Empower Portfolio & Net Worth Extractor", layout="wide")

# Now import all other modules
import os
import glob
import pandas as pd
import sys
from io import StringIO
import tempfile
import uuid
import time
import datetime
import traceback

# Add this import at the top of the file with the other imports
import plotly.express as px

# Add these imports at the top of the file with other imports
import plotly.graph_objects as go
import numpy as np

# Import functions from both the webarchive and mhtml modules
from read_empower_webarchive import (
    extract_webarchive_text as extract_webarchive_text_wa,
    extract_portfolio_holdings as extract_portfolio_holdings_wa,
    save_holdings_to_csv as save_holdings_to_csv_wa,
    format_holdings_as_text as format_holdings_as_text_wa,
    extract_net_worth_data as extract_net_worth_data_wa,
    save_networth_to_csv as save_networth_to_csv_wa,
    format_networth_as_text as format_networth_as_text_wa
)

from read_empower_mhtml_improved import (
    extract_mhtml_text as extract_mhtml_text_mht,
    extract_net_worth_data as extract_net_worth_data_mht
)
from read_empower_mhtml import (
    extract_portfolio_holdings as extract_portfolio_holdings_mht,
    save_holdings_to_csv as save_holdings_to_csv_mht,
    format_holdings_as_text as format_holdings_as_text_mht,
    save_networth_to_csv as save_networth_to_csv_mht,
    format_networth_as_text as format_networth_as_text_mht
)

from llm_helpers import send_query_to_llm

# Add JSON import for processing JSON files
import json
import re

def process_networth_json(file_path):
    """Process a JSON file containing net worth data and return structured data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # First try to parse as proper JSON
        try:
            data = json.loads(content)

            # Look for networthHistories in the parsed data
            if 'spData' in data and 'networthHistories' in data['spData']:
                networth_data = data['spData']['networthHistories']

                # Filter out zero networth entries and structure the data
                structured_data = []
                for entry in networth_data:
                    if 'date' in entry and 'networth' in entry and entry.get("networth", 0.0) != 0.0:
                        structured_data.append({
                            'Date': entry.get("date", ""),
                            'Account': 'Net Worth Timeline',
                            'Type': 'Net Worth',
                            'Balance': entry.get("networth", 0.0),
                            'Category': 'Net Worth',
                            'Total Assets': entry.get("totalAssets", 0.0),
                            'Total Liabilities': entry.get("totalLiabilities", 0.0),
                            'Total Cash': entry.get("totalCash", 0.0),
                            'Total Investment': entry.get("totalInvestment", 0.0),
                            'Total Empower': entry.get("totalEmpower", 0.0),
                            'Total Mortgage': entry.get("totalMortgage", 0.0),
                            'Total Loan': entry.get("totalLoan", 0.0),
                            'Total Credit': entry.get("totalCredit", 0.0),
                            'Total Other Assets': entry.get("totalOtherAssets", 0.0),
                            'Total Other Liabilities': entry.get("totalOtherLiabilities", 0.0),
                            'One Day Change': entry.get("oneDayNetworthChange", 0.0),
                            'One Day Change %': entry.get("oneDayNetworthPercentageChange", 0.0)
                        })

                return structured_data
            else:
                return "Could not find networthHistories in JSON structure"

        except json.JSONDecodeError:
            # Fallback to regex approach for malformed JSON
            if "networthHistories" in content:
                # Pattern to extract a complete entry with all fields
                entry_pattern = r'"date":"([^"]+)"[^}]*?"totalMortgage":([0-9.E]+)[^}]*?"totalOtherAssets":([0-9.E]+)[^}]*?"totalAssets":([0-9.E]+)[^}]*?"totalCredit":([0-9.E]+)[^}]*?"totalLoan":([0-9.E]+)[^}]*?"oneDayNetworthPercentageChange":([0-9.E\-]+)[^}]*?"totalLiabilities":([0-9.E]+)[^}]*?"totalOtherLiabilities":([0-9.E]+)[^}]*?"oneDayNetworthChange":([0-9.E\-]+)[^}]*?"totalEmpower":([0-9.E]+)[^}]*?"totalCash":([0-9.E]+)[^}]*?"networth":([0-9.E\-]+)[^}]*?"totalInvestment":([0-9.E]+)'
                matches = re.findall(entry_pattern, content)

                if matches:
                    structured_data = []
                    for match in matches:
                        date, totalMortgage, totalOtherAssets, totalAssets, totalCredit, totalLoan, oneDayNetworthPercentageChange, totalLiabilities, totalOtherLiabilities, oneDayNetworthChange, totalEmpower, totalCash, networth, totalInvestment = match
                        networth_val = float(networth)
                        if networth_val != 0.0:  # Skip zero values
                            structured_data.append({
                                'Date': date,
                                'Account': 'Net Worth Timeline',
                                'Type': 'Net Worth',
                                'Balance': networth_val,
                                'Category': 'Net Worth',
                                'Total Assets': float(totalAssets),
                                'Total Liabilities': float(totalLiabilities),
                                'Total Cash': float(totalCash),
                                'Total Investment': float(totalInvestment),
                                'Total Empower': float(totalEmpower),
                                'Total Mortgage': float(totalMortgage),
                                'Total Loan': float(totalLoan),
                                'Total Credit': float(totalCredit),
                                'Total Other Assets': float(totalOtherAssets),
                                'Total Other Liabilities': float(totalOtherLiabilities),
                                'One Day Change': float(oneDayNetworthChange),
                                'One Day Change %': float(oneDayNetworthPercentageChange)
                            })

                    return structured_data
                else:
                    return "Could not extract net worth data from JSON using regex"
            else:
                return "Could not find networthHistories section in JSON"

    except Exception as e:
        return f"Error processing JSON file: {str(e)}"

def save_networth_timeline_to_csv(networth_data, csv_path):
    """Save net worth timeline data to CSV file"""
    try:
        df = pd.DataFrame(networth_data)
        df.to_csv(csv_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving to CSV: {str(e)}")
        return False

def format_networth_timeline_as_text(networth_data):
    """Format net worth timeline data as human-readable text"""
    if isinstance(networth_data, str):
        return networth_data

    if not networth_data:
        return "No net worth data available"

    text = "NET WORTH TIMELINE\n"
    text += "==================\n\n"

    # Summary info
    text += f"Total entries: {len(networth_data)}\n"
    if networth_data:
        latest = networth_data[-1]  # Assuming data is chronological
        text += f"Latest date: {latest.get('Date', 'N/A')}\n"
        text += f"Latest net worth: ${latest.get('Balance', 0):,.2f}\n\n"

    text += "TIMELINE DATA:\n"
    text += "-" * 80 + "\n"
    text += f"{'Date':<12} {'Net Worth':<15} {'Assets':<15} {'Liabilities':<15} {'Change':<10}\n"
    text += "-" * 80 + "\n"

    for entry in networth_data[-20:]:  # Show last 20 entries
        date = entry.get('Date', 'N/A')[:10]  # Truncate date
        balance = entry.get('Balance', 0)
        assets = entry.get('Total Assets', 0)
        liabilities = entry.get('Total Liabilities', 0)
        change = entry.get('One Day Change', 0)

        text += f"{date:<12} ${balance:<14,.0f} ${assets:<14,.0f} ${liabilities:<14,.0f} ${change:<9,.0f}\n"

    return text

# Initialize session state variables
if 'processed_result' not in st.session_state:
    st.session_state.processed_result = None
if 'processed_file_path' not in st.session_state:
    st.session_state.processed_file_path = None

# Add user_id management - put this after imports but before other functions
def ensure_user_dirs():
    """Create the user_files directory and user-specific subdirectory"""
    # Create main user_files directory if it doesn't exist
    user_files_dir = os.path.join(os.getcwd(), "user_files")
    if not os.path.exists(user_files_dir):
        os.makedirs(user_files_dir)

    # Create/get user ID and ensure user-specific directory exists
    if 'user_id' not in st.session_state:
        # Generate a unique user ID using date format YYYYMMDD and 8-char uuid4
        today = datetime.datetime.now().strftime("%Y%m%d")
        st.session_state.user_id = f"{today}_{uuid.uuid4().hex[:8]}"

    # Create user-specific directory
    user_dir = os.path.join(user_files_dir, st.session_state.user_id)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    return user_dir

# Add this function after the ensure_user_dirs function
def cleanup_old_sessions():
    """Delete user session directories that are older than 24 hours"""
    user_files_dir = os.path.join(os.getcwd(), "user_files")

    # Skip if user_files directory doesn't exist
    if not os.path.exists(user_files_dir):
        return

    current_time = time.time()
    # 24 hours in seconds
    max_age = 24 * 60 * 60

    # Get list of all user directories
    user_dirs = [os.path.join(user_files_dir, d) for d in os.listdir(user_files_dir)
                if os.path.isdir(os.path.join(user_files_dir, d))]

    for user_dir in user_dirs:
        try:
            # Skip current user's directory
            if 'user_id' in st.session_state and user_dir.endswith(st.session_state.user_id):
                continue

            # Get directory creation/modification time
            dir_time = os.path.getmtime(user_dir)

            # If directory is older than max_age, delete it
            if current_time - dir_time > max_age:
                # Recursively delete the directory and all its contents
                for root, dirs, files in os.walk(user_dir, topdown=False):
                    for file in files:
                        os.remove(os.path.join(root, file))
                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))
                os.rmdir(user_dir)
        except Exception as e:
            # Log errors but continue processing other directories
            print(f"Error cleaning up directory {user_dir}: {str(e)}")

# Replace the original ensure_user_files_dir with the new function
def ensure_user_files_dir():
    """Get the user-specific directory path"""
    return ensure_user_dirs()

def get_available_files():
    """Find and list all .webarchive, .mhtml, and .mht files in the current directory and user's directory"""
    # Check both current directory and user-specific directory
    current_dir_webarchives = glob.glob("*.webarchive")
    current_dir_mhtml = glob.glob("*.mhtml") + glob.glob("*.mht")

    user_dir = ensure_user_files_dir()
    user_dir_webarchives = glob.glob(os.path.join(user_dir, "*.webarchive"))
    user_dir_mhtml = glob.glob(os.path.join(user_dir, "*.mhtml")) + glob.glob(os.path.join(user_dir, "*.mht"))

    # Return full paths for both sets of files
    return current_dir_webarchives + current_dir_mhtml + user_dir_webarchives + user_dir_mhtml

def save_raw_data_to_file(text, file_path_base):
    """Save raw extracted text to a file with _rawdata suffix"""
    user_dir = ensure_user_files_dir()
    base_name = os.path.basename(file_path_base)
    raw_data_path = os.path.join(user_dir, f"{base_name}_rawdata.txt")
    with open(raw_data_path, "w", encoding="utf-8") as f:
        f.write(text)
    return raw_data_path

def render_sidebar():
    """Render all sidebar elements and return user inputs"""
    with st.sidebar:
        st.markdown("""
            <style>
            /* Sidebar styling */
            [data-testid="stSidebar"][aria-expanded="true"] {
                min-width: 250px;
                max-width: 450px;
                background-color: lightblue;
            }
            </style>
        """, unsafe_allow_html=True)

        # Add Buy Me a Coffee button at the top of sidebar
        st.markdown("""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
                    Like what you see?
            <a href="https://www.buymeacoffee.com/PNhYc1Mjil" target="_blank">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
                     alt="Buy Me A Coffee"
                     style="height: 50px; width: auto;">
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.title("Empower Portfolio & Net Worth Extractor")

        st.markdown("""
        ### Instructions:
        1. Upload your .webarchive or .mhtml file
        2. Click Process and view the results
        """)

        # File upload section - now accepts .webarchive, .mhtml/.mht, and .json files
        st.header("Step 1: Upload File")

        file_path = None
        uploaded_file = st.file_uploader("Upload a file", type=["webarchive", "mhtml", "mht", "json"])
        if uploaded_file:
            # Save the uploaded file to user-specific directory
            user_dir = ensure_user_files_dir()
            temp_file_path = os.path.join(user_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            file_path = temp_file_path

        # Process button
        st.header("Step 2: Process")
        process_button = st.button("Process File")

    # Return all the user inputs from the sidebar
    # Always set extract_portfolio and save_csv to True
    return {
        "file_path": file_path,
        "file_selection_method": "Upload a file",  # Always upload now
        "extract_portfolio": True,  # Always extract portfolio
        "save_csv": True,           # Always save CSV
        "process_button": process_button
    }

def determine_file_type(file_path):
    """Determine if a file is webarchive, mhtml, or json based on extension"""
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    if extension == '.webarchive':
        return 'webarchive'
    elif extension in ['.mhtml', '.mht']:
        return 'mhtml'
    elif extension == '.json':
        return 'json'
    else:
        return None

def determine_content_type(file_path):
    """Determine if a file contains portfolio or net worth data based on filename"""
    filename = os.path.basename(file_path).lower()
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    # JSON files are typically net worth data
    if extension == '.json':
        return 'net_worth'
    elif 'net worth' in filename or 'net_worth' in filename:
        return 'net_worth'
    elif 'portfolio' in filename:
        return 'portfolio'
    else:
        # Default to portfolio for backward compatibility
        return 'portfolio'

def process_file(file_path, extract_portfolio=True, save_csv=True):
    """Process a file (webarchive, mhtml, or json) and return the extracted data"""
    # Determine file type and content type
    file_type = determine_file_type(file_path)
    content_type = determine_content_type(file_path)

    if not file_type:
        return {
            "success": False,
            "error": f"Unsupported file format. Please use .webarchive, .mhtml/.mht, or .json files.",
            "text": None,
            "holdings": None,
            "csv_path": None,
            "raw_data_path": None,
            "text_path": None,
            "content_type": content_type
        }

    # Extract text content based on file type
    extracted_text = None
    if file_type == 'webarchive':
        extracted_text = extract_webarchive_text_wa(file_path)
    elif file_type == 'mhtml':
        extracted_text = extract_mhtml_text_mht(file_path)
    elif file_type == 'json':
        # For JSON files, we'll process directly without text extraction
        extracted_text = "JSON file processed directly"

    if file_type != 'json' and (not extracted_text or extracted_text.startswith("Error")):
        return {
            "success": False,
            "error": extracted_text or "Extraction failed: No content extracted",
            "text": None,
            "holdings": None,
            "csv_path": None,
            "raw_data_path": None,
            "text_path": None,
            "file_type": file_type,
            "content_type": content_type
        }

    # Save raw data to file (skip for JSON files as they're already structured)
    output_file_base = os.path.splitext(os.path.basename(file_path))[0]
    raw_data_path = None
    if file_type != 'json':
        raw_data_path = save_raw_data_to_file(extracted_text, output_file_base)

    # Process based on content type
    holdings_data = None
    csv_path = None
    text_path = None
    morningstar_path = None
    report_path = None

    if content_type == 'net_worth':
        # Process net worth data
        if file_type == 'webarchive':
            holdings_data = extract_net_worth_data_wa(extracted_text)
        elif file_type == 'mhtml':
            holdings_data = extract_net_worth_data_mht(extracted_text)
        elif file_type == 'json':
            holdings_data = process_networth_json(file_path)

        if isinstance(holdings_data, str) and holdings_data.startswith("Could not"):
            return {
                "success": False,
                "error": holdings_data,
                "text": extracted_text,
                "holdings": None,
                "csv_path": None,
                "raw_data_path": raw_data_path,
                "text_path": None,
                "file_type": file_type,
                "content_type": content_type
            }

        # Save as CSV if requested
        if save_csv:
            user_dir = ensure_user_files_dir()
            csv_path = os.path.join(user_dir, f"{output_file_base}.csv")

            if file_type == 'webarchive':
                save_networth_to_csv_wa(holdings_data, csv_path)
            elif file_type == 'mhtml':
                save_networth_to_csv_mht(holdings_data, csv_path)
            elif file_type == 'json':
                save_networth_timeline_to_csv(holdings_data, csv_path)

        # Generate formatted text file
        user_dir = ensure_user_files_dir()
        text_path = os.path.join(user_dir, f"{output_file_base}.txt")

        if file_type == 'webarchive':
            formatted_text = format_networth_as_text_wa(holdings_data)
        elif file_type == 'mhtml':
            formatted_text = format_networth_as_text_mht(holdings_data)
        elif file_type == 'json':
            formatted_text = format_networth_timeline_as_text(holdings_data)

        with open(text_path, "w", encoding="utf-8") as file:
            file.write(formatted_text)

    else:  # portfolio
        # Process portfolio holdings
        if extract_portfolio:
            # Extract portfolio holdings based on file type
            if file_type == 'webarchive':
                holdings_data = extract_portfolio_holdings_wa(extracted_text)
            else:  # mhtml
                holdings_data = extract_portfolio_holdings_mht(extracted_text)

            if isinstance(holdings_data, str) and holdings_data.startswith("Could not"):
                return {
                    "success": False,
                    "error": holdings_data,
                    "text": extracted_text,
                    "holdings": None,
                    "csv_path": None,
                    "raw_data_path": raw_data_path,
                    "text_path": None,
                    "file_type": file_type,
                    "content_type": content_type
                }

            # Save as CSV if requested (both functions should work the same way)
            if save_csv:
                user_dir = ensure_user_files_dir()
                csv_path = os.path.join(user_dir, f"{output_file_base}.csv")

                if file_type == 'webarchive':
                    save_holdings_to_csv_wa(holdings_data, csv_path)
                else:  # mhtml
                    save_holdings_to_csv_mht(holdings_data, csv_path)

                # Create MorningStar CSV if possible (only for portfolio)
                df = pd.read_csv(csv_path)
                morningstar_path = create_morningstar_csv(df, output_file_base)

                # Calculate stats and create text report
                stats = calculate_portfolio_statistics(df)
                if 'error' not in stats:
                    report_path = create_text_report(stats, df, output_file_base)

            # Generate formatted text file
            user_dir = ensure_user_files_dir()
            text_path = os.path.join(user_dir, f"{output_file_base}.txt")

            if file_type == 'webarchive':
                formatted_text = format_holdings_as_text_wa(holdings_data)
            else:  # mhtml
                formatted_text = format_holdings_as_text_mht(holdings_data)

            with open(text_path, "w", encoding="utf-8") as file:
                file.write(formatted_text)

    return {
        "success": True,
        "error": None,
        "text": extracted_text,
        "holdings": holdings_data,
        "csv_path": csv_path,
        "raw_data_path": raw_data_path,
        "text_path": text_path,
        "morningstar_path": morningstar_path,
        "report_path": report_path,
        "file_type": file_type,
        "content_type": content_type
    }

def read_csv_to_dataframe(csv_path):
    """Read a CSV file and return a pandas DataFrame"""
    try:
        return pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"Error reading CSV file: {str(e)}")
        return None

def calculate_portfolio_statistics(df):
    """Calculate statistics for the portfolio"""
    stats = {}

    # Only calculate if we have the Value column
    if 'Value' in df.columns:
        try:
            # Handle value formatting (remove $ and commas if present)
            if df['Value'].dtype == 'object':
                df['Value_numeric'] = df['Value'].replace(r'[\$,]', '', regex=True).astype(float)
            else:
                df['Value_numeric'] = df['Value']

            # Calculate statistics
            stats['total_value'] = df['Value_numeric'].sum()
            stats['count'] = len(df)
            stats['avg_value'] = stats['total_value'] / stats['count'] if stats['count'] > 0 else 0
            stats['max_value'] = df['Value_numeric'].max()
            stats['min_value'] = df['Value_numeric'].min()

            # New statistics
            stats['median_value'] = df['Value_numeric'].median()
            stats['std_dev'] = df['Value_numeric'].std()
            stats['value_range'] = stats['max_value'] - stats['min_value']

            # Calculate concentration metrics
            df_sorted = df.sort_values('Value_numeric', ascending=False)
            stats['top_5_pct'] = df_sorted.head(5)['Value_numeric'].sum() / stats['total_value'] * 100 if stats['count'] >= 5 else 100
            stats['top_10_pct'] = df_sorted.head(10)['Value_numeric'].sum() / stats['total_value'] * 100 if stats['count'] >= 10 else 100

            # Calculate Herfindahl-Hirschman Index (HHI) - measure of concentration
            # HHI is the sum of squared percentages (0-10000 scale)
            weights = (df['Value_numeric'] / stats['total_value']) * 100
            stats['hhi'] = (weights ** 2).sum()

            # Categorize HHI
            if stats['hhi'] < 1500:
                stats['concentration'] = "Low concentration"
            elif stats['hhi'] < 2500:
                stats['concentration'] = "Moderate concentration"
            else:
                stats['concentration'] = "High concentration"

            # Map the expected column names to their actual counterparts
            column_mapping = {
                'Symbol': 'Ticker' if 'Ticker' in df.columns else None,
                'Name': 'Name'  # Name is already correctly named
            }

            # Check if any mapped columns are missing
            missing_columns = [exp for exp, act in column_mapping.items() if act is None]
            if missing_columns:
                stats['error'] = f"Missing required columns: {', '.join(missing_columns)}"
                return stats

            # Create a copy with standardized column names for easier processing
            df_mapped = df.copy()
            if 'Ticker' in df.columns:
                df_mapped['Symbol'] = df['Ticker']

            # Calculate top holdings (top 10 instead of top 5)
            top_holdings = df_mapped.sort_values(by='Value_numeric', ascending=False).head(10)
            stats['top_holdings'] = top_holdings

            # Calculate percentage of total for each holding
            df_mapped['pct_of_total'] = df_mapped['Value_numeric'] / stats['total_value'] * 100

            # Asset type classification if 'Category' column exists
            if 'Category' in df_mapped.columns:
                category_stats = df_mapped.groupby('Category')['Value_numeric'].sum().reset_index()
                category_stats['pct_of_total'] = category_stats['Value_numeric'] / stats['total_value'] * 100
                stats['asset_allocation'] = category_stats.sort_values('pct_of_total', ascending=False)

            # Use the mapped column names for the final dataframe
            cols_to_select = ['Name', 'Symbol', 'Value_numeric', 'pct_of_total']  # Swapped Name and Symbol order
            stats['holdings_pct'] = df_mapped[cols_to_select].sort_values(by='pct_of_total', ascending=False)

        except Exception as e:
            stats['error'] = f"Error calculating statistics: {str(e)}"
            import traceback
            stats['traceback'] = traceback.format_exc()
    else:
        stats['error'] = "Value column not found in data"

    return stats

def calculate_networth_statistics(df, file_type=None):
    """Calculate statistics for net worth data"""
    stats = {}

    # Only calculate if we have the Balance column
    if 'Balance' in df.columns:
        try:
            # Handle balance formatting (remove $ and commas if present)
            if df['Balance'].dtype == 'object':
                df['Balance_numeric'] = df['Balance'].replace(r'[\$,]', '', regex=True).astype(float)
            else:
                df['Balance_numeric'] = df['Balance']

            # For JSON files with timeline data, use only the most recent date for overview metrics
            if file_type == "json" and 'Date' in df.columns:
                # Sort by date and get the most recent entry for overview calculations
                df_sorted = df.sort_values('Date', ascending=False)
                most_recent = df_sorted.iloc[0]

                # Use the most recent date's values for overview metrics
                stats['total_net_worth'] = most_recent['Balance_numeric']
                stats['total_accounts'] = 1  # Timeline data represents one consolidated view

                # For JSON timeline data, we have specific columns for assets and liabilities
                stats['total_assets'] = most_recent.get('Total Assets', 0)
                stats['total_liabilities'] = most_recent.get('Total Liabilities', 0)
                stats['net_worth'] = stats['total_net_worth']  # Should be the same as Balance

                # Add all the additional total fields from JSON data
                stats['total_cash'] = most_recent.get('Total Cash', 0)
                stats['total_investment'] = most_recent.get('Total Investment', 0)
                stats['total_empower'] = most_recent.get('Total Empower', 0)
                stats['total_mortgage'] = most_recent.get('Total Mortgage', 0)
                stats['total_loan'] = most_recent.get('Total Loan', 0)
                stats['total_credit'] = most_recent.get('Total Credit', 0)
                stats['total_other_assets'] = most_recent.get('Total Other Assets', 0)
                stats['total_other_liabilities'] = most_recent.get('Total Other Liabilities', 0)
                stats['one_day_change'] = most_recent.get('One Day Change', 0)
                stats['one_day_change_pct'] = most_recent.get('One Day Change %', 0)

                # No category/type breakdown for JSON timeline data since it's consolidated
                stats['category_breakdown'] = None
                stats['type_breakdown'] = None
                stats['top_accounts'] = None
                stats['accounts_pct'] = df  # Return the full timeline for display purposes
                stats['category_provider_breakdown'] = None  # No provider breakdown for JSON
            else:
                # Original logic for non-JSON files (webarchive/mhtml with individual accounts)
                # Exclude the TOTAL NET WORTH row from calculations to avoid double counting
                accounts_df = df[df['Account'] != 'TOTAL NET WORTH'].copy()

                # Get the total from the TOTAL NET WORTH row if it exists
                total_row = df[df['Account'] == 'TOTAL NET WORTH']
                if not total_row.empty:
                    stats['total_net_worth'] = total_row['Balance_numeric'].iloc[0]
                else:
                    # If no total row, calculate from individual accounts
                    stats['total_net_worth'] = accounts_df['Balance_numeric'].sum()

                stats['total_accounts'] = len(accounts_df)  # Count only actual accounts, not the total row

                # Calculate assets vs liabilities from individual accounts only
                # Assets include: positive balances from Cash, Investment accounts, and other asset categories
                assets = accounts_df[accounts_df['Balance_numeric'] > 0]['Balance_numeric'].sum() if len(accounts_df[accounts_df['Balance_numeric'] > 0]) > 0 else 0
                liabilities = abs(accounts_df[accounts_df['Balance_numeric'] < 0]['Balance_numeric'].sum()) if len(accounts_df[accounts_df['Balance_numeric'] < 0]) > 0 else 0

                stats['total_assets'] = assets
                stats['total_liabilities'] = liabilities
                stats['net_worth'] = assets - liabilities

                # Add breakdown by category type for non-JSON files to match JSON structure
                if 'Category' in accounts_df.columns:
                    # Calculate detailed asset breakdowns similar to JSON format
                    stats['total_cash'] = accounts_df[accounts_df['Category'] == 'Cash']['Balance_numeric'].sum() if len(accounts_df[accounts_df['Category'] == 'Cash']) > 0 else 0
                    stats['total_brokerage'] = accounts_df[accounts_df['Category'] == 'Brokerage']['Balance_numeric'].sum() if len(accounts_df[accounts_df['Category'] == 'Brokerage']) > 0 else 0
                    stats['total_investment_category'] = accounts_df[accounts_df['Category'] == 'Investment']['Balance_numeric'].sum() if len(accounts_df[accounts_df['Category'] == 'Investment']) > 0 else 0
                    stats['total_retirement'] = accounts_df[accounts_df['Category'] == 'Retirement']['Balance_numeric'].sum() if len(accounts_df[accounts_df['Category'] == 'Retirement']) > 0 else 0
                    stats['total_investment'] = stats['total_brokerage'] + stats['total_investment_category'] + stats['total_retirement']  # Combined for compatibility
                    stats['total_credit'] = abs(accounts_df[accounts_df['Category'] == 'Credit']['Balance_numeric'].sum()) if len(accounts_df[accounts_df['Category'] == 'Credit']) > 0 else 0

                    # Calculate loan and mortgage amounts (these should be negative, so we take absolute value)
                    stats['total_loan'] = abs(accounts_df[accounts_df['Category'] == 'Loan']['Balance_numeric'].sum()) if len(accounts_df[accounts_df['Category'] == 'Loan']) > 0 else 0
                    stats['total_mortgage'] = abs(accounts_df[accounts_df['Category'] == 'Mortgage']['Balance_numeric'].sum()) if len(accounts_df[accounts_df['Category'] == 'Mortgage']) > 0 else 0

                    # Calculate other assets (anything that's positive balance but not Cash, Brokerage, Investment, or Retirement)
                    other_asset_categories = accounts_df[
                        (accounts_df['Balance_numeric'] > 0) &
                        (~accounts_df['Category'].isin(['Cash', 'Brokerage', 'Investment', 'Retirement', 'Total']))
                    ]['Balance_numeric'].sum() if len(accounts_df[
                        (accounts_df['Balance_numeric'] > 0) &
                        (~accounts_df['Category'].isin(['Cash', 'Brokerage', 'Investment', 'Retirement', 'Total']))
                    ]) > 0 else 0
                    stats['total_other_assets'] = other_asset_categories

                    # Calculate other liabilities (anything that's negative balance but not Credit, Loan, or Mortgage)
                    other_liability_categories = abs(accounts_df[
                        (accounts_df['Balance_numeric'] < 0) &
                        (~accounts_df['Category'].isin(['Credit', 'Loan', 'Mortgage']))
                    ]['Balance_numeric'].sum()) if len(accounts_df[
                        (accounts_df['Balance_numeric'] < 0) &
                        (~accounts_df['Category'].isin(['Credit', 'Loan', 'Mortgage']))
                    ]) > 0 else 0
                    stats['total_other_liabilities'] = other_liability_categories

                    # Total empower for compatibility (not typically available in non-JSON files)
                    stats['total_empower'] = 0  # This is typically JSON-specific

                    # No daily change data for non-JSON files
                    stats['one_day_change'] = 0
                    stats['one_day_change_pct'] = 0

                # Category breakdown (exclude total row)
                if 'Category' in accounts_df.columns:
                    category_stats = accounts_df.groupby('Category')['Balance_numeric'].sum().reset_index()
                    category_stats['pct_of_total'] = (category_stats['Balance_numeric'] / stats['total_net_worth'] * 100) if stats['total_net_worth'] != 0 else 0
                    stats['category_breakdown'] = category_stats.sort_values('Balance_numeric', ascending=False)

                    # Enhanced category breakdown with provider details
                    if 'Type' in accounts_df.columns:
                        # Use Provider column if available, otherwise fall back to Type
                        provider_col = 'Provider' if 'Provider' in accounts_df.columns else 'Type'

                        # Group by Category and Provider to show breakdown within each category
                        category_provider_stats = accounts_df.groupby(['Category', provider_col])['Balance_numeric'].agg(['sum', 'count']).reset_index()
                        category_provider_stats.columns = ['Category', 'Provider', 'Amount', 'Account_Count']

                        # Calculate percentage of each provider within its category
                        category_totals = category_stats.set_index('Category')['Balance_numeric'].to_dict()
                        category_provider_stats['pct_of_category'] = category_provider_stats.apply(
                            lambda row: (row['Amount'] / category_totals[row['Category']] * 100)
                            if category_totals.get(row['Category'], 0) != 0 else 0, axis=1
                        )

                        # Calculate percentage of total net worth
                        category_provider_stats['pct_of_total'] = (category_provider_stats['Amount'] / stats['total_net_worth'] * 100) if stats['total_net_worth'] != 0 else 0

                        # Sort by category first, then by amount within category
                        category_provider_stats = category_provider_stats.sort_values(['Category', 'Amount'], ascending=[True, False])
                        stats['category_provider_breakdown'] = category_provider_stats
                    else:
                        stats['category_provider_breakdown'] = None

                # Account type breakdown (exclude total row)
                if 'Type' in accounts_df.columns:
                    type_stats = accounts_df.groupby('Type')['Balance_numeric'].sum().reset_index()
                    type_stats['pct_of_total'] = (type_stats['Balance_numeric'] / stats['total_net_worth'] * 100) if stats['total_net_worth'] != 0 else 0
                    stats['type_breakdown'] = type_stats.sort_values('Balance_numeric', ascending=False)

                # Top accounts by value (exclude total row)
                top_accounts = accounts_df.sort_values(by='Balance_numeric', ascending=False).head(10)
                stats['top_accounts'] = top_accounts

                # Add percentage of total for each account (exclude total row)
                accounts_df['pct_of_total'] = (accounts_df['Balance_numeric'] / stats['total_net_worth'] * 100) if stats['total_net_worth'] != 0 else 0

                # Use the standard column names for the final dataframe
                cols_to_select = ['Account', 'Type', 'Balance_numeric', 'Category', 'pct_of_total']
                available_cols = [col for col in cols_to_select if col in df.columns]
                stats['accounts_pct'] = df[available_cols].sort_values(by='Balance_numeric', ascending=False)

        except Exception as e:
            stats['error'] = f"Error calculating net worth statistics: {str(e)}"
            stats['traceback'] = traceback.format_exc()
    else:
        stats['error'] = "Balance column not found in data"

    return stats

def create_morningstar_csv(df, output_file_base):
    """Create a MorningStar-compatible CSV with proper format and column headers"""
    # Check if we have the required columns
    name_col = 'Name' if 'Name' in df.columns else None
    ticker_col = 'Ticker' if 'Ticker' in df.columns else ('Symbol' if 'Symbol' in df.columns else None)
    shares_col = 'Shares' if 'Shares' in df.columns else None
    value_col = 'Value' if 'Value' in df.columns else None

    if not ticker_col or not shares_col:
        return None

    # Prepare the data
    ms_data = []
    for idx, row in df.iterrows():
        name = row.get(name_col, '') if name_col else ''
        symbol = row[ticker_col]
        shares = row[shares_col]

        # Calculate price per share if we have value and shares
        price = ''
        if value_col and shares and float(shares) > 0:
            try:
                # Handle value formatting (remove $ and commas if present)
                if isinstance(row[value_col], str):
                    value_clean = row[value_col].replace('$', '').replace(',', '')
                else:
                    value_clean = str(row[value_col])

                total_value = float(value_clean)
                price = total_value / float(shares)
                price = f"{price:.2f}"
            except (ValueError, ZeroDivisionError):
                price = ''

        # Use CASH$ for cash positions if symbol indicates cash
        if 'cash' in str(symbol).lower():
            symbol = 'CASH$'

        ms_data.append({
            'Name': name,
            'Symbol': symbol,
            'Action': 'buy',  # Default to buy for existing holdings
            'Shares': shares,
            'Price': price,
            'Commission': '0',  # Default to 0 commission
            'Date': ''  # Leave date empty as we don't have transaction dates
        })

    # Create DataFrame with proper column order
    ms_df = pd.DataFrame(ms_data, columns=['Name', 'Symbol', 'Action', 'Shares', 'Price', 'Commission', 'Date'])

    # Save to CSV in user-specific directory
    user_dir = ensure_user_files_dir()
    base_name = os.path.basename(output_file_base)
    ms_path = os.path.join(user_dir, f"{base_name}_morningstar.csv")
    ms_df.to_csv(ms_path, index=False)
    return ms_path

def create_text_report(stats, df, output_file_base):
    """Create a text report summarizing the portfolio analysis"""
    user_dir = ensure_user_files_dir()
    base_name = os.path.basename(output_file_base)
    report_path = os.path.join(user_dir, f"{base_name}_report.txt")

    with open(report_path, "w", encoding="utf-8") as file:
        file.write("PORTFOLIO ANALYSIS REPORT\n")
        file.write("=======================\n\n")

        # Summary statistics
        file.write("SUMMARY STATISTICS\n")
        file.write("-----------------\n")
        file.write(f"Total Portfolio Value: ${stats['total_value']:,.2f}\n")
        file.write(f"Number of Holdings: {stats['count']}\n")
        file.write(f"Average Holding Value: ${stats['avg_value']:,.2f}\n")
        file.write(f"Median Holding Value: ${stats['median_value']:,.2f}\n")
        file.write(f"Standard Deviation: ${stats['std_dev']:,.2f}\n")
        file.write(f"Largest Holding: ${stats['max_value']:,.2f}\n")
        file.write(f"Smallest Holding: ${stats['min_value']:,.2f}\n")
        file.write(f"Value Range: ${stats['value_range']:,.2f}\n\n")

        # Concentration metrics
        file.write("CONCENTRATION METRICS\n")
        file.write("--------------------\n")
        file.write(f"Top 5 Holdings: {stats['top_5_pct']:.2f}% of portfolio\n")
        file.write(f"Top 10 Holdings: {stats['top_10_pct']:.2f}% of portfolio\n")
        file.write(f"HHI Concentration Score: {stats['hhi']:.2f} ({stats['concentration']})\n\n")

        # Asset allocation if available
        if 'asset_allocation' in stats:
            file.write("ASSET ALLOCATION\n")
            file.write("----------------\n")
            for idx, row in stats['asset_allocation'].iterrows():
                file.write(f"{row['Category']}: {row['pct_of_total']:.2f}% (${row['Value_numeric']:,.2f})\n")
            file.write("\n")

        # Top holdings
        file.write("TOP HOLDINGS\n")
        file.write("-----------\n")

        top_holdings = stats['holdings_pct'].head(10)
        for idx, row in top_holdings.iterrows():
            file.write(f"{row['Name']} ({row['Symbol']}): {row['pct_of_total']:.2f}% (${row['Value_numeric']:,.2f})\n")

        # If there are more than 10 holdings, add an "Other" category
        if len(stats['holdings_pct']) > 10:
            others_sum = stats['holdings_pct'].iloc[10:]['pct_of_total'].sum()
            others_value = others_sum / 100 * stats['total_value']
            file.write(f"Other Holdings: {others_sum:.2f}% (${others_value:,.2f})\n\n")

        # All holdings sorted by value
        file.write("\nALL HOLDINGS (by value)\n")
        file.write("---------------------\n")

        for idx, row in df.sort_values('Value_numeric', ascending=False).iterrows():
            ticker = row.get('Ticker', row.get('Symbol', 'N/A'))
            name = row.get('Name', 'N/A')
            value = row.get('Value_numeric', row.get('Value', 0))
            shares = row.get('Shares', 'N/A')

            file.write(f"{name} ({ticker}): ${value:,.2f}")
            if shares != 'N/A':
                file.write(f", {shares} shares")
            file.write("\n")

    return report_path

def main():
    # Initialize user directory
    user_dir = ensure_user_dirs()

    # Render sidebar and get user inputs
    sidebar_inputs = render_sidebar()

    file_path = sidebar_inputs["file_path"]
    extract_portfolio = sidebar_inputs["extract_portfolio"]
    save_csv = sidebar_inputs["save_csv"]
    process_button = sidebar_inputs["process_button"]

    # Process file only if button clicked and file path provided or if we already have results
    process_file_flag = False

    if file_path and process_button:
        # Clean up old sessions before processing new file
        with st.spinner("Cleaning up old sessions..."):
            cleanup_old_sessions()

        # New file to process
        process_file_flag = True
        st.session_state.processed_file_path = file_path

    # Display results if we have processed data
    if process_file_flag:
        # Determine file type and display it
        file_type = determine_file_type(file_path)
        file_type_display = "WebArchive" if file_type == 'webarchive' else "MHTML"

        with st.spinner(f"Processing {file_type_display} file..."):
            result = process_file(
                file_path=file_path,
                extract_portfolio=extract_portfolio,
                save_csv=save_csv
            )
            # Store result in session state
            st.session_state.processed_result = result

        # Show toast only after processing a new file
        st.toast(f"{file_type_display} processed successfully!  ✅")

    # Use stored result if available
    result = st.session_state.processed_result

    if result and result.get("success", False):
        # Get file type for display
        file_type = result.get("file_type", "unknown")
        file_type_display = "WebArchive" if file_type == 'webarchive' else "MHTML" if file_type == 'mhtml' else "File"

        # --- Ensure df is loaded from CSV or holdings ---
        df = None
        if result.get("csv_path"):
            df = read_csv_to_dataframe(result["csv_path"])
        if df is None and result.get("holdings"):
            df = pd.DataFrame(result["holdings"])

        # --- DOWNLOAD OPTIONS SECTION (moved to top) ---
        st.header("Download Options")
        col1, col2, col3 = st.columns(3)

        # Provide CSV download
        if result["csv_path"]:
            with open(result["csv_path"], "r") as f:
                csv_data = f.read()

            with col1:
                download_csv = st.download_button(
                    label="Download CSV File",
                    data=csv_data,
                    file_name=os.path.basename(result["csv_path"]),
                    mime="text/csv",
                    key="download_csv"
                )

        # MorningStar CSV download or text file as fallback
        if result["morningstar_path"]:
            with open(result["morningstar_path"], "r") as f:
                ms_data = f.read()

            with col2:
                download_ms = st.download_button(
                    label="Download MorningStar CSV",
                    data=ms_data,
                    file_name=os.path.basename(result["morningstar_path"]),
                    mime="text/csv",
                    key="download_ms"
                )
        elif result["text_path"]:
            with open(result["text_path"], "r", encoding="utf-8") as f:
                text_data = f.read()

            with col2:
                download_text = st.download_button(
                    label="Download Formatted Text File",
                    data=text_data,
                    file_name=os.path.basename(result["text_path"]),
                    mime="text/plain",
                    key="download_text"
                )

        # Text report download or raw data as fallback
        if result["report_path"]:
            with open(result["report_path"], "r", encoding="utf-8") as f:
                report_data = f.read()

            with col3:
                download_report = st.download_button(
                    label="Download Text Report",
                    data=report_data,
                    file_name=os.path.basename(result["report_path"]),
                    mime="text/plain",
                    key="download_report"
                )
        elif result["raw_data_path"]:
            with open(result["raw_data_path"], "r", encoding="utf-8") as f:
                raw_data = f.read()

            with col3:
                download_raw = st.download_button(
                    label="Download Raw Data File",
                    data=raw_data,
                    file_name=os.path.basename(result["raw_data_path"]),
                    mime="text/plain",
                    key="download_raw"
                )

        # Display data based on content type
        content_type = result.get("content_type", "portfolio")

        if content_type == "net_worth":
            # Display net worth data
            if result["holdings"] and df is not None:
                st.header("Net Worth Summary")

                # Check if this is JSON net worth data (timeline data)
                if result.get("file_type") == "json" and 'Date' in df.columns:
                    # For JSON files, show ALL dates but only remove basic account-level columns
                    # Keep the detailed asset/liability breakdown columns
                    columns_to_remove = ['Account', 'Type', 'Category']
                    display_df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])

                    # Sort by date (most recent first) for better presentation
                    display_df = display_df.sort_values('Date', ascending=False)

                    st.dataframe(display_df, hide_index=True)
                else:
                    # Display only individual accounts (exclude TOTAL NET WORTH row) for non-JSON files
                    accounts_df = df[df['Account'] != 'TOTAL NET WORTH'].copy()
                    st.dataframe(accounts_df, hide_index=True)

                # Calculate net worth statistics
                # For JSON files, pass the file type so we can handle timeline data appropriately
                stats = calculate_networth_statistics(df, file_type=result.get("file_type"))

                if 'error' in stats:
                    st.error(stats['error'])
                    # Display raw dataframe columns to help debugging
                    st.write("Available columns in the dataframe:", df.columns.tolist())
                    # Display traceback if available
                    if 'traceback' in stats:
                        with st.expander("Error details"):
                            st.code(stats['traceback'])
                else:
                    # Create metrics for net worth overview
                    st.header("Net Worth Overview")

                    # For JSON files, show comprehensive breakdown with all total fields
                    if result.get("file_type") == "json":
                        # Primary metrics row
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(label="Total Net Worth", value=f"${stats['total_net_worth']:,.2f}")
                        with col2:
                            st.metric(label="Total Assets", value=f"${stats['total_assets']:,.2f}")
                        with col3:
                            st.metric(label="Total Liabilities", value=f"${stats['total_liabilities']:,.2f}")

                        # Asset breakdown row
                        st.subheader("Asset Breakdown")
                        col4, col5, col6, col7 = st.columns(4)
                        with col4:
                            st.metric(label="Total Cash", value=f"${stats['total_cash']:,.2f}")
                        with col5:
                            st.metric(label="Total Investment", value=f"${stats['total_investment']:,.2f}")
                        with col6:
                            st.metric(label="Total Empower", value=f"${stats['total_empower']:,.2f}")
                        with col7:
                            st.metric(label="Total Other Assets", value=f"${stats['total_other_assets']:,.2f}")

                        # Liability breakdown row
                        st.subheader("Liability Breakdown")
                        # First row: Credit and Loan
                        col8, col9 = st.columns(2)
                        with col8:
                            st.metric(label="Total Credit", value=f"${stats['total_credit']:,.2f}")
                        with col9:
                            st.metric(label="Total Loan", value=f"${stats['total_loan']:,.2f}")

                        # Second row: Mortgage and Other Liabilities
                        col10, col11 = st.columns(2)
                        with col10:
                            st.metric(label="Total Mortgage", value=f"${stats['total_mortgage']:,.2f}")
                        with col11:
                            st.metric(label="Total Other Liabilities", value=f"${stats['total_other_liabilities']:,.2f}")

                        # Daily change row
                        st.subheader("Daily Change")
                        col12, col13 = st.columns(2)
                        with col12:
                            change_value = stats['one_day_change']
                            delta_color = "normal" if change_value >= 0 else "inverse"
                            st.metric(
                                label="One Day Change",
                                value=f"${change_value:,.2f}",
                                delta=f"${change_value:,.2f}" if change_value != 0 else None,
                                delta_color=delta_color
                            )
                        with col13:
                            change_pct = stats['one_day_change_pct']
                            delta_color = "normal" if change_pct >= 0 else "inverse"
                            st.metric(
                                label="One Day Change %",
                                value=f"{change_pct:.2f}%",
                                delta=f"{change_pct:+.2f}%" if change_pct != 0 else None,
                                delta_color=delta_color
                            )
                    else:
                        # Enhanced layout for non-JSON files with detailed breakdown when available
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(label="Total Net Worth", value=f"${stats['total_net_worth']:,.2f}")
                        with col2:
                            st.metric(label="Total Assets", value=f"${stats['total_assets']:,.2f}")
                        with col3:
                            st.metric(label="Total Liabilities", value=f"${stats['total_liabilities']:,.2f}")

                        # Show detailed breakdown if we have category data
                        if 'total_cash' in stats:
                            # Asset breakdown row
                            st.subheader("Asset Breakdown")
                            col4, col5, col6, col7 = st.columns(4)
                            with col4:
                                st.metric(label="Total Cash", value=f"${stats['total_cash']:,.2f}")
                            with col5:
                                st.metric(label="Total Investment", value=f"${stats.get('total_investment_category', 0):,.2f}")
                            with col6:
                                st.metric(label="Total Retirement", value=f"${stats.get('total_retirement', 0):,.2f}")
                            with col7:
                                st.metric(label="Total Other Assets", value=f"${stats['total_other_assets']:,.2f}")

                            # Additional row for other metrics
                            st.subheader("Account Information")
                            col4b, col5b, col6b, col7b = st.columns(4)
                            with col4b:
                                st.metric(label="Number of Accounts", value=stats['total_accounts'])
                            with col5b:
                                st.metric(label="Total Investment", value=f"${stats['total_investment']:,.2f}", help="Combined Brokerage + Retirement")
                            with col6b:
                                st.metric(label=" ", value=" ", label_visibility="hidden")  # Empty column for spacing
                            with col7b:
                                st.metric(label="  ", value="  ", label_visibility="hidden")  # Empty column for spacing

                            # Liability breakdown row (if there are liabilities)
                            if stats['total_liabilities'] > 0 or stats['total_credit'] > 0:
                                st.subheader("Liability Breakdown")
                                # First row: Credit and Loan
                                col8, col9 = st.columns(2)
                                with col8:
                                    st.metric(label="Total Credit", value=f"${stats['total_credit']:,.2f}")
                                with col9:
                                    st.metric(label="Total Loan", value=f"${stats['total_loan']:,.2f}")

                                # Second row: Mortgage and Other Liabilities
                                col10, col11 = st.columns(2)
                                with col10:
                                    st.metric(label="Total Mortgage", value=f"${stats['total_mortgage']:,.2f}")
                                with col11:
                                    st.metric(label="Total Other Liabilities", value=f"${stats['total_other_liabilities']:,.2f}")
                        else:
                            # Fallback to simple 4-column layout if no detailed breakdown available
                            col4, = st.columns(1)
                            with st.container():
                                st.metric(label="Number of Accounts", value=stats['total_accounts'])

                    # Category breakdown
                    if 'category_breakdown' in stats and stats['category_breakdown'] is not None and not stats['category_breakdown'].empty:
                        st.header("Breakdown by Category")

                        # Create two columns for charts
                        chart_col1, chart_col2 = st.columns(2)

                        with chart_col1:
                            # Pie chart for category breakdown
                            fig_pie = px.pie(
                                stats['category_breakdown'],
                                values='Balance_numeric',
                                names='Category',
                                title='Net Worth by Category',
                                color_discrete_sequence=px.colors.qualitative.Bold
                            )
                            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_pie, use_container_width=True)

                        with chart_col2:
                            # Bar chart for category breakdown
                            fig_bar = px.bar(
                                stats['category_breakdown'],
                                x='Category',
                                y='Balance_numeric',
                                title='Net Worth by Category',
                                text_auto=True,
                                color='Category',
                                color_discrete_sequence=px.colors.qualitative.Bold
                            )
                            fig_bar.update_layout(showlegend=False)
                            st.plotly_chart(fig_bar, use_container_width=True)

                        # Display category table with provider breakdown
                        if 'category_provider_breakdown' in stats and stats['category_provider_breakdown'] is not None and not stats['category_provider_breakdown'].empty:
                            st.subheader("Category Breakdown by Provider")

                            # Display the enhanced table with provider details
                            enhanced_table = stats['category_provider_breakdown'][['Category', 'Provider', 'Amount', 'Account_Count', 'pct_of_category', 'pct_of_total']].rename(
                                columns={
                                    'Amount': 'Amount ($)',
                                    'Account_Count': 'Accounts',
                                    'pct_of_category': '% of Category',
                                    'pct_of_total': '% of Net Worth'
                                }
                            ).reset_index(drop=True)

                            # Format the monetary values and percentages
                            enhanced_table['Amount ($)'] = enhanced_table['Amount ($)'].apply(lambda x: f"${x:,.2f}")
                            enhanced_table['% of Category'] = enhanced_table['% of Category'].apply(lambda x: f"{x:.1f}%")
                            enhanced_table['% of Net Worth'] = enhanced_table['% of Net Worth'].apply(lambda x: f"{x:.1f}%")

                            st.dataframe(enhanced_table, hide_index=True)
                        else:
                            # Fallback to simple category table
                            st.dataframe(
                                stats['category_breakdown'][['Category', 'Balance_numeric', 'pct_of_total']].rename(
                                    columns={'Balance_numeric': 'Amount ($)', 'pct_of_total': '% of Net Worth'}
                                ).reset_index(drop=True),
                                hide_index=True
                            )

                    # Account type breakdown
                    if 'type_breakdown' in stats and stats['type_breakdown'] is not None and not stats['type_breakdown'].empty:
                        st.header("Breakdown by Account Type")

                        chart_col3, chart_col4 = st.columns(2)

                        with chart_col3:
                            # Pie chart for account type breakdown
                            fig_type_pie = px.pie(
                                stats['type_breakdown'],
                                values='Balance_numeric',
                                names='Type',
                                title='Net Worth by Account Type',
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                            fig_type_pie.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_type_pie, use_container_width=True)

                        with chart_col4:
                            # Horizontal bar chart for account types
                            type_data = stats['type_breakdown'].sort_values('Balance_numeric')
                            fig_type_bar = go.Figure(go.Bar(
                                x=type_data['Balance_numeric'],
                                y=type_data['Type'],
                                orientation='h',
                                marker=dict(
                                    color=type_data['Balance_numeric'],
                                    colorscale='Viridis'
                                ),
                                text=[f"${v:,.2f}" for v in type_data['Balance_numeric']],
                                textposition='auto'
                            ))
                            fig_type_bar.update_layout(
                                title='Net Worth by Account Type',
                                xaxis_title='Amount ($)',
                                yaxis_title='Account Type',
                                showlegend=False
                            )
                            st.plotly_chart(fig_type_bar, use_container_width=True)

                        # Display type table
                        st.dataframe(
                            stats['type_breakdown'][['Type', 'Balance_numeric', 'pct_of_total']].rename(
                                columns={'Balance_numeric': 'Amount ($)', 'pct_of_total': '% of Net Worth'}
                            ).reset_index(drop=True),
                            hide_index=True
                        )

                    # Top accounts
                    if 'top_accounts' in stats and stats['top_accounts'] is not None and not stats['top_accounts'].empty:
                        st.header("Top 10 Accounts by Value")
                        top_accounts_display = stats['top_accounts'][['Account', 'Type', 'Balance_numeric', 'Category']].rename(
                            columns={'Balance_numeric': 'Balance ($)'}
                        ).reset_index(drop=True)
                        st.dataframe(top_accounts_display, hide_index=True)

        else:
            # Display portfolio data (existing logic)
            if result["holdings"] and df is not None:
                st.header("Portfolio Holdings")
                st.dataframe(df, hide_index=True)

                # --- LLM Portfolio Review Button (moved inside data validation) ---
                st.subheader("Portfolio Review by AI")
                stats = calculate_portfolio_statistics(df)
                if st.button("Ask AI for Portfolio Insights", key="llm_review_btn"):
                    with st.spinner("AI is reviewing your portfolio..."):
                        llm_prompt = (
                            "You are a financial portfolio expert. "
                            "Review the following portfolio holdings and statistics. "
                            "Provide a concise, actionable assessment of the portfolio's quality, diversification, risks, and suggest improvements. "
                            "Here is the data:\n\n"
                            f"Holdings (top 10):\n{df.head(10).to_string(index=False)}\n\n"
                            f"Portfolio statistics:\n{stats}\n"
                        )
                        system_message = (
                            "You are a helpful assistant that provides expert financial portfolio analysis. "
                            "Be concise, actionable, and clear for a general audience."
                        )
                        llm_response = send_query_to_llm(
                            query=llm_prompt,
                            system_message=system_message
                        )
                        st.success("AI Portfolio Review:")
                        st.write(llm_response)

                # Now continue with portfolio statistics section
                st.header("Portfolio Statistics")

                # Calculate portfolio statistics
                stats = calculate_portfolio_statistics(df)

                if 'error' in stats:
                    st.error(stats['error'])
                    # Display raw dataframe columns to help debugging
                    st.write("Available columns in the dataframe:", df.columns.tolist())
                    # Display traceback if available
                    if 'traceback' in stats:
                        with st.expander("Error details"):
                            st.code(stats['traceback'])
                else:
                    # Create three columns for better organization
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Summary Statistics")
                        metrics_col1, metrics_col2 = st.columns(2)

                        with metrics_col1:
                            st.metric(label="Total Value", value=f"${stats['total_value']:,.2f}")
                            st.metric(label="Holdings Count", value=stats['count'])
                            st.metric(label="Average Value", value=f"${stats['avg_value']:,.2f}")
                            st.metric(label="Median Value", value=f"${stats['median_value']:,.2f}")

                        with metrics_col2:
                            st.metric(label="Largest Holding", value=f"${stats['max_value']:,.2f}")
                            st.metric(label="Smallest Holding", value=f"${stats['min_value']:,.2f}")
                            st.metric(label="Value Range", value=f"${stats['value_range']:,.2f}")
                            st.metric(label="Standard Deviation", value=f"${stats['std_dev']:,.2f}")

                        # Concentration metrics
                        st.subheader("Portfolio Concentration")
                        metrics_col3, metrics_col4 = st.columns(2)

                        with metrics_col3:
                            st.metric(label="Top 5 Holdings", value=f"{stats['top_5_pct']:.2f}%")
                            st.metric(label="HHI Score", value=f"{stats['hhi']:.2f}")

                        with metrics_col4:
                            st.metric(label="Top 10 Holdings", value=f"{stats['top_10_pct']:.2f}%")
                            st.metric(label="Concentration", value=stats['concentration'])

                    # Asset allocation chart if available
                    if 'asset_allocation' in stats and not stats['asset_allocation'].empty:
                        with st.expander("Asset Allocation", expanded=True):
                            asset_data = stats['asset_allocation']
                            st.bar_chart(asset_data.set_index('Category')['pct_of_total'])
                            st.dataframe(
                                asset_data[['Category', 'pct_of_total']].rename(
                                    columns={'pct_of_total': '% of Portfolio'}
                                ).reset_index(drop=True),
                                hide_index=True
                            )

                    with col2:
                        st.subheader("Top Holdings")
                        # Get top 10 holdings
                        top_data = stats['holdings_pct'].head(10)

                        # Calculate "Others" only if more than 10 holdings
                        others_sum = stats['holdings_pct'].iloc[10:]['pct_of_total'].sum() if len(stats['holdings_pct']) > 10 else 0

                        # Add "Other" category if there are more than 10 holdings
                        if others_sum > 0:
                            others_row = pd.DataFrame({
                                'Symbol': ['OTHER'],
                                'Name': ['Other Holdings'],
                                'Value_numeric': [others_sum / 100 * stats['total_value']],
                                'pct_of_total': [others_sum]
                            })
                            display_data = pd.concat([top_data, others_row])
                        else:
                            display_data = top_data

                        # Create a table showing top holdings with percentages
                        # Increase the height of the dataframe to avoid scrolling
                        st.dataframe(
                            display_data[['Name', 'Symbol', 'pct_of_total']].rename(
                                columns={'pct_of_total': '% of Portfolio'}
                            ).reset_index(drop=True),
                            hide_index=True,
                            height=420  # Set a fixed height that should accommodate 10-11 rows
                        )


                    # Add a new section for more charts
                    st.header("Portfolio Visualizations")

                    # Create tabs for different chart types
                    tabs = st.tabs(["Holdings Treemap", "Top 10 Bar Chart", "Value Distribution", "Portfolio Concentration"])

                    # Tab 1: Holdings Treemap - Shows hierarchical view of holdings
                    with tabs[0]:
                        # Create a treemap of holdings
                        treemap_data = display_data.copy()
                        fig_treemap = px.treemap(
                            treemap_data,
                            path=['Symbol'],
                            values='pct_of_total',
                            color='Value_numeric',
                            color_continuous_scale='Viridis',
                            hover_data=['Name', 'Value_numeric'],
                            title='Portfolio Holdings Treemap'
                        )
                        fig_treemap.update_layout(
                            height=600,
                            margin=dict(t=50, l=25, r=25, b=25)
                        )
                        st.plotly_chart(fig_treemap, use_container_width=True)
                        st.caption("Treemap visualization shows each holding sized by percentage of portfolio with color intensity based on value.")

                    # Tab 2: Top 10 Bar Chart
                    with tabs[1]:
                        # Create horizontal bar chart of top holdings
                        top10_data = stats['holdings_pct'].head(10).copy()
                        top10_data = top10_data.sort_values('pct_of_total')

                        fig_bar = go.Figure(go.Bar(
                            x=top10_data['pct_of_total'],
                            y=top10_data['Name'] + " (" + top10_data['Symbol'] + ")",
                            orientation='h',
                            marker=dict(
                                color=top10_data['pct_of_total'],
                                colorscale='Viridis'
                            ),
                            text=[f"${v:,.2f}" for v in top10_data['Value_numeric']],
                            textposition='auto'
                        ))
                        fig_bar.update_layout(
                            title='Top 10 Holdings by Portfolio Percentage',
                            xaxis_title='Percentage of Portfolio',
                            yaxis_title='Holdings',
                            height=500,
                            margin=dict(l=250, r=50)  # Increase left margin for longer holding names
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)

                    # Tab 3: Value Distribution Histogram
                    with tabs[2]:
                        # Create a histogram of holding values
                        # Filter out extreme outliers for better visualization
                        q1 = np.percentile(df['Value_numeric'], 25)
                        q3 = np.percentile(df['Value_numeric'], 75)
                        iqr = q3 - q1
                        upper_bound = q3 + 2.5 * iqr  # Less strict than 1.5*IQR to include more data

                        filtered_values = df[df['Value_numeric'] <= upper_bound]['Value_numeric']

                        fig_hist = px.histogram(
                            filtered_values,
                            nbins=20,
                            title='Distribution of Holding Values',
                            labels={'value': 'Holding Value ($)', 'count': 'Number of Holdings'},
                            color_discrete_sequence=['lightblue'],
                        )
                        fig_hist.update_layout(
                            showlegend=False,
                            height=500
                        )
                        st.plotly_chart(fig_hist, use_container_width=True)

                        # Add descriptive statistics
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Mean Value", f"${stats['avg_value']:,.2f}")
                        col2.metric("Median Value", f"${stats['median_value']:,.2f}")
                        col3.metric("Standard Deviation", f"${stats['std_dev']:,.2f}")

                        if upper_bound < stats['max_value']:
                            st.info(f"Note: Some holdings with values greater than ${upper_bound:,.2f} were excluded from the histogram for better visualization.")

                    # Tab 4: Portfolio Concentration Analysis
                    with tabs[3]:
                        # Create data for Lorenz curve (measure of inequality in portfolio distribution)
                        lorenz_data = stats['holdings_pct'].copy().sort_values('Value_numeric')
                        lorenz_data['cumulative_pct'] = lorenz_data['Value_numeric'].cumsum() / stats['total_value'] * 100
                        lorenz_data['holding_pct'] = 100 * (np.arange(1, len(lorenz_data) + 1) / len(lorenz_data))

                        # Create Lorenz curve
                        fig_lorenz = go.Figure()

                        # Add perfect equality line (diagonal)
                        fig_lorenz.add_trace(go.Scatter(
                            x=[0, 100],
                            y=[0, 100],
                            mode='lines',
                            name='Perfect Equality',
                            line=dict(color='black', dash='dash')
                        ))

                        # Add Lorenz curve
                        fig_lorenz.add_trace(go.Scatter(
                            x=lorenz_data['holding_pct'].tolist(),
                            y=lorenz_data['cumulative_pct'].tolist(),
                            mode='lines',
                            name='Portfolio Distribution',
                            fill='tozeroy',
                            line=dict(color='blue')
                        ))

                        fig_lorenz.update_layout(
                            title='Portfolio Concentration Analysis (Lorenz Curve)',
                            xaxis_title='Cumulative % of Holdings',
                            yaxis_title='Cumulative % of Portfolio Value',
                            height=500
                        )
                        st.plotly_chart(fig_lorenz, use_container_width=True)

                        # Explanation of the Lorenz curve
                        st.caption("""
                        **Interpreting the Lorenz Curve:**
                        - The diagonal line represents perfect equality (all holdings have equal value)
                        - The curve shows actual distribution of your portfolio
                        - The greater the distance between the curve and diagonal, the more concentrated your portfolio
                        - A concentrated portfolio may have higher risk due to lack of diversification
                        """)

                        # Add Gini coefficient (measure of inequality) if we have enough holdings
                        if len(lorenz_data) > 5:
                            # Calculate approximate Gini coefficient from Lorenz curve data
                            x = lorenz_data['holding_pct'].values / 100
                            y = lorenz_data['cumulative_pct'].values / 100
                            x = np.insert(x, 0, 0)
                            y = np.insert(y, 0, 0)
                            # Use np.trapezoid instead of np.trapz to avoid DeprecationWarning
                            B = np.trapezoid(y, x)
                            gini = 1 - 2 * B

                            st.metric(
                                "Portfolio Gini Coefficient",
                                f"{gini:.2f}",
                                help="Measures inequality in your portfolio. Values range from 0 (perfect equality) to 1 (perfect inequality)."
                            )

                            # Interpret Gini coefficient
                            if gini < 0.2:
                                concentration = "Very Low"
                            elif gini < 0.4:
                                concentration = "Low"
                            elif gini < 0.6:
                                concentration = "Moderate"
                            elif gini < 0.8:
                                concentration = "High"
                            else:
                                concentration = "Very High"

                            st.info(f"Your portfolio has a **{concentration}** concentration level based on the Gini coefficient.")

                            st.markdown("""
                            ### 📘 Understanding Gini vs HHI

                            **Gini Coefficient**
                            - Measures overall *inequality* in your portfolio.
                            - Sensitive to **all holdings**, including small ones.
                            - A high Gini (close to 1) means a few holdings make up most of the portfolio, with many very small ones.

                            **HHI (Herfindahl-Hirschman Index)**
                            - Measures *concentration* using squared percentage weights.
                            - Focuses more on **large holdings**.
                            - A low HHI means no single holding dominates—even if many others are small.

                            🧠 **Why they can differ:**
                            You might have a few large holdings and many tiny ones.
                            Gini will say "high inequality", while HHI might still say "low concentration".

                            Both are useful — Gini shows diversification risk; HHI shows exposure to dominant assets.
                            """)

                    # Asset allocation section - if available, AFTER the tabs
                    if 'asset_allocation' in stats and not stats['asset_allocation'].empty:
                        st.header("Asset Allocation")
                        asset_data = stats['asset_allocation']

                        # Create pie chart for asset allocation
                        fig_asset = px.pie(
                            asset_data,
                            values='pct_of_total',
                            names='Category',
                            title='Asset Allocation by Category',
                            hover_data=['Value_numeric'],
                            labels={'Value_numeric': 'Value ($)'},
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )
                        fig_asset.update_traces(textposition='inside', textinfo='percent+label')
                        fig_asset.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')

                        # Create bar chart for asset allocation
                        fig_asset_bar = px.bar(
                            asset_data,
                            x='Category',
                            y='pct_of_total',
                            title='Asset Allocation by Category',
                            text_auto=True,
                            labels={'pct_of_total': 'Percentage of Portfolio', 'Category': 'Asset Category'},
                            color='Category',
                            color_discrete_sequence=px.colors.qualitative.Bold
                        )

                        # Use columns to display charts side by side
                        asset_col1, asset_col2 = st.columns(2)

                        with asset_col1:
                            st.plotly_chart(fig_asset, use_container_width=True)

                        with asset_col2:
                            st.plotly_chart(fig_asset_bar, use_container_width=True)

    else:
        # No file processed yet, show instructions
        st.markdown("""
        ### Empower Portfolio & Net Worth Extractor
        1. **Get your data from Empower**:
           - Log in to your Empower Personal Dashboard account at [home.personalcapital.com](https://home.personalcapital.com)
           - **For Portfolio data**: Navigate to **Investing** → **Holdings** in the main menu
           - **For Net Worth data**: Navigate to **Overview** → **Net Worth** in the main menu
           - **For Safari users**:
             - Right-click and select "Save As"
             - Choose "Web Archive" format (.webarchive)
           - **For Chrome/Edge/Firefox users**:
             - Right-click and select "Save As" or "Save Page As"
             - Choose "Web Page, Complete" or "MHTML" format (.mhtml)

        2. **Process your data**:
           - Upload the saved file using the file uploader in the sidebar ←
           - The app will automatically detect if it's a portfolio or net worth file
           - Click **Process File** button
           - View your data and download various file formats

        3. **Download options**:
           - **For Portfolio files**: CSV file, MorningStar CSV, Text Report with detailed analysis
           - **For Net Worth files**: CSV file, Text Report with net worth summary
        """)

        # Add tabs for different browser instructions
        browser_tabs = st.tabs(["Safari", "Chrome", "Edge", "Firefox"])

        with browser_tabs[0]:
            st.subheader("Safari Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. From the menu bar, select **File** → **Save As**
            3. In the save dialog, select format: **Web Archive (.webarchive)**
            4. Choose a location and save
            5. Upload the .webarchive file using the sidebar
            """)

        with browser_tabs[1]:
            st.subheader("Chrome Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. Press **Ctrl+S** (Windows) or **⌘+S** (Mac)
            3. In the save dialog, change "Save as type" to **Webpage, Complete (.mhtml)**
            4. Choose a location and save
            5. Upload the .mhtml file using the sidebar
            """)

        with browser_tabs[2]:
            st.subheader("Edge Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. Press **Ctrl+S** (Windows) or **⌘+S** (Mac)
            3. In the save dialog, change "Save as type" to **Webpage, Complete (.mhtml)**
            4. Choose a location and save
            5. Upload the .mhtml file using the sidebar
            """)

        with browser_tabs[3]:
            st.subheader("Firefox Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. Press **Ctrl+S** (Windows) or **⌘+S** (Mac)
            3. In the save dialog, change "Save as" to **Web Page, complete**
            4. This will create an HTML file and a folder - you'll need to manually combine them into MHTML format
            5. Alternatively, install the "Save Page WE" add-on to save as MHTML directly
            6. Upload the .mhtml file using the sidebar
            """)

        # Add some helpful tips
        st.info("💡 **Tip**: This tool works entirely in your browser - your financial data never leaves your computer.")

    # Clean up temporary files after processing - no need to check file_selection_method anymore
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
        except:
            pass

    # Add a small footer to show user ID (optional)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Session ID: {st.session_state.user_id}")

if __name__ == "__main__":
    main()
