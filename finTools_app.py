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
from urllib.parse import quote_plus, unquote_plus
import urllib.request
import urllib.error
import yfinance as yf

# Add this import at the top of the file with the other imports
import plotly.express as px

# Add these imports at the top of the file with other imports
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

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
                # Provide diagnostic information about what was found
                error_msg = "Could not find networthHistories in JSON structure."
                if 'spData' in data:
                    available_keys = list(data['spData'].keys())
                    error_msg += f" Found these keys in spData: {', '.join(available_keys)}."

                    # Check if it's a transactions file
                    if 'transactions' in data['spData']:
                        error_msg += " This appears to be a TRANSACTIONS export, not a networth history export."
                    # Check if it's an account summaries file
                    elif 'accountSummaries' in data['spData']:
                        num_accounts = len(data['spData']['accountSummaries'])
                        error_msg += f" This appears to be an ACCOUNT SUMMARIES export (snapshot of {num_accounts} accounts), not a networth HISTORY timeline export. Please export the 'Net Worth Over Time' data from Empower instead."
                    else:
                        error_msg += " This does not appear to be a recognized Empower export format for networth history."
                else:
                    error_msg += " 'spData' key not found in JSON."

                return error_msg

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

def process_holdings_json(file_path):
    """Process a JSON file containing portfolio holdings data and return structured data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Look for holdings in the parsed data
        if 'spData' in data and 'holdings' in data['spData']:
            holdings = data['spData']['holdings']
            total_value = data['spData'].get('holdingsTotalValue', 0.0)

            # Structure holdings data to match the format from webarchive/mhtml
            structured_data = []
            for holding in holdings:
                # Calculate 1 day % change if not present
                one_day_pct = holding.get('oneDayPercentChange', 0.0)

                ticker = holding.get('ticker', holding.get('originalTicker', ''))
                description = holding.get('description', holding.get('originalDescription', ''))
                # Cash entries have no ticker in Empower's data; assign "CASH" so the CSV column is populated
                if not ticker and (holding.get('holdingType', '') == 'Cash' or description == 'Cash'):
                    ticker = 'CASH'
                structured_data.append({
                    'Ticker': ticker,
                    'Name': description,
                    'Shares': holding.get('quantity', 0.0),
                    'Price': holding.get('price', 0.0),
                    'Change': holding.get('change', 0.0),
                    '1 Day %': f"{one_day_pct:.2f}%",
                    '1 day $': holding.get('oneDayValueChange', 0.0),
                    'Value': holding.get('value', 0.0),
                    'Type': holding.get('type', holding.get('holdingType', '')),
                    'Account': holding.get('accountName', ''),
                    'CUSIP': holding.get('cusip', ''),
                    'Cost Basis': holding.get('costBasis', 0.0),
                    'Exchange': holding.get('exchange', ''),
                    'Category': holding.get('type', holding.get('holdingType', ''))  # Using type as category
                })

            return {
                'holdings': structured_data,
                'total_value': total_value,
                'count': len(structured_data)
            }
        else:
            # Provide diagnostic information
            error_msg = "Could not find holdings in JSON structure."
            if 'spData' in data:
                available_keys = list(data['spData'].keys())
                error_msg += f" Found these keys in spData: {', '.join(available_keys)}."
            else:
                error_msg += " 'spData' key not found in JSON."

            return error_msg

    except json.JSONDecodeError as e:
        return f"JSON parsing error: {str(e)}"
    except Exception as e:
        return f"Error processing holdings JSON file: {str(e)}"

def consolidate_holdings(holdings_data):
    """Consolidate holdings with the same ticker/name across multiple accounts"""
    if isinstance(holdings_data, str):
        return holdings_data

    if not isinstance(holdings_data, dict) or 'holdings' not in holdings_data:
        return holdings_data

    holdings = holdings_data['holdings']
    consolidated = {}

    # Group holdings by ticker (or name if ticker is empty)
    for holding in holdings:
        ticker = holding.get('Ticker', '').strip()
        name = holding.get('Name', '').strip()

        # Use ticker as key, or name if ticker is empty
        key = ticker if ticker else name

        # Create a unique key combining ticker and name for better matching
        # (handles cases where ticker might be empty or name variations)
        if not key:
            key = name

        if key not in consolidated:
            # First occurrence - initialize
            consolidated[key] = {
                'Ticker': ticker,
                'Name': name,
                'Shares': holding.get('Shares', 0.0),
                'Price': holding.get('Price', 0.0),
                'Change': holding.get('Change', 0.0),
                '1 Day %': holding.get('1 Day %', '0.00%'),
                '1 day $': holding.get('1 day $', 0.0),
                'Value': holding.get('Value', 0.0),
                'Type': holding.get('Type', ''),
                'Account': holding.get('Account', ''),
                'CUSIP': holding.get('CUSIP', ''),
                'Cost Basis': holding.get('Cost Basis', 0.0),
                'Exchange': holding.get('Exchange', ''),
                'Category': holding.get('Category', ''),
                '_accounts': [holding.get('Account', '')],  # Track all accounts
                '_value_for_price_calc': holding.get('Value', 0.0)  # For weighted avg
            }
        else:
            # Consolidate with existing entry
            existing = consolidated[key]

            # Sum quantities and values
            existing['Shares'] += holding.get('Shares', 0.0)
            existing['Value'] += holding.get('Value', 0.0)
            existing['1 day $'] += holding.get('1 day $', 0.0)
            existing['Cost Basis'] += holding.get('Cost Basis', 0.0)

            # Track value for weighted average price calculation
            existing['_value_for_price_calc'] += holding.get('Value', 0.0)

            # Collect accounts
            account = holding.get('Account', '')
            if account and account not in existing['_accounts']:
                existing['_accounts'].append(account)

    # Post-process consolidated holdings
    consolidated_list = []
    for key, holding in consolidated.items():
        # Calculate weighted average price (total value / total shares)
        if holding['Shares'] > 0:
            holding['Price'] = holding['Value'] / holding['Shares']

        # Calculate percentage change if we have the day $ and value
        if holding['Value'] != 0:
            day_pct = (holding['1 day $'] / (holding['Value'] - holding['1 day $'])) * 100
            holding['1 Day %'] = f"{day_pct:.2f}%"

        # Set account to "Multiple Accounts" if consolidated from multiple
        if len(holding['_accounts']) > 1:
            holding['Account'] = f"Multiple Accounts ({len(holding['_accounts'])})"
        elif len(holding['_accounts']) == 1:
            holding['Account'] = holding['_accounts'][0]

        # Remove temporary fields
        del holding['_accounts']
        del holding['_value_for_price_calc']

        consolidated_list.append(holding)

    return {
        'holdings': consolidated_list,
        'total_value': holdings_data.get('total_value', 0.0),
        'count': len(consolidated_list),
        'original_count': len(holdings)
    }

def save_holdings_json_to_csv(holdings_data, csv_path):
    """Save holdings data from JSON to CSV file"""
    try:
        if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
            df = pd.DataFrame(holdings_data['holdings'])
            # Drop real-time-only columns from the saved CSV
            df = df.drop(columns=[c for c in ["Change", "1 Day %", "1 day $"] if c in df.columns])
            # Sort by Value in descending order
            df = df.sort_values(by='Value', ascending=False)
            # Reorder columns to put Name before Ticker
            cols = df.columns.tolist()
            if 'Name' in cols and 'Ticker' in cols:
                # Move Name to the first position and Ticker to second
                cols.remove('Name')
                cols.remove('Ticker')
                cols = ['Name', 'Ticker'] + cols
                df = df[cols]
            df.to_csv(csv_path, index=False)
            return True
        else:
            print(f"Error: Invalid holdings data format")
            return False
    except Exception as e:
        print(f"Error saving holdings to CSV: {str(e)}")
        return False

def format_holdings_json_as_text(holdings_data):
    """Format holdings data from JSON as human-readable text"""
    if isinstance(holdings_data, str):
        return holdings_data

    if not isinstance(holdings_data, dict) or 'holdings' not in holdings_data:
        return "No holdings data available"

    holdings = holdings_data['holdings']
    total_value = holdings_data.get('total_value', 0.0)
    count = holdings_data.get('count', len(holdings))

    text = "PORTFOLIO HOLDINGS\n"
    text += "==================\n\n"
    text += f"Total Holdings: {count}\n"
    text += f"Total Portfolio Value: ${total_value:,.2f}\n\n"

    text += "HOLDINGS DETAIL:\n"
    text += "-" * 120 + "\n"
    text += f"{'Ticker':<10} {'Name':<35} {'Shares':<12} {'Price':<12} {'Value':<15} {'1 Day %':<10} {'Type':<10}\n"
    text += "-" * 120 + "\n"

    # Sort by value descending
    sorted_holdings = sorted(holdings, key=lambda x: x.get('Value', 0), reverse=True)

    for holding in sorted_holdings:
        ticker = holding.get('Ticker', '')[:9]
        name = holding.get('Name', '')[:34]
        shares = holding.get('Shares', 0)
        price = holding.get('Price', 0)
        value = holding.get('Value', 0)
        day_pct = holding.get('1 Day %', '0.00%')
        htype = holding.get('Type', '')[:9]

        text += f"{ticker:<10} {name:<35} {shares:<12.2f} ${price:<11.2f} ${value:<14,.2f} {day_pct:<10} {htype:<10}\n"

    return text

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

def create_networth_timeline_chart(df):
    """Create an interactive area chart for net worth timeline data similar to Empower's interface"""
    try:
        # Ensure we have the required columns
        if 'Date' not in df.columns or 'Balance' not in df.columns:
            return None

        # Convert date to datetime and sort by date
        df_chart = df.copy()
        df_chart['Date'] = pd.to_datetime(df_chart['Date'])
        df_chart = df_chart.sort_values('Date')

        # Handle balance formatting (remove $ and commas if present)
        if df_chart['Balance'].dtype == 'object':
            df_chart['Balance_numeric'] = df_chart['Balance'].replace(r'[\$,]', '', regex=True).astype(float)
        else:
            df_chart['Balance_numeric'] = df_chart['Balance']

        # Calculate statistics
        current_value = df_chart['Balance_numeric'].iloc[-1]
        start_value = df_chart['Balance_numeric'].iloc[0]
        total_change = current_value - start_value
        total_change_pct = (total_change / start_value * 100) if start_value != 0 else 0
        date_range_days = (df_chart['Date'].max() - df_chart['Date'].min()).days

        # Get one day change if available
        one_day_change = df_chart['One Day Change'].iloc[-1] if 'One Day Change' in df_chart.columns else 0

        # Create the area chart with styling similar to the Empower UI
        fig = go.Figure()

        # Add the main net worth area trace with blue fill
        fig.add_trace(go.Scatter(
            x=df_chart['Date'],
            y=df_chart['Balance_numeric'],
            mode='lines',
            name='Net Worth',
            fill='tozeroy',
            line=dict(color='#0066CC', width=1.5),
            fillcolor='rgba(0, 102, 204, 0.4)',
            hovertemplate='<b>%{x|%b %d, %Y}</b><br>Net Worth: $%{y:,.2f}<extra></extra>'
        ))

        # Add horizontal reference lines at key levels
        min_val = df_chart['Balance_numeric'].min()
        max_val = df_chart['Balance_numeric'].max()

        # Add dotted horizontal gridlines
        for y_val in np.linspace(min_val, max_val, 5):
            fig.add_hline(
                y=y_val,
                line_dash="dot",
                line_color="rgba(150, 150, 150, 0.3)",
                line_width=1
            )

        # Update layout with styling similar to Empower
        fig.update_layout(
            title=dict(
                text=(f'<b>Net Worth</b><br>'
                      f'<span style="font-size:11px;">ALL ACCOUNTS: <b>${current_value:,.2f}</b> | '
                      f'{date_range_days} days: <span style="color:{"green" if total_change >= 0 else "red"}">+${total_change:,.0f}</span> | '
                      f'1-day change: <span style="color:{"green" if one_day_change >= 0 else "red"}">+${one_day_change:,.0f}</span></span>'),
                x=0.01,
                xanchor='left',
                font=dict(size=16, color='black')
            ),
            xaxis=dict(
                title='',
                showgrid=False,
                zeroline=False,
                tickformat='%m/%d/%Y',
                tickangle=-45,
                tickfont=dict(color='black', size=12),
                linecolor='black'
            ),
            yaxis=dict(
                title='',
                showgrid=False,
                zeroline=False,
                tickformat='$,.1s',
                side='right',
                ticksuffix='M' if current_value > 1000000 else '',
                tickfont=dict(color='black', size=12),
                linecolor='black'
            ),
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=500,
            margin=dict(l=20, r=60, t=80, b=80),
            showlegend=False,
            font=dict(color='black')
        )

        return fig
    except Exception as e:
        st.error(f"Error creating timeline chart: {str(e)}")
        return None

