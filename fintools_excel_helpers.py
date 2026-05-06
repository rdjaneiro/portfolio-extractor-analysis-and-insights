"""Excel building helpers for finTools_app.

Contains:
  - classify_tax_status   : classify account name as Taxable / Tax-Deferred / Tax-Exempt
  - _enrich_holdings_df   : add P&L / ROI% / Account Type columns
  - build_holdings_excel  : Holdings + Details + Portfolio Statistics workbook
  - build_performance_excel : Performance report workbook
"""
import re
import numpy as np
import pandas as pd

# ── Tax-status classification ─────────────────────────────────────────────────
_TAX_DEFERRED_RE = re.compile(
    r'\b(401k|401\(k\)|403b|403\(b\)|457|tsp|sep[\s\-]?ira|simple[\s\-]?ira|pension|profit[\s\-]?sharing|'
    r'traditional[\s\-]?ira|rollover[\s\-]?ira|inherited[\s\-]?ira|ira)\b',
    re.IGNORECASE,
)
_TAX_EXEMPT_RE = re.compile(r'\b(roth)\b', re.IGNORECASE)


def classify_tax_status(account_name: str) -> str:
    """Return 'Tax-Exempt (Roth)', 'Tax-Deferred', or 'Taxable' for an account name."""
    name = str(account_name or "")
    if _TAX_EXEMPT_RE.search(name):
        return "Tax-Exempt (Roth)"
    if _TAX_DEFERRED_RE.search(name):
        return "Tax-Deferred"
    return "Taxable"


def _enrich_holdings_df(df: pd.DataFrame) -> pd.DataFrame:
    """Insert computed P&L, ROI%, and Account Type columns into a holdings DataFrame."""
    df = df.copy()

    # P&L and ROI% — insert right after the Value column
    if "Value" in df.columns and "Cost Basis" in df.columns:
        val   = pd.to_numeric(df["Value"],      errors="coerce")
        basis = pd.to_numeric(df["Cost Basis"], errors="coerce")
        has_basis = basis.notna() & (basis != 0)
        df["P&L"]  = np.where(has_basis, val - basis, np.nan)
        df["ROI%"] = np.where(has_basis, (val - basis) / basis, np.nan)
        cols = list(df.columns)
        for c in ["ROI%", "P&L"]:          # remove from wherever they landed
            if c in cols:
                cols.remove(c)
        val_idx = cols.index("Value")
        cols.insert(val_idx + 1, "P&L")
        cols.insert(val_idx + 2, "ROI%")
        df = df[cols]

    # Account Type — insert right after the Account column
    if "Account" in df.columns:
        df["Account Type"] = df["Account"].apply(classify_tax_status)
        cols = list(df.columns)
        cols.remove("Account Type")
        cols.insert(cols.index("Account") + 1, "Account Type")
        df = df[cols]

    return df


