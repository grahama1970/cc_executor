#!/usr/bin/env python3
import pandas as pd
import json
from datetime import datetime
from collections import defaultdict

# Read the sales data
df = pd.read_csv('cleaned_sales_data.csv')

# Convert date column to datetime
df['date'] = pd.to_datetime(df['date'])

# Calculate metrics
metrics = {}

# 1. Total Revenue
total_revenue = df['total'].sum()
metrics['total_revenue'] = round(total_revenue, 2)

# 2. Revenue by Product (Top 5)
revenue_by_product = df.groupby('product')['total'].sum().sort_values(ascending=False)
top_5_products = revenue_by_product.head(5)
metrics['revenue_by_product_top_5'] = {
    product: round(revenue, 2) for product, revenue in top_5_products.items()
}

# 3. Revenue by Month
df['year_month'] = df['date'].dt.to_period('M').astype(str)
revenue_by_month = df.groupby('year_month')['total'].sum().sort_index()
metrics['revenue_by_month'] = {
    month: round(revenue, 2) for month, revenue in revenue_by_month.items()
}

# Calculate month-over-month percentage changes
month_changes = {}
months = list(revenue_by_month.index)
for i in range(1, len(months)):
    prev_revenue = revenue_by_month.iloc[i-1]
    curr_revenue = revenue_by_month.iloc[i]
    pct_change = ((curr_revenue - prev_revenue) / prev_revenue) * 100
    month_changes[months[i]] = round(pct_change, 2)
metrics['month_over_month_pct_change'] = month_changes

# 4. Average Order Value
average_order_value = df['total'].mean()
metrics['average_order_value'] = round(average_order_value, 2)

# 5. Customer Lifetime Value (Top 10)
# Assuming customer_id exists, otherwise use customer name
customer_col = 'customer_id' if 'customer_id' in df.columns else 'customer'
clv = df.groupby(customer_col)['total'].sum().sort_values(ascending=False)
top_10_customers = clv.head(10)
metrics['customer_lifetime_value_top_10'] = {
    str(customer): round(value, 2) for customer, value in top_10_customers.items()
}

# 6. Best and Worst Performing Days
daily_revenue = df.groupby(df['date'].dt.date)['total'].sum()
best_day = daily_revenue.idxmax()
worst_day = daily_revenue.idxmin()
metrics['best_performing_day'] = {
    'date': str(best_day),
    'revenue': round(daily_revenue[best_day], 2)
}
metrics['worst_performing_day'] = {
    'date': str(worst_day),
    'revenue': round(daily_revenue[worst_day], 2)
}

# Calculate additional insights
metrics['total_orders'] = len(df)
metrics['unique_customers'] = df[customer_col].nunique()
metrics['unique_products'] = df['product'].nunique()

# Product performance percentages
total_product_revenue = revenue_by_product.sum()
product_percentages = {}
for product, revenue in top_5_products.items():
    percentage = (revenue / total_product_revenue) * 100
    product_percentages[product] = round(percentage, 2)
metrics['product_revenue_percentage'] = product_percentages

# Save to JSON
with open('metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("Metrics calculated and saved to metrics.json")
print(f"\nSummary:")
print(f"Total Revenue: ${metrics['total_revenue']:,.2f}")
print(f"Total Orders: {metrics['total_orders']:,}")
print(f"Average Order Value: ${metrics['average_order_value']:.2f}")
print(f"Unique Customers: {metrics['unique_customers']:,}")
print(f"Unique Products: {metrics['unique_products']:,}")