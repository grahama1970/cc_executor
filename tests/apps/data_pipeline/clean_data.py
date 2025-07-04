#!/usr/bin/env python3
"""Clean and transform sales data for the data processing pipeline."""

import csv
from datetime import datetime
from collections import defaultdict

def clean_and_transform_data(input_file='sales_data.csv', output_file='cleaned_sales_data.csv'):
    """Clean and transform sales data with documented strategies."""
    
    print("Starting data cleaning and transformation...")
    
    # Track statistics
    total_rows = 0
    duplicate_rows = 0
    missing_values = 0
    
    # Store unique rows to remove duplicates
    seen_rows = set()
    cleaned_data = []
    
    # Read and process data
    with open(input_file, 'r') as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            total_rows += 1
            
            # Check for missing values
            has_missing = False
            for field in ['date', 'product_id', 'quantity', 'price', 'customer_id']:
                if not row.get(field) or row[field].strip() == '':
                    has_missing = True
                    missing_values += 1
                    break
            
            # Skip rows with missing values (strategy: complete case analysis)
            if has_missing:
                print(f"  Skipping row {total_rows} due to missing values")
                continue
            
            # Create unique row identifier for duplicate detection
            row_key = (row['date'], row['product_id'], row['customer_id'], row['quantity'], row['price'])
            
            # Check for duplicates
            if row_key in seen_rows:
                duplicate_rows += 1
                print(f"  Skipping duplicate row {total_rows}")
                continue
            
            seen_rows.add(row_key)
            
            # Transform the data
            # 1. Parse and standardize date to ISO format (already in YYYY-MM-DD)
            date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
            
            # 2. Calculate revenue
            quantity = int(row['quantity'])
            price = float(row['price'])
            revenue = round(quantity * price, 2)
            
            # 3. Add temporal features
            day_of_week = date_obj.strftime('%A')  # Monday, Tuesday, etc.
            month = date_obj.strftime('%B')  # January, February, etc.
            
            # Create cleaned row
            cleaned_row = {
                'date': date_obj.strftime('%Y-%m-%d'),  # ISO format
                'product_id': row['product_id'].strip(),
                'quantity': quantity,
                'price': price,
                'customer_id': row['customer_id'].strip(),
                'revenue': revenue,
                'day_of_week': day_of_week,
                'month': month
            }
            
            cleaned_data.append(cleaned_row)
    
    # Write cleaned data
    with open(output_file, 'w', newline='') as outfile:
        fieldnames = ['date', 'product_id', 'quantity', 'price', 'customer_id', 
                     'revenue', 'day_of_week', 'month']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in cleaned_data:
            writer.writerow(row)
    
    # Print cleaning summary
    print("\n=== Data Cleaning Summary ===")
    print(f"Total rows processed: {total_rows}")
    print(f"Duplicate rows removed: {duplicate_rows}")
    print(f"Rows with missing values removed: {missing_values}")
    print(f"Clean rows written: {len(cleaned_data)}")
    print(f"\nOutput saved to: {output_file}")
    
    # Document cleaning strategies
    with open('data_cleaning_log.txt', 'w') as log:
        log.write("DATA CLEANING STRATEGIES\n")
        log.write("========================\n\n")
        log.write("1. Missing Values Strategy: Complete Case Analysis\n")
        log.write("   - Removed any rows with missing values in any field\n")
        log.write(f"   - Total rows with missing values: {missing_values}\n\n")
        log.write("2. Duplicate Removal Strategy: Exact Match\n")
        log.write("   - Identified duplicates based on all fields (date, product, customer, quantity, price)\n")
        log.write(f"   - Total duplicate rows removed: {duplicate_rows}\n\n")
        log.write("3. Data Transformations Applied:\n")
        log.write("   - Added revenue column: quantity * price\n")
        log.write("   - Added day_of_week column (Monday, Tuesday, etc.)\n")
        log.write("   - Added month column (January, February, etc.)\n")
        log.write("   - Dates already in ISO format (YYYY-MM-DD), no conversion needed\n\n")
        log.write(f"4. Final Statistics:\n")
        log.write(f"   - Original rows: {total_rows}\n")
        log.write(f"   - Clean rows: {len(cleaned_data)}\n")
        log.write(f"   - Data reduction: {round((1 - len(cleaned_data)/total_rows) * 100, 2)}%\n")
    
    print("\nCleaning strategies documented in: data_cleaning_log.txt")

if __name__ == "__main__":
    clean_and_transform_data()