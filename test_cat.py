import sys, pandas as pd
from collections import defaultdict, Counter
sys.path.insert(0, '/workspace')

import warnings
warnings.filterwarnings('ignore')

# suppress streamlit logging
import logging
logging.disable(logging.CRITICAL)

from fintools_helpers import process_transactions_json

result = process_transactions_json('/workspace/user_files/20260505_d8603630/transactions_list_20260205_20260505.json')
txns = result['transactions']

emp = pd.read_csv('/workspace/user_files/2026-02-05 thru 2026-05-05 transactions.csv')
emp['key'] = emp['Date'].astype(str) + '|' + emp['Description'].str.strip().str.lower() + '|' + emp['Amount'].abs().round(2).astype(str)
emp_by_key = defaultdict(list)
for _, row in emp.iterrows():
    emp_by_key[row['key']].append(row)

matched = []
for t in txns:
    key = str(t.get('Date','')) + '|' + (t.get('Description','') or '').strip().lower() + '|' + str(round(abs(t.get('Amount',0)),2))
    rows = emp_by_key.get(key, [])
    if rows:
        matched.append((t, rows[0]))

mismatches = [(t, row) for t, row in matched if t['Category'] != row.get('Category','')]
print(f'Matched: {len(matched)} | Category mismatches: {len(mismatches)}')
pairs = Counter((t['Category'], row['Category']) for t, row in mismatches)
for (ac, ec), cnt in sorted(pairs.items(), key=lambda x: -x[1]):
    print(f'  {cnt:3d}  app={ac:35} -> emp={ec}')