def build_holdings_excel(csv_path, raw_holdings_list=None, stats=None):
    """Build a formatted Excel workbook from a holdings CSV and return BytesIO.

    Sheet 1 – Holdings: consolidated summary (one row per ticker).
    Sheet 2 – Holdings Details: one row per ticker per account (pre-consolidation).
    Sheet 3 – Portfolio Statistics: key metrics, allocation, and tax-status breakdown.
    """
    import io as _io
    buf = _io.BytesIO()
    df = pd.read_csv(csv_path)

    # Numeric coercion for value/shares/price columns
    for col in ["Value", "Shares", "Price", "Value_numeric"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Use Value_numeric if present, otherwise Value
    if "Value_numeric" in df.columns and "Value" not in df.columns:
        df = df.rename(columns={"Value_numeric": "Value"})
    elif "Value_numeric" in df.columns:
        df["Value"] = df["Value_numeric"].combine_first(df["Value"])
        df = df.drop(columns=["Value_numeric"])

    # Sort by value descending
    if "Value" in df.columns:
        df = df.sort_values("Value", ascending=False, na_position="last").reset_index(drop=True)
    # Add computed columns (P&L, ROI%, Account Type)
    df = _enrich_holdings_df(df)

    # Build details DataFrame from raw per-account holdings
    detail_df = None
    if raw_holdings_list:
        detail_df = pd.DataFrame(raw_holdings_list)
        drop_cols = [c for c in ["Change", "1 Day %", "1 day $", "_accounts", "_value_for_price_calc"] if c in detail_df.columns]
        if drop_cols:
            detail_df = detail_df.drop(columns=drop_cols)
        for col in ["Value", "Shares", "Price", "Cost Basis"]:
            if col in detail_df.columns:
                detail_df[col] = pd.to_numeric(detail_df[col], errors="coerce")
        # Preferred column order for details sheet
        detail_pref = ["Account", "Ticker", "Name", "Shares", "Price", "Value", "Type", "CUSIP", "Cost Basis", "Exchange", "Category"]
        detail_cols = [c for c in detail_pref if c in detail_df.columns] + \
                      [c for c in detail_df.columns if c not in detail_pref]
        detail_df = detail_df[detail_cols]
        if "Value" in detail_df.columns:
            detail_df = detail_df.sort_values(["Account", "Value"], ascending=[True, False], na_position="last").reset_index(drop=True)
        # Add computed columns
        detail_df = _enrich_holdings_df(detail_df)

    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Holdings")
        wb = writer.book

        # ── shared formats ────────────────────────────────────────────────────
        hdr_fmt = wb.add_format({
            "bold": True, "bg_color": "#252A40", "font_color": "#C5CAE8",
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
        })
        currency_fmt = wb.add_format({"num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
        num_fmt      = wb.add_format({"num_format": "#,##0.00",  "border": 1, "valign": "vcenter"})
        text_fmt     = wb.add_format({"border": 1, "valign": "vcenter"})
        pos_fmt      = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80",
                                       "num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
        neg_fmt      = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171",
                                       "num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
        roi_pos_fmt  = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80",
                                       "num_format": "0.00%", "border": 1, "valign": "vcenter"})
        roi_neg_fmt  = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171",
                                       "num_format": "0.00%", "border": 1, "valign": "vcenter"})
        roi_neu_fmt  = wb.add_format({"num_format": "0.00%", "border": 1, "valign": "vcenter"})
        acct_fmt     = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "#C5CAE8",
                                       "border": 1, "valign": "vcenter"})

        col_widths = {"Ticker": 10, "Symbol": 10, "Name": 35, "Shares": 12,
                      "Price": 13, "Value": 15, "P&L": 14, "ROI%": 10,
                      "Type": 14, "Account": 24, "Account Type": 20,
                      "Category": 20, "CUSIP": 14, "Cost Basis": 14, "Exchange": 12}

        currency_cols = {"Price", "Cost Basis"}
        number_cols   = {"Shares"}

        def _write_sheet(ws, frame, with_acct_highlight=False):
            COLS   = list(frame.columns)
            pnl_ci = COLS.index("P&L") if "P&L" in COLS else None
            for ci, col in enumerate(COLS):
                ws.write(0, ci, col, hdr_fmt)
            for ri, row_vals in enumerate(frame.itertuples(index=False), start=1):
                # Determine sign from P&L for coloring Value, P&L, and ROI%
                _sign = 0
                if pnl_ci is not None:
                    _pnl = row_vals[pnl_ci]
                    try:
                        if not (isinstance(_pnl, float) and np.isnan(_pnl)) and _pnl is not None:
                            _sign = 1 if float(_pnl) > 0 else (-1 if float(_pnl) < 0 else 0)
                    except (TypeError, ValueError):
                        pass
                _money_fmt = pos_fmt if _sign > 0 else (neg_fmt if _sign < 0 else currency_fmt)
                _roi_fmt   = roi_pos_fmt if _sign > 0 else (roi_neg_fmt if _sign < 0 else roi_neu_fmt)
                for ci, col in enumerate(COLS):
                    val = row_vals[ci]
                    is_none = val is None or (isinstance(val, float) and np.isnan(val))
                    if is_none:
                        ws.write(ri, ci, "", text_fmt)
                    elif col in ("Value", "P&L"):
                        ws.write_number(ri, ci, float(val), _money_fmt)
                    elif col == "ROI%":
                        ws.write_number(ri, ci, float(val), _roi_fmt)
                    elif col in currency_cols:
                        ws.write_number(ri, ci, float(val), currency_fmt)
                    elif col in number_cols:
                        ws.write_number(ri, ci, float(val), num_fmt)
                    else:
                        ws.write(ri, ci, val, text_fmt)
            for ci, col in enumerate(COLS):
                ws.set_column(ci, ci, col_widths.get(col, 14))
            ws.freeze_panes(1, 0)
            ws.set_row(0, 22)

        # ── Sheet 1: Holdings (consolidated) ─────────────────────────────────
        _write_sheet(writer.sheets["Holdings"], df)

        # ── Sheet 2: Holdings Details (per account) ───────────────────────────
        if detail_df is not None and not detail_df.empty:
            detail_df.to_excel(writer, index=False, sheet_name="Holdings Details")
            dws = writer.sheets["Holdings Details"]
            DCOLS  = list(detail_df.columns)
            acct_ci = DCOLS.index("Account") if "Account" in DCOLS else None
            pnl_dci = DCOLS.index("P&L")     if "P&L"     in DCOLS else None

            for ci, col in enumerate(DCOLS):
                dws.write(0, ci, col, hdr_fmt)

            prev_acct = None
            for ri, row_vals in enumerate(detail_df.itertuples(index=False), start=1):
                cur_acct = row_vals[acct_ci] if acct_ci is not None else None
                # Determine sign from P&L
                _sign = 0
                if pnl_dci is not None:
                    _pnl = row_vals[pnl_dci]
                    try:
                        if not (isinstance(_pnl, float) and np.isnan(_pnl)) and _pnl is not None:
                            _sign = 1 if float(_pnl) > 0 else (-1 if float(_pnl) < 0 else 0)
                    except (TypeError, ValueError):
                        pass
                _money_fmt = pos_fmt if _sign > 0 else (neg_fmt if _sign < 0 else currency_fmt)
                _roi_fmt   = roi_pos_fmt if _sign > 0 else (roi_neg_fmt if _sign < 0 else roi_neu_fmt)
                for ci, col in enumerate(DCOLS):
                    val = row_vals[ci]
                    is_none = val is None or (isinstance(val, float) and np.isnan(val))
                    use_acct_fmt = (col == "Account" and cur_acct != prev_acct)
                    if is_none:
                        dws.write(ri, ci, "", acct_fmt if use_acct_fmt else text_fmt)
                    elif col in ("Value", "P&L"):
                        dws.write_number(ri, ci, float(val), _money_fmt)
                    elif col == "ROI%":
                        dws.write_number(ri, ci, float(val), _roi_fmt)
                    elif col in currency_cols:
                        dws.write_number(ri, ci, float(val), currency_fmt)
                    elif col in number_cols:
                        dws.write_number(ri, ci, float(val), num_fmt)
                    else:
                        dws.write(ri, ci, val, acct_fmt if use_acct_fmt else text_fmt)
                prev_acct = cur_acct

            for ci, col in enumerate(DCOLS):
                dws.set_column(ci, ci, col_widths.get(col, 14))
            dws.freeze_panes(1, 0)
            dws.set_row(0, 22)

        # ── Sheet 3: Portfolio Statistics ─────────────────────────────────────
        if stats and 'error' not in stats:
            st_ws = wb.add_worksheet("Portfolio Statistics")
            st_ws.set_zoom(110)
            st_ws.set_column(0, 0, 32)   # label column
            st_ws.set_column(1, 1, 20)   # value column
            st_ws.set_column(2, 2, 18)   # extra column

            sec_fmt  = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "#C5CAE8",
                                       "border": 1, "font_size": 11, "valign": "vcenter"})
            lbl_fmt  = wb.add_format({"bg_color": "#252A40", "font_color": "#C5CAE8",
                                       "border": 1, "valign": "vcenter"})
            val_fmt  = wb.add_format({"border": 1, "valign": "vcenter"})
            cur_fmt  = wb.add_format({"num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
            pct_fmt  = wb.add_format({"num_format": "0.00%", "border": 1, "valign": "vcenter"})
            pct1_fmt = wb.add_format({"num_format": "0.0%", "border": 1, "valign": "vcenter"})
            num2_fmt = wb.add_format({"num_format": "#,##0.00", "border": 1, "valign": "vcenter"})
            col_hdr  = wb.add_format({"bold": True, "bg_color": "#252A40", "font_color": "#C5CAE8",
                                       "border": 1, "align": "center", "valign": "vcenter"})
            # Coloured tax-status labels
            tax_fmt = {
                "Taxable":           wb.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "#93C5FD", "border": 1, "valign": "vcenter"}),
                "Tax-Deferred":      wb.add_format({"bold": True, "bg_color": "#451a03", "font_color": "#FCD34D", "border": 1, "valign": "vcenter"}),
                "Tax-Exempt (Roth)": wb.add_format({"bold": True, "bg_color": "#052e16", "font_color": "#6EE7B7", "border": 1, "valign": "vcenter"}),
            }

            row = 0

            def _section(title):
                nonlocal row
                st_ws.merge_range(row, 0, row, 2, title, sec_fmt)
                st_ws.set_row(row, 18)
                row += 1

            def _kv(label, value, fmt=val_fmt):
                nonlocal row
                st_ws.write(row, 0, label, lbl_fmt)
                if fmt in (cur_fmt, pct_fmt, pct1_fmt, num2_fmt) and value is not None:
                    try:
                        st_ws.write_number(row, 1, float(value), fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 1, value, val_fmt)
                else:
                    st_ws.write(row, 1, value, fmt)
                st_ws.write(row, 2, "", val_fmt)
                row += 1

            # ── Summary ───────────────────────────────────────────────────────
            _section("Summary Statistics")
            _kv("Total Value",        stats.get("total_value"),   cur_fmt)
            _kv("Holdings Count",     stats.get("count"),         val_fmt)
            _kv("Average Value",      stats.get("avg_value"),     cur_fmt)
            _kv("Median Value",       stats.get("median_value"),  cur_fmt)
            _kv("Largest Holding",    stats.get("max_value"),     cur_fmt)
            _kv("Smallest Holding",   stats.get("min_value"),     cur_fmt)
            _kv("Value Range",        stats.get("value_range"),   cur_fmt)
            _kv("Standard Deviation", stats.get("std_dev"),       cur_fmt)
            row += 1

            # ── Concentration ─────────────────────────────────────────────────
            _section("Portfolio Concentration")
            top5  = stats.get("top_5_pct")
            top10 = stats.get("top_10_pct")
            _kv("Top 5 Holdings %",  (top5 / 100) if top5 is not None else None,   pct_fmt)
            _kv("Top 10 Holdings %", (top10 / 100) if top10 is not None else None, pct_fmt)
            _kv("HHI Score",         stats.get("hhi"),            num2_fmt)
            _kv("Concentration",     stats.get("concentration"),  val_fmt)
            row += 1

            # ── Top Holdings ──────────────────────────────────────────────────
            if "holdings_pct" in stats:
                _section("Top 10 Holdings")
                st_ws.write(row, 0, "Name",  col_hdr)
                st_ws.write(row, 1, "Symbol", col_hdr)
                st_ws.write(row, 2, "% of Portfolio", col_hdr)
                row += 1
                for _, hr in stats["holdings_pct"].head(10).iterrows():
                    st_ws.write(row, 0, hr.get("Name", ""), val_fmt)
                    st_ws.write(row, 1, hr.get("Symbol", ""), val_fmt)
                    _pct = hr.get("pct_of_total")
                    try:
                        st_ws.write_number(row, 2, float(_pct) / 100, pct1_fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 2, "", val_fmt)
                    row += 1
                row += 1

            # ── Asset Allocation ──────────────────────────────────────────────
            if "asset_allocation" in stats and not stats["asset_allocation"].empty:
                _section("Asset Allocation (by Category)")
                st_ws.write(row, 0, "Category",       col_hdr)
                st_ws.write(row, 1, "Value",           col_hdr)
                st_ws.write(row, 2, "% of Portfolio",  col_hdr)
                row += 1
                _tot = stats.get("total_value", 1) or 1
                for _, ar in stats["asset_allocation"].iterrows():
                    st_ws.write(row, 0, ar.get("Category", ""), val_fmt)
                    _v = ar.get("Value_numeric") if "Value_numeric" in ar.index else None
                    if _v is None:
                        _v = float(ar.get("pct_of_total", 0)) / 100 * _tot
                    try:
                        st_ws.write_number(row, 1, float(_v), cur_fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 1, "", val_fmt)
                    _ap = ar.get("pct_of_total")
                    try:
                        st_ws.write_number(row, 2, float(_ap) / 100, pct1_fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 2, "", val_fmt)
                    row += 1
                row += 1

            # ── Tax-Status Allocation ─────────────────────────────────────────
            if "tax_allocation" in stats and not stats["tax_allocation"].empty:
                _section("Tax-Status Allocation")
                st_ws.write(row, 0, "Tax Status",      col_hdr)
                st_ws.write(row, 1, "Value",           col_hdr)
                st_ws.write(row, 2, "% of Portfolio",  col_hdr)
                row += 1
                for _, tr in stats["tax_allocation"].iterrows():
                    _ts = tr.get("Tax Status", "")
                    _tfmt = tax_fmt.get(_ts, lbl_fmt)
                    st_ws.write(row, 0, _ts, _tfmt)
                    try:
                        st_ws.write_number(row, 1, float(tr["Value"]), cur_fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 1, "", val_fmt)
                    try:
                        st_ws.write_number(row, 2, float(tr["% of Portfolio"]) / 100, pct1_fmt)
                    except (TypeError, ValueError):
                        st_ws.write(row, 2, "", val_fmt)
                    row += 1
                row += 1

                if "tax_allocation_by_account" in stats and not stats["tax_allocation_by_account"].empty:
                    _section("Tax-Status Allocation — By Account")
                    st_ws.write(row, 0, "Account",         col_hdr)
                    st_ws.write(row, 1, "Tax Status",      col_hdr)
                    st_ws.write(row, 2, "% of Portfolio",  col_hdr)
                    row += 1
                    for _, ab in stats["tax_allocation_by_account"].iterrows():
                        _ts = ab.get("Tax Status", "")
                        _tfmt = tax_fmt.get(_ts, val_fmt)
                        st_ws.write(row, 0, ab.get("Account", ""), val_fmt)
                        st_ws.write(row, 1, _ts, _tfmt)
                        try:
                            st_ws.write_number(row, 2, float(ab["% of Portfolio"]) / 100, pct1_fmt)
                        except (TypeError, ValueError):
                            st_ws.write(row, 2, "", val_fmt)
                        row += 1

    buf.seek(0)
    return buf


