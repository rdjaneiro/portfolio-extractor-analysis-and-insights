#!/usr/bin/env python3

from read_empower_webarchive import extract_webarchive_text

def minimal_debug_extract(text_content):
    """Minimal debug version to trace MorganStanley-LAL specifically"""

    accounts = []
    lines = text_content.split('\n')

    # Find the structured section start
    structured_section_start = -1
    for i, line in enumerate(lines):
        if (line.strip() == "Account" and
            i + 1 < len(lines) and lines[i + 1].strip() == "Type" and
            i + 2 < len(lines) and lines[i + 2].strip() == "Balance"):
            structured_section_start = i + 3
            break

    if structured_section_start == -1:
        return "Could not find structured section"

    print(f"Starting at line {structured_section_start}")

    providers = [
        'Apple Federal Credit Union', 'Charles Schwab', 'Fidelity', 'Morgan Stanley', 'M1 Finance',
        'Manual Investment Holdings', 'Wells Fargo', 'Chase', 'American Express', 'Brex',
        'E*TRADE', 'T-RowePrice Manual Holdings', 'Bluevine', 'Webull', 'Coinbase', 'Truist',
        'MorganStanley', 'Manual', 'Cyber Connective Corporation'
    ]

    i = structured_section_start
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Check if this is the MorganStanley-LAL line specifically
        if line == "MorganStanley-LAL":
            print(f"\\n=== FOUND MorganStanley-LAL AT LINE {i} ===")

            # Set provider - apply the same logic as the real parser
            provider = line
            if line.startswith('MorganStanley-'):
                provider = 'Morgan Stanley'
            print(f"Provider set to: '{provider}'")

            # Look ahead for account details
            j = i + 1
            account_name = line  # Use full line as account name
            account_type = None
            balance = None
            date = None

            print(f"Looking ahead from line {j}...")
            while j < len(lines) and j < i + 15:
                next_line = lines[j].strip()

                if not next_line:
                    j += 1
                    continue

                print(f"  Line {j}: '{next_line}'")

                # Check for account type
                if (not account_type and next_line in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                               '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                               'Line Of Credit', 'Cryptocurrency']):
                    account_type = next_line
                    print(f"    -> Account type: {account_type}")
                    j += 1
                    continue

                # Check for balance
                if ((next_line.startswith('$') or next_line.startswith('-$') or next_line.startswith('-')) and
                    any(c.isdigit() for c in next_line) and
                    ('.' in next_line or next_line.replace('$', '').replace('-', '').replace(',', '').isdigit())):
                    if not balance:
                        balance = next_line
                        print(f"    -> Balance: {balance}")
                    j += 1
                    continue

                # Check for date
                if ('/' in next_line and ('AM' in next_line or 'PM' in next_line or 'ago' in next_line)):
                    date = next_line
                    print(f"    -> Date: {date}")
                    break

                j += 1

            # Now process the account if we have the required data
            if account_name and balance:
                print(f"\\n--- PROCESSING ACCOUNT ---")
                print(f"Account: {account_name}")
                print(f"Type: {account_type}")
                print(f"Balance: {balance}")
                print(f"Provider: {provider}")

                # Clean up balance
                is_negative = balance.startswith('-$') or balance.startswith('-')
                balance_clean = balance.replace('$', '').replace(',', '')
                if is_negative:
                    balance_clean = balance_clean.lstrip('-')

                print(f"Balance clean: {balance_clean}")
                print(f"Is negative: {is_negative}")

                # Determine category
                account_type_lower = (account_type or 'Unknown').lower()
                if account_type_lower == 'line of credit':
                    category = 'Loan'
                else:
                    category = 'Unknown'

                print(f"Category: {category}")

                # Create account entry
                account_entry = {
                    'Account': account_name,
                    'Type': account_type or 'Unknown',
                    'Balance': f"-{balance_clean}" if is_negative else balance_clean,
                    'Category': category,
                    'Provider': provider,
                    'Date': date or 'Unknown'
                }

                print(f"\\n--- ACCOUNT ENTRY ---")
                for key, value in account_entry.items():
                    print(f"{key}: {value}")

                accounts.append(account_entry)
                print(f"\\n*** ADDED TO ACCOUNTS LIST ***")

                return f"SUCCESS: Added MorganStanley-LAL account with balance {account_entry['Balance']}"
            else:
                print(f"\\n--- FAILED TO PROCESS ---")
                print(f"Account name: {account_name}")
                print(f"Balance: {balance}")
                return "FAILED: Missing account name or balance"

            i = j

        else:
            i += 1

        # Limit search to avoid infinite loops
        if i > structured_section_start + 5000:
            break

    return "MorganStanley-LAL not found in processing loop"

# Test the function
text = extract_webarchive_text('/workspace/user_files/Empower - Net Worth - 20250807.webarchive')
if text and not text.startswith('Error'):
    result = minimal_debug_extract(text)
    print(f"\\nFINAL RESULT: {result}")
else:
    print('Error extracting text:', text)
