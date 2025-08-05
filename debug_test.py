#!/usr/bin/env python3
"""Simple test file to verify debugging works"""

def test_function():
    message = "Debug test working!"
    print(message)  # Set a breakpoint here
    return message

if __name__ == "__main__":
    result = test_function()
    print(f"Result: {result}")
