#!/usr/bin/env python3
"""
Test script to verify HTML sanitization functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import sanitize_html_content, basic_html_sanitize

def test_sanitization():
    """Test HTML sanitization functions"""
    
    print("Testing HTML Sanitization...")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'name': 'Basic HTML',
            'input': '<p>Hello <strong>World</strong>!</p>',
            'expected_safe': True
        },
        {
            'name': 'Script injection',
            'input': '<p>Hello</p><script>alert("xss")</script>',
            'expected_safe': False
        },
        {
            'name': 'Event handlers',
            'input': '<div onclick="alert()">Click me</div>',
            'expected_safe': False
        },
        {
            'name': 'Email with inline styles',
            'input': '<div style="color: red; font-size: 14px;">Styled content</div>',
            'expected_safe': True
        },
        {
            'name': 'Links',
            'input': '<a href="https://example.com">Safe link</a>',
            'expected_safe': True
        },
        {
            'name': 'JavaScript URL',
            'input': '<a href="javascript:alert()">Dangerous link</a>',
            'expected_safe': False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        
        # Test with main sanitization function
        try:
            result = sanitize_html_content(test_case['input'])
            print(f"Sanitized: {result}")
            
            # Basic safety check
            contains_script = '<script' in result.lower()
            contains_onclick = 'onclick' in result.lower()
            contains_javascript = 'javascript:' in result.lower()
            
            is_safe = not (contains_script or contains_onclick or contains_javascript)
            
            if test_case['expected_safe'] == is_safe:
                print("✅ PASS - Sanitization working as expected")
            else:
                print("❌ FAIL - Sanitization not working as expected")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            
            # Test fallback function
            try:
                fallback_result = basic_html_sanitize(test_case['input'])
                print(f"Fallback result: {fallback_result}")
            except Exception as fe:
                print(f"❌ FALLBACK ERROR: {fe}")

if __name__ == "__main__":
    test_sanitization()
    print("\n" + "=" * 50)
    print("Test completed!")