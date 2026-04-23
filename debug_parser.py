#!/usr/bin/env python3

from read_empower_webarchive import extract_webarchive_text

def debug_extract_net_worth_data(text_content):
    """Debug version of extract_net_worth_data to trace the parsing"""
    if not text_content:
        return "Could not extract net worth data: No text content provided"

    # Look for patterns that indicate this is net worth data
    if "Net worth" not in text_content and "Net Worth" not in text_content and "ALL ACCOUNTS" not in text_content:
        return "Could not extract net worth data: No net worth indicators found"

    accounts = []
    lines = text_content.split('\n')

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

    print(f"Found structured section starting at line {structured_section_start}")

    # Process the structured section
    current_group = None
    current_group_total = None
    i = structured_section_start

    providers = [
        'Apple Federal Credit Union', 'Charles Schwab', 'Fidelity', 'Morgan Stanley', 'M1 Finance',
        'Manual Investment Holdings', 'Wells Fargo', 'Chase', 'American Express', 'Brex',
        'E*TRADE', 'T-RowePrice Manual Holdings', 'Bluevine', 'Webull', 'Coinbase', 'Truist',
        'MorganStanley', 'Manual', 'Cyber Connective Corporation'
    ]

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this is a provider name (looking for known providers)
        if any(provider in line for provider in providers):
            print(f"Found provider at line {i}: '{line}'")

            # Special check for MorganStanley-LAL
            if line == "MorganStanley-LAL":
                print(f"  -> This is the MorganStanley-LAL account we're looking for!")
                print(f"  -> Looking ahead from line {i+1}...")

                # Look ahead for account details
                j = i + 1
                account_name = line  # Use the full line as account name
                account_type = None
                balance = None
                date = None

                # Parse the next several lines for account details
                while j < len(lines) and j < i + 15:
                    next_line = lines[j].strip()
                    print(f"    Line {j}: '{next_line}'")

                    if not next_line:
                        j += 1
                        continue

                    # Check for account type (common types) - only if we don't already have one
                    if (not account_type and next_line in ['Checking', 'Savings', 'Investment', 'IRA Traditional', 'IRA SEP',
                                   '401k Traditional', 'Personal', 'Line of Credit', 'Mortgage', 'Assets',
                                   'Line Of Credit', 'Cryptocurrency']):
                        account_type = next_line
                        print(f"      -> Found account type: {account_type}")
                        j += 1
                        continue

                    # Check for balance (multiple formats: $123.45, -$123.45, -123.45)
                    if ((next_line.startswith('$') or next_line.startswith('-$') or next_line.startswith('-')) and
                        any(c.isdigit() for c in next_line) and
                        ('.' in next_line or next_line.replace('$', '').replace('-', '').replace(',', '').isdigit())):
                        if not balance:
                            balance = next_line
                            print(f"      -> Found balance: {balance}")
                        j += 1
                        continue

                    # Check for date pattern (contains / and time info)
                    if ('/' in next_line and ('AM' in next_line or 'PM' in next_line or 'ago' in next_line)):
                        date = next_line
                        print(f"      -> Found date: {date}")
                        break

                    j += 1

                # Check if we found the required details
                if account_name and balance:
                    print(f"  -> SUCCESS! Found account details:")
                    print(f"     Account: {account_name}")
                    print(f"     Type: {account_type}")
                    print(f"     Balance: {balance}")
                    print(f"     Date: {date}")

                    return f"Found MorganStanley-LAL: {account_name}, {account_type}, {balance}"
                else:
                    print(f"  -> FAILED! Missing details:")
                    print(f"     Account: {account_name}")
                    print(f"     Type: {account_type}")
                    print(f"     Balance: {balance}")

                i = j
            else:
                i += 1
        else:
            i += 1

        # Stop after a reasonable search to avoid infinite loops
        if i > structured_section_start + 5000:
            break

    return "Debug complete - no MorganStanley-LAL found"

# Test the debug function
text = extract_webarchive_text('/workspace/user_files/Empower - Net Worth - 20250807.webarchive')
if text and not text.startswith('Error'):
    result = debug_extract_net_worth_data(text)
    print("\nFinal result:", result)
else:
    print('Error extracting text:', text)
