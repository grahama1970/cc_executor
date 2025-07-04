#!/usr/bin/env python3
"""Calculate business metrics from cleaned sales data."""

import csv
import json
from collections import defaultdict
from datetime import datetime

def calculate_business_metrics(input_file='cleaned_sales_data.csv', output_file='metrics.json'):
    """Calculate key business metrics and save to JSON."""
    
    print("Calculating business metrics...")
    
    # Initialize data structures
    total_revenue = 0
    revenue_by_product = defaultdict(float)
    revenue_by_month = defaultdict(float)
    revenue_by_day = defaultdict(float)
    customer_spending = defaultdict(float)
    order_count = 0
    
    # Read and process data
    with open(input_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            revenue = float(row['revenue'])
            product = row['product_id']
            month = row['month']
            date = row['date']
            customer = row['customer_id']
            
            # Aggregate metrics
            total_revenue += revenue
            revenue_by_product[product] += revenue
            revenue_by_month[month] += revenue
            revenue_by_day[date] += revenue
            customer_spending[customer] += revenue
            order_count += 1
    
    # Calculate derived metrics
    average_order_value = round(total_revenue / order_count, 2) if order_count > 0 else 0
    
    # Top 5 products by revenue
    top_products = sorted(revenue_by_product.items(), key=lambda x: x[1], reverse=True)[:5]
    top_products_dict = {
        product: {
            "revenue": round(revenue, 2),
            "percentage": round((revenue / total_revenue) * 100, 2)
        } for product, revenue in top_products
    }
    
    # Revenue by month with percentage
    months_order = ['April', 'May', 'June', 'July']
    revenue_by_month_dict = {}
    prev_month_revenue = None
    
    for month in months_order:
        if month in revenue_by_month:
            revenue = revenue_by_month[month]
            month_data = {
                "revenue": round(revenue, 2),
                "percentage_of_total": round((revenue / total_revenue) * 100, 2)
            }
            
            # Calculate month-over-month change
            if prev_month_revenue is not None:
                change = ((revenue - prev_month_revenue) / prev_month_revenue) * 100
                month_data["mom_change_percent"] = round(change, 2)
            
            revenue_by_month_dict[month] = month_data
            prev_month_revenue = revenue
    
    # Top 10 customers by lifetime value
    top_customers = sorted(customer_spending.items(), key=lambda x: x[1], reverse=True)[:10]
    top_customers_dict = {
        customer: {
            "lifetime_value": round(spending, 2),
            "percentage_of_total": round((spending / total_revenue) * 100, 2)
        } for customer, spending in top_customers
    }
    
    # Best and worst performing days
    daily_revenues = [(date, revenue) for date, revenue in revenue_by_day.items()]
    daily_revenues.sort(key=lambda x: x[1], reverse=True)
    
    best_days = [
        {"date": date, "revenue": round(revenue, 2)} 
        for date, revenue in daily_revenues[:5]
    ]
    
    worst_days = [
        {"date": date, "revenue": round(revenue, 2)} 
        for date, revenue in daily_revenues[-5:]
    ]
    
    # Compile all metrics
    metrics = {
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": order_count,
            "average_order_value": average_order_value,
            "unique_products": len(revenue_by_product),
            "unique_customers": len(customer_spending)
        },
        "revenue_by_product_top5": top_products_dict,
        "revenue_by_month": revenue_by_month_dict,
        "customer_lifetime_value_top10": top_customers_dict,
        "best_performing_days": best_days,
        "worst_performing_days": worst_days,
        "insights": {
            "top_product_concentration": f"Top 5 products account for {sum(p['percentage'] for p in top_products_dict.values()):.1f}% of revenue",
            "top_customer_concentration": f"Top 10 customers account for {sum(c['percentage_of_total'] for c in top_customers_dict.values()):.1f}% of revenue",
            "revenue_trend": "Revenue increased from April to June, with partial July data"
        }
    }
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n✓ Business metrics calculated and saved to: {output_file}")
    print(f"\nKey Highlights:")
    print(f"- Total Revenue: ${metrics['summary']['total_revenue']:,.2f}")
    print(f"- Average Order Value: ${metrics['summary']['average_order_value']}")
    print(f"- Top Product: {list(top_products_dict.keys())[0]} (${list(top_products_dict.values())[0]['revenue']:,.2f})")
    print(f"- Top Customer: {list(top_customers_dict.keys())[0]} (${list(top_customers_dict.values())[0]['lifetime_value']:,.2f})")

if __name__ == "__main__":
    calculate_business_metrics()