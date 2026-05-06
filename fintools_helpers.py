"""Helper functions and UI components for finTools_app.

This module contains all processing, charting, Excel-building,
and Streamlit render functions used by the Empower Portfolio tool.
"""
import streamlit as st

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

def process_transactions_json(file_path):
    """Parse an Empower transactions JSON export (getUserTransactions).
    Returns a dict with 'transactions' list and summary fields,
    or an error string on failure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'spData' not in data or 'transactions' not in data['spData']:
            error_msg = "Could not find transactions in JSON structure."
            if 'spData' in data:
                error_msg += f" Found these keys in spData: {', '.join(data['spData'].keys())}."
            else:
                error_msg += " 'spData' key not found in JSON."
            return error_msg

        sp = data['spData']
        raw_txns = sp['transactions']

        # Canonical mapping from Empower categoryId -> (display_name, category_type).
        # The JSON `categoryName` field is unreliable: it returns the original/system category
        # name which can be stale when user rules or custom categories override it.
        # These IDs and names are derived from the official Empower API category schema.
        EMPOWER_CATEGORY_MAP = {
            # Standard Empower categories
            1:  ('ATM/Cash',                   'EXPENSE'),
            2:  ('Advertising',                'EXPENSE'),
            3:  ('Alcohol & Bars',             'EXPENSE'),
            4:  ('Miscellaneous',              'EXPENSE'),
            5:  ('Books',                      'EXPENSE'),
            6:  ('Auto Insurance',             'EXPENSE'),
            7:  ('Checks',                     'EXPENSE'),
            8:  ('Clothing/Shoes',             'EXPENSE'),
            9:  ('Personal & Sports Goods',    'EXPENSE'),
            10: ('Dues & Subscriptions',       'EXPENSE'),
            11: ('Education',                  'EXPENSE'),
            12: ('Electronics',                'EXPENSE'),
            13: ('Entertainment',              'EXPENSE'),
            14: ('Auto & Gas',                 'EXPENSE'),
            15: ('General Merchandise',        'EXPENSE'),
            16: ('Gifts',                      'EXPENSE'),
            17: ('Groceries',                  'EXPENSE'),
            18: ('Healthcare/Medical',         'EXPENSE'),
            19: ('Home & Garden',              'EXPENSE'),
            20: ('Home Improvement',           'EXPENSE'),
            21: ('Home Maintenance',           'EXPENSE'),
            22: ('Insurance',                  'EXPENSE'),
            23: ('Loans payment',             'EXPENSE'),
            24: ('Mortgages',                  'EXPENSE'),
            25: ('Music',                      'EXPENSE'),
            26: ('Office Supplies',            'EXPENSE'),
            27: ('Online Services',            'EXPENSE'),
            28: ('Personal Care',              'EXPENSE'),
            29: ('Pets/Pet Care',              'EXPENSE'),
            30: ('Postage & Shipping',         'EXPENSE'),
            31: ('Professional Services',      'EXPENSE'),
            32: ('Real Estate',                'EXPENSE'),
            33: ('Recreation',                 'EXPENSE'),
            34: ('Restaurants',                'EXPENSE'),
            35: ('Restaurants',                'EXPENSE'),
            36: ('Service Charges/Fees',       'EXPENSE'),
            37: ('Taxes',                      'EXPENSE'),
            38: ('Telecom',                    'EXPENSE'),
            39: ('Travel',                     'EXPENSE'),
            40: ('Utilities & Telecom',        'EXPENSE'),
            41: ('Vacation',                   'EXPENSE'),
            42: ('Veterinary',                 'EXPENSE'),
            43: ('Clothing/Shoes',             'EXPENSE'),
            44: ('Interest',                   'INCOME'),
            45: ('Investment Income',          'INCOME'),
            46: ('Other Income',               'INCOME'),
            47: ('Paycheck',                   'INCOME'),
            48: ('Rental Income',              'INCOME'),
            49: ('Retirement Income',          'INCOME'),
            50: ('Deposits',                   'INCOME'),
            51: ('Credit Card Payments',       'TRANSFER'),
            52: ('Loan Payment',               'TRANSFER'),
            53: ('Securities Trades',          'TRANSFER'),
            54: ('Transfers',                  'TRANSFER'),
            55: ('Mortgage & Rent',            'EXPENSE'),
            56: ('Uncategorized',              'UNCATEGORIZE'),
            57: ('Business Miscellaneous',     'EXPENSE'),
            58: ('Advisory Fee',               'EXPENSE'),
            59: ('Dividends Received',         'INCOME'),
            60: ('Interest',                   'INCOME'),
            61: ('Other Expenses',             'EXPENSE'),
            62: ('Donations',                  'EXPENSE'),
            63: ('Business Meals',             'EXPENSE'),
            64: ('Office Expenses',            'EXPENSE'),
            65: ('Business Travel',            'EXPENSE'),
            66: ('Payroll',                    'EXPENSE'),
            67: ('Bank Fees',                  'EXPENSE'),
            68: ('Dividends Received',         'INCOME'),
            69: ('Capital Gains',              'INCOME'),
            70: ('Contributions',              'TRANSFER'),
            71: ('Withdrawals',                'TRANSFER'),
            72: ('Rewards',                    'INCOME'),
            73: ('Refunds & Reimbursements',   'INCOME'),
            74: ('Business Income',            'INCOME'),
            75: ('Healthcare',                 'EXPENSE'),
            # User-specific custom categories observed in this account:
            6054352: ('BigBuy - Auto',         'EXPENSE'),
            6054354: ('BigBuy - Electronics',  'EXPENSE'),
            6063778: ('Payment Transfer',      'TRANSFER'),
            6353184: ('Business Spend',        'EXPENSE'),
        }

        structured = []
        for t in raw_txns:
            cat_id       = t.get('categoryId')
            category_name = t.get('categoryName', '')
            category_type = t.get('categoryType', '')
            transaction_type = t.get('transactionType', '') or ''
            investment_type  = t.get('investmentType', '') or ''

            # Use the canonical categoryId map as the primary source of truth.
            # The JSON `categoryName` is the system/original name and is unreliable when
            # user rules, custom categories, or originalCategoryId bleed-through are present.
            if cat_id in EMPOWER_CATEGORY_MAP:
                category_name, category_type = EMPOWER_CATEGORY_MAP[cat_id]

            # Secondary overrides for specific transactionType/investmentType signals
            # where the categoryId alone is ambiguous.
            if transaction_type == 'Administrative Fee' and investment_type == 'Mgmt Fees':
                category_name = 'Advisory Fee'
                category_type = 'EXPENSE'

            structured.append({
                'Date': t.get('transactionDate', ''),
                'Description': t.get('description', t.get('originalDescription', '')),
                'Simple Description': t.get('simpleDescription', ''),
                'Amount': t.get('amount', 0.0),
                'Is Credit': t.get('isCredit', False),
                'Category': category_name,
                'Category Type': category_type,
                'Account': t.get('accountName', ''),
                'Transaction Type': t.get('transactionType', ''),
                'Status': t.get('status', ''),
                'Is Income': t.get('isIncome', False),
                'Is Spending': t.get('isSpending', False),
                'Currency': t.get('currency', 'USD'),
            })

        return {
            'transactions': structured,
            'count': len(structured),
            'money_in': sp.get('moneyIn', 0.0),
            'money_out': sp.get('moneyOut', 0.0),
            'net_cashflow': sp.get('netCashflow', 0.0),
            'average_in': sp.get('averageIn', 0.0),
            'average_out': sp.get('averageOut', 0.0),
            'start_date': sp.get('startDate', ''),
            'end_date': sp.get('endDate', ''),
            'interval_type': sp.get('intervalType', ''),
        }

    except json.JSONDecodeError as e:
        return f"JSON parsing error: {str(e)}"
    except Exception as e:
        return f"Error processing transactions JSON file: {str(e)}"

def process_accounts_json(file_path):
    """Parse an Empower accounts JSON export (getAccounts / getUserAccountDetails).
    Returns a dict with 'accounts' list, 'totals' dict, and 'count' int,
    or an error string on failure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'spData' not in data or 'accounts' not in data['spData']:
            error_msg = "Could not find accounts in JSON structure."
            if 'spData' in data:
                error_msg += f" Found these keys in spData: {', '.join(data['spData'].keys())}."
            else:
                error_msg += " 'spData' key not found in JSON."
            return error_msg

        sp = data['spData']
        accounts = sp['accounts']

        return {
            'accounts': accounts,
            'totals': {
                'assets':                         sp.get('assets', 0),
                'liabilities':                    sp.get('liabilities', 0),
                'networth':                       sp.get('networth', 0),
                'investmentAccountsTotal':        sp.get('investmentAccountsTotal', 0),
                'cashAccountsTotal':              sp.get('cashAccountsTotal', 0),
                'creditCardAccountsTotal':        sp.get('creditCardAccountsTotal', 0),
                'mortgageAccountsTotal':          sp.get('mortgageAccountsTotal', 0),
                'loanAccountsTotal':              sp.get('loanAccountsTotal', 0),
                'otherAssetAccountsTotal':        sp.get('otherAssetAccountsTotal', 0),
                'otherLiabilitiesAccountsTotal':  sp.get('otherLiabilitiesAccountsTotal', 0),
            },
            'count': len(accounts),
        }

    except json.JSONDecodeError as e:
        return f"JSON parsing error: {str(e)}"
    except Exception as e:
        return f"Error processing accounts JSON file: {str(e)}"


