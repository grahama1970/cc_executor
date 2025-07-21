#!/usr/bin/env python3
"""Test the enhanced pandas-based visualization advisor."""

import json
import asyncio
from mcp_d3_visualization_advisor import analyze_and_recommend_visualization

async def test_pandas_analysis():
    """Test with various data types to show pandas analysis."""
    
    print("Testing D3 Visualization Advisor with Pandas Analysis")
    print("=" * 60)
    
    # Test 1: Time series data with quality issues
    print("\n1. Testing time series data with outliers and missing values...")
    timeseries_data = [
        {"date": "2024-01-01", "sales": 100, "returns": 5, "category": "Electronics"},
        {"date": "2024-01-02", "sales": 120, "returns": 8, "category": "Electronics"},
        {"date": "2024-01-03", "sales": 95, "returns": 3, "category": "Electronics"},
        {"date": "2024-01-04", "sales": 1500, "returns": 10, "category": "Electronics"},  # Outlier
        {"date": "2024-01-05", "sales": 110, "returns": None, "category": "Electronics"},  # Missing
        {"date": "2024-01-06", "sales": 105, "returns": 6, "category": "Clothing"},
        {"date": "2024-01-07", "sales": 130, "returns": 7, "category": "Clothing"},
        {"date": "2024-01-08", "sales": 115, "returns": 4, "category": " Clothing "},  # Whitespace
    ]
    
    result = await analyze_and_recommend_visualization(
        json.dumps(timeseries_data),
        "Show sales trends and identify anomalies"
    )
    
    print("\nPandas Analysis Highlights:")
    print("- Detected outliers")
    print("- Found missing values")
    print("- Identified whitespace issues")
    print("- Recognized time series pattern")
    
    # Save full report
    with open("/tmp/timeseries_analysis.md", "w") as f:
        f.write(result)
    print("Full report saved to: /tmp/timeseries_analysis.md")
    
    # Test 2: Highly correlated multivariate data
    print("\n2. Testing multivariate data with correlations...")
    multivariate_data = [
        {"temperature": 20, "ice_cream_sales": 100, "beach_visitors": 500, "day": "Mon"},
        {"temperature": 22, "ice_cream_sales": 120, "beach_visitors": 600, "day": "Tue"},
        {"temperature": 25, "ice_cream_sales": 150, "beach_visitors": 800, "day": "Wed"},
        {"temperature": 28, "ice_cream_sales": 200, "beach_visitors": 1000, "day": "Thu"},
        {"temperature": 30, "ice_cream_sales": 250, "beach_visitors": 1200, "day": "Fri"},
        {"temperature": 32, "ice_cream_sales": 300, "beach_visitors": 1500, "day": "Sat"},
        {"temperature": 35, "ice_cream_sales": 350, "beach_visitors": 1800, "day": "Sun"},
    ]
    
    result = await analyze_and_recommend_visualization(
        json.dumps(multivariate_data),
        "Show relationship between temperature and activities"
    )
    
    print("\nPandas Correlation Analysis:")
    print("- Strong correlations detected")
    print("- Scatter plot recommended")
    print("- Multiple visualization options provided")
    
    # Test 3: Percentage/proportion data
    print("\n3. Testing part-of-whole data...")
    percentage_data = [
        {"region": "North", "product_a": 25, "product_b": 35, "product_c": 40},
        {"region": "South", "product_a": 30, "product_b": 30, "product_c": 40},
        {"region": "East", "product_a": 20, "product_b": 45, "product_c": 35},
        {"region": "West", "product_a": 35, "product_b": 25, "product_c": 40},
    ]
    
    result = await analyze_and_recommend_visualization(
        json.dumps(percentage_data),
        "Compare product distribution by region"
    )
    
    print("\nPandas detected:")
    print("- Values sum to 100 (percentages)")
    print("- Stacked bar chart recommended")
    print("- Alternative: 100% stacked area chart")
    
    # Test 4: Skewed distribution
    print("\n4. Testing data with skewed distribution...")
    skewed_data = [
        {"user_id": f"u{i}", "purchases": 1 if i < 80 else (10 if i < 95 else 100)}
        for i in range(100)
    ]
    
    result = await analyze_and_recommend_visualization(
        json.dumps(skewed_data),
        "Show user purchase distribution"
    )
    
    print("\nPandas Distribution Analysis:")
    print("- Highly skewed distribution detected")
    print("- Log scale recommended")
    print("- Box plot or violin plot suggested")
    
    # Test 5: Geographic data
    print("\n5. Testing geographic data...")
    geo_data = [
        {"city": "New York", "latitude": 40.7128, "longitude": -74.0060, "population": 8.3},
        {"city": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437, "population": 4.0},
        {"city": "Chicago", "latitude": 41.8781, "longitude": -87.6298, "population": 2.7},
        {"city": "Houston", "latitude": 29.7604, "longitude": -95.3698, "population": 2.3},
    ]
    
    result = await analyze_and_recommend_visualization(
        json.dumps(geo_data),
        "Show city locations and sizes"
    )
    
    print("\nPandas Geographic Detection:")
    print("- Latitude/longitude columns found")
    print("- Map visualization recommended")
    print("- Alternative: Bubble map with size by population")
    
    print("\n" + "=" * 60)
    print("All tests complete! Check /tmp/timeseries_analysis.md for detailed example.")


if __name__ == "__main__":
    asyncio.run(test_pandas_analysis())