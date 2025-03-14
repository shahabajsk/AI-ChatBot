from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import os
import json
import requests
from models.analysis import analyze_file, query_data

# For visualization
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import seaborn as sns
import io
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store the analyzed data
analyzed_data = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    global analyzed_data
    
    # First check if it's a file upload request
    if user_message.lower() in ["upload a file", "upload file", "upload", "i want to upload a file"]:
        return jsonify({'response': "Please click the paperclip icon below to upload your CSV file for analysis."})
    
    # If we have analyzed data, check if the query is analytical
    if analyzed_data is not None:
        # Try to answer with our data analysis
        try:
            answer = query_data(user_message, analyzed_data)
            
            # Check if the response contains visualization data
            if isinstance(answer, dict) and 'visualization' in answer:
                return jsonify({
                    'response': answer['response'],
                    'visualization': answer['visualization']
                })
            elif answer:
                return jsonify({'response': answer})
        except Exception as e:
            print(f"Error in data query: {e}")
            # Return a friendly error message
            return jsonify({'response': f"I encountered an issue analyzing that request. Could you rephrase your question?"})
    
    # Otherwise, use Ollama for general questions
    try:
        # Call the Ollama API
        response = requests.post('http://localhost:11434/api/generate', 
            json={
                "model": "llama3.2",  # Using the installed model
                "prompt": user_message,
                "stream": False
            })
        
        if response.status_code == 200:
            return jsonify({'response': response.json().get('response', 'Sorry, I could not generate a response.')})
        else:
            return jsonify({'response': f"Error: {response.status_code}"})
    except Exception as e:
        return jsonify({'response': f"Error connecting to Ollama: {str(e)}"})

@app.route('/upload', methods=['POST'])
def upload_file():
    global analyzed_data
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    
    # Add debug print
    print(f"Received file: {file.filename}, type: {file.content_type}")
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and file.filename.lower().endswith('.csv'):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        # Analyze the file
        try:
            analyzed_data = analyze_file(filename)
            return jsonify({'success': 'File uploaded and analyzed successfully', 
                           'summary': analyzed_data['summary']})
        except Exception as e:
            print(f"Error analyzing file: {e}")
            return jsonify({'error': f'Error analyzing file: {str(e)}'})
    
    return jsonify({'error': 'Invalid file format. Please upload a CSV file.'})

@app.route('/generate_graph', methods=['POST'])
def generate_graph():
    global analyzed_data
    if analyzed_data is None:
        return jsonify({'error': 'No data has been analyzed yet. Please upload a file first.'})
    
    graph_type = request.json.get('type', '')
    
    if graph_type == 'price_by_supplier':
        return generate_price_by_supplier_graph()
    elif graph_type == 'price_by_date':
        return generate_price_by_date_graph()
    elif graph_type == 'price_by_category':
        return generate_price_by_category_graph()
    elif graph_type == 'supplier_comparison':
        suppliers = request.json.get('suppliers', [])
        category = request.json.get('category', '')
        return generate_supplier_comparison_graph(suppliers, category)
    elif graph_type == 'weekend_weekday_comparison':
        return generate_weekend_weekday_comparison()
    elif graph_type == 'best_deals':
        return generate_best_deals_graph()
    elif graph_type == 'category_price_difference':
        categories = request.json.get('categories', [])
        return generate_category_price_difference(categories)
    elif graph_type == 'weekly_comparison':
        return generate_weekly_comparison()
    else:
        return jsonify({'error': 'Unknown graph type'})