def create_networth_category_timeline_chart(df):
    """Create stacked area chart showing net worth breakdown by category over time"""
    try:
        # Check if we have the required category columns
        category_columns = ['Total Cash', 'Total Investment', 'Total Credit', 'Total Loan', 'Total Mortgage', 'Total Other Assets']
        available_categories = [col for col in category_columns if col in df.columns]

        if 'Date' not in df.columns or not available_categories:
            return None

        # Prepare data
        df_chart = df.copy()
        df_chart['Date'] = pd.to_datetime(df_chart['Date'])
        df_chart = df_chart.sort_values('Date')

        # Convert numeric columns
        for col in available_categories:
            if df_chart[col].dtype == 'object':
                df_chart[col] = df_chart[col].replace(r'[\$,]', '', regex=True).astype(float)

        # Create figure with stacked area traces
        fig = go.Figure()

        # Define colors for each category
        colors = {
            'Total Cash': '#2ecc71',
            'Total Investment': '#3498db',
            'Total Credit': '#e74c3c',
            'Total Loan': '#e67e22',
            'Total Mortgage': '#95a5a6',
            'Total Other Assets': '#9b59b6'
        }

        # Add asset categories (positive values)
        asset_categories = ['Total Cash', 'Total Investment', 'Total Other Assets']
        for category in asset_categories:
            if category in available_categories:
                fig.add_trace(go.Scatter(
                    x=df_chart['Date'],
                    y=df_chart[category],
                    mode='lines',
                    name=category.replace('Total ', ''),
                    stackgroup='assets',
                    line=dict(width=0.5, color=colors.get(category, '#999')),
                    fillcolor=colors.get(category, '#999'),
                    hovertemplate='<b>%{fullData.name}</b><br>$%{y:,.2f}<extra></extra>'
                ))

        # Update layout
        fig.update_layout(
            title=dict(
                text='Net Worth Breakdown Over Time',
                font=dict(color='black', size=16)
            ),
            xaxis=dict(
                title=dict(text='Date', font=dict(color='black', size=12)),
                showgrid=True,
                gridcolor='rgba(200, 200, 200, 0.2)',
                tickfont=dict(color='black', size=11),
                linecolor='black'
            ),
            yaxis=dict(
                title=dict(text='Amount ($)', font=dict(color='black', size=12)),
                showgrid=True,
                gridcolor='rgba(200, 200, 200, 0.2)',
                tickformat='$,.0f',
                tickfont=dict(color='black', size=11),
                linecolor='black'
            ),
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=400,
            margin=dict(l=60, r=40, t=60, b=60),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.3,
                xanchor='center',
                x=0.5,
                font=dict(color='black', size=11)
            ),
            font=dict(color='black')
        )

        return fig
    except Exception as e:
        st.error(f"Error creating category timeline chart: {str(e)}")
        return None

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
        1. Upload your Empower file:
           - **JSON** (easiest): use the **Site JSON Capture Exporter** Chrome extension
             — navigate to the Empower page, click the extension, hit **Download**
             - `Empower - holdings_getHoldings_*.json` – portfolio holdings
             - `Empower - networth_getHistories_*.json` – net worth history
             - `Empower - transactions_getUserTransactions_*.json` – transactions
           - **Webarchive / MHTML**: save the Empower page directly from your browser
        2. Click **Process File** and view the results
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
    """Determine if a file contains portfolio or net worth data based on filename and content"""
    filename = os.path.basename(file_path).lower()
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    # For JSON files, check filename and content
    if extension == '.json':
        # Check filename for hints
        if 'holdings' in filename or 'getholdings' in filename or 'portfolio' in filename:
            return 'portfolio'
        elif 'networth' in filename or 'net_worth' in filename:
            return 'net_worth'
        elif 'transaction' in filename:
            return 'transactions'

        # If unclear from filename, peek at the JSON structure
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'spData' in data:
                spdata_keys = data['spData'].keys()
                if 'holdings' in spdata_keys:
                    return 'portfolio'
                elif 'networthHistories' in spdata_keys:
                    return 'net_worth'
                elif 'transactions' in spdata_keys:
                    return 'transactions'
        except:
            pass  # If we can't read it, fall through to default logic

        # Default for JSON is net worth for backward compatibility
        return 'net_worth'
    elif 'net worth' in filename or 'net_worth' in filename:
        return 'net_worth'
    elif 'portfolio' in filename or 'holdings' in filename:
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
            elif file_type == 'mhtml':
                holdings_data = extract_portfolio_holdings_mht(extracted_text)
            elif file_type == 'json':
                holdings_data = process_holdings_json(file_path)
                # Consolidate holdings with the same ticker/name
                if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
                    holdings_data = consolidate_holdings(holdings_data)

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
                elif file_type == 'mhtml':
                    save_holdings_to_csv_mht(holdings_data, csv_path)
                elif file_type == 'json':
                    save_holdings_json_to_csv(holdings_data, csv_path)

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
            elif file_type == 'mhtml':
                formatted_text = format_holdings_as_text_mht(holdings_data)
            elif file_type == 'json':
                formatted_text = format_holdings_json_as_text(holdings_data)

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