def save_accounts_json_to_csv(accounts_data, csv_path):
    """Save accounts data to a CSV file."""
    rows = []
    for acct in accounts_data.get('accounts', []):
        rows.append({
            'Name':         acct.get('name', ''),
            'Institution':  acct.get('firmName', ''),
            'Group':        acct.get('accountTypeGroup', ''),
            'Type':         acct.get('accountType', ''),
            'Balance':      acct.get('balance', 0),
            'Is Liability': acct.get('isLiability', False),
            'Is Asset':     acct.get('isAsset', True),
            'Is Closed':    bool(acct.get('closedDate', '')),
            'Is Crypto':    acct.get('isCrypto', False),
            'Tax Deferred': acct.get('isTaxDeferredOrNonTaxable', False),
            'Is Manual':    acct.get('isManual', False),
            'Currency':     acct.get('currency', 'USD'),
        })
    pd.DataFrame(rows).to_csv(csv_path, index=False)


def format_accounts_json_as_text(accounts_data):
    """Format accounts data as a fixed-width text report."""
    lines = []
    totals = accounts_data.get('totals', {})
    accounts = accounts_data.get('accounts', [])

    lines.append("=" * 100)
    lines.append("EMPOWER ACCOUNTS SUMMARY")
    lines.append("=" * 100)
    lines.append("")

    # Summary metrics
    lines.append(f"{'Net Worth:':<30} {totals.get('networth', 0):>15,.2f}")
    lines.append(f"{'Total Assets:':<30} {totals.get('assets', 0):>15,.2f}")
    lines.append(f"{'Total Liabilities:':<30} {totals.get('liabilities', 0):>15,.2f}")
    lines.append("")
    lines.append(f"{'Investment Total:':<30} {totals.get('investmentAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Cash Total:':<30} {totals.get('cashAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Other Assets Total:':<30} {totals.get('otherAssetAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Credit Card Total:':<30} {totals.get('creditCardAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Mortgage Total:':<30} {totals.get('mortgageAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Loan Total:':<30} {totals.get('loanAccountsTotal', 0):>15,.2f}")
    lines.append(f"{'Total Accounts:':<30} {len(accounts):>15}")
    lines.append("")

    # Accounts table header
    lines.append("-" * 100)
    lines.append(f"{'Name':<35} {'Institution':<25} {'Group':<18} {'Balance':>14} {'Closed':<8} {'TaxDef':<8}")
    lines.append("-" * 100)

    # Sort: assets first (by balance desc), then liabilities (by balance desc)
    assets   = sorted([a for a in accounts if a.get('isAsset')],   key=lambda x: abs(x.get('balance', 0)), reverse=True)
    liab     = sorted([a for a in accounts if a.get('isLiability')], key=lambda x: abs(x.get('balance', 0)), reverse=True)

    def _row(a):
        name    = str(a.get('name', ''))[:34]
        firm    = str(a.get('firmName', ''))[:24]
        group   = str(a.get('accountTypeGroup', ''))[:17]
        bal     = a.get('balance', 0)
        closed  = 'Yes' if a.get('closedDate', '') else 'No'
        tax     = 'Yes' if a.get('isTaxDeferredOrNonTaxable', False) else 'No'
        return f"{name:<35} {firm:<25} {group:<18} {bal:>14,.2f} {closed:<8} {tax:<8}"

    for a in assets:
        lines.append(_row(a))
    if liab:
        lines.append("")
        lines.append(f"{'--- LIABILITIES ---'}")
        for a in liab:
            lines.append(_row(a))

    lines.append("-" * 100)
    return "\n".join(lines)