def generate_price_by_supplier_graph():
    df = analyzed_data['df']
    
    # Calculate average price by supplier
    supplier_prices = df.groupby('WebsiteSupplier')['InclusiveRate'].mean().sort_values()
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(12, 7))
    
    # Use a nicer color palette
    colors = sns.color_palette("viridis", len(supplier_prices))
    
    bars = plt.bar(supplier_prices.index, supplier_prices.values, color=colors)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.xlabel('Supplier', fontsize=12)
    plt.ylabel('Average Price ($)', fontsize=12)
    plt.title('Average Rental Prices by Supplier', fontsize=14, fontweight='bold')
    
    # Add price labels on top of the bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'${height:.2f}',
                ha='center', va='bottom', fontsize=9)
    
    # Add a light grid
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Improve layout
    plt.tight_layout()
    
    # Add a subtle border
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_price_by_date_graph():
    df = analyzed_data['df']
    
    # Calculate average price by date
    date_prices = df.groupby(df['PickUpDate'].dt.strftime('%Y-%m-%d'))['InclusiveRate'].mean()
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(12, 7))
    
    # Convert string dates to datetime for better x-axis formatting
    dates = [datetime.strptime(date, '%Y-%m-%d') for date in date_prices.index]
    
    # Plot with improved styling
    plt.plot(dates, date_prices.values, marker='o', linestyle='-', linewidth=2, 
             color='#3498db', markerfacecolor='white', markeredgecolor='#3498db', 
             markeredgewidth=2, markersize=8)
    
    # Format the date axis
    date_format = DateFormatter('%b %d')
    plt.gca().xaxis.set_major_formatter(date_format)
    
    # Improve the look
    plt.xticks(rotation=45, fontsize=10)
    plt.xlabel('Pickup Date', fontsize=12)
    plt.ylabel('Average Price ($)', fontsize=12)
    plt.title('Average Rental Prices by Pickup Date', fontsize=14, fontweight='bold')
    
    # Add prices directly on the graph
    for i, (date, price) in enumerate(zip(dates, date_prices.values)):
        plt.text(date, price + 5, f'${price:.2f}', ha='center', fontsize=8)
    
    # Add a light grid
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Highlight weekends with a light background
    min_price = min(date_prices.values) - 20
    max_price = max(date_prices.values) + 20
    
    for date in dates:
        if date.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
            plt.axvspan(date - timedelta(hours=12), date + timedelta(hours=12), 
                        color='#f5f5f5', alpha=0.5, zorder=0)
    
    # Improve layout
    plt.tight_layout()
    
    # Remove top and right spines
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_price_by_category_graph():
    df = analyzed_data['df']
    
    # Calculate average price by car category
    category_prices = df.groupby('WebsiteCarCategory')['InclusiveRate'].mean().sort_values()
    
    # Select top 15 categories for better visualization
    top_categories = category_prices.tail(15)
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(12, 8))
    
    # Use a nicer color palette
    colors = sns.color_palette("viridis", len(top_categories))
    
    # Create horizontal bar chart
    bars = plt.barh(top_categories.index, top_categories.values, color=colors)
    
    # Improve styling
    plt.xlabel('Average Price ($)', fontsize=12)
    plt.ylabel('Car Category', fontsize=12)
    plt.title('Average Rental Prices by Car Category (Top 15)', fontsize=14, fontweight='bold')
    
    # Add price labels
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 5, bar.get_y() + bar.get_height()/2.,
                f'${width:.2f}',
                ha='left', va='center', fontsize=9)
    
    # Add a light grid
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Improve layout
    plt.tight_layout()
    
    # Remove top and right spines
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_supplier_comparison_graph(suppliers, category):
    df = analyzed_data['df']
    
    if not category:
        # Filter only for the specified suppliers
        filtered_data = df[df['WebsiteSupplier'].isin(suppliers)]
        
        # Calculate average price by supplier and car category
        comparison_data = filtered_data.groupby(['WebsiteSupplier', 'WebsiteCarCategory'])['InclusiveRate'].mean().unstack()
    else:
        # Filter for the specified suppliers and category
        filtered_data = df[(df['WebsiteSupplier'].isin(suppliers)) & 
                          (df['WebsiteCarCategory'].str.contains(category, case=False))]
        
        # Calculate average price by supplier and pickup date
        comparison_data = filtered_data.groupby(['WebsiteSupplier', filtered_data['PickUpDate'].dt.strftime('%Y-%m-%d')])['InclusiveRate'].mean().unstack()
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Create a better color palette
    colors = sns.color_palette("Set2", len(comparison_data.index))
    
    # Plot with better styling
    for i, supplier in enumerate(comparison_data.index):
        plt.plot(comparison_data.columns, comparison_data.loc[supplier], 
                 marker='o', linestyle='-', linewidth=2, color=colors[i], 
                 markerfacecolor='white', markeredgecolor=colors[i], 
                 markeredgewidth=2, markersize=8, label=supplier)
    
    # Improve styling
    plt.title(f'Price Comparison for {category if category else "All Categories"}', 
              fontsize=14, fontweight='bold')
    plt.xlabel('Date' if category else 'Car Category', fontsize=12)
    plt.ylabel('Average Price ($)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Supplier', fontsize=10, title_fontsize=12)
    
    if len(comparison_data.columns) > 10:
        plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # Remove top and right spines
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Improve layout
    plt.tight_layout()
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_weekend_weekday_comparison():
    df = analyzed_data['df']
    
    # Add day of week
    df['DayOfWeek'] = df['PickUpDate'].dt.day_name()
    
    # Classify as weekend or weekday
    df['IsWeekend'] = df['PickUpDate'].dt.dayofweek >= 5
    
    # Calculate average prices
    weekend_price = df[df['IsWeekend']]['InclusiveRate'].mean()
    weekday_price = df[~df['IsWeekend']]['InclusiveRate'].mean()
    
    # Create a DataFrame for easier plotting
    comparison_df = pd.DataFrame({
        'Period': ['Weekday', 'Weekend'],
        'Average Price': [weekday_price, weekend_price]
    })
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(10, 7))
    
    # Use nicer colors
    colors = ['#3498db', '#e74c3c']
    
    # Create bar chart
    bars = plt.bar(comparison_df['Period'], comparison_df['Average Price'], color=colors, width=0.6)
    
    # Improve styling
    plt.ylabel('Average Price ($)', fontsize=12)
    plt.title('Weekend vs Weekday Average Rental Prices', fontsize=14, fontweight='bold')
    
    # Add price labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'${height:.2f}',
                ha='center', va='bottom', fontsize=11)
    
    # Highlight price difference
    price_diff = abs(weekend_price - weekday_price)
    diff_percent = (price_diff / min(weekend_price, weekday_price)) * 100
    
    if weekend_price > weekday_price:
        plt.text(0.5, 0.5, f"Weekends are ${price_diff:.2f} more expensive\n({diff_percent:.1f}% higher)", 
                 ha='center', va='center', transform=plt.gca().transAxes, 
                 bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'), 
                 fontsize=12)
    else:
        plt.text(0.5, 0.5, f"Weekdays are ${price_diff:.2f} more expensive\n({diff_percent:.1f}% higher)", 
                 ha='center', va='center', transform=plt.gca().transAxes, 
                 bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'), 
                 fontsize=12)
    
    # Add a light grid
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Improve layout
    plt.tight_layout()
    
    # Remove top and right spines
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_best_deals_graph():
    df = analyzed_data['df']
    aggs = analyzed_data['aggs']
    
    # Find deals below average price by category
    deals = []
    threshold = 30  # 30% below average
    
    for category, avg_price in aggs['avg_by_category'].items():
        category_data = df[df['WebsiteCarCategory'] == category]
        for _, row in category_data.iterrows():
            discount = (avg_price - row['InclusiveRate']) / avg_price * 100
            if discount > threshold:
                deals.append({
                    'category': category,
                    'supplier': row['WebsiteSupplier'],
                    'vehicle': row['VehicleName'],
                    'price': row['InclusiveRate'],
                    'avg_price': avg_price,
                    'discount': discount,
                    'date': row['PickUpDate'].strftime('%Y-%m-%d')
                })
    
    # Sort by discount percentage
    deals.sort(key=lambda x: x['discount'], reverse=True)
    
    # Take top 10 deals
    top_deals = deals[:10]
    
    # Create a DataFrame
    deals_df = pd.DataFrame(top_deals)
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(14, 8))
    
    # Create bar chart of discounts
    labels = [f"{row['supplier']} - {row['vehicle'][:15]}..." for _, row in deals_df.iterrows()]
    discount_bars = plt.barh(labels, deals_df['discount'], color='#27ae60')
    
    # Add price comparison on the same plot
    for i, (_, row) in enumerate(deals_df.iterrows()):
        plt.text(row['discount'] + 2, i, 
                 f"${row['price']:.2f} vs. avg ${row['avg_price']:.2f}", 
                 va='center', fontsize=9)
    
    # Improve styling
    plt.xlabel('Discount Percentage (%)', fontsize=12)
    plt.title('Top 10 Car Rental Deals (% Below Average Price)', fontsize=14, fontweight='bold')
    
    # Add percentage labels
    for bar in discount_bars:
        width = bar.get_width()
        plt.text(width - 5, bar.get_y() + bar.get_height()/2.,
                f"{width:.1f}%",
                ha='right', va='center', fontsize=9, color='white', fontweight='bold')
    
    # Improve layout
    plt.tight_layout()
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Remove top and right spines
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_category_price_difference(categories):
    df = analyzed_data['df']
    
    if not categories or len(categories) < 2:
        # Default to comparing economy and luxury
        categories = ['Economy', 'Luxury']
    
    # Filter data for the requested categories
    category_data = {}
    all_prices = []
    
    for category in categories:
        filtered = df[df['WebsiteCarCategory'].str.contains(category, case=False)]
        if not filtered.empty:
            avg_price = filtered['InclusiveRate'].mean()
            category_data[category] = {
                'avg_price': avg_price,
                'min_price': filtered['InclusiveRate'].min(),
                'max_price': filtered['InclusiveRate'].max(),
                'count': len(filtered),
                'suppliers': filtered['WebsiteSupplier'].nunique()
            }
            all_prices.append(avg_price)
    
    if len(category_data) < 2:
        return jsonify({'error': 'Could not find enough data for the requested categories'})
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    plt.figure(figsize=(12, 8))
    
    # Create a comparison chart with multiple segments
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'width_ratios': [2, 1]})
    
    # 1. Price bars on the left
    categories_list = list(category_data.keys())
    avg_prices = [category_data[cat]['avg_price'] for cat in categories_list]
    
    colors = sns.color_palette("viridis", len(categories_list))
    bars = ax1.bar(categories_list, avg_prices, color=colors)
    
    # Add price labels
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'${height:.2f}',
                ha='center', va='bottom', fontsize=10)
    
    # Improve left subplot
    ax1.set_ylabel('Average Price ($)', fontsize=12)
    ax1.set_title('Average Prices by Category', fontsize=13)
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 2. Price difference on the right
    price_diffs = []
    labels = []
    for i in range(len(categories_list)):
        for j in range(i+1, len(categories_list)):
            cat1, cat2 = categories_list[i], categories_list[j]
            price1, price2 = category_data[cat1]['avg_price'], category_data[cat2]['avg_price']
            diff = abs(price1 - price2)
            pct_diff = (diff / min(price1, price2)) * 100
            price_diffs.append(diff)
            labels.append(f"{cat1} vs {cat2}")
            
            # Add percent diff annotation
            higher = cat1 if price1 > price2 else cat2
            ax2.text(0.5, 0.3 + 0.2*len(price_diffs), 
                      f"{higher} is {pct_diff:.1f}% more expensive", 
                      ha='center', va='center', transform=ax2.transAxes, 
                      bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'), 
                      fontsize=10)
    
    # Plot the differences
    diff_bars = ax2.bar(labels, price_diffs, color='#3498db')
    
    # Add difference labels
    for bar in diff_bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'${height:.2f}',
                ha='center', va='bottom', fontsize=10)
    
    # Improve right subplot
    ax2.set_ylabel('Price Difference ($)', fontsize=12)
    ax2.set_title('Price Differences Between Categories', fontsize=13)
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Overall figure improvements
    plt.suptitle(f'Price Comparison: {" vs ".join(categories_list)}', fontsize=14, fontweight='bold')
    
    # Remove top and right spines
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    # Improve layout
    plt.tight_layout()
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    plt.close(fig)  # Close this figure to avoid warnings
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

