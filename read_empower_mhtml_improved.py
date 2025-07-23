#!/usr/bin/env python3
"""
Improved MHTML parser that uses the advanced webarchive parser logic
"""

import email
from email import policy
import bs4
import logging

# Set up logging
logger = logging.getLogger(__name__)

def extract_mhtml_text(file_path):
    """Extract text content from an MHTML file."""
    try:
        # Read the MHTML file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            mhtml_content = file.read()

        # Parse the MHTML content using email parser
        message = email.message_from_string(mhtml_content, policy=policy.default)

        # Extract HTML content from MHTML
        html_content = None

        # Iterate through parts to find HTML content
        for part in message.walk():
            content_type = part.get_content_type()

            if content_type == 'text/html':
                html_content = part.get_content()
                break

        if not html_content:
            return "Error: No HTML content found in MHTML file."

        # Parse HTML with BeautifulSoup
        soup = bs4.BeautifulSoup(html_content, "html.parser")

        # Extract visible text
        extracted_text = soup.get_text(separator="\n")

        return extracted_text
    except Exception as e:
        logger.error(f"Error reading MHTML file: {e}", exc_info=True)
        return f"Error reading MHTML file: {e}"

def extract_net_worth_data(text_content):
    """Extract net worth data from MHTML text content using improved webarchive parser logic"""
    # Import the improved parser from webarchive module
    from read_empower_webarchive import extract_net_worth_data as webarchive_parser

    # Use the webarchive parser on the MHTML text
    return webarchive_parser(text_content)
