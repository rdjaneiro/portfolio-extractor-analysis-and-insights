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
st.set_page_config(
    page_title="Empower Portfolio & Net Worth Extractor",
    layout="wide",
    page_icon="📈",
)

# ── Global modern UI stylesheet ───────────────────────────────────────────────
_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── App background ── */
.stApp {
    background: linear-gradient(135deg, #0f1117 0%, #1a1d2e 100%);
    color: #e8eaf0;
}

/* ── Main block padding ── */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* ── Headings ── */
h1 { font-size: 2rem !important; font-weight: 700 !important; color: #f0f2ff !important; letter-spacing: -0.5px; }
h2 { font-size: 1.5rem !important; font-weight: 600 !important; color: #dde1f5 !important; }
h3 { font-size: 1.15rem !important; font-weight: 600 !important; color: #c5cae8 !important; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #1e2235, #252a40);
    border: 1px solid #2e3350;
    border-radius: 12px;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.35);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
}
[data-testid="stMetricLabel"] { color: #8892b0 !important; font-size: 0.78rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.06em; }
[data-testid="stMetricValue"] { color: #ccd6f6 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] svg { display: none; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #4f8ef7 0%, #3a7bd5 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.25rem !important;
    letter-spacing: 0.02em;
    box-shadow: 0 2px 8px rgba(79,142,247,0.35);
    transition: opacity 0.2s ease, transform 0.15s ease, box-shadow 0.2s ease !important;
}
.stButton > button:hover {
    opacity: 0.92 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(79,142,247,0.5) !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #27ae60 0%, #4ade80 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(39,174,96,0.35);
    transition: opacity 0.2s ease, transform 0.15s ease !important;
}
.stDownloadButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}

/* ── Dataframes / tables ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: #1a1d2e !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #8892b0 !important;
    font-weight: 500 !important;
    transition: background 0.2s ease, color 0.2s ease !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg, #4f8ef7, #3a7bd5) !important;
    color: #fff !important;
    font-weight: 600 !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: #1e2235 !important;
    border: 1px solid #2e3350 !important;
    border-radius: 10px !important;
    margin-bottom: 0.5rem;
}

/* ── Alerts / info banners ── */
.stAlert {
    border-radius: 10px !important;
    border-left-width: 4px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0f1a 0%, #141728 100%) !important;
    border-right: 1px solid #1e2235 !important;
}
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
    color: #c5cae8 !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #dde1f5 !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100% !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #1e2235 !important;
    border: 2px dashed #2e3350 !important;
    border-radius: 10px !important;
    padding: 1rem !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #4f8ef7 !important;
}

/* ── Divider ── */
hr {
    border-color: #2e3350 !important;
    margin: 1.5rem 0 !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #4f8ef7 !important; }

/* ── Captions ── */
.stCaption { color: #636b87 !important; font-size: 0.78rem !important; }

/* ── Select boxes & inputs ── */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #1e2235 !important;
    border-color: #2e3350 !important;
    border-radius: 8px !important;
    color: #c5cae8 !important;
}
</style>
"""
st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


from fintools_helpers import *


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

    refresh_raw = str(query_params.get("refresh", "900")).strip()
    try:
        realtime_refresh_seconds = max(5, min(900, int(refresh_raw)))
    except ValueError:
        realtime_refresh_seconds = 900

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
    if "processed_result" not in st.session_state:
        result = None
    else:
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

        # Resolve content type early so download section can use it
        content_type = result.get("content_type", "portfolio")

        # --- DOWNLOAD OPTIONS SECTION (not shown for transactions or net_worth — they handle downloads inline) ---
        if content_type not in ("transactions", "net_worth"):
            if content_type not in ("accounts",):
                st.header("Portfolio Holdings")
            col1, col2, col3 = st.columns(3)

            # Provide CSV download
            if result["csv_path"]:
                csv_df = pd.read_csv(result["csv_path"])
                csv_data = csv_df.to_csv(index=False)

                with col1:
                    download_csv = st.download_button(
                        label="Download CSV File",
                        data=csv_data,
                        file_name=os.path.basename(result["csv_path"]),
                        mime="text/csv",
                        key="download_csv"
                    )

            # Holdings Excel download (portfolio only — not applicable for accounts/networth/transactions)
            if result["csv_path"] and content_type not in ("accounts", "net_worth"):
                _holdings_stats = calculate_portfolio_statistics(
                    pd.read_csv(result["csv_path"]),
                    raw_holdings_list=result.get("raw_holdings_list"),
                )
                excel_buf = build_holdings_excel(
                    result["csv_path"],
                    result.get("raw_holdings_list"),
                    stats=_holdings_stats if "error" not in _holdings_stats else None,
                )
                xlsx_name = os.path.basename(result["csv_path"]).replace(".csv", ".xlsx")
                with col2:
                    st.download_button(
                        label="Download Excel File",
                        data=excel_buf,
                        file_name=xlsx_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_holdings_excel"
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
        if content_type == "net_worth":
            # Display net worth data
            if result["holdings"] and df is not None:
                st.header("Net Worth Summary")

                # CSV download inline (replaces the top-level Download Options section for net worth)
                if result["csv_path"]:
                    _nw_csv_df = pd.read_csv(result["csv_path"])
                    st.download_button(
                        label="Download CSV File",
                        data=_nw_csv_df.to_csv(index=False),
                        file_name=os.path.basename(result["csv_path"]),
                        mime="text/csv",
                        key="download_networth_csv"
                    )

                # Calculate net worth statistics up front so the overview appears immediately below
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
                    # Net Worth Overview immediately below the summary header
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

                    # Build CSV for download (all dates, all category columns, sorted newest first)
                    _cols_to_drop = ['Account', 'Type', 'Category']
                    _download_df = df.drop(columns=[c for c in _cols_to_drop if c in df.columns])
                    _download_df = _download_df.sort_values('Date', ascending=False)
                    _csv_bytes = _download_df.to_csv(index=False).encode('utf-8')
                    # Derive a filename from the uploaded file name
                    _upload_name = os.path.splitext(os.path.basename(result.get("raw_data_path") or "networth_history"))[0]
                    st.download_button(
                        label="Download History CSV",
                        data=_csv_bytes,
                        file_name=f"{_upload_name}_history.csv",
                        mime="text/csv",
                        key="download_networth_history_csv"
                    )

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

                if 'error' not in stats:
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

        elif content_type == "accounts":
            # ── Accounts snapshot display ─────────────────────────────────────
            accounts_data = result.get("holdings", {})
            totals = accounts_data.get("totals", {}) if isinstance(accounts_data, dict) else {}
            all_accounts = accounts_data.get("accounts", []) if isinstance(accounts_data, dict) else []

            st.header("Accounts Snapshot")

            # Summary metrics row 1
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Net Worth", f"${totals.get('networth', 0):,.2f}")
            with c2:
                st.metric("Total Assets", f"${totals.get('assets', 0):,.2f}")
            with c3:
                st.metric("Total Liabilities", f"${totals.get('liabilities', 0):,.2f}")

            # Summary metrics row 2
            c4, c5, c6, c7, c8 = st.columns(5)
            with c4:
                st.metric("Investment", f"${totals.get('investmentAccountsTotal', 0):,.2f}")
            with c5:
                st.metric("Cash", f"${totals.get('cashAccountsTotal', 0):,.2f}")
            with c6:
                st.metric("Other Assets", f"${totals.get('otherAssetAccountsTotal', 0):,.2f}")
            with c7:
                st.metric("Credit Cards", f"${totals.get('creditCardAccountsTotal', 0):,.2f}")
            with c8:
                st.metric("Mortgage + Loans", f"${totals.get('mortgageAccountsTotal', 0) + totals.get('loanAccountsTotal', 0):,.2f}")

            # Charts
            if all_accounts:
                import plotly.express as _px
                from collections import defaultdict as _dd

                # Build group summary
                group_totals = _dd(float)
                for a in all_accounts:
                    if not a.get("closedDate") and a.get("isAsset"):
                        group_totals[a.get("accountTypeGroup", "Other")] += abs(a.get("balance", 0))

                gt_df = pd.DataFrame(
                    [{"Group": k, "Balance": v} for k, v in sorted(group_totals.items(), key=lambda x: -x[1]) if v > 0]
                )
                if not gt_df.empty:
                    ch1, ch2 = st.columns(2)
                    with ch1:
                        fig_pie = _px.pie(gt_df, values="Balance", names="Group",
                                          title="Assets by Account Group",
                                          color_discrete_sequence=_px.colors.qualitative.Bold)
                        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
                        st.plotly_chart(fig_pie, width="stretch")
                    with ch2:
                        fig_bar = _px.bar(gt_df, x="Balance", y="Group", orientation="h",
                                          title="Assets by Account Group",
                                          text_auto=True,
                                          color="Group",
                                          color_discrete_sequence=_px.colors.qualitative.Bold)
                        fig_bar.update_layout(showlegend=False)
                        st.plotly_chart(fig_bar, width="stretch")

                # Account table with tabs by group
                _group_order = ["INVESTMENT", "RETIREMENT", "BANK", "CREDIT_CARD",
                                 "MORTGAGE", "LINE", "REVOLVING_CREDIT",
                                 "CRYPTO_CURRENCY", "ESOP", "TRUST", ""]
                _groups_present = sorted(set(a.get("accountTypeGroup", "") for a in all_accounts),
                                         key=lambda g: _group_order.index(g) if g in _group_order else 99)
                tab_labels = ["All"] + [g if g else "Other" for g in _groups_present]
                tabs = st.tabs(tab_labels)

                def _build_acct_df(accts):
                    rows = []
                    for a in accts:
                        rows.append({
                            "Name":        a.get("name", ""),
                            "Institution": a.get("firmName", ""),
                            "Group":       a.get("accountTypeGroup", ""),
                            "Balance":     a.get("balance", 0),
                            "Liability":   a.get("isLiability", False),
                            "Closed":      bool(a.get("closedDate", "")),
                            "Tax Deferred": a.get("isTaxDeferredOrNonTaxable", False),
                            "Manual":      a.get("isManual", False),
                            "Crypto":      a.get("isCrypto", False),
                        })
                    df_ = pd.DataFrame(rows)
                    if not df_.empty:
                        df_ = df_.sort_values("Balance", ascending=False)
                    return df_

                with tabs[0]:  # All
                    st.dataframe(_build_acct_df(all_accounts), hide_index=True)

                for idx, grp in enumerate(_groups_present):
                    with tabs[idx + 1]:
                        grp_accts = [a for a in all_accounts if a.get("accountTypeGroup", "") == grp]
                        st.dataframe(_build_acct_df(grp_accts), hide_index=True)

            # ── Account Histories ─────────────────────────────────────────────
            st.markdown("---")
            st.subheader("Account Histories")
            st.caption(
                "Upload a `networthSummaryHistories_*.json` file captured from the "
                "**Overview → Net Worth** Empower page to see per-account balance timelines."
            )

            hist_file = st.file_uploader(
                "Upload Histories JSON",
                type=["json"],
                key="accounts_histories_upload",
            )

            if hist_file is not None:
                # Save upload to user dir
                user_dir = ensure_user_files_dir()
                hist_path = os.path.join(user_dir, hist_file.name)
                with open(hist_path, "wb") as _hf:
                    _hf.write(hist_file.getvalue())

                with st.spinner("Parsing account histories…"):
                    hist_result = parse_account_histories(hist_path, accounts_data)

                if isinstance(hist_result, str):
                    st.error(f"Could not parse histories file: {hist_result}")
                else:
                    tl_df = hist_result["timeline_df"]
                    acct_cols = hist_result["account_cols"]
                    interval = hist_result["interval_type"].capitalize()

                    # ── Summary change metrics ────────────────────────────────
                    hs = hist_result["histories_summary"]
                    if hs:
                        m1, m2, m3, m4 = st.columns(4)
                        rng_chg   = hs.get("dateRangeChange", None)
                        rng_pct   = hs.get("dateRangePercentageChange", None)
                        inv_chg   = hs.get("dateRangeInvestmentChange", None)
                        cash_chg  = hs.get("dateRangeCashChange", None)
                        with m1:
                            if rng_chg is not None:
                                st.metric("Net Worth Change (range)", f"${rng_chg:+,.2f}")
                        with m2:
                            if rng_pct is not None:
                                st.metric("Net Worth Change %", f"{rng_pct:+.2f}%")
                        with m3:
                            if inv_chg is not None:
                                st.metric("Investment Change", f"${inv_chg:+,.2f}")
                        with m4:
                            if cash_chg is not None:
                                st.metric("Cash Change", f"${cash_chg:+,.2f}")

                    # ── Date range info ───────────────────────────────────────
                    date_min = tl_df["Date"].min().strftime("%Y-%m-%d")
                    date_max = tl_df["Date"].max().strftime("%Y-%m-%d")
                    st.caption(
                        f"{len(acct_cols)} accounts with non-zero balance  ·  "
                        f"{len(tl_df)} {interval} records  ·  {date_min} → {date_max}"
                    )

                    # ── Aggregate balance line chart ──────────────────────────
                    agg_fig = go.Figure()
                    agg_fig.add_trace(go.Scatter(
                        x=tl_df["Date"],
                        y=tl_df["Net Worth"],
                        mode="lines",
                        name="Net Worth",
                        line=dict(color="#4f8ef7", width=2),
                        hovertemplate="%{x|%Y-%m-%d}<br>$%{y:,.2f}<extra></extra>",
                    ))
                    agg_fig.update_layout(
                        title="Net Worth Over Time",
                        xaxis_title="Date",
                        yaxis_title="Balance ($)",
                        hovermode="x unified",
                        legend=dict(orientation="h", y=-0.15),
                        margin=dict(l=0, r=0, t=40, b=0),
                    )
                    st.plotly_chart(agg_fig, width="stretch")

                    # ── Per-account line chart (top 10 by latest balance) ─────
                    # Sort acct_cols by last non-zero value in the timeline
                    def _last_val(col):
                        s = tl_df[col].replace(0, pd.NA).dropna()
                        return abs(s.iloc[-1]) if len(s) else 0

                    top_cols = sorted(acct_cols, key=_last_val, reverse=True)[:10]

                    per_fig = go.Figure()
                    palette = px.colors.qualitative.Bold
                    for i, col in enumerate(top_cols):
                        per_fig.add_trace(go.Scatter(
                            x=tl_df["Date"],
                            y=tl_df[col],
                            mode="lines",
                            name=col,
                            line=dict(color=palette[i % len(palette)]),
                            hovertemplate=f"<b>{col}</b><br>%{{x|%Y-%m-%d}}<br>${{y:,.2f}}<extra></extra>",
                        ))
                    per_fig.update_layout(
                        title="Top 10 Accounts by Latest Balance",
                        xaxis_title="Date",
                        yaxis_title="Balance ($)",
                        hovermode="x unified",
                        legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
                        margin=dict(l=0, r=0, t=40, b=0),
                    )
                    st.plotly_chart(per_fig, width="stretch")

                    # ── Data table ────────────────────────────────────────────
                    st.subheader("Timeline Data Table")
                    display_tl = tl_df.copy()
                    display_tl["Date"] = display_tl["Date"].dt.strftime("%Y-%m-%d")
                    # Put Aggregate Balance first, then accounts sorted by latest balance
                    col_order = ["Date", "Net Worth"] + sorted(
                        acct_cols, key=_last_val, reverse=True
                    )
                    display_tl = display_tl[col_order].sort_values("Date", ascending=False)
                    st.dataframe(display_tl, hide_index=True)

                    # ── CSV download ─────────────────────────────────────────
                    csv_hist_name = os.path.basename(hist_path).replace(".json", "_account_timelines.csv")
                    st.download_button(
                        label="Download Account Histories CSV",
                        data=display_tl.to_csv(index=False).encode("utf-8"),
                        file_name=csv_hist_name,
                        mime="text/csv",
                        key="download_account_histories_csv",
                    )

                    # ── Investment Account Performance ────────────────────────
                    st.markdown("---")
                    st.subheader("Investment Account Performance")

                    perf_df = compute_account_performance(
                        tl_df, acct_cols, hist_result["account_map"]
                    )

                    if perf_df.empty:
                        st.info("No investment accounts with sufficient history to compute performance.")
                    else:
                        today_date = tl_df["Date"].max()
                        data_start = tl_df["Date"].min()

                        # Determine which period columns actually have data
                        period_pairs = [
                            ("30d",  today_date - pd.Timedelta(days=30),  False),
                            ("90d",  today_date - pd.Timedelta(days=90),  False),
                            ("YTD",  pd.Timestamp(today_date.year, 1, 1), True),
                            ("1yr",  today_date - pd.Timedelta(days=365), False),
                        ]

                        available_periods = []
                        period_notes = {}
                        for p_label, p_target, p_ytd in period_pairs:
                            col_dollar = f"{p_label} $"
                            col_pct    = f"{p_label} %"
                            if col_dollar in perf_df.columns and perf_df[col_dollar].notna().any():
                                available_periods.append(p_label)
                                if p_ytd and "YTD Note" in perf_df.columns:
                                    sample_note = perf_df["YTD Note"].dropna()
                                    sample_note = sample_note[sample_note != ""].values
                                    if len(sample_note):
                                        period_notes["YTD"] = f"YTD ({sample_note[0]})"
                                elif p_target < data_start:
                                    period_notes[p_label] = f"{p_label} (partial)"

                        st.caption(
                            f"Based on {len(tl_df)}-day history ({data_start.strftime('%b %d')} → "
                            f"{today_date.strftime('%b %d, %Y')})  ·  "
                            f"{len(perf_df)} investment/retirement accounts"
                            + ("  ·  * = partial period (data starts after period start)" if period_notes else "")
                        )

                        # Build display DataFrame
                        display_cols = ["Account", "Group", "Institution", "Latest Balance"]
                        for p_label in available_periods:
                            display_cols += [f"{p_label} $", f"{p_label} %"]

                        disp_perf = perf_df[display_cols].copy()

                        # Rename YTD columns if partial
                        if "YTD" in period_notes:
                            rename_map = {
                                "YTD $": f"{period_notes['YTD']} $",
                                "YTD %": f"{period_notes['YTD']} %",
                            }
                            disp_perf = disp_perf.rename(columns=rename_map)

                        # Format currency & pct for display
                        def _fmt_dollar(v):
                            if v is None or (isinstance(v, float) and pd.isna(v)):
                                return "—"
                            return f"${v:+,.0f}"

                        def _fmt_pct(v):
                            if v is None or (isinstance(v, float) and pd.isna(v)):
                                return "—"
                            return f"{v:+.2f}%"

                        styled_rows = []
                        for _, r in disp_perf.iterrows():
                            styled_row = {
                                "Account":        r["Account"],
                                "Group":          r["Group"],
                                "Institution":    r["Institution"],
                                "Latest Balance": f"${r['Latest Balance']:,.2f}",
                            }
                            for col in disp_perf.columns:
                                if col.endswith(" $") and col not in styled_row:
                                    styled_row[col] = _fmt_dollar(r[col])
                                elif col.endswith(" %") and col not in styled_row:
                                    styled_row[col] = _fmt_pct(r[col])
                            styled_rows.append(styled_row)

                        styled_df = pd.DataFrame(styled_rows)

                        # Compute totals row
                        # Build a mapping: display col name -> raw perf_df col name
                        raw_col_map = {}
                        for col in disp_perf.columns:
                            if col in perf_df.columns:
                                raw_col_map[col] = col
                            else:
                                # renamed (e.g. "YTD (from Feb 01) $" -> "YTD $")
                                for raw_c in perf_df.columns:
                                    if raw_c.endswith(" $") or raw_c.endswith(" %"):
                                        suffix = " $" if col.endswith(" $") else " %"
                                        period_raw = raw_c[:-2]
                                        if col.startswith(period_raw) and col.endswith(suffix):
                                            raw_col_map[col] = raw_c
                                            break

                        total_bal = perf_df["Latest Balance"].sum()
                        total_row = {
                            "Account":        "TOTAL",
                            "Group":          "",
                            "Institution":    "",
                            "Latest Balance": f"${total_bal:,.2f}",
                        }
                        for col in disp_perf.columns:
                            if col in ("Account", "Group", "Institution", "Latest Balance"):
                                continue
                            raw_c = raw_col_map.get(col)
                            if raw_c is None:
                                total_row[col] = "—"
                            elif col.endswith(" $"):
                                s = perf_df[raw_c].dropna().sum()
                                total_row[col] = f"${s:+,.0f}"
                            elif col.endswith(" %"):
                                mask = perf_df[raw_c].notna()
                                if mask.any():
                                    w = perf_df.loc[mask, "Latest Balance"]
                                    v = perf_df.loc[mask, raw_c]
                                    wavg = (v * w).sum() / w.sum()
                                    total_row[col] = f"{wavg:+.2f}%"
                                else:
                                    total_row[col] = "—"
                        styled_df = pd.concat(
                            [styled_df, pd.DataFrame([total_row])], ignore_index=True
                        )

                        st.dataframe(styled_df, hide_index=True)

                        # Download — raw numeric CSV (unformatted)
                        csv_perf_name = os.path.basename(hist_path).replace(".json", "_investment_performance.csv")
                        dl_perf = perf_df[display_cols].copy()
                        st.download_button(
                            label="Download Investment Performance CSV",
                            data=dl_perf.to_csv(index=False).encode("utf-8"),
                            file_name=csv_perf_name,
                            mime="text/csv",
                            key="download_investment_perf_csv",
                        )


        if content_type == "transactions":
            txn_data = result.get("holdings", {})
            transactions = txn_data.get("transactions", []) if isinstance(txn_data, dict) else []

            st.header("💰 Transactions")

            # Summary metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Money In", f"${txn_data.get('money_in', 0):,.2f}")
            with c2:
                st.metric("Money Out", f"${txn_data.get('money_out', 0):,.2f}")
            with c3:
                st.metric("Net Cashflow", f"${txn_data.get('net_cashflow', 0):,.2f}")
            with c4:
                st.metric("Avg Monthly In", f"${txn_data.get('average_in', 0):,.2f}")
            with c5:
                st.metric("Avg Monthly Out", f"${txn_data.get('average_out', 0):,.2f}")

            st.caption(
                f"Period: {txn_data.get('start_date', '')} → {txn_data.get('end_date', '')}  |  "
                f"Interval: {txn_data.get('interval_type', '')}  |  "
                f"Total transactions: {txn_data.get('count', 0)}"
            )

            if transactions:
                txn_df = pd.DataFrame(transactions)
                txn_df['Date'] = pd.to_datetime(txn_df['Date'], errors='coerce')
                txn_df = txn_df.sort_values('Date', ascending=False)
                txn_df['Date'] = txn_df['Date'].dt.strftime('%Y-%m-%d')

                # === EXPORT OPTIONS ===
                st.subheader("📥 Export Options")
                ex_col1, ex_col2, ex_col3, ex_col4 = st.columns(4)

                with ex_col1:
                    # Full transactions export
                    import csv as _csv_mod
                    from fintools_helpers import save_transactions_json_to_csv
                    _txn_df = pd.DataFrame(transactions)
                    if 'CUSIP' in _txn_df.columns:
                        _txn_df['CUSIP'] = _txn_df['CUSIP'].astype(str)
                    # Ensure priority columns appear first
                    _priority_cols = ['Date', 'Account', 'Description', 'Category', 'Tags', 'Amount']
                    _rest_cols = [c for c in _txn_df.columns if c not in _priority_cols]
                    _txn_df = _txn_df[[c for c in _priority_cols if c in _txn_df.columns] + _rest_cols]
                    csv_buf = _txn_df.to_csv(index=False, quoting=_csv_mod.QUOTE_NONNUMERIC)
                    st.download_button(
                        label="📋 All Transactions",
                        data=csv_buf.encode("utf-8"),
                        file_name=os.path.basename(result.get("csv_path", "transactions.csv")),
                        mime="text/csv",
                        key="download_txn_all_csv",
                    )

                with ex_col2:
                    # Cash flow export
                    from fintools_helpers import export_transactions_cash_flow_csv
                    cash_df = txn_df[txn_df['Category Type'].isin(['EXPENSE', 'INCOME'])].copy()
                    if not cash_df.empty:
                        _cash_cols = ['Date', 'Account', 'Description', 'Category', 'Tags', 'Amount',
                                      'Is Credit', 'Category Type', 'Transaction Type', 'Is Income', 'Is Spending']
                        cash_df_export = cash_df[[c for c in _cash_cols if c in cash_df.columns]].copy()
                        cash_buf = cash_df_export.to_csv(index=False)
                        st.download_button(
                            label="💵 Cash Flow",
                            data=cash_buf.encode("utf-8"),
                            file_name=os.path.basename(result.get("csv_path", "transactions.csv")).replace(".csv", "_cash_flow.csv"),
                            mime="text/csv",
                            key="download_txn_cash_csv",
                        )

                with ex_col3:
                    # Investment export (portfolio trades only, excluding dividends/interest which are in cash flow)
                    invest_df = txn_df[(txn_df['Investment Type'].notna()) &
                                       (txn_df['Investment Type'] != '') &
                                       (txn_df['Investment Type'].isin(['Buy', 'Sell', 'Fund Exchange', 'Shares In', 'Shares Out']))].copy()
                    if not invest_df.empty:
                        invest_df_export = invest_df[[
                            'Date', 'Account', 'Description', 'Symbol', 'Investment Type',
                            'Quantity', 'Price', 'Amount', 'Is Credit', 'Category'
                        ]].copy()
                        invest_buf = invest_df_export.to_csv(index=False)
                        st.download_button(
                            label="📈 Investments",
                            data=invest_buf.encode("utf-8"),
                            file_name=os.path.basename(result.get("csv_path", "transactions.csv")).replace(".csv", "_investments.csv"),
                            mime="text/csv",
                            key="download_txn_invest_csv",
                        )

                with ex_col4:
                    # Transfers export
                    transfer_df = txn_df[(txn_df['Category Type'] == 'TRANSFER') &
                                        (txn_df['Investment Type'].isna() | (txn_df['Investment Type'] == ''))].copy()
                    if not transfer_df.empty:
                        transfer_df_export = transfer_df[[
                            'Date', 'Account', 'Description', 'Amount', 'Is Credit',
                            'Transaction Type', 'Category Type'
                        ]].copy()
                        transfer_buf = transfer_df_export.to_csv(index=False)
                        st.download_button(
                            label="🔄 Transfers",
                            data=transfer_buf.encode("utf-8"),
                            file_name=os.path.basename(result.get("csv_path", "transactions.csv")).replace(".csv", "_transfers.csv"),
                            mime="text/csv",
                            key="download_txn_transfer_csv",
                        )

                st.divider()

                # === CASH TRANSACTIONS ===
                st.subheader("💰 Cash Transactions (Spending & Income)")
                cash_df = txn_df[txn_df['Category Type'].isin(['EXPENSE', 'INCOME'])].copy()
                cash_count = len(cash_df)
                st.caption(f"{cash_count} transactions")

                if not cash_df.empty:
                    import plotly.express as _px
                    _chart_view = st.radio(
                        "View", ["Expense", "Income", "Cash Flow"],
                        index=0, horizontal=True, label_visibility="collapsed",
                        key="cash_chart_view"
                    )

                    cf_df = cash_df.copy()
                    if _chart_view == "Expense":
                        _chart_df = cf_df[cf_df['Category Type'] == 'EXPENSE'].copy()
                        _cat_totals = _chart_df.groupby('Category')['Amount'].sum().reset_index()
                        # expenses are negative — sort ascending (most negative first)
                        _cat_totals = _cat_totals.sort_values('Amount', ascending=True).head(15)
                        _colors = ['#EF553B'] * len(_cat_totals)
                        _title = 'Top Expense Categories'
                        _total = _cat_totals['Amount'].sum()
                        st.caption(f"Total expenses shown: **${abs(_total):,.2f}**")
                    elif _chart_view == "Income":
                        _chart_df = cf_df[cf_df['Category Type'] == 'INCOME'].copy()
                        _cat_totals = _chart_df.groupby('Category')['Amount'].sum().reset_index()
                        _cat_totals = _cat_totals.sort_values('Amount', ascending=False).head(15)
                        _colors = ['#00CC96'] * len(_cat_totals)
                        _title = 'Top Income Categories'
                        _total = _cat_totals['Amount'].sum()
                        st.caption(f"Total income shown: **${_total:,.2f}**")
                    else:  # Cash Flow
                        _cat_totals = cf_df.groupby('Category')['Amount'].sum().reset_index()
                        _cat_totals = _cat_totals.sort_values('Amount', key=lambda s: s.abs(), ascending=False).head(15)
                        _colors = ['#00CC96' if x >= 0 else '#EF553B' for x in _cat_totals['Amount']]
                        _title = 'Top Cash Flow Categories (Income in Green, Expenses in Red)'
                        _net = cf_df['Amount'].sum()
                        st.caption(f"Net cash flow: **${_net:,.2f}**")

                    if not _cat_totals.empty:
                        fig_cat = _px.bar(_cat_totals, x='Category', y='Amount', orientation='v',
                                         title=_title, color_discrete_sequence=_colors)
                        fig_cat.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0),
                                              xaxis_tickangle=-35)
                        st.plotly_chart(fig_cat, width='stretch')

                    # Cash transactions table
                    cash_cols = ['Date', 'Account', 'Description', 'Amount', 'Category', 'Transaction Type', 'Is Income']
                    display_cash = cash_df[cash_cols].copy()
                    display_cash['Amount'] = display_cash.apply(
                        lambda r: f"+${r['Amount']:,.2f}" if r['Is Income'] else f"-${abs(r['Amount']):,.2f}",
                        axis=1
                    )
                    display_cash = display_cash.drop('Is Income', axis=1)
                    st.dataframe(display_cash, hide_index=True, width='stretch')

                st.divider()

                # === INVESTMENT ACTIVITY ===
                st.subheader("📈 Investment Activity (Portfolio Trades)")
                invest_df = txn_df[(txn_df['Investment Type'].notna()) &
                                   (txn_df['Investment Type'] != '') &
                                   (txn_df['Investment Type'].isin(['Buy', 'Sell', 'Fund Exchange', 'Shares In', 'Shares Out']))].copy()
                invest_count = len(invest_df)
                st.caption(f"{invest_count} portfolio transactions")

                if not invest_df.empty:
                    # Investment summary
                    inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)
                    with inv_col1:
                        buy_count = len(invest_df[invest_df['Investment Type'] == 'Buy'])
                        st.metric("Buys", buy_count)
                    with inv_col2:
                        sell_count = len(invest_df[invest_df['Investment Type'] == 'Sell'])
                        st.metric("Sells", sell_count)
                    with inv_col3:
                        exchange_count = len(invest_df[invest_df['Investment Type'] == 'Fund Exchange'])
                        st.metric("Exchanges", exchange_count)
                    with inv_col4:
                        transfer_count = len(invest_df[invest_df['Investment Type'].isin(['Shares In', 'Shares Out'])])
                        st.metric("Share Transfers", transfer_count)

                    # Investment transactions table
                    invest_cols = ['Date', 'Account', 'Investment Type', 'Symbol', 'Description', 'Quantity', 'Price', 'Amount']
                    display_invest = invest_df[invest_cols].copy()
                    display_invest['Amount'] = display_invest['Amount'].apply(lambda x: f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
                    display_invest['Quantity'] = display_invest['Quantity'].apply(lambda x: f"{x:.2f}" if x != 0 else "—")
                    display_invest['Price'] = display_invest['Price'].apply(lambda x: f"${x:.2f}" if x != 0 else "—")
                    st.dataframe(display_invest, hide_index=True, width='stretch')

                st.divider()

                # === TRANSFERS ===
                st.subheader("🔄 Transfers (Between Accounts)")
                transfer_df = txn_df[(txn_df['Category Type'] == 'TRANSFER') &
                                    (txn_df['Investment Type'].isna() | (txn_df['Investment Type'] == ''))].copy()
                transfer_count = len(transfer_df)
                st.caption(f"{transfer_count} transfer transactions")

                if not transfer_df.empty:
                    transfer_cols = ['Date', 'Account', 'Description', 'Amount', 'Is Credit', 'Transaction Type']
                    display_transfer = transfer_df[transfer_cols].copy()
                    display_transfer['Amount'] = display_transfer['Amount'].apply(lambda x: f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
                    display_transfer['Direction'] = display_transfer['Is Credit'].apply(lambda x: "← In" if x else "→ Out")
                    display_transfer = display_transfer.drop('Is Credit', axis=1)
                    st.dataframe(display_transfer, hide_index=True, width='stretch')

        if content_type not in ("accounts", "net_worth", "transactions") and result["holdings"] and df is not None:
            if result.get("csv_path") and os.path.exists(result["csv_path"]):
                realtime_url = f"?realtime=1&refresh=900&csv_file={quote_plus(result['csv_path'])}"
                st.markdown(
                    f'<a href="{realtime_url}" target="_blank" rel="noopener noreferrer">Open Real-Time Dashboard ↗</a>',
                    unsafe_allow_html=True,
                )

            render_portfolio_analysis(df, raw_holdings_list=result.get("raw_holdings_list"))

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
           - The app automatically detects the file type (holdings, net worth, transactions, or accounts)
           - Click **Process File** and view your results

        3. **Download options**:
           - **Portfolio / Holdings**: CSV + detailed text report
           - **Net Worth History**: CSV + net worth summary report
           - **Transactions**: CSV export
           - **Accounts Snapshot**: CSV + summary text
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
            | **Overview / Accounts** (`#/accounts`) | Accounts snapshot | `accounts_YYYYMMDD.json` |

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
