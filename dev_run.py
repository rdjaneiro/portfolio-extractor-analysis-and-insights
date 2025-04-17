"""
Empower Portfolio WebArchive Extractor
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
"""
#!/usr/bin/env python3
import argparse
import subprocess
import sys

def run_streamlit_dev():
    print("Starting Streamlit in development mode on port 8502...")
    subprocess.run([
        "streamlit", "run",
        "streamlit_app.py",
        "--server.port", "8502",
        "--server.address", "localhost"
    ])

def run_dash_dev():
    print("Starting Dash in development mode on port 8052...")
    subprocess.run([
        "python", "dash_app.py",
        "--port", "8052",
        "--host", "localhost"
    ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run development servers")
    parser.add_argument(
        "app",
        choices=["streamlit", "dash"],
        help="Which app to run in development mode"
    )

    args = parser.parse_args()

    try:
        if args.app == "streamlit":
            run_streamlit_dev()
        else:
            run_dash_dev()
    except KeyboardInterrupt:
        print("\nDevelopment server stopped")
        sys.exit(0)