def parse_account_histories(histories_file_path, accounts_data):
    """Cross-reference a networthSummaryHistories JSON with already-parsed accounts_data.

    Parameters
    ----------
    histories_file_path : str
        Path to the networthSummaryHistories JSON file.
    accounts_data : dict
        Dict returned by ``process_accounts_json()`` — must contain ``'accounts'`` list.

    Returns
    -------
    dict with keys:
        'timeline_df'   : pd.DataFrame  — Date + one column per matched account (non-zero,
                          liability balances stored as negative) + 'Net Worth' column
                          (from networthHistories); sorted ascending by Date.
        'account_cols'  : list[str]     — column names for individual accounts (excl. Net Worth)
        'account_map'   : dict          — userAccountId(str) -> account info dict
        'histories_summary' : dict      — networthSummary totals (change metrics)
        'interval_type' : str           — 'DAY' / 'WEEK' / 'MONTH'
    or an error string on failure.
    """
    try:
        with open(histories_file_path, 'r', encoding='utf-8') as f:
            hdata = json.load(f)

        if 'spData' not in hdata or 'histories' not in hdata['spData']:
            return "Could not find histories in JSON structure."

        sp = hdata['spData']
        histories = sp['histories']         # list of {date, balances, aggregateBalance}
        interval_type = sp.get('intervalType', 'DAY')
        histories_summary = sp.get('networthSummary', {})

        # Build a date -> networth lookup from networthHistories (assets - liabilities,
        # correctly computed by Empower).  Fall back to None if not present.
        nw_by_date = {
            h['date']: h.get('networth')
            for h in sp.get('networthHistories', [])
        }

        # Build userAccountId -> account info map from accounts_data
        account_map = {
            str(a.get('userAccountId', '')): a
            for a in accounts_data.get('accounts', [])
        }

        # Collect all account IDs present in any history record (ignoring Annotation keys)
        all_ids = set()
        for h in histories:
            for k in h.get('balances', {}):
                if not k.endswith('Annotation'):
                    all_ids.add(k)

        # Filter to IDs that have a non-zero balance in at least one record AND exist in accounts
        def _has_nonzero(acct_id):
            return any(
                h['balances'].get(acct_id, 0) != 0
                for h in histories
            )

        active_ids = sorted(
            [aid for aid in all_ids if aid in account_map and _has_nonzero(aid)],
            key=lambda aid: abs(account_map[aid].get('balance', 0)),
            reverse=True,
        )

        # Build column label for each account: "Name (Institution)"
        def _col_label(aid):
            a = account_map[aid]
            name = a.get('name', aid)
            firm = a.get('firmName', '')
            return f"{name} ({firm})" if firm else name

        col_labels = [_col_label(aid) for aid in active_ids]

        # Build rows.
        # Liability account balances are stored as NEGATIVE so they correctly reduce
        # the "Net Worth" total. The aggregate column uses networthHistories.networth
        # (assets − liabilities) rather than the raw aggregateBalance field which
        # adds all values as positives.
        rows = []
        for h in histories:
            row = {'Date': h['date']}
            for aid, lbl in zip(active_ids, col_labels):
                raw_val = h['balances'].get(aid, 0)
                is_liability = account_map[aid].get('isLiability', False)
                # Store liabilities as negative to reflect their impact on net worth
                row[lbl] = -abs(raw_val) if is_liability and raw_val != 0 else raw_val
            # Use Empower's own computed net worth (assets − liabilities) as the
            # aggregate column instead of the raw aggregateBalance which double-counts
            # liabilities as positive.
            nw = nw_by_date.get(h['date'])
            row['Net Worth'] = nw if nw is not None else h.get('aggregateBalance', 0)
            rows.append(row)

        timeline_df = pd.DataFrame(rows)
        timeline_df['Date'] = pd.to_datetime(timeline_df['Date'])
        timeline_df = timeline_df.sort_values('Date').reset_index(drop=True)

        return {
            'timeline_df': timeline_df,
            'account_cols': col_labels,
            'account_map': account_map,
            'histories_summary': histories_summary,
            'interval_type': interval_type,
        }

    except json.JSONDecodeError as e:
        return f"JSON parsing error: {str(e)}"
    except Exception as e:
        return f"Error processing histories file: {str(e)}"


# Investment-type account groups for performance filtering
_INVESTMENT_GROUPS = {'INVESTMENT', 'RETIREMENT', 'ESOP', 'CRYPTO_CURRENCY', 'TRUST'}