def generate_weekly_comparison():
    df = analyzed_data['df']
    
    # Get all dates
    min_date = df['PickUpDate'].min()
    max_date = df['PickUpDate'].max()
    
    # Define weeks
    first_week_start = min_date
    first_week_end = min_date + timedelta(days=6)
    last_week_start = max_date - timedelta(days=6)
    last_week_end = max_date
    
    # Filter by week
    first_week_data = df[(df['PickUpDate'] >= first_week_start) & (df['PickUpDate'] <= first_week_end)]
    last_week_data = df[(df['PickUpDate'] >= last_week_start) & (df['PickUpDate'] <= last_week_end)]
    
    # Calculate daily averages for each week
    first_week_daily = first_week_data.groupby(first_week_data['PickUpDate'].dt.strftime('%Y-%m-%d'))['InclusiveRate'].mean()
    last_week_daily = last_week_data.groupby(last_week_data['PickUpDate'].dt.strftime('%Y-%m-%d'))['InclusiveRate'].mean()
    
    # Calculate overall averages
    first_week_avg = first_week_data['InclusiveRate'].mean()
    last_week_avg = last_week_data['InclusiveRate'].mean()
    
    # Set the style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Create the plot with a larger figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
    
    # Plot daily averages on top subplot
    ax1.plot(range(len(first_week_daily)), first_week_daily.values, 'o-', label=f'First Week ({first_week_start.strftime("%b %d")} - {first_week_end.strftime("%b %d")})', color='#3498db')
    ax1.plot(range(len(last_week_daily)), last_week_daily.values, 'o-', label=f'Last Week ({last_week_start.strftime("%b %d")} - {last_week_end.strftime("%b %d")})', color='#e74c3c')
    
    # Add data labels
    for i, (price1, price2) in enumerate(zip(first_week_daily.values, last_week_daily.values)):
        ax1.text(i, price1 + 2, f'${price1:.2f}', ha='center', va='bottom', fontsize=9, color='#3498db')
        ax1.text(i, price2 + 2, f'${price2:.2f}', ha='center', va='bottom', fontsize=9, color='#e74c3c')
    