def normalize_realtime_quote_symbol(ticker, name=""):
    """Map CSV ticker values to quote provider symbols."""
    symbol = str(ticker or "").strip().upper()
    holding_name = str(name or "").strip().lower()

    if holding_name == "cash" or symbol in {"", "CASH", "CASH$"}:
        return None

    if symbol.endswith(".COIN"):
        base_symbol = symbol.split(".", 1)[0]
        return f"{base_symbol}-USD"

    return symbol


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_performance_metrics(symbols):
    """Fetch YTD, 1-Year, 3-Yr Ann, 5-Yr Ann, 10-Yr Ann returns for a tuple of symbols."""
    import datetime as _dt
    metrics = {}
    sym_list = [s for s in dict.fromkeys(symbols) if s]
    if not sym_list:
        return metrics

    today = _dt.date.today()

    def _ann_return(series, years):
        """Annualised return over `years` years using first/last close."""
        cutoff = today - _dt.timedelta(days=int(years * 365.25))
        sub = series[series.index.date >= cutoff]
        if len(sub) < 2:
            return None
        start, end = float(sub.iloc[0]), float(sub.iloc[-1])
        if start <= 0:
            return None
        total = end / start
        return (total ** (1 / years) - 1) * 100

    def _ytd_return(series):
        jan1 = _dt.date(today.year, 1, 1)
        sub = series[series.index.date >= jan1]
        if len(sub) < 1:
            # Fall back to first available price this year
            sub = series
        if len(sub) < 2:
            return None
        start, end = float(sub.iloc[0]), float(sub.iloc[-1])
        if start <= 0:
            return None
        return (end / start - 1) * 100

    try:
        raw = yf.download(
            sym_list,
            period="10y",
            interval="1mo",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        close = raw["Close"] if "Close" in raw else raw

        if hasattr(close, "columns"):
            col_iter = [(sym, close[sym].dropna()) for sym in close.columns]
        else:
            col_iter = [(sym_list[0], close.dropna())]

        for sym, series in col_iter:
            if series.empty:
                continue
            metrics[sym] = {
                "ytd":    _ytd_return(series),
                "1y":     _ann_return(series, 1),
                "3y":     _ann_return(series, 3),
                "5y":     _ann_return(series, 5),
                "10y":    _ann_return(series, 10),
            }
    except Exception:
        pass

    return metrics


@st.cache_data(ttl=60, show_spinner=False)
def fetch_realtime_quotes(symbols):
    """Fetch real-time quotes for a list of symbols using yfinance."""
    quote_data = {}
    unique_symbols = [symbol for symbol in dict.fromkeys(symbols) if symbol]

    if not unique_symbols:
        return quote_data

    try:
        # Batch download last 2 days so we always have a previous-close for change calculation
        raw = yf.download(
            unique_symbols,
            period="2d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        close = raw["Close"] if "Close" in raw else raw

        # Normalise to a dict: symbol -> latest close
        if hasattr(close, "columns"):  # multi-symbol DataFrame
            for sym in close.columns:
                series = close[sym].dropna()
                if len(series) >= 1:
                    price = float(series.iloc[-1])
                    prev  = float(series.iloc[-2]) if len(series) >= 2 else price
                    change = price - prev
                    change_pct = (change / prev * 100) if prev else 0.0
                    quote_data[sym] = {
                        "price": price,
                        "change": change,
                        "change_percent": change_pct,
                    }
        else:  # single-symbol Series
            sym = unique_symbols[0]
            series = close.dropna()
            if len(series) >= 1:
                price = float(series.iloc[-1])
                prev  = float(series.iloc[-2]) if len(series) >= 2 else price
                change = price - prev
                change_pct = (change / prev * 100) if prev else 0.0
                quote_data[sym] = {
                    "price": price,
                    "change": change,
                    "change_percent": change_pct,
                }
    except Exception:
        pass  # Return whatever was collected; caller handles missing symbols

    return quote_data


def build_realtime_holdings_dataframe(csv_path):
    """Load a holdings CSV and update price-related columns with live quotes."""
    df = read_csv_to_dataframe(csv_path)
    if df is None or df.empty:
        return None, {"updated_rows": 0, "quoted_symbols": 0, "missing_symbols": []}

    original_columns = df.columns.tolist()

    # Ensure real-time columns always exist (may be absent from saved CSV)
    for _rt_col in ["Change", "1 day $"]:
        if _rt_col not in df.columns:
            df[_rt_col] = np.nan
    if "1 Day %" not in df.columns:
        df["1 Day %"] = ""  # string column, not float

    for column in ["Shares", "Price", "Change", "1 day $", "Value", "Cost Basis"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    requested_symbols = []
    row_quote_symbols = {}
    for row_index, row in df.iterrows():
        quote_symbol = normalize_realtime_quote_symbol(row.get("Ticker", ""), row.get("Name", ""))
        row_quote_symbols[row_index] = quote_symbol
        if quote_symbol:
            requested_symbols.append(quote_symbol)

    quotes = fetch_realtime_quotes(tuple(requested_symbols))
    updated_rows = 0
    missing_symbols = []

    for row_index, quote_symbol in row_quote_symbols.items():
        if not quote_symbol:
            continue

        quote = quotes.get(quote_symbol)
        if not quote:
            missing_symbols.append(str(df.at[row_index, "Ticker"]))
            continue

        shares = pd.to_numeric(df.at[row_index, "Shares"], errors="coerce") if "Shares" in df.columns else np.nan

        if "Price" in df.columns:
            df.at[row_index, "Price"] = quote["price"]
        if "Change" in df.columns:
            df.at[row_index, "Change"] = quote["change"]
        if "1 Day %" in df.columns:
            df.at[row_index, "1 Day %"] = f"{quote['change_percent']:.2f}%"
        if "1 day $" in df.columns and not pd.isna(shares):
            df.at[row_index, "1 day $"] = shares * quote["change"]
        if "Value" in df.columns and not pd.isna(shares):
            df.at[row_index, "Value"] = shares * quote["price"]

        updated_rows += 1

    if "Value" in df.columns:
        df = df.sort_values(by="Value", ascending=False, na_position="last")

    display_columns = [column for column in original_columns if column in df.columns]
    # Append real-time columns that were injected but not in the original CSV
    for _rt_col in ["Change", "1 Day %", "1 day $"]:
        if _rt_col not in display_columns and _rt_col in df.columns:
            display_columns.append(_rt_col)
    return df[display_columns], {
        "updated_rows": updated_rows,
        "quoted_symbols": len(quotes),
        "missing_symbols": sorted(set(symbol for symbol in missing_symbols if symbol and symbol != "nan")),
    }


def build_performance_excel(perf_df):
    """Build and return a formatted Excel workbook as BytesIO for the performance report."""
    import io as _io
    buf = _io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        perf_df.to_excel(writer, index=False, sheet_name="Portfolio Performance")
        wb = writer.book
        ws = writer.sheets["Portfolio Performance"]
        nrows = len(perf_df)

        hdr_fmt = wb.add_format({
            "bold": True, "bg_color": "#1A1A2E", "font_color": "#E0E0E0",
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
        })
        base = {"valign": "vcenter", "border": 1}
        even_base = {**base, "bg_color": "#F0F4FA"}
        odd_base  = {**base, "bg_color": "#FFFFFF"}
        money_even = wb.add_format({**even_base, "num_format": "$#,##0.00"})
        money_odd  = wb.add_format({**odd_base,  "num_format": "$#,##0.00"})
        pct_even = wb.add_format({**even_base, "num_format": "0.00%"})
        pct_odd  = wb.add_format({**odd_base,  "num_format": "0.00%"})
        num_even = wb.add_format({**even_base, "num_format": "#,##0.000"})
        num_odd  = wb.add_format({**odd_base,  "num_format": "#,##0.000"})
        text_even = wb.add_format({**even_base})
        text_odd  = wb.add_format({**odd_base})

        COLS = list(perf_df.columns)
        col_widths = {
            "Symbol": 10, "Name": 34, "Shares": 10, "Price": 12, "Value": 14,
            "Weight %": 9, "Day Chg $": 12, "Day Chg %": 10,
            "YTD %": 9, "1-Year %": 9, "3-Yr Ann %": 10, "5-Yr Ann %": 10, "10-Yr Ann %": 11,
        }
        PCT_COLS   = {"Weight %", "Day Chg %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"}
        MONEY_COLS = {"Price", "Value", "Day Chg $"}
        PERF_COLS  = {"Day Chg %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"}

        for ci, cname in enumerate(COLS):
            ws.write(0, ci, cname, hdr_fmt)
            ws.set_column(ci, ci, col_widths.get(cname, 12))

        for ri, (_, drow) in enumerate(perf_df.iterrows()):
            excel_row = ri + 1
            is_even = (ri % 2 == 0)
            for ci, cname in enumerate(COLS):
                val = drow[cname]
                is_none = val is None or (isinstance(val, float) and np.isnan(val))
                if is_none:
                    ws.write(excel_row, ci, "N/A", text_even if is_even else text_odd)
                    continue
                if cname in PCT_COLS:
                    ws.write_number(excel_row, ci, val / 100.0, pct_even if is_even else pct_odd)
                elif cname in MONEY_COLS:
                    ws.write_number(excel_row, ci, float(val), money_even if is_even else money_odd)
                elif cname == "Shares":
                    ws.write_number(excel_row, ci, float(val), num_even if is_even else num_odd)
                else:
                    ws.write(excel_row, ci, val, text_even if is_even else text_odd)

        for cname in PERF_COLS:
            ci = COLS.index(cname)
            cl = chr(ord('A') + ci)
            rng = f"{cl}2:{cl}{nrows + 1}"
            # Use formula-type so text cells ("N/A") are never matched
            ws.conditional_format(rng, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2<0)",
                "format": wb.add_format({"bg_color": "#FADBD8", "font_color": "#C0392B", "bold": True, "num_format": "0.00%", "border": 1})})
            ws.conditional_format(rng, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2>0)",
                "format": wb.add_format({"bg_color": "#D5F5E3", "font_color": "#1E8449", "bold": True, "num_format": "0.00%", "border": 1})})

        ci_day = COLS.index("Day Chg $")
        cl = chr(ord('A') + ci_day)
        rng_day = f"{cl}2:{cl}{nrows+1}"
        ws.conditional_format(rng_day, {"type": "formula",
            "criteria": f"AND(ISNUMBER({cl}2),{cl}2<0)",
            "format": wb.add_format({"bg_color": "#FADBD8", "font_color": "#C0392B", "bold": True, "num_format": "$#,##0.00", "border": 1})})
        ws.conditional_format(rng_day, {"type": "formula",
            "criteria": f"AND(ISNUMBER({cl}2),{cl}2>0)",
            "format": wb.add_format({"bg_color": "#D5F5E3", "font_color": "#1E8449", "bold": True, "num_format": "$#,##0.00", "border": 1})})

        ws.freeze_panes(1, 0)
        ws.set_row(0, 28)
        ws.set_zoom(110)
    buf.seek(0)
    return buf


