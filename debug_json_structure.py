import json
import sys

def check_json_structure(file_path):
    """Check the structure of a JSON file and print its keys"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n{'='*80}")
        print(f"File: {file_path}")
        print(f"{'='*80}")

        # Check top-level keys
        print(f"\nTop-level keys: {list(data.keys())}")

        # Check spData keys if present
        if 'spData' in data:
            print(f"\nspData keys: {list(data['spData'].keys())}")

            # Check for networthHistories
            if 'networthHistories' in data['spData']:
                networth_histories = data['spData']['networthHistories']
                print(f"\n✓ networthHistories FOUND")
                print(f"  - Number of entries: {len(networth_histories)}")
                if networth_histories:
                    print(f"  - First entry keys: {list(networth_histories[0].keys())}")
                    print(f"  - First entry date: {networth_histories[0].get('date', 'N/A')}")
                    print(f"  - Last entry date: {networth_histories[-1].get('date', 'N/A')}")
            else:
                print(f"\n✗ networthHistories NOT FOUND")

            # Check for transactions
            if 'transactions' in data['spData']:
                transactions = data['spData']['transactions']
                print(f"\n✓ transactions FOUND")
                print(f"  - Number of transactions: {len(transactions)}")
                if transactions:
                    print(f"  - First transaction keys: {list(transactions[0].keys())[:10]}...")
            else:
                print(f"\n✗ transactions NOT FOUND")

            # Check for histories
            if 'histories' in data['spData']:
                histories = data['spData']['histories']
                print(f"\n✓ histories FOUND")
                print(f"  - Number of history entries: {len(histories)}")
                if histories:
                    print(f"  - First history entry keys: {list(histories[0].keys())}")
            else:
                print(f"\n✗ histories NOT FOUND")

        else:
            print("\n✗ spData NOT FOUND in JSON")

        return True

    except json.JSONDecodeError as e:
        print(f"\n✗ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == "__main__":
    # Check the files you're having issues with
    files_to_check = [
        "user_files/networth.json",
        "user_files/Empower - GetHistories 2025-11-09.json",
    ]

    # If files are provided as arguments, use those instead
    if len(sys.argv) > 1:
        files_to_check = sys.argv[1:]

    for file_path in files_to_check:
        try:
            check_json_structure(file_path)
        except FileNotFoundError:
            print(f"\n✗ File not found: {file_path}")

    print(f"\n{'='*80}\n")