# Improve top subplot
    ax1.set_ylabel('Average Daily Price ($)', fontsize=12)
    ax1.set_title('Daily Price Comparison: First Week vs Last Week', fontsize=14)
    ax1.set_xticks(range(len(first_week_daily)))
    ax1.set_xticklabels([f'Day {i+1}' for i in range(len(first_week_daily))], rotation=45)
    ax1.legend()
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Plot overall averages on bottom subplot
    weeks = ['First Week', 'Last Week']
    avgs = [first_week_avg, last_week_avg]
    colors = ['#3498db', '#e74c3c']
    
    bars = ax2.bar(weeks, avgs, color=colors)
    
    # Add price labels
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'${height:.2f}',
                ha='center', va='bottom', fontsize=10)
    
    # Calculate and show price difference
    price_diff = abs(first_week_avg - last_week_avg)
    diff_percent = (price_diff / min(first_week_avg, last_week_avg)) * 100
    
    if last_week_avg > first_week_avg:
        ax2.text(0.5, 0.8, f"Last week is ${price_diff:.2f} more expensive\n({diff_percent:.1f}% higher)", 
                ha='center', va='center', transform=ax2.transAxes, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'), 
                fontsize=10)
    else:
        ax2.text(0.5, 0.8, f"First week is ${price_diff:.2f} more expensive\n({diff_percent:.1f}% higher)", 
                ha='center', va='center', transform=ax2.transAxes, 
                bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'), 
                fontsize=10)
    
    # Improve bottom subplot
    ax2.set_ylabel('Average Price ($)', fontsize=12)
    ax2.set_title('Overall Weekly Price Comparison', fontsize=14)
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Remove top and right spines
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    # Improve layout
    plt.tight_layout()
    
    # Save the plot to a bytes buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100)
    plt.close(fig)
    buffer.seek(0)
    
    # Encode the image to base64
    image_png = buffer.getvalue()
    buffer.close()
    encoded = base64.b64encode(image_png).decode('utf-8')
    
    return jsonify({'image': encoded})

if __name__ == '__main__':
    app.run(debug=True, port=5002)