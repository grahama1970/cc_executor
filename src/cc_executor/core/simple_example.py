#!/usr/bin/env python3
"""
Simple example showing how to use OutputCapture for response saving.
"""

if __name__ == "__main__":
    from usage_helper import OutputCapture
    
    with OutputCapture(__file__) as capture:
        print("=== Simple Example Module ===")
        print()
        print("This demonstrates the OutputCapture pattern:")
        print("1. Import OutputCapture from usage_helper")
        print("2. Use it as a context manager")
        print("3. All print statements are captured")
        print("4. Output is automatically saved as prettified JSON")
        print()
        print("Benefits:")
        print("• Clean, consistent code")
        print("• Automatic JSON formatting")
        print("• Includes metadata (timestamp, duration, etc.)")
        print("• No duplicate text files")
        print()
        print("✅ Example completed successfully!")