def compute_account_performance(timeline_df, account_cols, account_map):
    """Compute per-account performance over 30d, 90d, YTD, and 1-Year periods.

    Only investment/retirement accounts (INVESTMENT, RETIREMENT, ESOP,
    CRYPTO_CURRENCY, TRUST) are included.

    Parameters
    ----------
    timeline_df  : pd.DataFrame  from parse_account_histories()
    account_cols : list[str]     column names for individual accounts
    account_map  : dict          userAccountId -> account info dict

    Returns
    -------
    pd.DataFrame with columns:
        Account, Group, Institution,
        Latest Balance,
        30d $, 30d %,
        90d $, 90d %,
        YTD $, YTD %, YTD Note,
        1yr $, 1yr %
    Sorted by Latest Balance descending.
    """
    if timeline_df.empty or not account_cols:
        return pd.DataFrame()

    # Build label -> account info lookup
    def _col_label(a):
        name = a.get('name', '')
        firm = a.get('firmName', '')
        return f"{name} ({firm})" if firm else name

    label_to_info = {_col_label(a): a for a in account_map.values()}

    tl = timeline_df.set_index('Date').sort_index()
    today = tl.index.max()
    data_start = tl.index.min()

    def _period_start(days=None, ytd=False):
        if ytd:
            return pd.Timestamp(today.year, 1, 1)
        return today - pd.Timedelta(days=days)

    def _nearest_row(target_date, max_gap_days=45):
        """Return the row at or just before target_date.
        If target_date is before data_start but within max_gap_days, fall forward
        to the earliest available row (approximate).  Further gaps return None."""
        candidates = tl[tl.index <= target_date]
        if not candidates.empty:
            return candidates.iloc[-1], False          # exact / on-time
        # target is before data_start — fall forward if gap is small enough
        gap = (data_start - target_date).days
        if gap <= max_gap_days:
            return tl.iloc[0], True                    # approximate
        return None, False                             # too far back

    periods = [
        ('30d',  _period_start(days=30),                False, 10),
        ('90d',  _period_start(days=90),                False, 45),
        ('YTD',  _period_start(ytd=True),               True,  45),
        ('1yr',  _period_start(days=365),               False, 30),  # allow up to 30d gap
    ]

    rows = []
    for col in account_cols:
        info = label_to_info.get(col)
        if not info:
            continue
        group = info.get('accountTypeGroup', '')
        if group not in _INVESTMENT_GROUPS:
            continue
        if info.get('isLiability'):
            continue

        latest_val = tl[col].iloc[-1] if col in tl.columns else 0
        if latest_val == 0:
            continue

        row = {
            'Account':         col,
            'Group':           group,
            'Institution':     info.get('firmName', ''),
            'Latest Balance':  latest_val,
        }

        for period_label, target_date, is_ytd, max_gap in periods:
            start_row, is_approx = _nearest_row(target_date, max_gap_days=max_gap)
            if start_row is None or col not in start_row.index:
                row[f'{period_label} $'] = None
                row[f'{period_label} %'] = None
                if is_ytd:
                    row['YTD Note'] = ''
                continue

            start_val = start_row[col]
            if start_val == 0:
                row[f'{period_label} $'] = None
                row[f'{period_label} %'] = None
                if is_ytd:
                    row['YTD Note'] = ''
                continue

            chg_dollar = latest_val - start_val
            chg_pct    = (chg_dollar / abs(start_val)) * 100

            row[f'{period_label} $'] = round(chg_dollar, 2)
            row[f'{period_label} %'] = round(chg_pct, 2)

            if is_ytd:
                actual_start = start_row.name
                if is_approx or actual_start > target_date:
                    row['YTD Note'] = f"from {actual_start.strftime('%b %d')}"
                else:
                    row['YTD Note'] = ''

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    perf_df = pd.DataFrame(rows)
    # Ensure YTD Note column exists
    if 'YTD Note' not in perf_df.columns:
        perf_df['YTD Note'] = ''

    perf_df = perf_df.sort_values('Latest Balance', ascending=False).reset_index(drop=True)
    return perf_df


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
    text += f"{'Ticker':<10} {'Name':<35} {'Shares':<12} {'Price':<12} {'Value':<15} {'Type':<10}\n"
    text += "-" * 100 + "\n"

    # Sort by value descending
    sorted_holdings = sorted(holdings, key=lambda x: x.get('Value', 0), reverse=True)

    for holding in sorted_holdings:
        ticker = holding.get('Ticker', '')[:9]
        name = holding.get('Name', '')[:34]
        shares = holding.get('Shares', 0)
        price = holding.get('Price', 0)
        value = holding.get('Value', 0)
        htype = holding.get('Type', '')[:9]

        text += f"{ticker:<10} {name:<35} {shares:<12.2f} ${price:<11.2f} ${value:<14,.2f} {htype:<10}\n"

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

            # Remove empty directories immediately, regardless of age
            if not any(True for _ in os.scandir(user_dir)):
                os.rmdir(user_dir)
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
             - `accounts_*.json` – accounts snapshot
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
        elif 'account' in filename:
            return 'accounts'

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
                elif 'accounts' in spdata_keys:
                    return 'accounts'
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
    raw_holdings_list = None  # pre-consolidation per-account rows

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

    elif content_type == 'transactions':
        # Process transactions data (JSON only)
        holdings_data = process_transactions_json(file_path)

        if isinstance(holdings_data, str):
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

        # Save as CSV
        if save_csv:
            user_dir = ensure_user_files_dir()
            csv_path = os.path.join(user_dir, f"{output_file_base}.csv")
            import csv as _csv
            if holdings_data['transactions']:
                keys = list(holdings_data['transactions'][0].keys())
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = _csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(holdings_data['transactions'])

        # Generate simple text summary
        user_dir = ensure_user_files_dir()
        text_path = os.path.join(user_dir, f"{output_file_base}.txt")
        with open(text_path, "w", encoding="utf-8") as file:
            file.write(f"Transactions Export\n")
            file.write(f"Period: {holdings_data['start_date']} to {holdings_data['end_date']}\n")
            file.write(f"Interval: {holdings_data['interval_type']}\n\n")
            file.write(f"Money In:     ${holdings_data['money_in']:,.2f}\n")
            file.write(f"Money Out:    ${holdings_data['money_out']:,.2f}\n")
            file.write(f"Net Cashflow: ${holdings_data['net_cashflow']:,.2f}\n\n")
            file.write(f"Total Transactions: {holdings_data['count']}\n")

    elif content_type == 'accounts':
        # Process accounts snapshot data (JSON only)
        holdings_data = process_accounts_json(file_path)

        if isinstance(holdings_data, str) and (holdings_data.startswith("Could not") or holdings_data.startswith("JSON") or holdings_data.startswith("Error")):
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

        # Save as CSV
        if save_csv:
            user_dir = ensure_user_files_dir()
            csv_path = os.path.join(user_dir, f"{output_file_base}.csv")
            save_accounts_json_to_csv(holdings_data, csv_path)

        # Generate formatted text file
        user_dir = ensure_user_files_dir()
        text_path = os.path.join(user_dir, f"{output_file_base}.txt")
        with open(text_path, "w", encoding="utf-8") as file:
            file.write(format_accounts_json_as_text(holdings_data))

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
                # Capture raw (per-account) rows before consolidation only for
                # detail-level files (e.g. holdings_detail_getHoldings_*.json)
                _is_detail_file = "detail" in os.path.basename(file_path).lower()
                if isinstance(holdings_data, dict) and 'holdings' in holdings_data:
                    if _is_detail_file:
                        raw_holdings_list = [dict(h) for h in holdings_data['holdings']]
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
        "raw_holdings_list": raw_holdings_list,
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
    """Fetch 30d, 90d, YTD, 1-Year, 3-Yr Ann, 5-Yr Ann, 10-Yr Ann returns for a tuple of symbols."""
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

    def _simple_return(series, days):
        """Simple return over the last `days` calendar days."""
        cutoff = today - _dt.timedelta(days=days)
        sub = series[series.index.date >= cutoff]
        if len(sub) < 2:
            return None
        start, end = float(sub.iloc[0]), float(sub.iloc[-1])
        if start <= 0:
            return None
        return (end / start - 1) * 100

    def _ytd_return(series):
        jan1 = _dt.date(today.year, 1, 1)
        sub = series[series.index.date >= jan1]
        if len(sub) < 1:
            sub = series
        if len(sub) < 2:
            return None
        start, end = float(sub.iloc[0]), float(sub.iloc[-1])
        if start <= 0:
            return None
        return (end / start - 1) * 100

    try:
        # Use daily interval for 90-day accuracy, then reuse for all periods
        raw = yf.download(
            sym_list,
            period="10y",
            interval="1d",
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
                "30d":  _simple_return(series, 30),
                "90d":  _simple_return(series, 90),
                "180d": _simple_return(series, 180),
                "ytd":  _ytd_return(series),
                "1y":   _ann_return(series, 1),
                "3y":   _ann_return(series, 3),
                "5y":   _ann_return(series, 5),
                "10y":  _ann_return(series, 10),
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



from fintools_excel_helpers import _enrich_holdings_df, build_holdings_excel, build_performance_excel  # noqa: F401
from fintools_excel_helpers import classify_tax_status, _TAX_DEFERRED_RE, _TAX_EXEMPT_RE  # noqa: F401

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

    PCT_COLS  = ["30d %", "90d %", "180d %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"]
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
    for _c in PCT_COLS + ["Day Chg %", "180d %"]:
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
                    return "background-color:#0d2b1a;color:#4ade80;font-weight:bold"
                if v < 0:
                    return "background-color:#2b0d0d;color:#f87171;font-weight:bold"
            except (TypeError, ValueError):
                pass
            return ""

        return _disp.style.map(_clr, subset=[pct_col])

    st.subheader("Performance Highlights")

    # Best / Worst performers – 30d
    if "30d %" in _hl_df.columns:
        _30d_valid = _hl_df.dropna(subset=["30d %"])
        _col_b0, _col_w0 = st.columns(2)
        with _col_b0:
            st.markdown("**Top 5 – 30-Day Return**")
            st.dataframe(_hl_table(_30d_valid.nlargest(5, "30d %"), "30d %"), hide_index=True, width="stretch")
        with _col_w0:
            st.markdown("**Bottom 5 – 30-Day Return**")
            st.dataframe(_hl_table(_30d_valid.nsmallest(5, "30d %"), "30d %"), hide_index=True, width="stretch")

    # Best / Worst performers – 90d
    if "90d %" in _hl_df.columns:
        _90d_valid = _hl_df.dropna(subset=["90d %"])
        _col_b00, _col_w00 = st.columns(2)
        with _col_b00:
            st.markdown("**Top 5 – 90-Day Return**")
            st.dataframe(_hl_table(_90d_valid.nlargest(5, "90d %"), "90d %"), hide_index=True, width="stretch")
        with _col_w00:
            st.markdown("**Bottom 5 – 90-Day Return**")
            st.dataframe(_hl_table(_90d_valid.nsmallest(5, "90d %"), "90d %"), hide_index=True, width="stretch")

    # Best / Worst performers – 180d
    if "180d %" in _hl_df.columns:
        _180d_valid = _hl_df.dropna(subset=["180d %"])
        _col_b180, _col_w180 = st.columns(2)
        with _col_b180:
            st.markdown("**Top 5 – 180-Day Return**")
            st.dataframe(_hl_table(_180d_valid.nlargest(5, "180d %"), "180d %"), hide_index=True, width="stretch")
        with _col_w180:
            st.markdown("**Bottom 5 – 180-Day Return**")
            st.dataframe(_hl_table(_180d_valid.nsmallest(5, "180d %"), "180d %"), hide_index=True, width="stretch")

    # Best / Worst performers – YTD
    if "YTD %" in _hl_df.columns:
        _ytd_valid = _hl_df.dropna(subset=["YTD %"])
        _best_ytd  = _ytd_valid.nlargest(5, "YTD %")
        _worst_ytd = _ytd_valid.nsmallest(5, "YTD %")

        _col_b, _col_w = st.columns(2)
        with _col_b:
            st.markdown("**Top 5 – YTD Return**")
            st.dataframe(_hl_table(_best_ytd, "YTD %"), hide_index=True, width="stretch")
        with _col_w:
            st.markdown("**Bottom 5 – YTD Return**")
            st.dataframe(_hl_table(_worst_ytd, "YTD %"), hide_index=True, width="stretch")

    # Best / Worst performers – 1-Year
    if "1-Year %" in _hl_df.columns:
        _1y_valid  = _hl_df.dropna(subset=["1-Year %"])
        _best_1y   = _1y_valid.nlargest(5, "1-Year %")
        _worst_1y  = _1y_valid.nsmallest(5, "1-Year %")

        _col_b2, _col_w2 = st.columns(2)
        with _col_b2:
            st.markdown("**Top 5 – 1-Year Return**")
            st.dataframe(_hl_table(_best_1y, "1-Year %"), hide_index=True, width="stretch")
        with _col_w2:
            st.markdown("**Bottom 5 – 1-Year Return**")
            st.dataframe(_hl_table(_worst_1y, "1-Year %"), hide_index=True, width="stretch")

    # Momentum – composite score weighted toward recent periods
    # 30d is intentionally low-weight (noise filter); 90d+180d carry the medium-term signal
    # Score = 0.10*30d + 0.25*90d + 0.30*180d + 0.20*YTD + 0.10*1-Year + 0.03*3-Yr + 0.02*5-Yr
    _mom_weights = [("30d %", 0.10), ("90d %", 0.25), ("180d %", 0.30), ("YTD %", 0.20), ("1-Year %", 0.10), ("3-Yr Ann %", 0.03), ("5-Yr Ann %", 0.02)]
    _avail_mom   = [(c, w) for c, w in _mom_weights if c in _hl_df.columns]
    if len(_avail_mom) >= 2:
        _mom_df = _hl_df.copy()
        _weight_sum = sum(w for _, w in _avail_mom)
        _mom_df["Momentum Score"] = sum(
            pd.to_numeric(_mom_df[c], errors="coerce").fillna(0) * w
            for c, w in _avail_mom
        ) / _weight_sum
        _mom_valid = _mom_df.dropna(subset=["Momentum Score"])
        _mom_top   = _mom_valid.nlargest(10, "Momentum Score")
        _mom_bot   = _mom_valid.nsmallest(10, "Momentum Score")
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
                    return "background-color:#0d2b1a;color:#4ade80;font-weight:bold"
                if v < 0:
                    return "background-color:#2b0d0d;color:#f87171;font-weight:bold"
            except (TypeError, ValueError):
                pass
            return ""

        _mom_label = "*(weighted: 10% 30d · 25% 90d · 30% 180d · 20% YTD · 10% 1-Year · 3% 3-Year · 2% 5-Year)*"
        st.markdown(f"**Top 10 – Momentum** {_mom_label}")
        st.dataframe(_fmt_mom_df(_mom_top).style.map(_mom_clr, subset=["Momentum Score"]), hide_index=True, width="stretch")
        st.markdown(f"**Bottom 10 – Momentum** {_mom_label}")
        st.dataframe(_fmt_mom_df(_mom_bot).style.map(_mom_clr, subset=["Momentum Score"]), hide_index=True, width="stretch")

    st.divider()

    # ── Styled table ─────────────────────────────────────────────────────────
    def _colour_pct(val):
        try:
            v = float(val)
            if v < 0:
                return "background-color: #2b0d0d; color: #f87171; font-weight: bold"
            elif v > 0:
                return "background-color: #0d2b1a; color: #4ade80; font-weight: bold"
        except (TypeError, ValueError):
            pass
        return ""

    def _colour_dollar(val):
        try:
            v = float(val)
            if v < 0:
                return "color: #f87171; font-weight: bold"
            elif v > 0:
                return "color: #4ade80; font-weight: bold"
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

    st.dataframe(style, hide_index=True, width="stretch")

    st.divider()

    # ── Price map from perf_df (yfinance-updated prices) ─────────────────────
    _price_map = {}
    if "Symbol" in perf_df.columns and "Price" in perf_df.columns:
        for _, _pr in perf_df[["Symbol", "Price"]].iterrows():
            _sym = str(_pr["Symbol"]).strip().upper()
            _p   = _pr["Price"]
            if _sym and _p is not None and not (isinstance(_p, float) and np.isnan(_p)):
                _price_map[_sym] = float(_p)

    def _apply_price_map(frame):
        """Overwrite Price with updated yfinance prices and recalculate Value = Shares × Price."""
        if frame is None or frame.empty or not _price_map:
            return frame
        _tc = next((c for c in ["Ticker", "Symbol"] if c in frame.columns), None)
        if not _tc:
            return frame
        frame = frame.copy()
        for _c in ["Shares", "Price", "Value"]:
            if _c in frame.columns:
                frame[_c] = pd.to_numeric(frame[_c], errors="coerce")
        _new_prices = frame[_tc].apply(
            lambda t: _price_map.get(str(t).strip().upper()) if pd.notna(t) else None
        )
        _mask = _new_prices.notna()
        if _mask.any():
            frame.loc[_mask, "Price"] = _new_prices[_mask]
        if "Shares" in frame.columns and "Price" in frame.columns:
            _new_val = frame["Shares"] * frame["Price"]
            frame.loc[_new_val.notna(), "Value"] = _new_val[_new_val.notna()]
        return frame

    # ── Load holdings sidecar (saved alongside the perf report JSON) ──────────
    _holdings_df = None
    _detail_df   = None
    _sidecar_path = report_file.replace(".json", "_holdings.json")
    if os.path.exists(_sidecar_path):
        try:
            import json as _json2
            with open(_sidecar_path, "r", encoding="utf-8") as _sf:
                _sc = _json2.load(_sf)
            if _sc.get("holdings"):
                _holdings_df = _apply_price_map(pd.DataFrame(_sc["holdings"]))
            if _sc.get("raw_holdings_list"):
                _raw = _sc["raw_holdings_list"]
                _detail_df = pd.DataFrame(_raw)
                _drop = [c for c in ["Change", "1 Day %", "1 day $", "_accounts", "_value_for_price_calc"] if c in _detail_df.columns]
                if _drop:
                    _detail_df = _detail_df.drop(columns=_drop)
                for _col in ["Value", "Shares", "Price", "Cost Basis"]:
                    if _col in _detail_df.columns:
                        _detail_df[_col] = pd.to_numeric(_detail_df[_col], errors="coerce")
                _detail_df = _apply_price_map(_detail_df)
                _dpref = ["Account", "Ticker", "Name", "Shares", "Price", "Value", "Type", "CUSIP", "Cost Basis", "Exchange", "Category"]
                _dcols = [c for c in _dpref if c in _detail_df.columns] + \
                         [c for c in _detail_df.columns if c not in _dpref]
                _detail_df = _detail_df[_dcols]
                if "Value" in _detail_df.columns:
                    _detail_df = _detail_df.sort_values(["Account", "Value"], ascending=[True, False], na_position="last").reset_index(drop=True)
        except Exception:
            pass

    # ── Excel download ────────────────────────────────────────────────────────
    # Build stats for the Portfolio Statistics sheet using the best available
    # price data.  Priority:
    #   1. _holdings_df from sidecar (already has yfinance prices applied)
    #   2. perf_df itself (Symbol/Shares/Price/Value already reflect yfinance)
    _perf_stats = None
    if _holdings_df is not None and not _holdings_df.empty:
        _stats_df = _holdings_df.copy()
        if "Ticker" in _stats_df.columns and "Symbol" not in _stats_df.columns:
            _stats_df = _stats_df.rename(columns={"Ticker": "Symbol"})
        _raw_list = _detail_df.to_dict(orient="records") if (_detail_df is not None and not _detail_df.empty) else None
        _perf_stats = calculate_portfolio_statistics(_stats_df, raw_holdings_list=_raw_list)
    else:
        # Fall back: derive stats directly from perf_df (has updated prices)
        _stats_df = perf_df[["Symbol", "Shares", "Price", "Value"]].copy() if \
                    all(c in perf_df.columns for c in ["Symbol", "Shares", "Price", "Value"]) else perf_df.copy()
        _stats_df = _stats_df.rename(columns={"Symbol": "Symbol"})  # ensure name
        # calculate_portfolio_statistics expects a "Name" column
        if "Name" not in _stats_df.columns and "Symbol" in _stats_df.columns:
            _stats_df["Name"] = _stats_df["Symbol"]
        for _c in ["Value", "Shares", "Price"]:
            if _c in _stats_df.columns:
                _stats_df[_c] = pd.to_numeric(_stats_df[_c], errors="coerce")
        _perf_stats = calculate_portfolio_statistics(_stats_df)

    if _perf_stats and "error" in _perf_stats:
        _perf_stats = None

    excel_buf = build_performance_excel(perf_df, holdings_df=_holdings_df, detail_df=_detail_df, stats=_perf_stats)
    fname = f"portfolio_performance_{_dt3.date.today().isoformat()}.xlsx"
    st.download_button(
        label="⬇️ Download Excel Report",
        data=excel_buf,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="perf_report_excel_dl",
    )


def render_portfolio_analysis(df, is_realtime=False, raw_holdings_list=None):
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
        _prog = st.progress(0, text="Preparing symbols…")
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
        _prog.progress(10, text=f"Fetching real-time quotes for {len(unique_syms)} symbols…")
        quotes = fetch_realtime_quotes(unique_syms)
        _prog.progress(30, text=f"Fetching 10-year price history for {len(unique_syms)} symbols (this takes ~15–30 s)…")
        perf   = fetch_performance_metrics(unique_syms)
        _prog.progress(75, text=f"Building report rows for {len(df)} holdings…")
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
                "30d %":     p.get("30d"),
                "90d %":     p.get("90d"),
                "180d %":    p.get("180d"),
                "YTD %":     p.get("ytd"),
                "1-Year %":  p.get("1y"),
                "3-Yr Ann %": p.get("3y"),
                "5-Yr Ann %": p.get("5y"),
                "10-Yr Ann %": p.get("10y"),
            })

        _prog.progress(92, text="Saving report…")
        perf_df = pd.DataFrame(rows)
        # Save report data to a temp JSON in the user dir
        user_dir = ensure_user_dirs()
        import datetime as _dt2
        report_file = os.path.join(user_dir, f"perf_report_{_dt2.date.today().isoformat()}.json")
        perf_df.to_json(report_file, orient="records")

        # Save holdings sidecar so the performance report page can embed the sheets
        holdings_sidecar = os.path.join(user_dir, f"perf_report_{_dt2.date.today().isoformat()}_holdings.json")
        _sidecar = {
            "holdings": df.to_dict(orient="records"),
            "raw_holdings_list": raw_holdings_list or [],
        }
        import json as _json
        with open(holdings_sidecar, "w", encoding="utf-8") as _sf:
            _json.dump(_sidecar, _sf)

        _prog.progress(100, text=f"Done — {len(rows)} holdings processed.")
        _prog.empty()

        report_url = f"?report=1&report_file={quote_plus(report_file)}"
        st.markdown(
            f'<a href="{report_url}" target="_blank" style="display:inline-block;padding:8px 16px;'
            f'background:#1A6B3C;color:white;border-radius:6px;text-decoration:none;font-weight:bold;">'
            f'📊 Open Performance Report ↗</a>',
            unsafe_allow_html=True,
        )

    # --- LLM Portfolio Review Button ---
    st.subheader("Portfolio Review by AI")
    stats = calculate_portfolio_statistics(df, raw_holdings_list=raw_holdings_list)
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
    stats = calculate_portfolio_statistics(df, raw_holdings_list=raw_holdings_list)

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

        if 'tax_allocation' in stats and not stats['tax_allocation'].empty:
            _TAX_COLOURS = {
                "Taxable":           "#3B82F6",
                "Tax-Deferred":      "#F59E0B",
                "Tax-Exempt (Roth)": "#10B981",
            }
            with st.expander("Tax-Status Allocation", expanded=True):
                _ta = stats['tax_allocation']
                _pie_cols = st.columns([1, 1])
                with _pie_cols[0]:
                    _fig_tax = px.pie(
                        _ta,
                        names="Tax Status",
                        values="Value",
                        color="Tax Status",
                        color_discrete_map=_TAX_COLOURS,
                        title="Portfolio by Tax Status",
                        hole=0.4,
                    )
                    _fig_tax.update_traces(textposition="inside", textinfo="percent+label")
                    _fig_tax.update_layout(height=320, margin=dict(t=40, l=10, r=10, b=10), showlegend=False)
                    st.plotly_chart(_fig_tax, width="stretch")
                with _pie_cols[1]:
                    st.dataframe(
                        _ta.assign(Value=_ta["Value"].map("${:,.2f}".format),
                                   **{"% of Portfolio": _ta["% of Portfolio"].map("{:.1f}%".format)}
                                  )[["Tax Status", "Value", "% of Portfolio"]],
                        hide_index=True,
                    )
                    st.caption(
                        "**Taxable** — brokerage / individual / joint accounts  \n"
                        "**Tax-Deferred** — Traditional IRA, 401(k), 403(b), SEP-IRA, SIMPLE IRA, rollover IRA, etc.  \n"
                        "**Tax-Exempt (Roth)** — Roth IRA, Roth 401(k)"
                    )

                if 'tax_allocation_by_account' in stats and not stats['tax_allocation_by_account'].empty:
                    st.markdown("**By Account**")
                    _ab = stats['tax_allocation_by_account'].copy()
                    _ab["Value"] = _ab["Value"].map("${:,.2f}".format)
                    _ab["% of Portfolio"] = _ab["% of Portfolio"].map("{:.1f}%".format)
                    st.dataframe(_ab, hide_index=True)

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