def build_performance_excel(perf_df, holdings_df=None, detail_df=None, stats=None):
    """Build and return a formatted Excel workbook as BytesIO for the performance report."""
    import io as _io
    from xlsxwriter.utility import xl_col_to_name
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
            "30d %": 8, "90d %": 8, "180d %": 9,
            "YTD %": 9, "1-Year %": 9, "3-Yr Ann %": 10, "5-Yr Ann %": 10, "10-Yr Ann %": 11,
        }
        PCT_COLS   = {"Weight %", "Day Chg %", "30d %", "90d %", "180d %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"}
        MONEY_COLS = {"Price", "Value", "Day Chg $"}
        PERF_COLS  = {"Day Chg %", "30d %", "90d %", "180d %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"}

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
            if cname not in COLS:
                continue
            ci = COLS.index(cname)
            cl = xl_col_to_name(ci)
            rng = f"{cl}2:{cl}{nrows + 1}"
            # Use formula-type so text cells ("N/A") are never matched
            ws.conditional_format(rng, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2<0)",
                "format": wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171", "bold": True, "num_format": "0.00%", "border": 1})})
            ws.conditional_format(rng, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2>0)",
                "format": wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80", "bold": True, "num_format": "0.00%", "border": 1})})

        if "Day Chg $" in COLS:
            ci_day = COLS.index("Day Chg $")
            cl = xl_col_to_name(ci_day)
            rng_day = f"{cl}2:{cl}{nrows+1}"
            ws.conditional_format(rng_day, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2<0)",
                "format": wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171", "bold": True, "num_format": "$#,##0.00", "border": 1})})
            ws.conditional_format(rng_day, {"type": "formula",
                "criteria": f"AND(ISNUMBER({cl}2),{cl}2>0)",
                "format": wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80", "bold": True, "num_format": "$#,##0.00", "border": 1})})

        ws.freeze_panes(1, 0)
        ws.set_row(0, 28)
        ws.set_zoom(110)

        # ── Performance Highlights sheet ──────────────────────────────────────
        HL_PCT_COLS = ["30d %", "90d %", "180d %", "YTD %", "1-Year %", "3-Yr Ann %", "5-Yr Ann %", "10-Yr Ann %"]
        _hl = perf_df.copy()
        for _c in HL_PCT_COLS:
            if _c in _hl.columns:
                _hl[_c] = pd.to_numeric(_hl[_c], errors="coerce")

        _id_cols = [c for c in ["Symbol", "Name"] if c in _hl.columns]

        # Momentum score
        _mom_weights = [("30d %", 0.10), ("90d %", 0.25), ("180d %", 0.30),
                        ("YTD %", 0.20), ("1-Year %", 0.10), ("3-Yr Ann %", 0.03), ("5-Yr Ann %", 0.02)]
        _avail_mom = [(c, w) for c, w in _mom_weights if c in _hl.columns]
        if _avail_mom:
            _wsum = sum(w for _, w in _avail_mom)
            _hl["Momentum Score"] = sum(
                _hl[c].fillna(0) * w for c, w in _avail_mom
            ) / _wsum

        hl_ws = wb.add_worksheet("Performance Highlights")
        hl_ws.set_zoom(110)

        # Formats reused from parent scope
        pos_pct_fmt  = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80", "bold": True, "num_format": "0.00%", "border": 1, "valign": "vcenter"})
        neg_pct_fmt  = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171", "bold": True, "num_format": "0.00%", "border": 1, "valign": "vcenter"})
        neu_pct_fmt  = wb.add_format({"num_format": "0.00%", "border": 1, "valign": "vcenter"})
        pos_num_fmt  = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80", "bold": True, "num_format": "0.00", "border": 1, "valign": "vcenter"})
        neg_num_fmt  = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171", "bold": True, "num_format": "0.00", "border": 1, "valign": "vcenter"})
        neu_num_fmt  = wb.add_format({"num_format": "0.00", "border": 1, "valign": "vcenter"})
        sec_hdr_fmt  = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "#E0E0E0",
                                       "border": 1, "align": "center", "valign": "vcenter", "font_size": 12})
        col_hdr_fmt  = wb.add_format({"bold": True, "bg_color": "#252A40", "font_color": "#C5CAE8",
                                       "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True})
        text_fmt     = wb.add_format({"border": 1, "valign": "vcenter"})

        def _write_hl_block(ws_obj, start_row, title, df_block, pct_cols, score_col=None):
            """Write a titled block and return the next free row."""
            block_cols = list(df_block.columns)
            ncols = len(block_cols)
            if ncols > 1:
                ws_obj.merge_range(start_row, 0, start_row, ncols - 1, title, sec_hdr_fmt)
            else:
                ws_obj.write(start_row, 0, title, sec_hdr_fmt)
            ws_obj.set_row(start_row, 20)
            start_row += 1
            for ci, cname in enumerate(block_cols):
                ws_obj.write(start_row, ci, cname, col_hdr_fmt)
            start_row += 1
            for ri, (_, row) in enumerate(df_block.iterrows()):
                for ci, cname in enumerate(block_cols):
                    val = row[cname]
                    is_none = val is None or (isinstance(val, float) and np.isnan(val))
                    if is_none:
                        ws_obj.write(start_row, ci, "N/A", text_fmt)
                    elif cname in pct_cols:
                        v = float(val) / 100.0
                        ws_obj.write_number(start_row, ci, v, pos_pct_fmt if v > 0 else (neg_pct_fmt if v < 0 else neu_pct_fmt))
                    elif score_col and cname == score_col:
                        v = float(val)
                        ws_obj.write_number(start_row, ci, v, pos_num_fmt if v > 0 else (neg_num_fmt if v < 0 else neu_num_fmt))
                    else:
                        ws_obj.write(start_row, ci, val, text_fmt)
                start_row += 1
            return start_row + 1  # blank gap

        # Column widths on HL sheet
        hl_ws.set_column(0, 0, 10)   # Symbol
        hl_ws.set_column(1, 1, 30)   # Name
        for _ci in range(2, 12):
            hl_ws.set_column(_ci, _ci, 11)

        current_row = 0
        _pct_set = set(HL_PCT_COLS)

        def _top_bot_block(col, n=5):
            nonlocal current_row
            if col not in _hl.columns:
                return
            valid = _hl.dropna(subset=[col])
            top = valid.nlargest(n, col)[_id_cols + [col]].reset_index(drop=True)
            bot = valid.nsmallest(n, col)[_id_cols + [col]].reset_index(drop=True)
            current_row = _write_hl_block(hl_ws, current_row, f"Top {n} – {col}", top, _pct_set)
            current_row = _write_hl_block(hl_ws, current_row, f"Bottom {n} – {col}", bot, _pct_set)

        _top_bot_block("30d %")
        _top_bot_block("90d %")
        _top_bot_block("180d %")
        _top_bot_block("YTD %")
        _top_bot_block("1-Year %")

        # ── Momentum sheet ────────────────────────────────────────────────────
        if "Momentum Score" in _hl.columns:
            mom_ws = wb.add_worksheet("Momentum")
            mom_ws.set_zoom(110)
            mom_ws.set_column(0, 0, 10)   # Symbol
            mom_ws.set_column(1, 1, 30)   # Name
            for _ci in range(2, 15):
                mom_ws.set_column(_ci, _ci, 11)

            _mom_disp_cols = _id_cols + [c for c, _ in _avail_mom] + ["Momentum Score"]
            _mom_valid = _hl.dropna(subset=["Momentum Score"])
            mom_row = 0
            for _label, _getter in [("Top 10", lambda d: d.nlargest(10, "Momentum Score")),
                                     ("Bottom 10", lambda d: d.nsmallest(10, "Momentum Score"))]:
                _blk = _getter(_mom_valid)[_mom_disp_cols].reset_index(drop=True)
                mom_row = _write_hl_block(
                    mom_ws, mom_row,
                    f"{_label} – Momentum (10% 30d · 25% 90d · 30% 180d · 20% YTD · 10% 1-Year · 3% 3-Yr · 2% 5-Yr)",
                    _blk, _pct_set, score_col="Momentum Score"
                )

        # ── Holdings sheet (consolidated) ─────────────────────────────────────
        if holdings_df is not None and not holdings_df.empty:
            holdings_df = _enrich_holdings_df(holdings_df)
            if detail_df is not None and not detail_df.empty:
                detail_df = _enrich_holdings_df(detail_df)
            _h_col_widths = {"Ticker": 10, "Symbol": 10, "Name": 35, "Shares": 12,
                             "Price": 13, "Value": 15, "P&L": 14, "ROI%": 10,
                             "Type": 14, "Account": 24, "Account Type": 20,
                             "Category": 20, "CUSIP": 14, "Cost Basis": 14, "Exchange": 12}
            _h_currency_cols = {"Price", "Cost Basis"}
            _h_number_cols   = {"Shares"}

            _h_hdr_fmt = wb.add_format({
                "bold": True, "bg_color": "#252A40", "font_color": "#C5CAE8",
                "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
            })
            _h_currency_fmt = wb.add_format({"num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
            _h_num_fmt      = wb.add_format({"num_format": "#,##0.00",  "border": 1, "valign": "vcenter"})
            _h_text_fmt     = wb.add_format({"border": 1, "valign": "vcenter"})
            _h_pos_fmt      = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80",
                                             "num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
            _h_neg_fmt      = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171",
                                             "num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
            _h_roi_pos_fmt  = wb.add_format({"bg_color": "#0d2b1a", "font_color": "#4ade80",
                                             "num_format": "0.00%", "border": 1, "valign": "vcenter"})
            _h_roi_neg_fmt  = wb.add_format({"bg_color": "#2b0d0d", "font_color": "#f87171",
                                             "num_format": "0.00%", "border": 1, "valign": "vcenter"})
            _h_roi_neu_fmt  = wb.add_format({"num_format": "0.00%", "border": 1, "valign": "vcenter"})
            _h_acct_fmt     = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "#C5CAE8",
                                             "border": 1, "valign": "vcenter"})

            def _write_holdings_sheet(ws_obj, frame, with_acct_highlight=False):
                HCOLS   = list(frame.columns)
                acct_ci = HCOLS.index("Account") if "Account" in HCOLS else None
                pnl_ci  = HCOLS.index("P&L")     if "P&L"     in HCOLS else None
                for ci, col in enumerate(HCOLS):
                    ws_obj.write(0, ci, col, _h_hdr_fmt)
                prev_acct = None
                for ri, row_vals in enumerate(frame.itertuples(index=False), start=1):
                    cur_acct = row_vals[acct_ci] if acct_ci is not None else None
                    # Determine sign from P&L
                    _sign = 0
                    if pnl_ci is not None:
                        _pnl = row_vals[pnl_ci]
                        try:
                            if not (isinstance(_pnl, float) and np.isnan(_pnl)) and _pnl is not None:
                                _sign = 1 if float(_pnl) > 0 else (-1 if float(_pnl) < 0 else 0)
                        except (TypeError, ValueError):
                            pass
                    _money_fmt = _h_pos_fmt if _sign > 0 else (_h_neg_fmt if _sign < 0 else _h_currency_fmt)
                    _roi_fmt   = _h_roi_pos_fmt if _sign > 0 else (_h_roi_neg_fmt if _sign < 0 else _h_roi_neu_fmt)
                    for ci, col in enumerate(HCOLS):
                        val = row_vals[ci]
                        is_none = val is None or (isinstance(val, float) and np.isnan(val))
                        use_acct = with_acct_highlight and col == "Account" and cur_acct != prev_acct
                        if is_none:
                            ws_obj.write(ri, ci, "", _h_acct_fmt if use_acct else _h_text_fmt)
                        elif col in ("Value", "P&L"):
                            ws_obj.write_number(ri, ci, float(val), _money_fmt)
                        elif col == "ROI%":
                            ws_obj.write_number(ri, ci, float(val), _roi_fmt)
                        elif col in _h_currency_cols:
                            ws_obj.write_number(ri, ci, float(val), _h_currency_fmt)
                        elif col in _h_number_cols:
                            ws_obj.write_number(ri, ci, float(val), _h_num_fmt)
                        else:
                            ws_obj.write(ri, ci, val, _h_acct_fmt if use_acct else _h_text_fmt)
                    prev_acct = cur_acct
                for ci, col in enumerate(HCOLS):
                    ws_obj.set_column(ci, ci, _h_col_widths.get(col, 14))
                ws_obj.freeze_panes(1, 0)
                ws_obj.set_row(0, 22)

            holdings_df.to_excel(writer, index=False, sheet_name="Holdings")
            _write_holdings_sheet(writer.sheets["Holdings"], holdings_df, with_acct_highlight=False)

        # ── Holdings Details sheet (per-account) ──────────────────────────────
        if detail_df is not None and not detail_df.empty:
            detail_df.to_excel(writer, index=False, sheet_name="Holdings Details")
            _write_holdings_sheet(writer.sheets["Holdings Details"], detail_df, with_acct_highlight=True)

        # ── Portfolio Statistics sheet ─────────────────────────────────────────
        if stats and "error" not in stats:
            _ps_ws = wb.add_worksheet("Portfolio Statistics")
            _ps_ws.set_zoom(110)
            _ps_ws.set_column(0, 0, 32)
            _ps_ws.set_column(1, 1, 20)
            _ps_ws.set_column(2, 2, 18)

            _ps_sec  = wb.add_format({"bold": True, "bg_color": "#1A1A2E", "font_color": "#C5CAE8",
                                       "border": 1, "font_size": 11, "valign": "vcenter"})
            _ps_lbl  = wb.add_format({"bg_color": "#252A40", "font_color": "#C5CAE8",
                                       "border": 1, "valign": "vcenter"})
            _ps_val  = wb.add_format({"border": 1, "valign": "vcenter"})
            _ps_cur  = wb.add_format({"num_format": "$#,##0.00", "border": 1, "valign": "vcenter"})
            _ps_pct  = wb.add_format({"num_format": "0.00%", "border": 1, "valign": "vcenter"})
            _ps_pct1 = wb.add_format({"num_format": "0.0%",  "border": 1, "valign": "vcenter"})
            _ps_num2 = wb.add_format({"num_format": "#,##0.00", "border": 1, "valign": "vcenter"})
            _ps_chdr = wb.add_format({"bold": True, "bg_color": "#252A40", "font_color": "#C5CAE8",
                                       "border": 1, "align": "center", "valign": "vcenter"})
            _ps_tax_fmt = {
                "Taxable":           wb.add_format({"bold": True, "bg_color": "#1e3a5f", "font_color": "#93C5FD", "border": 1, "valign": "vcenter"}),
                "Tax-Deferred":      wb.add_format({"bold": True, "bg_color": "#451a03", "font_color": "#FCD34D", "border": 1, "valign": "vcenter"}),
                "Tax-Exempt (Roth)": wb.add_format({"bold": True, "bg_color": "#052e16", "font_color": "#6EE7B7", "border": 1, "valign": "vcenter"}),
            }

            _ps_row = 0

            def _ps_section(title):
                nonlocal _ps_row
                _ps_ws.merge_range(_ps_row, 0, _ps_row, 2, title, _ps_sec)
                _ps_ws.set_row(_ps_row, 18)
                _ps_row += 1

            def _ps_kv(label, value, fmt=None):
                nonlocal _ps_row
                _fmt = fmt or _ps_val
                _ps_ws.write(_ps_row, 0, label, _ps_lbl)
                if _fmt in (_ps_cur, _ps_pct, _ps_pct1, _ps_num2) and value is not None:
                    try:
                        _ps_ws.write_number(_ps_row, 1, float(value), _fmt)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 1, value, _ps_val)
                else:
                    _ps_ws.write(_ps_row, 1, value, _fmt)
                _ps_ws.write(_ps_row, 2, "", _ps_val)
                _ps_row += 1

            _ps_section("Summary Statistics (prices updated by yfinance)")
            _ps_kv("Total Value",        stats.get("total_value"),  _ps_cur)
            _ps_kv("Holdings Count",     stats.get("count"),        _ps_val)
            _ps_kv("Average Value",      stats.get("avg_value"),    _ps_cur)
            _ps_kv("Median Value",       stats.get("median_value"), _ps_cur)
            _ps_kv("Largest Holding",    stats.get("max_value"),    _ps_cur)
            _ps_kv("Smallest Holding",   stats.get("min_value"),    _ps_cur)
            _ps_kv("Value Range",        stats.get("value_range"),  _ps_cur)
            _ps_kv("Standard Deviation", stats.get("std_dev"),      _ps_cur)
            _ps_row += 1

            _ps_section("Portfolio Concentration")
            _top5  = stats.get("top_5_pct")
            _top10 = stats.get("top_10_pct")
            _ps_kv("Top 5 Holdings %",  (_top5  / 100) if _top5  is not None else None, _ps_pct)
            _ps_kv("Top 10 Holdings %", (_top10 / 100) if _top10 is not None else None, _ps_pct)
            _ps_kv("HHI Score",         stats.get("hhi"),           _ps_num2)
            _ps_kv("Concentration",     stats.get("concentration"), _ps_val)
            _ps_row += 1

            if "holdings_pct" in stats:
                _ps_section("Top 10 Holdings")
                _ps_ws.write(_ps_row, 0, "Name",           _ps_chdr)
                _ps_ws.write(_ps_row, 1, "Symbol",         _ps_chdr)
                _ps_ws.write(_ps_row, 2, "% of Portfolio", _ps_chdr)
                _ps_row += 1
                for _, _hr in stats["holdings_pct"].head(10).iterrows():
                    _ps_ws.write(_ps_row, 0, _hr.get("Name",   ""), _ps_val)
                    _ps_ws.write(_ps_row, 1, _hr.get("Symbol", ""), _ps_val)
                    try:
                        _ps_ws.write_number(_ps_row, 2, float(_hr.get("pct_of_total", 0)) / 100, _ps_pct1)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 2, "", _ps_val)
                    _ps_row += 1
                _ps_row += 1

            if "asset_allocation" in stats and not stats["asset_allocation"].empty:
                _ps_section("Asset Allocation (by Category)")
                _ps_ws.write(_ps_row, 0, "Category",       _ps_chdr)
                _ps_ws.write(_ps_row, 1, "Value",          _ps_chdr)
                _ps_ws.write(_ps_row, 2, "% of Portfolio", _ps_chdr)
                _ps_row += 1
                _tot_v = stats.get("total_value", 1) or 1
                for _, _ar in stats["asset_allocation"].iterrows():
                    _ps_ws.write(_ps_row, 0, _ar.get("Category", ""), _ps_val)
                    _av = _ar.get("Value_numeric") if "Value_numeric" in _ar.index else None
                    if _av is None:
                        _av = float(_ar.get("pct_of_total", 0)) / 100 * _tot_v
                    try:
                        _ps_ws.write_number(_ps_row, 1, float(_av), _ps_cur)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 1, "", _ps_val)
                    try:
                        _ps_ws.write_number(_ps_row, 2, float(_ar.get("pct_of_total", 0)) / 100, _ps_pct1)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 2, "", _ps_val)
                    _ps_row += 1
                _ps_row += 1

            if "tax_allocation" in stats and not stats["tax_allocation"].empty:
                _ps_section("Tax-Status Allocation")
                _ps_ws.write(_ps_row, 0, "Tax Status",     _ps_chdr)
                _ps_ws.write(_ps_row, 1, "Value",          _ps_chdr)
                _ps_ws.write(_ps_row, 2, "% of Portfolio", _ps_chdr)
                _ps_row += 1
                for _, _tr in stats["tax_allocation"].iterrows():
                    _ts = _tr.get("Tax Status", "")
                    _ps_ws.write(_ps_row, 0, _ts, _ps_tax_fmt.get(_ts, _ps_lbl))
                    try:
                        _ps_ws.write_number(_ps_row, 1, float(_tr["Value"]), _ps_cur)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 1, "", _ps_val)
                    try:
                        _ps_ws.write_number(_ps_row, 2, float(_tr["% of Portfolio"]) / 100, _ps_pct1)
                    except (TypeError, ValueError):
                        _ps_ws.write(_ps_row, 2, "", _ps_val)
                    _ps_row += 1
                _ps_row += 1

                if "tax_allocation_by_account" in stats and not stats["tax_allocation_by_account"].empty:
                    _ps_section("Tax-Status Allocation — By Account")
                    _ps_ws.write(_ps_row, 0, "Account",        _ps_chdr)
                    _ps_ws.write(_ps_row, 1, "Tax Status",     _ps_chdr)
                    _ps_ws.write(_ps_row, 2, "% of Portfolio", _ps_chdr)
                    _ps_row += 1
                    for _, _ab in stats["tax_allocation_by_account"].iterrows():
                        _ts = _ab.get("Tax Status", "")
                        _ps_ws.write(_ps_row, 0, _ab.get("Account", ""), _ps_val)
                        _ps_ws.write(_ps_row, 1, _ts, _ps_tax_fmt.get(_ts, _ps_val))
                        try:
                            _ps_ws.write_number(_ps_row, 2, float(_ab["% of Portfolio"]) / 100, _ps_pct1)
                        except (TypeError, ValueError):
                            _ps_ws.write(_ps_row, 2, "", _ps_val)
                        _ps_row += 1

    buf.seek(0)
    return buf

