import json, csv

try:
    # Load the saved JSON
    with open("user_files/networth.json") as f:
        content = f.read()

    print(f"File size: {len(content)} characters")

    # First try to parse as proper JSON since it appears to be valid
    try:
        data = json.loads(content)
        print("JSON is valid, checking structure...")

        # Look for networthHistories in the parsed data
        if 'spData' in data and 'networthHistories' in data['spData']:
            networth_data = data['spData']['networthHistories']
            print(f"Found {len(networth_data)} entries in networthHistories")

            # Write out daily CSV with all available fields
            with open("user_files/networth_daily.csv", "w", newline="") as f:
                w = csv.writer(f)
                # CSV header with all available fields
                w.writerow([
                    "date", "networth", "totalAssets", "totalLiabilities",
                    "totalCash", "totalInvestment", "totalEmpower",
                    "totalMortgage", "totalLoan", "totalCredit",
                    "totalOtherAssets", "totalOtherLiabilities",
                    "oneDayNetworthChange", "oneDayNetworthPercentageChange"
                ])
                count = 0
                for entry in networth_data:
                    if 'date' in entry and 'networth' in entry:
                        # Skip entries with zero networth (likely placeholder data)
                        if entry["networth"] != 0.0:
                            w.writerow([
                                entry.get("date", ""),
                                entry.get("networth", 0.0),
                                entry.get("totalAssets", 0.0),
                                entry.get("totalLiabilities", 0.0),
                                entry.get("totalCash", 0.0),
                                entry.get("totalInvestment", 0.0),
                                entry.get("totalEmpower", 0.0),
                                entry.get("totalMortgage", 0.0),
                                entry.get("totalLoan", 0.0),
                                entry.get("totalCredit", 0.0),
                                entry.get("totalOtherAssets", 0.0),
                                entry.get("totalOtherLiabilities", 0.0),
                                entry.get("oneDayNetworthChange", 0.0),
                                entry.get("oneDayNetworthPercentageChange", 0.0)
                            ])
                            count += 1

            print(f"Successfully extracted {count} non-zero networth entries with all fields to user_files/networth_daily.csv")

        else:
            print("networthHistories not found in parsed JSON structure")
            if 'spData' in data:
                print(f"Available keys in spData: {list(data['spData'].keys())}")

    except json.JSONDecodeError as parse_error:
        print(f"JSON parsing failed: {parse_error}")

        # Fallback to regex approach
        print("Falling back to regex extraction...")
        if "networthHistories" in content:
            print("Found networthHistories section")

            # Extract networth data using string parsing
            import re

            # Pattern to extract a complete entry with all fields
            entry_pattern = r'"date":"([^"]+)"[^}]*?"totalMortgage":([0-9.E]+)[^}]*?"totalOtherAssets":([0-9.E]+)[^}]*?"totalAssets":([0-9.E]+)[^}]*?"totalCredit":([0-9.E]+)[^}]*?"totalLoan":([0-9.E]+)[^}]*?"oneDayNetworthPercentageChange":([0-9.E\-]+)[^}]*?"totalLiabilities":([0-9.E]+)[^}]*?"totalOtherLiabilities":([0-9.E]+)[^}]*?"oneDayNetworthChange":([0-9.E\-]+)[^}]*?"totalEmpower":([0-9.E]+)[^}]*?"totalCash":([0-9.E]+)[^}]*?"networth":([0-9.E\-]+)[^}]*?"totalInvestment":([0-9.E]+)'
            matches = re.findall(entry_pattern, content)

            if matches:
                # Write out daily CSV with all fields, filtering out zero networth values
                with open("user_files/networth_daily.csv", "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow([
                        "date", "networth", "totalAssets", "totalLiabilities",
                        "totalCash", "totalInvestment", "totalEmpower",
                        "totalMortgage", "totalLoan", "totalCredit",
                        "totalOtherAssets", "totalOtherLiabilities",
                        "oneDayNetworthChange", "oneDayNetworthPercentageChange"
                    ])
                    count = 0
                    for match in matches:
                        date, totalMortgage, totalOtherAssets, totalAssets, totalCredit, totalLoan, oneDayNetworthPercentageChange, totalLiabilities, totalOtherLiabilities, oneDayNetworthChange, totalEmpower, totalCash, networth, totalInvestment = match
                        networth_val = float(networth)
                        if networth_val != 0.0:  # Skip zero values
                            w.writerow([
                                date,
                                networth_val,
                                float(totalAssets),
                                float(totalLiabilities),
                                float(totalCash),
                                float(totalInvestment),
                                float(totalEmpower),
                                float(totalMortgage),
                                float(totalLoan),
                                float(totalCredit),
                                float(totalOtherAssets),
                                float(totalOtherLiabilities),
                                float(oneDayNetworthChange),
                                float(oneDayNetworthPercentageChange)
                            ])
                            count += 1

                print(f"Successfully extracted {count} non-zero networth entries with all fields to user_files/networth_daily.csv")
            else:
                print("No networth data found with regex pattern")

except FileNotFoundError:
    print("File user_files/networth.json not found")
except Exception as e:
    print(f"Error: {e}")