def calculate_portfolio_statistics(df, raw_holdings_list=None):
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
            # Accept either 'Ticker' or 'Symbol' as the symbol column
            _sym_col = 'Ticker' if 'Ticker' in df.columns else ('Symbol' if 'Symbol' in df.columns else None)
            column_mapping = {
                'Symbol': _sym_col,
                'Name': 'Name' if 'Name' in df.columns else None,
            }

            # Check if any mapped columns are missing
            missing_columns = [exp for exp, act in column_mapping.items() if act is None]
            if missing_columns:
                stats['error'] = f"Missing required columns: {', '.join(missing_columns)}"
                return stats

            # Create a copy with standardized column names for easier processing
            df_mapped = df.copy()
            if _sym_col != 'Symbol':
                df_mapped['Symbol'] = df[_sym_col]

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

            # ── Tax-status allocation ─────────────────────────────────────────
            # Prefer raw_holdings_list (per-account rows) for accurate account names.
            # Fall back to consolidated df if no raw list provided.
            _tax_rows = []
            if raw_holdings_list:
                for _rh in raw_holdings_list:
                    _acct = _rh.get("Account", "") or ""
                    _val  = pd.to_numeric(_rh.get("Value", 0), errors="coerce") or 0.0
                    if _val:
                        _tax_rows.append({"Account": _acct, "Value_numeric": _val,
                                          "Tax Status": classify_tax_status(_acct)})
            elif "Account" in df_mapped.columns:
                for _, _row in df_mapped.iterrows():
                    _acct = str(_row.get("Account", "") or "")
                    _val  = pd.to_numeric(_row.get("Value_numeric", 0), errors="coerce") or 0.0
                    if _val:
                        _tax_rows.append({"Account": _acct, "Value_numeric": _val,
                                          "Tax Status": classify_tax_status(_acct)})

            if _tax_rows:
                _tax_df = pd.DataFrame(_tax_rows)
                _tax_total = _tax_df["Value_numeric"].sum()
                _tax_summary = (
                    _tax_df.groupby("Tax Status")["Value_numeric"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Value_numeric": "Value"})
                )
                _tax_summary["% of Portfolio"] = _tax_summary["Value"] / _tax_total * 100
                _order = ["Taxable", "Tax-Deferred", "Tax-Exempt (Roth)"]
                _tax_summary["_sort"] = _tax_summary["Tax Status"].map(
                    {v: i for i, v in enumerate(_order)}
                ).fillna(99)
                _tax_summary = _tax_summary.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
                stats["tax_allocation"] = _tax_summary

                # Account-level breakdown (aggregated per account)
                _acct_tax = (
                    _tax_df.groupby(["Account", "Tax Status"])["Value_numeric"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Value_numeric": "Value"})
                    .sort_values("Value", ascending=False)
                    .reset_index(drop=True)
                )
                _acct_tax["% of Portfolio"] = _acct_tax["Value"] / _tax_total * 100
                stats["tax_allocation_by_account"] = _acct_tax

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
        file.write("=" * 100 + "\n\n")

        # Summary statistics
        file.write("SUMMARY STATISTICS\n")
        file.write("-" * 50 + "\n")
        W = 30  # label width
        file.write(f"{'Total Portfolio Value:':<{W}} ${stats['total_value']:>15,.2f}\n")
        file.write(f"{'Number of Holdings:':<{W}} {stats['count']:>16}\n")
        file.write(f"{'Average Holding Value:':<{W}} ${stats['avg_value']:>15,.2f}\n")
        file.write(f"{'Median Holding Value:':<{W}} ${stats['median_value']:>15,.2f}\n")
        file.write(f"{'Standard Deviation:':<{W}} ${stats['std_dev']:>15,.2f}\n")
        file.write(f"{'Largest Holding:':<{W}} ${stats['max_value']:>15,.2f}\n")
        file.write(f"{'Smallest Holding:':<{W}} ${stats['min_value']:>15,.2f}\n")
        file.write(f"{'Value Range:':<{W}} ${stats['value_range']:>15,.2f}\n\n")

        # Concentration metrics
        file.write("CONCENTRATION METRICS\n")
        file.write("-" * 50 + "\n")
        file.write(f"{'Top 5 Holdings:':<{W}} {stats['top_5_pct']:>14.2f}%  of portfolio\n")
        file.write(f"{'Top 10 Holdings:':<{W}} {stats['top_10_pct']:>14.2f}%  of portfolio\n")
        file.write(f"{'HHI Concentration Score:':<{W}} {stats['hhi']:>14.2f}  ({stats['concentration']})\n\n")

        # Asset allocation if available
        if 'asset_allocation' in stats:
            file.write("ASSET ALLOCATION\n")
            file.write("-" * 60 + "\n")
            file.write(f"{'Category':<30} {'Weight %':>10}   {'Value':>15}\n")
            file.write("-" * 60 + "\n")
            for idx, row in stats['asset_allocation'].iterrows():
                cat = str(row['Category'])[:29]
                pct = row['pct_of_total']
                val = row['Value_numeric']
                file.write(f"{cat:<30} {pct:>9.2f}%   ${val:>14,.2f}\n")
            file.write("\n")

        # Top holdings
        file.write("TOP HOLDINGS\n")
        file.write("-----------\n")
        file.write(f"{'Rank':<6} {'Ticker':<10} {'Name':<35} {'Value':<15} {'Weight %':<10}\n")
        file.write("-" * 78 + "\n")

        top_holdings = stats['holdings_pct'].head(10)
        for rank, (idx, row) in enumerate(top_holdings.iterrows(), 1):
            sym = str(row.get('Symbol', ''))[:9]
            nm  = str(row.get('Name', ''))[:34]
            val = row.get('Value_numeric', 0)
            pct = row.get('pct_of_total', 0)
            file.write(f"{rank:<6} {sym:<10} {nm:<35} ${val:<14,.2f} {pct:.2f}%\n")

        if len(stats['holdings_pct']) > 10:
            others_sum = stats['holdings_pct'].iloc[10:]['pct_of_total'].sum()
            others_value = others_sum / 100 * stats['total_value']
            file.write(f"{'':6} {'(other)':<10} {'':<35} ${others_value:<14,.2f} {others_sum:.2f}%\n")
        file.write("\n")

        # All holdings sorted by value
        file.write("\nALL HOLDINGS (by value)\n")
        file.write("-" * 100 + "\n")
        file.write(f"{'Ticker':<10} {'Name':<35} {'Shares':<12} {'Price':<12} {'Value':<15} {'Type':<10}\n")
        file.write("-" * 100 + "\n")

        for idx, row in df.sort_values('Value_numeric', ascending=False).iterrows():
            ticker = str(row.get('Ticker', row.get('Symbol', '')))[:9]
            name   = str(row.get('Name', ''))[:34]
            value  = row.get('Value_numeric', row.get('Value', 0))
            try:
                shares = float(row.get('Shares', 0) or 0)
                shares_str = f"{shares:.2f}"
            except (TypeError, ValueError):
                shares_str = str(row.get('Shares', ''))
            try:
                price = float(row.get('Price', 0) or 0)
                price_str = f"${price:.2f}"
            except (TypeError, ValueError):
                price_str = str(row.get('Price', ''))
            htype = str(row.get('Type', row.get('Asset Type', '')))[:9]
            file.write(f"{ticker:<10} {name:<35} {shares_str:<12} {price_str:<12} ${value:<14,.2f} {htype:<10}\n")

    return report_path