def render_performance_report_dashboard(report_file):
    """Render the portfolio performance report in-page from a saved JSON file."""
    import datetime as _dt3

    st.title("📊 Portfolio Performance Report")
    st.caption(f"Generated: {_dt3.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Source: {os.path.basename(report_file)}")

    if not os.path.exists(report_file):
        st.error("Report data file not found. Please regenerate the report from the main page.")
        return

    perf_df = pd.read_json(report_file, orient="records")
    if perf_df.empty:
        st.warning("Report contains no data.")
        return

    PCT_COLS  = ["YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"]
    PERF_COLS = PCT_COLS  # same set for colour styling

    # ── Summary metrics ──────────────────────────────────────────────────────
    total_value = pd.to_numeric(perf_df["Value"], errors="coerce").fillna(0).sum()
    day_chg_total = pd.to_numeric(perf_df["Day Chg $"], errors="coerce").fillna(0).sum()
    n_positive = sum(1 for v in pd.to_numeric(perf_df.get("YTD %", []), errors="coerce") if v and v > 0)
    n_negative = sum(1 for v in pd.to_numeric(perf_df.get("YTD %", []), errors="coerce") if v and v < 0)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Portfolio Value", f"${total_value:,.2f}")
    sc2.metric("Today's Change", f"${day_chg_total:,.2f}", delta=f"${day_chg_total:,.2f}")
    sc3.metric("YTD Positive", f"{n_positive} symbols")
    sc4.metric("YTD Negative", f"{n_negative} symbols")

    st.divider()

    # ── Performance Highlights ───────────────────────────────────────────────
    _hl_df = perf_df.copy()
    for _c in PCT_COLS + ["Day Chg %"]:
        if _c in _hl_df.columns:
            _hl_df[_c] = pd.to_numeric(_hl_df[_c], errors="coerce")

    _id_cols = [c for c in ["Symbol", "Name"] if c in _hl_df.columns]

    def _hl_table(subset_df, pct_col):
        """Return a display-ready copy of subset_df with colour-formatted pct_col."""
        _disp = subset_df[_id_cols + [pct_col]].copy().reset_index(drop=True)
        _raw  = pd.to_numeric(_disp[pct_col], errors="coerce")
        _disp[pct_col] = _raw.map(lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A")

        def _clr(val):
            try:
                v = float(str(val).replace("%", "").replace("+", ""))
                if v > 0:
                    return "background-color:#D5F5E3;color:#1E8449;font-weight:bold"
                if v < 0:
                    return "background-color:#FADBD8;color:#C0392B;font-weight:bold"
            except (TypeError, ValueError):
                pass
            return ""

        return _disp.style.map(_clr, subset=[pct_col])

    st.subheader("Performance Highlights")

    # Best / Worst performers – YTD
    if "YTD %" in _hl_df.columns:
        _ytd_valid = _hl_df.dropna(subset=["YTD %"])
        _best_ytd  = _ytd_valid.nlargest(5, "YTD %")
        _worst_ytd = _ytd_valid.nsmallest(5, "YTD %")

        _col_b, _col_w = st.columns(2)
        with _col_b:
            st.markdown("**Top 5 – YTD Return**")
            st.dataframe(_hl_table(_best_ytd, "YTD %"), hide_index=True, use_container_width=True)
        with _col_w:
            st.markdown("**Bottom 5 – YTD Return**")
            st.dataframe(_hl_table(_worst_ytd, "YTD %"), hide_index=True, use_container_width=True)

    # Best / Worst performers – 1-Year
    if "1-Year %" in _hl_df.columns:
        _1y_valid  = _hl_df.dropna(subset=["1-Year %"])
        _best_1y   = _1y_valid.nlargest(5, "1-Year %")
        _worst_1y  = _1y_valid.nsmallest(5, "1-Year %")

        _col_b2, _col_w2 = st.columns(2)
        with _col_b2:
            st.markdown("**Top 5 – 1-Year Return**")
            st.dataframe(_hl_table(_best_1y, "1-Year %"), hide_index=True, use_container_width=True)
        with _col_w2:
            st.markdown("**Bottom 5 – 1-Year Return**")
            st.dataframe(_hl_table(_worst_1y, "1-Year %"), hide_index=True, use_container_width=True)

    # Momentum – composite score weighted toward recent periods
    # Score = 0.40 * YTD% + 0.35 * 1-Year% + 0.15 * 3-Yr Ann% + 0.10 * 5-Yr Ann%
    _mom_weights = [("YTD %", 0.40), ("1-Year %", 0.35), ("3-Yr Ann %", 0.15), ("5-Yr Ann %", 0.10)]
    _avail_mom   = [(c, w) for c, w in _mom_weights if c in _hl_df.columns]
    if len(_avail_mom) >= 2:
        _mom_df = _hl_df.copy()
        _weight_sum = sum(w for _, w in _avail_mom)
        _mom_df["Momentum Score"] = sum(
            pd.to_numeric(_mom_df[c], errors="coerce").fillna(0) * w
            for c, w in _avail_mom
        ) / _weight_sum
        _mom_valid = _mom_df.dropna(subset=["Momentum Score"])
        _mom_top   = _mom_valid.nlargest(5, "Momentum Score")
        _mom_bot   = _mom_valid.nsmallest(5, "Momentum Score")
        _mom_display_cols = _id_cols + [c for c, _ in _avail_mom] + ["Momentum Score"]

        def _fmt_mom_df(subset):
            _d = subset[_mom_display_cols].reset_index(drop=True).copy()
            for _mc in [c for c, _ in _avail_mom]:
                _d[_mc] = pd.to_numeric(_d[_mc], errors="coerce").map(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
                )
            _d["Momentum Score"] = pd.to_numeric(_d["Momentum Score"], errors="coerce").map(
                lambda x: f"{x:+.2f}" if pd.notna(x) else "N/A"
            )
            return _d

        def _mom_clr(val):
            try:
                v = float(str(val).replace("+", ""))
                if v > 0:
                    return "background-color:#D5F5E3;color:#1E8449;font-weight:bold"
                if v < 0:
                    return "background-color:#FADBD8;color:#C0392B;font-weight:bold"
            except (TypeError, ValueError):
                pass
            return ""

        _mom_label = "*(weighted: 40% YTD · 35% 1-Year · 15% 3-Year · 10% 5-Year)*"
        _mom_col_t, _mom_col_b = st.columns(2)
        with _mom_col_t:
            st.markdown(f"**Top 5 – Momentum** {_mom_label}")
            st.dataframe(_fmt_mom_df(_mom_top).style.map(_mom_clr, subset=["Momentum Score"]), hide_index=True, use_container_width=True)
        with _mom_col_b:
            st.markdown(f"**Bottom 5 – Momentum** {_mom_label}")
            st.dataframe(_fmt_mom_df(_mom_bot).style.map(_mom_clr, subset=["Momentum Score"]), hide_index=True, use_container_width=True)

    st.divider()

    # ── Styled table ─────────────────────────────────────────────────────────
    def _colour_pct(val):
        try:
            v = float(val)
            if v < 0:
                return "background-color: #FADBD8; color: #C0392B; font-weight: bold"
            elif v > 0:
                return "background-color: #D5F5E3; color: #1E8449; font-weight: bold"
        except (TypeError, ValueError):
            pass
        return ""

    def _colour_dollar(val):
        try:
            v = float(val)
            if v < 0:
                return "color: #C0392B; font-weight: bold"
            elif v > 0:
                return "color: #1E8449; font-weight: bold"
        except (TypeError, ValueError):
            pass
        return ""

    # Build display copy with formatted strings for non-numeric presentation
    disp = perf_df.copy()
    for c in ["Price", "Value"]:
        if c in disp.columns:
            disp[c] = pd.to_numeric(disp[c], errors="coerce").map(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
    if "Day Chg $" in disp.columns:
        disp["Day Chg $"] = pd.to_numeric(disp["Day Chg $"], errors="coerce").map(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
    if "Day Chg %" in disp.columns:
        disp["Day Chg %"] = pd.to_numeric(disp["Day Chg %"], errors="coerce").map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    if "Shares" in disp.columns:
        disp["Shares"] = pd.to_numeric(disp["Shares"], errors="coerce").map(lambda x: f"{x:,.3f}" if pd.notna(x) else "N/A")
    if "Weight %" in disp.columns:
        disp["Weight %"] = pd.to_numeric(disp["Weight %"], errors="coerce").map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    for c in PERF_COLS:
        if c in disp.columns:
            disp[c] = pd.to_numeric(disp[c], errors="coerce").map(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")

    style = disp.style
    for c in PERF_COLS:
        if c in disp.columns:
            style = style.map(_colour_pct, subset=[c])
    if "Day Chg $" in disp.columns:
        style = style.map(_colour_dollar, subset=["Day Chg $"])
    if "Day Chg %" in disp.columns:
        style = style.map(_colour_pct, subset=["Day Chg %"])

    st.dataframe(style, hide_index=True, use_container_width=True)

    st.divider()

    # ── Excel download ────────────────────────────────────────────────────────
    excel_buf = build_performance_excel(perf_df)
    fname = f"portfolio_performance_{_dt3.date.today().isoformat()}.xlsx"
    st.download_button(
        label="⬇️ Download Excel Report",
        data=excel_buf,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="perf_report_excel_dl",
    )


def render_portfolio_analysis(df, is_realtime=False):
    """Render the full portfolio analysis (table, statistics, charts) for a given holdings DataFrame."""
    btn_key_suffix = "_rt" if is_realtime else ""

    st.header("Portfolio Holdings")
    REALTIME_ONLY_COLS = ["Change", "1 Day %", "1 day $"]
    currency_cols = {
        col: st.column_config.NumberColumn(col, format="$%,.2f")
        for col in ["Price", "Change", "1 day $", "Value", "Cost Basis"]
        if col in df.columns
    }
    if is_realtime:
        display_df = df
    else:
        display_df = df.drop(columns=[c for c in REALTIME_ONLY_COLS if c in df.columns])
    st.dataframe(display_df, hide_index=True, column_config=currency_cols)

    # --- Performance Report Download ---
    if st.button("Generate Portfolio Performance Report", key=f"perf_report_btn{btn_key_suffix}"):
        with st.spinner("Fetching performance metrics (this may take a moment)..."):
            ticker_col = "Ticker" if "Ticker" in df.columns else None
            name_col = "Name" if "Name" in df.columns else None
            total_val = pd.to_numeric(df["Value"], errors="coerce").fillna(0).sum() if "Value" in df.columns else 0

            sym_map = {}  # row_index -> yahoo_symbol
            for idx, row in df.iterrows():
                t = str(row.get(ticker_col, "") if ticker_col else "").strip()
                n = str(row.get(name_col, "") if name_col else "").strip()
                sym = normalize_realtime_quote_symbol(t, n)
                sym_map[idx] = sym

            unique_syms = tuple(s for s in dict.fromkeys(sym_map.values()) if s)
            quotes = fetch_realtime_quotes(unique_syms)
            perf   = fetch_performance_metrics(unique_syms)

            rows = []
            for idx, row in df.iterrows():
                sym = sym_map.get(idx)
                q = quotes.get(sym, {}) if sym else {}
                p = perf.get(sym, {}) if sym else {}

                price  = q.get("price") or (pd.to_numeric(row.get("Price", None), errors="coerce") if "Price" in df.columns else None)
                shares = pd.to_numeric(row.get("Shares", None), errors="coerce") if "Shares" in df.columns else None
                value  = (shares * price) if (shares and price) else (pd.to_numeric(row.get("Value", None), errors="coerce") if "Value" in df.columns else None)
                weight = (value / total_val * 100) if (value and total_val) else None
                day_chg = (shares * q["change"]) if (shares and "change" in q) else None
                day_chg_pct = q.get("change_percent") if q else None

                rows.append({
                    "Symbol":    str(row.get(ticker_col, "") if ticker_col else ""),
                    "Name":      str(row.get(name_col, "") if name_col else ""),
                    "Shares":    shares,
                    "Price":     price,
                    "Value":     value,
                    "Weight %":  weight,
                    "Day Chg $": day_chg,
                    "Day Chg %": day_chg_pct,
                    "YTD %":     p.get("ytd"),
                    "1-Year %":  p.get("1y"),
                    "3-Yr Ann %": p.get("3y"),
                    "5-Yr Ann %": p.get("5y"),
                    "10-Yr Ann %": p.get("10y"),
                })

            perf_df = pd.DataFrame(rows)
            # Save report data to a temp JSON in the user dir
            user_dir = ensure_user_dirs()
            import datetime as _dt2
            report_file = os.path.join(user_dir, f"perf_report_{_dt2.date.today().isoformat()}.json")
            perf_df.to_json(report_file, orient="records")

        report_url = f"?report=1&report_file={quote_plus(report_file)}"
        st.markdown(
            f'<a href="{report_url}" target="_blank" style="display:inline-block;padding:8px 16px;'
            f'background:#1A6B3C;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">'
            f'📊 Open Performance Report ↗</a>',
            unsafe_allow_html=True,
        )

    # --- LLM Portfolio Review Button ---
    st.subheader("Portfolio Review by AI")
    stats = calculate_portfolio_statistics(df)
    if st.button("Ask AI for Portfolio Insights", key=f"llm_review_btn{btn_key_suffix}"):
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

    # Portfolio statistics section
    st.header("Portfolio Statistics")
    stats = calculate_portfolio_statistics(df)

    if 'error' in stats:
        st.error(stats['error'])
        st.write("Available columns in the dataframe:", df.columns.tolist())
        if 'traceback' in stats:
            with st.expander("Error details"):
                st.code(stats['traceback'])
    else:
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

            st.subheader("Portfolio Concentration")
            metrics_col3, metrics_col4 = st.columns(2)

            with metrics_col3:
                st.metric(label="Top 5 Holdings", value=f"{stats['top_5_pct']:.2f}%")
                st.metric(label="HHI Score", value=f"{stats['hhi']:.2f}")

            with metrics_col4:
                st.metric(label="Top 10 Holdings", value=f"{stats['top_10_pct']:.2f}%")
                st.metric(label="Concentration", value=stats['concentration'])

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
            top_data = stats['holdings_pct'].head(10)
            others_sum = stats['holdings_pct'].iloc[10:]['pct_of_total'].sum() if len(stats['holdings_pct']) > 10 else 0

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

            st.dataframe(
                display_data[['Name', 'Symbol', 'pct_of_total']].rename(
                    columns={'pct_of_total': '% of Portfolio'}
                ).reset_index(drop=True),
                hide_index=True,
                height=420
            )

        st.header("Portfolio Visualizations")
        tabs = st.tabs(["Holdings Treemap", "Top 10 Bar Chart", "Value Distribution", "Portfolio Concentration"])

        with tabs[0]:
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
            fig_treemap.update_layout(height=600, margin=dict(t=50, l=25, r=25, b=25))
            st.plotly_chart(fig_treemap, width='stretch')
            st.caption("Treemap visualization shows each holding sized by percentage of portfolio with color intensity based on value.")

        with tabs[1]:
            top10_data = stats['holdings_pct'].head(10).copy()
            top10_data = top10_data.sort_values('pct_of_total')
            fig_bar = go.Figure(go.Bar(
                x=top10_data['pct_of_total'],
                y=top10_data['Name'] + " (" + top10_data['Symbol'] + ")",
                orientation='h',
                marker=dict(color=top10_data['pct_of_total'], colorscale='Viridis'),
                text=[f"${v:,.2f}" for v in top10_data['Value_numeric']],
                textposition='auto'
            ))
            fig_bar.update_layout(
                title='Top 10 Holdings by Portfolio Percentage',
                xaxis_title='Percentage of Portfolio',
                yaxis_title='Holdings',
                height=500,
                margin=dict(l=250, r=50)
            )
            st.plotly_chart(fig_bar, width='stretch')

        with tabs[2]:
            q1 = np.percentile(df['Value_numeric'], 25)
            q3 = np.percentile(df['Value_numeric'], 75)
            iqr = q3 - q1
            upper_bound = q3 + 2.5 * iqr
            filtered_values = df[df['Value_numeric'] <= upper_bound]['Value_numeric']
            fig_hist = px.histogram(
                filtered_values,
                nbins=20,
                title='Distribution of Holding Values',
                labels={'value': 'Holding Value ($)', 'count': 'Number of Holdings'},
                color_discrete_sequence=['lightblue'],
            )
            fig_hist.update_layout(showlegend=False, height=500)
            st.plotly_chart(fig_hist, width='stretch')
            c1, c2, c3 = st.columns(3)
            c1.metric("Mean Value", f"${stats['avg_value']:,.2f}")
            c2.metric("Median Value", f"${stats['median_value']:,.2f}")
            c3.metric("Standard Deviation", f"${stats['std_dev']:,.2f}")
            if upper_bound < stats['max_value']:
                st.info(f"Note: Some holdings with values greater than ${upper_bound:,.2f} were excluded from the histogram for better visualization.")

        with tabs[3]:
            lorenz_data = stats['holdings_pct'].copy().sort_values('Value_numeric')
            lorenz_data['cumulative_pct'] = lorenz_data['Value_numeric'].cumsum() / stats['total_value'] * 100
            lorenz_data['holding_pct'] = 100 * (np.arange(1, len(lorenz_data) + 1) / len(lorenz_data))

            fig_lorenz = go.Figure()
            fig_lorenz.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode='lines', name='Perfect Equality', line=dict(color='black', dash='dash')))
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
            st.plotly_chart(fig_lorenz, width='stretch')
            st.caption("""
            **Interpreting the Lorenz Curve:**
            - The diagonal line represents perfect equality (all holdings have equal value)
            - The curve shows actual distribution of your portfolio
            - The greater the distance between the curve and diagonal, the more concentrated your portfolio
            - A concentrated portfolio may have higher risk due to lack of diversification
            """)

            if len(lorenz_data) > 5:
                x = lorenz_data['holding_pct'].values / 100
                y = lorenz_data['cumulative_pct'].values / 100
                x = np.insert(x, 0, 0)
                y = np.insert(y, 0, 0)
                B = np.trapezoid(y, x)
                gini = 1 - 2 * B
                st.metric("Portfolio Gini Coefficient", f"{gini:.2f}", help="Measures inequality in your portfolio. Values range from 0 (perfect equality) to 1 (perfect inequality).")
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

        if 'asset_allocation' in stats and not stats['asset_allocation'].empty:
            st.header("Asset Allocation")
            asset_data = stats['asset_allocation']
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
            asset_col1, asset_col2 = st.columns(2)
            with asset_col1:
                st.plotly_chart(fig_asset, width='stretch')
            with asset_col2:
                st.plotly_chart(fig_asset_bar, width='stretch')


def render_realtime_holdings_dashboard(csv_path, refresh_seconds):
    """Render a full portfolio analysis dashboard using the CSV with live-refreshed quotes."""
    st.title("Real-Time Holdings Dashboard")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Source: {os.path.basename(csv_path)}  |  Last refreshed: {now}  |  Auto-refreshes every {refresh_seconds}s")

    if not csv_path or not os.path.exists(csv_path):
        st.error("The holdings CSV for the real-time dashboard was not found.")
        return

    with st.spinner("Fetching live quotes..."):
        live_df, quote_meta = build_realtime_holdings_dataframe(csv_path)

    if live_df is None:
        st.error("Unable to load the holdings CSV for the real-time dashboard.")
        return

    # Status banner
    status_col1, status_col2, status_col3 = st.columns(3)
    with status_col1:
        total_value = pd.to_numeric(live_df["Value"], errors="coerce").fillna(0).sum() if "Value" in live_df.columns else 0
        st.metric(label="Live Portfolio Value", value=f"${total_value:,.2f}")
    with status_col2:
        st.metric(label="Symbols with Live Quotes", value=f"{quote_meta['updated_rows']} / {quote_meta['updated_rows'] + len(quote_meta['missing_symbols'])}")
    with status_col3:
        daily_change = pd.to_numeric(live_df.get("1 day $", pd.Series(dtype=float)), errors="coerce").fillna(0).sum() if "1 day $" in live_df.columns else 0
        st.metric(label="Today's Change", value=f"${daily_change:,.2f}")

    if quote_meta["missing_symbols"]:
        st.info("Stale prices (no live quote) for: " + ", ".join(quote_meta["missing_symbols"][:15]))

    # Reorder columns: Name, Ticker first, then the rest
    if "Name" in live_df.columns and "Ticker" in live_df.columns:
        other_cols = [c for c in live_df.columns if c not in ("Name", "Ticker")]
        live_df = live_df[["Name", "Ticker"] + other_cols]

    # --- Top 5 Winners / Losers for the Day ---
    if "1 day $" in live_df.columns:
        _mover_df = live_df.copy()
        _mover_df["_day_dollar"] = pd.to_numeric(_mover_df["1 day $"], errors="coerce")
        _mover_df = _mover_df.dropna(subset=["_day_dollar"])
        if not _mover_df.empty:
            _winners = _mover_df.nlargest(5, "_day_dollar")
            _losers = _mover_df.nsmallest(5, "_day_dollar")
            _display_cols = [c for c in ["Name", "Ticker", "1 Day %", "1 day $"] if c in _mover_df.columns]
            _mover_col_cfg = {}
            if "1 day $" in _display_cols:
                _mover_col_cfg["1 day $"] = st.column_config.NumberColumn("1 day $", format="$%,.2f")

            st.subheader("Today's Top Movers")
            _win_col, _lose_col = st.columns(2)
            with _win_col:
                st.markdown("**Top 5 Winners**")
                st.dataframe(_winners[_display_cols].reset_index(drop=True), hide_index=True, column_config=_mover_col_cfg)
            with _lose_col:
                st.markdown("**Top 5 Losers**")
                st.dataframe(_losers[_display_cols].reset_index(drop=True), hide_index=True, column_config=_mover_col_cfg)

    render_portfolio_analysis(live_df, is_realtime=True)

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
            'Symbol': symbol,
            'Shares': shares
        })

    # Create DataFrame with only Symbol and Shares columns
    ms_df = pd.DataFrame(ms_data, columns=['Symbol', 'Shares'])

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

    # Optional real-time dashboard mode for holdings CSV files:
    # ?realtime=1&csv_file=<url_encoded_path>&refresh=30
    query_params = st.query_params
    realtime_mode = str(query_params.get("realtime", "0")).lower() in {"1", "true", "yes", "on"}
    realtime_csv_file = str(query_params.get("csv_file", "")).strip()
    if realtime_csv_file:
        realtime_csv_file = unquote_plus(realtime_csv_file)

    refresh_raw = str(query_params.get("refresh", "300")).strip()
    try:
        realtime_refresh_seconds = max(5, min(300, int(refresh_raw)))
    except ValueError:
        realtime_refresh_seconds = 30

    if realtime_mode:
        st.caption(f"Real-time mode is active. Dashboard auto-refreshes every {realtime_refresh_seconds} seconds.")
        components.html(
            f"<script>setTimeout(function(){{window.parent.location.reload();}}, {realtime_refresh_seconds * 1000});</script>",
            height=0,
        )

        if realtime_csv_file:
            render_realtime_holdings_dashboard(realtime_csv_file, realtime_refresh_seconds)
            st.sidebar.markdown("---")
            st.sidebar.caption(f"Session ID: {st.session_state.user_id}")
            return

    # ── Performance report mode: ?report=1&report_file=<url_encoded_path> ────
    report_mode = str(query_params.get("report", "0")).lower() in {"1", "true", "yes", "on"}
    report_file_param = unquote_plus(str(query_params.get("report_file", "")).strip())
    if report_mode and report_file_param:
        render_performance_report_dashboard(report_file_param)
        return

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

    # Handle error case first
    if result and not result.get("success", False):
        # Processing failed - display error message
        st.error("❌ Failed to process file")
        if result.get("error"):
            st.error(result["error"])

        # Show raw data if available for debugging
        if result.get("raw_data_path") and os.path.exists(result["raw_data_path"]):
            with st.expander("View Raw Extracted Data (for debugging)"):
                with open(result["raw_data_path"], "r", encoding="utf-8") as f:
                    st.text(f.read()[:5000])  # Show first 5000 characters

        # Show instructions again after error
        st.markdown("---")

    if result and result.get("success", False):
        # Get file type for display
        file_type = result.get("file_type", "unknown")
        file_type_display = "WebArchive" if file_type == 'webarchive' else "MHTML" if file_type == 'mhtml' else "File"

        # --- Ensure df is loaded from CSV or holdings ---
        df = None
        if result.get("csv_path"):
            df = read_csv_to_dataframe(result["csv_path"])
        if df is None and result.get("holdings"):
            # Handle both dict (consolidated) and list formats
            holdings_data = result["holdings"]
            if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
                df = pd.DataFrame(holdings_data['holdings'])
            else:
                df = pd.DataFrame(result["holdings"])

        # Sort DataFrame by Value in descending order if it exists
        if df is not None and 'Value' in df.columns:
            df = df.sort_values(by='Value', ascending=False)

        # Reorder columns to put Name before Ticker
        if df is not None and 'Name' in df.columns and 'Ticker' in df.columns:
            cols = df.columns.tolist()
            cols.remove('Name')
            cols.remove('Ticker')
            cols = ['Name', 'Ticker'] + cols
            df = df[cols]

        # Show consolidation info if available
        if result.get("holdings") and isinstance(result["holdings"], dict):
            original_count = result["holdings"].get("original_count")
            consolidated_count = result["holdings"].get("count")
            if original_count and consolidated_count and original_count > consolidated_count:
                st.info(f"📊 Holdings consolidated: {original_count} entries → {consolidated_count} unique holdings ({original_count - consolidated_count} duplicates merged)")

        # --- DOWNLOAD OPTIONS SECTION (moved to top) ---
        st.header("Download Options")
        col1, col2, col3 = st.columns(3)

        # Provide CSV download
        if result["csv_path"]:
            csv_df = pd.read_csv(result["csv_path"])
            cols_to_drop = [c for c in ["Account", "Type"] if c in csv_df.columns]
            if cols_to_drop:
                csv_df = csv_df.drop(columns=cols_to_drop)
            csv_data = csv_df.to_csv(index=False)

            with col1:
                download_csv = st.download_button(
                    label="Download CSV File",
                    data=csv_data,
                    file_name=os.path.basename(result["csv_path"]),
                    mime="text/csv",
                    key="download_csv"
                )

        # Formatted text file download
        if result["text_path"]:
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
                    # Add account type filter tabs similar to Empower
                    account_tabs = st.tabs(["All", "Cash", "Investment", "Credit", "Loan", "Mortgage", "Other"])

                    with account_tabs[0]:  # All
                        # Create and display the timeline visualization
                        timeline_chart = create_networth_timeline_chart(df)
                        if timeline_chart:
                            st.plotly_chart(timeline_chart, width='stretch')

                    with account_tabs[1]:  # Cash
                        if 'Total Cash' in df.columns:
                            df_cash = df.copy()
                            df_cash['Balance'] = df_cash['Total Cash']
                            chart_cash = create_networth_timeline_chart(df_cash)
                            if chart_cash:
                                chart_cash.update_layout(title=dict(text='<b>Cash Accounts</b>'))
                                st.plotly_chart(chart_cash, width='stretch')

                    with account_tabs[2]:  # Investment
                        if 'Total Investment' in df.columns:
                            df_inv = df.copy()
                            df_inv['Balance'] = df_inv['Total Investment']
                            chart_inv = create_networth_timeline_chart(df_inv)
                            if chart_inv:
                                chart_inv.update_layout(title=dict(text='<b>Investment Accounts</b>'))
                                st.plotly_chart(chart_inv, width='stretch')

                    with account_tabs[3]:  # Credit
                        if 'Total Credit' in df.columns:
                            df_credit = df.copy()
                            df_credit['Balance'] = df_credit['Total Credit'] * -1  # Show as positive for display
                            chart_credit = create_networth_timeline_chart(df_credit)
                            if chart_credit:
                                chart_credit.update_layout(title=dict(text='<b>Credit Accounts</b>'))
                                st.plotly_chart(chart_credit, width='stretch')

                    with account_tabs[4]:  # Loan
                        if 'Total Loan' in df.columns:
                            df_loan = df.copy()
                            df_loan['Balance'] = df_loan['Total Loan'] * -1  # Show as positive for display
                            chart_loan = create_networth_timeline_chart(df_loan)
                            if chart_loan:
                                chart_loan.update_layout(title=dict(text='<b>Loan Accounts</b>'))
                                st.plotly_chart(chart_loan, width='stretch')

                    with account_tabs[5]:  # Mortgage
                        if 'Total Mortgage' in df.columns:
                            df_mortgage = df.copy()
                            df_mortgage['Balance'] = df_mortgage['Total Mortgage'] * -1  # Show as positive for display
                            chart_mortgage = create_networth_timeline_chart(df_mortgage)
                            if chart_mortgage:
                                chart_mortgage.update_layout(title=dict(text='<b>Mortgage Accounts</b>'))
                                st.plotly_chart(chart_mortgage, width='stretch')

                    with account_tabs[6]:  # Other
                        if 'Total Other Assets' in df.columns:
                            df_other = df.copy()
                            df_other['Balance'] = df_other['Total Other Assets']
                            chart_other = create_networth_timeline_chart(df_other)
                            if chart_other:
                                chart_other.update_layout(title=dict(text='<b>Other Assets</b>'))
                                st.plotly_chart(chart_other, width='stretch')

                    # Create and display the category breakdown over time
                    category_chart = create_networth_category_timeline_chart(df)
                    if category_chart:
                        st.plotly_chart(category_chart, width='stretch')

                    # Add a tab view for different time ranges
                    st.subheader("Timeline Data")
                    time_range_tabs = st.tabs(["All Time", "Last 90 Days", "Last 30 Days", "Last 7 Days"])

                    with time_range_tabs[0]:
                        # For JSON files, show ALL dates but only remove basic account-level columns
                        columns_to_remove = ['Account', 'Type', 'Category']
                        display_df = df.drop(columns=[col for col in columns_to_remove if col in df.columns])
                        # Sort by date (most recent first) for better presentation
                        display_df = display_df.sort_values('Date', ascending=False)
                        st.dataframe(display_df, hide_index=True)

                    with time_range_tabs[1]:
                        # Last 90 days
                        df_sorted = df.sort_values('Date', ascending=False)
                        df_90 = df_sorted.head(90)
                        columns_to_remove = ['Account', 'Type', 'Category']
                        display_df_90 = df_90.drop(columns=[col for col in columns_to_remove if col in df_90.columns])
                        st.dataframe(display_df_90, hide_index=True)

                    with time_range_tabs[2]:
                        # Last 30 days
                        df_sorted = df.sort_values('Date', ascending=False)
                        df_30 = df_sorted.head(30)
                        columns_to_remove = ['Account', 'Type', 'Category']
                        display_df_30 = df_30.drop(columns=[col for col in columns_to_remove if col in df_30.columns])
                        st.dataframe(display_df_30, hide_index=True)

                    with time_range_tabs[3]:
                        # Last 7 days
                        df_sorted = df.sort_values('Date', ascending=False)
                        df_7 = df_sorted.head(7)
                        columns_to_remove = ['Account', 'Type', 'Category']
                        display_df_7 = df_7.drop(columns=[col for col in columns_to_remove if col in df_7.columns])
                        st.dataframe(display_df_7, hide_index=True)
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
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(label="Total Net Worth", value=f"${stats['total_net_worth']:,.2f}")
                        with col2:
                            st.metric(label="Total Assets", value=f"${stats['total_assets']:,.2f}")
                        with col3:
                            st.metric(label="Total Liquid Assets", value=f"${stats['total_cash'] + stats['total_investment']:,.2f}", help="Cash + Total Investment")
                        with col4:
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
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(label="Total Net Worth", value=f"${stats['total_net_worth']:,.2f}")
                        with col2:
                            st.metric(label="Total Assets", value=f"${stats['total_assets']:,.2f}")
                        with col3:
                            st.metric(label="Total Liquid Assets", value=f"${stats.get('total_cash', 0) + stats.get('total_investment', 0):,.2f}", help="Cash + Total Investment")
                        with col4:
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
                                st.metric(label="Total Portfolio", value=f"${stats['total_cash'] + stats['total_investment']:,.2f}", help="Cash + Total Investment")
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
                            st.plotly_chart(fig_pie, width='stretch')

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
                            st.plotly_chart(fig_bar, width='stretch')

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
                            st.plotly_chart(fig_type_pie, width='stretch')

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
                            st.plotly_chart(fig_type_bar, width='stretch')

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
            # Display portfolio data
            if result["holdings"] and df is not None:
                if result.get("csv_path") and os.path.exists(result["csv_path"]):
                    realtime_url = f"?realtime=1&refresh=300&csv_file={quote_plus(result['csv_path'])}"
                    st.markdown(
                        f'<a href="{realtime_url}" target="_blank" rel="noopener noreferrer">Open Real-Time Dashboard ↗</a>',
                        unsafe_allow_html=True,
                    )

                render_portfolio_analysis(df)

    if not result or not result.get("success", False):
        # No file processed yet or processing failed, show instructions
        st.markdown("""
        ### Empower Portfolio & Net Worth Extractor
        1. **Get your data from Empower**:
           - Log in to your Empower Personal Dashboard at [home.personalcapital.com](https://home.personalcapital.com)

           **Option A – JSON via the Site JSON Capture Exporter extension (easiest)**:
           Install the Chrome extension (see the *JSON via Browser Extension* tab below), then simply
           navigate to each Empower page — the extension captures the API response automatically.
           Click the extension icon and hit **Download** to save the file:
           - `Empower - holdings_getHoldings_*.json` – portfolio holdings
           - `Empower - networth_getHistories_*.json` – net worth history
           - `Empower - transactions_getUserTransactions_*.json` – transactions

           **Option B – Web page files**:
           - Navigate to **Investing → Holdings** (portfolio) or **Overview → Net Worth** (net worth)
           - **Safari**: Save As → Web Archive (.webarchive)
           - **Chrome / Edge**: Ctrl+S / ⌘+S → Webpage, Complete (.mhtml)

        2. **Process your data**:
           - Upload the saved file using the file uploader in the sidebar ←
           - The app automatically detects the file type (holdings, net worth, or transactions)
           - Click **Process File** and view your results

        3. **Download options**:
           - **Portfolio / Holdings**: CSV + detailed text report
           - **Net Worth History**: CSV + net worth summary report
           - **Transactions**: CSV export
        """)

        # Add tabs for different export methods
        browser_tabs = st.tabs(["JSON via DevTools", "Safari", "Chrome", "Edge", "Firefox"])

        with browser_tabs[0]:
            st.subheader("JSON via Browser Extension (Easiest)")
            st.markdown("""
            The **Site JSON Capture Exporter** Chrome extension automates the capture — no DevTools needed.

            **One-time setup:**
            1. Load the extension in Chrome:
               - Go to `chrome://extensions`
               - Enable **Developer mode** (top-right toggle)
               - Click **Load unpacked** and select the `site-json-capture-exporter-mv3` folder
            2. The extension icon will appear in your toolbar

            **Capturing data (repeat as needed):**
            1. Log in to Empower at [participant.empower-retirement.com](https://participant.empower-retirement.com)
            2. Navigate to the page for the data you want — the extension captures automatically as the page loads:

            | Empower page | Data captured | Filename saved |
            |---|---|---|
            | **Net Worth** (`#/net-worth`) | Net worth history | `Empower - networth_getHistories_YYYYMMDD.json` |
            | **All Transactions** (`#/all-transactions`) | Transaction history | `Empower - transactions_getUserTransactions_YYYYMMDD.json` |
            | **Portfolio → Allocation** (`#/portfolio/allocation`) | Allocation data | `Empower - allocations_getHoldings_YYYYMMDD.json` |
            | **Portfolio → Holdings** (`#/portfolio/holdings`) | Holdings (consolidated) | `Empower - holdings_getHoldings_YYYYMMDD.json` |
            | **Portfolio → Holdings** (`#/portfolio/holdings`) | Holdings (per account) | `Empower - holdings_detail_getHoldings_YYYYMMDD.json` |

            3. Click the extension icon in the toolbar
            4. Click **Download latest** (or **Download all** to grab every captured file at once)
            5. Upload the downloaded `.json` file using the sidebar ←

            > The extension only runs on the Empower site and saves files directly to your device — your data is never sent anywhere else.
            """)

        with browser_tabs[1]:
            st.subheader("Safari Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. From the menu bar, select **File** → **Save As**
            3. In the save dialog, select format: **Web Archive (.webarchive)**
            4. Choose a location and save
            5. Upload the .webarchive file using the sidebar
            """)

        with browser_tabs[2]:
            st.subheader("Chrome Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. Press **Ctrl+S** (Windows) or **⌘+S** (Mac)
            3. In the save dialog, change "Save as type" to **Webpage, Complete (.mhtml)**
            4. Choose a location and save
            5. Upload the .mhtml file using the sidebar
            """)

        with browser_tabs[3]:
            st.subheader("Edge Instructions")
            st.markdown("""
            1. Navigate to your Empower **Portfolio** or **Net Worth** page
            2. Press **Ctrl+S** (Windows) or **⌘+S** (Mac)
            3. In the save dialog, change "Save as type" to **Webpage, Complete (.mhtml)**
            4. Choose a location and save
            5. Upload the .mhtml file using the sidebar
            """)

        with browser_tabs[4]:
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

    # Keep uploaded files so real-time links can re-process the same source in a new tab.

    # Add a small footer to show user ID (optional)
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Session ID: {st.session_state.user_id}")

if __name__ == "__main__":
    main()
