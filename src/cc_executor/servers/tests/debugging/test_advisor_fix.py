#!/usr/bin/env python3
"""Test the advisor fix - ensures col_types bug is resolved."""

import json
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Import the analysis function directly
from mcp_d3_visualization_advisor import _analyze_data_structure, _get_tabular_recommendations

def test_col_types_fix():
    """Test that the col_types bug is fixed."""
    
    print("Testing col_types bug fix...")
    print("=" * 60)
    
    # Create test data with both categorical and numeric columns
    test_data = [
        {"category": "A", "value": 100, "subcategory": "X"},
        {"category": "B", "value": 150, "subcategory": "Y"},
        {"category": "C", "value": 200, "subcategory": "X"},
        {"category": "D", "value": 175, "subcategory": "Y"},
    ]
    
    # Analyze the data
    analysis = _analyze_data_structure(test_data)
    
    print("\nPandas Analysis Results:")
    print(f"- Categorical columns: {analysis['pandas_analysis'].get('categorical_columns', [])}")
    print(f"- Numeric columns: {analysis['pandas_analysis'].get('numeric_columns', [])}")
    
    # Generate recommendations - this should not crash with NameError
    try:
        recommendations = _get_tabular_recommendations(analysis, test_data)
        print("\n✅ SUCCESS: No NameError for col_types!")
        print("\nGenerated Recommendations Preview:")
        print(recommendations[:500] + "...")
        
        # Check that bar chart is recommended
        if "Bar Chart" in recommendations:
            print("\n✅ Bar Chart correctly recommended for categorical + numeric data")
        
    except NameError as e:
        print(f"\n❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_col_types_fix()
    print("\n" + "=" * 60)
    print(f"Test Result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)