#!/usr/bin/env python3
"""Generate sample sales data for the data processing pipeline."""

import csv
import random
from datetime import datetime, timedelta

def generate_sales_data(filename='sales_data.csv', num_rows=1000):
    """Generate sample sales data CSV file."""
    
    # Define ranges
    products = [f'P{str(i).zfill(3)}' for i in range(1, 21)]  # P001-P020
    customers = [f'C{str(i).zfill(3)}' for i in range(1, 101)]  # C001-C100
    
    # Date range: last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # Create CSV
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['date', 'product_id', 'quantity', 'price', 'customer_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Generate rows
        for i in range(num_rows):
            # Random date in range
            days_offset = random.randint(0, 90)
            sale_date = start_date + timedelta(days=days_offset)
            
            row = {
                'date': sale_date.strftime('%Y-%m-%d'),
                'product_id': random.choice(products),
                'quantity': random.randint(1, 10),
                'price': round(random.uniform(10.00, 500.00), 2),
                'customer_id': random.choice(customers)
            }
            writer.writerow(row)
    
    print(f"✓ Generated {num_rows} rows of sales data in {filename}")
    print(f"  Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"  Products: {len(products)} unique")
    print(f"  Customers: {len(customers)} unique")

if __name__ == "__main__":
    generate_sales_data()