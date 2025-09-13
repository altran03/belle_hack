#!/usr/bin/env python3
"""
Sample Python application with deliberate bugs for BugSniper Pro testing.
This file contains various issues that BugSniper Pro should detect and fix.
"""

import os
import sys
import json
from typing import List, Dict, Optional

# Bug 1: Unused import
import datetime

# Bug 2: Bare except clause
def divide_numbers(a: int, b: int) -> float:
    try:
        return a / b
    except:  # Should specify exception type
        return 0.0

# Bug 3: Missing docstring
def process_data(data: List[Dict]) -> List[str]:
    """Process a list of dictionaries and return string values."""
    result = []
    for item in data:
        if isinstance(item, dict):
            for key, value in item.items():
                result.append(str(value))
    return result

# Bug 4: Potential security issue - using eval
def calculate_expression(expr: str) -> float:
    """Calculate mathematical expression (SECURITY RISK)."""
    try:
        return eval(expr)  # Dangerous!
    except:
        return 0.0

# Bug 5: Missing type hints
def get_user_info(user_id):
    """Get user information by ID."""
    # Bug 6: Hardcoded path
    config_path = "/tmp/config.json"
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data.get('users', {}).get(str(user_id))
    
    return None

# Bug 7: Inefficient algorithm
def find_duplicates(items: List[int]) -> List[int]:
    """Find duplicate items in a list."""
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates

# Bug 8: Missing error handling
def read_config_file(file_path: str) -> Dict:
    """Read configuration from file."""
    with open(file_path, 'r') as f:
        return json.load(f)

# Bug 9: Global variable usage
counter = 0

def increment_counter():
    """Increment global counter."""
    global counter
    counter += 1
    return counter

# Bug 10: Print statement (Python 2 style)
def debug_print(message):
    print message  # Should be print(message)

class DataProcessor:
    """Data processing class with various issues."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.data = []
    
    # Bug 11: Missing docstring
    def add_item(self, item):
        self.data.append(item)
    
    # Bug 12: No input validation
    def get_item(self, index: int):
        return self.data[index]
    
    # Bug 13: Resource leak
    def process_file(self, file_path: str):
        file = open(file_path, 'r')
        content = file.read()
        # Missing file.close()
        return content

def main():
    """Main function with various issues."""
    print("BugSniper Pro Sample Application")
    
    # Bug 14: Unused variable
    unused_var = "This variable is never used"
    
    # Bug 15: Division by zero potential
    numbers = [1, 2, 3, 0, 4, 5]
    for num in numbers:
        result = divide_numbers(10, num)
        print(f"10 / {num} = {result}")
    
    # Bug 16: Inefficient list comprehension
    squares = [i*i for i in range(1000) if i % 2 == 0]
    print(f"Even squares: {squares[:5]}")
    
    # Bug 17: Missing exception handling
    user_data = get_user_info(123)
    print(f"User data: {user_data}")
    
    # Bug 18: Using exec (security risk)
    code = "print('Hello from exec!')"
    exec(code)
    
    # Bug 19: Inconsistent naming
    processor = DataProcessor({"debug": True})
    processor.add_item("test")
    
    # Bug 20: Memory inefficient operation
    large_list = list(range(1000000))
    duplicates = find_duplicates(large_list[:100])  # Only check first 100 items
    print(f"Found {len(duplicates)} duplicates")

if __name__ == "__main__":
    main()
