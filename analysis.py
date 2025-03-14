import pandas as pd
import numpy as np
import re
import datetime
from collections import defaultdict

def analyze_file(filename):
    """Analyze a rate shopping CSV file and extract useful information."""
    # Read the CSV file
    df = pd.read_csv(filename)
    
    # Basic cleanup
    # Convert date columns to datetime
    for col in ['PickUpDate', 'DropOffDate', 'ShopDate']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Summary statistics
    summary = {
        'total_records': len(df),
        'unique_suppliers': df['WebsiteSupplier'].nunique() if 'WebsiteSupplier' in df.columns else 0,
        'unique_categories': df['WebsiteCarCategory'].nunique() if 'WebsiteCarCategory' in df.columns else 0,
        'date_range': {
            'min': df['PickUpDate'].min().strftime('%Y-%m-%d') if 'PickUpDate' in df.columns else '',
            'max': df['PickUpDate'].max().strftime('%Y-%m-%d') if 'PickUpDate' in df.columns else ''
        },
        'websites': df['Website'].unique().tolist() if 'Website' in df.columns else []
    }
    
    # Precompute some useful aggregations
    aggs = {}
    
    # Average rates by car category
    if 'WebsiteCarCategory' in df.columns and 'InclusiveRate' in df.columns:
        aggs['avg_by_category'] = df.groupby('WebsiteCarCategory')['InclusiveRate'].mean().to_dict()
    
    # Average rates by supplier
    if 'WebsiteSupplier' in df.columns and 'InclusiveRate' in df.columns:
        aggs['avg_by_supplier'] = df.groupby('WebsiteSupplier')['InclusiveRate'].mean().to_dict()
    
    # Average rates by pickup date
    if 'PickUpDate' in df.columns and 'InclusiveRate' in df.columns:
        aggs['avg_by_date'] = df.groupby(df['PickUpDate'].dt.strftime('%Y-%m-%d'))['InclusiveRate'].mean().to_dict()
    
    # Average rates by day of week
    if 'PickUpDate' in df.columns and 'InclusiveRate' in df.columns:
        aggs['avg_by_day_of_week'] = df.groupby(df['PickUpDate'].dt.day_name())['InclusiveRate'].mean().to_dict()
    
    # Minimum rate by car category
    if 'WebsiteCarCategory' in df.columns and 'InclusiveRate' in df.columns:
        min_rates = {}
        for category in df['WebsiteCarCategory'].unique():
            category_df = df[df['WebsiteCarCategory'] == category]
            if not category_df.empty:
                min_idx = category_df['InclusiveRate'].idxmin()
                min_rates[category] = {
                    'rate': category_df.loc[min_idx, 'InclusiveRate'],
                    'supplier': category_df.loc[min_idx, 'WebsiteSupplier'],
                    'vehicle': category_df.loc[min_idx, 'VehicleName']
                }
        aggs['min_by_category'] = min_rates
    
    # Average rates by supplier for each car category
    if 'WebsiteCarCategory' in df.columns and 'WebsiteSupplier' in df.columns and 'InclusiveRate' in df.columns:
        supplier_category_rates = {}
        for category in df['WebsiteCarCategory'].unique():
            category_df = df[df['WebsiteCarCategory'] == category]
            supplier_rates = category_df.groupby('WebsiteSupplier')['InclusiveRate'].mean().to_dict()
            supplier_category_rates[category] = supplier_rates
        aggs['supplier_by_category'] = supplier_category_rates
    
    # Weekend vs weekday rates
    if 'PickUpDate' in df.columns and 'InclusiveRate' in df.columns:
        df['is_weekend'] = df['PickUpDate'].dt.dayofweek >= 5  # 5 = Saturday, 6 = Sunday
        weekend_avg = df[df['is_weekend']]['InclusiveRate'].mean()
        weekday_avg = df[~df['is_weekend']]['InclusiveRate'].mean()
        aggs['weekend_weekday'] = {
            'weekend': weekend_avg,
            'weekday': weekday_avg
        }
    
    # Return the dataframe and aggregations
    return {
        'df': df,
        'summary': summary,
        'aggs': aggs
    }

def query_data(question, data):
    """Attempt to answer analytical questions about the rate shopping data."""
    df = data['df']
    aggs = data['aggs']
    question = question.lower()
    
    # Check for visualization requests
    if any(term in question for term in ['plot', 'graph', 'chart', 'visualize', 'visualization', 'show me']):
        return handle_visualization_request(question, df)

    # PRICE ANALYSIS QUESTIONS
    
    # Cheapest car by category and date
    cheapest_car_match = re.search(r"cheapest\s+(\w+)\s+car.*?for\s+(.*?)(\?|$)", question)
    if cheapest_car_match:
        category = cheapest_car_match.group(1).capitalize()
        date_str = cheapest_car_match.group(2).strip()
        
        # Try to parse the date
        try:
            # Convert things like "April 5" to a date
            current_year = datetime.datetime.now().year
            date_obj = pd.to_datetime(f"{date_str}, {current_year}")
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Filter the data
            filtered = df[(df['WebsiteCarCategory'].str.contains(category, case=False)) & 
                          (df['PickUpDate'].dt.strftime('%Y-%m-%d') == date_str)]
            
            if not filtered.empty:
                cheapest = filtered.loc[filtered['InclusiveRate'].idxmin()]
                return f"The cheapest {category} car for {date_obj.strftime('%B %d')} is a {cheapest['VehicleName']} " \
                       f"from {cheapest['WebsiteSupplier']} at ${cheapest['InclusiveRate']:.2f} per day."
            else:
                return f"Sorry, I couldn't find any {category} cars available for {date_str}."
        except:
            return f"I couldn't understand the date format. Please specify a date like 'April 5'."
    
    # Best rates by category
    best_rates_match = re.search(r"(which|what) supplier has the best rates for (.*?)(\?|$)", question)
    if best_rates_match:
        category = best_rates_match.group(2).strip()
        
        # Check for SUVs
        if "suv" in category.lower():
            # Filter for SUV categories
            filtered = df[df['WebsiteCarCategory'].str.contains('SUV', case=False)]
            
            if not filtered.empty:
                supplier_rates = filtered.groupby('WebsiteSupplier')['InclusiveRate'].mean().sort_values()
                best_supplier = supplier_rates.index[0]
                best_rate = supplier_rates.iloc[0]
                
                return f"For SUVs, {best_supplier} has the best average rate at ${best_rate:.2f} per day."
            else:
                return "Sorry, I couldn't find any SUV categories in the data."
        else:
            # Try to match the category
            matching_categories = [cat for cat in df['WebsiteCarCategory'].unique() 
                                  if category.lower() in cat.lower()]
            
            if matching_categories:
                best_rates = {}
                for cat in matching_categories:
                    filtered = df[df['WebsiteCarCategory'] == cat]
                    if not filtered.empty:
                        supplier_rates = filtered.groupby('WebsiteSupplier')['InclusiveRate'].mean()
                        best_supplier = supplier_rates.idxmin()
                        best_rate = supplier_rates.min()
                        best_rates[cat] = (best_supplier, best_rate)
                
                if best_rates:
                    response = f"Here are the suppliers with the best rates for {category} car categories:\n\n"
                    for cat, (supplier, rate) in best_rates.items():
                        response += f"- {cat}: {supplier} at ${rate:.2f} per day\n"
                    return response
            
            return f"Sorry, I couldn't find data for '{category}' car categories."
    
    # Compare websites
    website_compare_match = re.search(r"is (.*?) or (.*?) offering better deals", question)
    if website_compare_match:
        website1 = website_compare_match.group(1).strip().capitalize()
        website2 = website_compare_match.group(2).strip().capitalize()
        
        site1_data = df[df['Website'] == website1]
        site2_data = df[df['Website'] == website2]
        
        if not site1_data.empty and not site2_data.empty:
            avg1 = site1_data['InclusiveRate'].mean()
            avg2 = site2_data['InclusiveRate'].mean()
            
            better_site = website1 if avg1 < avg2 else website2
            diff_percent = abs(avg1 - avg2) / max(avg1, avg2) * 100
            
            return f"{better_site} is currently offering better deals with average rates " \
                   f"${min(avg1, avg2):.2f} vs ${max(avg1, avg2):.2f} " \
                   f"({diff_percent:.1f}% difference)."
        else:
            available_websites = df['Website'].unique()
            return f"Sorry, I couldn't find data for both {website1} and {website2}. Available websites in the data are: {', '.join(available_websites)}."
    
    # Best time to rent
    best_time_match = re.search(r"best time to rent.*?in (.*?) in (.*?)(\?|$)", question)
    if best_time_match:
        location = best_time_match.group(1).strip()
        month = best_time_match.group(2).strip()
        
        # Filter by month
        try:
            month_num = pd.to_datetime(month, format='%B').month
            monthly_data = df[df['PickUpDate'].dt.month == month_num]
            
            if not monthly_data.empty:
                daily_avg = monthly_data.groupby(monthly_data['PickUpDate'].dt.day)['InclusiveRate'].mean()
                best_day = daily_avg.idxmin()
                
                return f"Based on the data, the best time to rent a car in {location} during {month} " \
                       f"is around the {best_day}th, with an average rate of ${daily_avg.min():.2f}."
            else:
                return f"Sorry, I don't have enough data for rentals in {location} during {month}."
        except:
            return "I couldn't determine the best time based on the available data."
    
    # Show deals below average
    below_avg_match = re.search(r"deals more than (\d+)% below average", question)
    if below_avg_match:
        threshold = int(below_avg_match.group(1))
        
        deals = []
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
                        'discount': discount,
                        'date': row['PickUpDate'].strftime('%Y-%m-%d')
                    })
        
        if deals:
            # Sort by discount percentage
            deals.sort(key=lambda x: x['discount'], reverse=True)
            
            # Format response
            response = f"I found {len(deals)} deals with more than {threshold}% below average price. Here are the top 5:\n\n"
            for i, deal in enumerate(deals[:5]):
                response += f"{i+1}. {deal['vehicle']} ({deal['category']}) from {deal['supplier']}: " \
                           f"${deal['price']:.2f} ({deal['discount']:.1f}% below avg) on {deal['date']}\n"
            
            return response
        else:
            return f"Sorry, I couldn't find any deals more than {threshold}% below average price."
    
    # Compare suppliers for a category
    supplier_compare_match = re.search(r"compare rates between (.*?) and (.*?) for (.*?) cars", question)
    if supplier_compare_match:
        supplier1 = supplier_compare_match.group(1).strip()
        supplier2 = supplier_compare_match.group(2).strip()
        category = supplier_compare_match.group(3).strip()
        
        filtered = df[df['WebsiteCarCategory'].str.contains(category, case=False)]
        supplier1_data = filtered[filtered['WebsiteSupplier'] == supplier1]
        supplier2_data = filtered[filtered['WebsiteSupplier'] == supplier2]
        
        if not supplier1_data.empty and not supplier2_data.empty:
            avg1 = supplier1_data['InclusiveRate'].mean()
            avg2 = supplier2_data['InclusiveRate'].mean()
            
            cheaper = supplier1 if avg1 < avg2 else supplier2
            diff = abs(avg1 - avg2)
            diff_percent = diff / max(avg1, avg2) * 100
            
            return f"For {category} cars, {cheaper} offers better rates with an average of ${min(avg1, avg2):.2f} " \
                   f"compared to ${max(avg1, avg2):.2f} from {supplier2 if cheaper == supplier1 else supplier1}. " \
                   f"That's a difference of ${diff:.2f} ({diff_percent:.1f}%)."
        else:
            return f"Sorry, I couldn't find comparison data for both {supplier1} and {supplier2} for {category} cars."
    
    # Price difference between categories
    category_diff_match = re.search(r"price difference between (.*?) and (.*?) cars", question)
    if category_diff_match:
        cat1 = category_diff_match.group(1).strip()
        cat2 = category_diff_match.group(2).strip()
        
        filtered1 = df[df['WebsiteCarCategory'].str.contains(cat1, case=False)]
        filtered2 = df[df['WebsiteCarCategory'].str.contains(cat2, case=False)]
        
        if not filtered1.empty and not filtered2.empty:
            avg1 = filtered1['InclusiveRate'].mean()
            avg2 = filtered2['InclusiveRate'].mean()
            
            diff = abs(avg1 - avg2)
            diff_percent = diff / min(avg1, avg2) * 100
            
            return f"The average price difference between {cat1} and {cat2} cars is ${diff:.2f}. " \
                   f"{cat2 if avg2 > avg1 else cat1} cars are {diff_percent:.1f}% more expensive than " \
                   f"{cat1 if avg2 > avg1 else cat2} cars (${max(avg1, avg2):.2f} vs ${min(avg1, avg2):.2f})."
        else:
            return f"Sorry, I couldn't find comparison data for both {cat1} and {cat2} car categories."
    
    # Day of week with lowest rates
    if "day of the week has the lowest rates" in question:
        if 'avg_by_day_of_week' in aggs:
            day_rates = aggs['avg_by_day_of_week']
            lowest_day = min(day_rates.items(), key=lambda x: x[1])
            
            return f"Based on the data, {lowest_day[0]} has the lowest average rates at ${lowest_day[1]:.2f}."
        else:
            return "Sorry, I couldn't analyze rates by day of the week from the available data."
    
    # Most affordable car category
    if "most affordable car category" in question or "cheapest car category" in question:
        if 'avg_by_category' in aggs:
            category_rates = aggs['avg_by_category']
            affordable_categories = sorted(category_rates.items(), key=lambda x: x[1])
            
            # Take top 5 most affordable
            top_affordable = affordable_categories[:5]
            
            response = "The most affordable car categories based on average rates are:\n\n"
            for i, (category, rate) in enumerate(top_affordable):
                response += f"{i+1}. {category}: ${rate:.2f} per day\n"
            
            return response
        else:
            return "Sorry, I couldn't analyze prices by car category from the available data."
    
    # Luxury cars under specific price
    luxury_price_match = re.search(r"(find|show|get) (luxury|premium) cars under \$(\d+)", question)
    if luxury_price_match:
        car_type = luxury_price_match.group(2).strip()
        price_limit = float(luxury_price_match.group(3))
        
        # Find luxury categories
        luxury_cats = [cat for cat in df['WebsiteCarCategory'].unique() 
                      if car_type.lower() in cat.lower()]
        
        if luxury_cats:
            luxury_cars = df[df['WebsiteCarCategory'].isin(luxury_cats)]
            affordable_luxury = luxury_cars[luxury_cars['InclusiveRate'] < price_limit]
            
            if not affordable_luxury.empty:
                # Group by model and supplier, take minimum price
                grouped = affordable_luxury.groupby(['VehicleName', 'WebsiteSupplier'])['InclusiveRate'].min().reset_index()
                sorted_cars = grouped.sort_values('InclusiveRate')
                
                response = f"Here are {car_type} cars under ${price_limit:.2f} per day:\n\n"
                for i, (_, row) in enumerate(sorted_cars.iterrows()):
                    if i >= 5:  # Limit to top 5
                        break
                    response += f"{i+1}. {row['VehicleName']} from {row['WebsiteSupplier']}: ${row['InclusiveRate']:.2f} per day\n"
                
                return response
            else:
                return f"Sorry, I couldn't find any {car_type} cars under ${price_limit:.2f} per day."
        else:
            return f"Sorry, I couldn't find any car categories matching '{car_type}' in the data."
    
    # Average price for a category
    avg_price_match = re.search(r"average price for a (.*?) car", question)
    if avg_price_match:
        category = avg_price_match.group(1).strip()
        
        matching_categories = [cat for cat in df['WebsiteCarCategory'].unique() 
                              if category.lower() in cat.lower()]
        
        if matching_categories:
            response = f"Here are the average prices for {category} car categories:\n\n"
            for cat in matching_categories:
                cat_data = df[df['WebsiteCarCategory'] == cat]
                avg_price = cat_data['InclusiveRate'].mean()
                response += f"- {cat}: ${avg_price:.2f} per day\n"
            
            return response
        else:
            return f"Sorry, I couldn't find any car categories matching '{category}' in the data."
    
    # Compare suppliers overall
    if "which supplier has the lowest prices" in question:
        if 'avg_by_supplier' in aggs:
            supplier_rates = aggs['avg_by_supplier']
            sorted_suppliers = sorted(supplier_rates.items(), key=lambda x: x[1])
            
            # Get top 5 cheapest suppliers
            cheapest_suppliers = sorted_suppliers[:5]
            
            response = "The suppliers with the lowest average prices are:\n\n"
            for i, (supplier, rate) in enumerate(cheapest_suppliers):
                response += f"{i+1}. {supplier}: ${rate:.2f} per day\n"
            
            return response
        else:
            return "Sorry, I couldn't analyze prices by supplier from the available data."
    
    # Compare two specific suppliers
    compare_suppliers_match = re.search(r"compare (.*?) and (.*?) prices", question)
    if compare_suppliers_match:
        supplier1 = compare_suppliers_match.group(1).strip()
        supplier2 = compare_suppliers_match.group(2).strip()
        
        supplier1_data = df[df['WebsiteSupplier'] == supplier1]
        supplier2_data = df[df['WebsiteSupplier'] == supplier2]
        
        if not supplier1_data.empty and not supplier2_data.empty:
            avg1 = supplier1_data['InclusiveRate'].mean()
            avg2 = supplier2_data['InclusiveRate'].mean()
            
            # Compare by car category
            common_categories = set(supplier1_data['WebsiteCarCategory'].unique()) & set(supplier2_data['WebsiteCarCategory'].unique())
            
            response = f"Comparing {supplier1} vs {supplier2}:\n\n"
            response += f"Overall average: {supplier1}: ${avg1:.2f} | {supplier2}: ${avg2:.2f}\n\n"
            
            if common_categories:
                response += "Comparison by car category:\n"
                for category in common_categories:
                    cat1_price = supplier1_data[supplier1_data['WebsiteCarCategory'] == category]['InclusiveRate'].mean()
                    cat2_price = supplier2_data[supplier2_data['WebsiteCarCategory'] == category]['InclusiveRate'].mean()
                    cheaper = supplier1 if cat1_price < cat2_price else supplier2
                    diff = abs(cat1_price - cat2_price)
                    response += f"- {category}: {cheaper} is ${diff:.2f} cheaper\n"
            
            return response
        else:
            return f"Sorry, I couldn't find data for both {supplier1} and {supplier2}."
    
    # Best value car category
    if "which car category has the best value" in question:
        # This is subjective, but we'll use a simple price-to-size ratio approach
        # We'll categorize cars by size (small, medium, large) and calculate value
        
        size_categories = {
            'small': ['Economy', 'Compact', 'Mini'],
            'medium': ['Midsize', 'Standard', 'Intermediate'],
            'large': ['Fullsize', 'Premium', 'Luxury', 'SUV']
        }
        
        # Calculate average price for each size category
        size_prices = {}
        for size, categories in size_categories.items():
            matching_cars = df[df['WebsiteCarCategory'].apply(
                lambda x: any(cat.lower() in x.lower() for cat in categories))]
            if not matching_cars.empty:
                size_prices[size] = matching_cars['InclusiveRate'].mean()
        
        if size_prices:
            # Calculate a simple value score (lower is better)
            size_values = {
                'small': size_prices.get('small', float('inf')),
                'medium': size_prices.get('medium', float('inf')) / 1.2,  # Adjust for more space
                'large': size_prices.get('large', float('inf')) / 1.5   # Adjust for much more space
            }
            
            best_value_size = min(size_values.items(), key=lambda x: x[1])[0]
            
            # Find the specific category with the best value
            best_categories = []
            for category in df['WebsiteCarCategory'].unique():
                size = next((s for s, cats in size_categories.items() 
                           if any(cat.lower() in category.lower() for cat in cats)), None)
                if size == best_value_size:
                    cat_data = df[df['WebsiteCarCategory'] == category]
                    avg_price = cat_data['InclusiveRate'].mean()
                    best_categories.append((category, avg_price))
            
            if best_categories:
                sorted_categories = sorted(best_categories, key=lambda x: x[1])
                
                response = f"Based on price-to-size value, {best_value_size.title()} cars offer the best value.\n\n"
                response += "The best value specific categories are:\n"
                for i, (category, price) in enumerate(sorted_categories[:3]):
                    response += f"{i+1}. {category}: ${price:.2f} per day\n"
                
                return response
        
        return "Sorry, I couldn't determine which car category has the best value."
    
    # How much cheaper is Supplier X than Supplier Y
    supplier_cheaper_match = re.search(r"how much cheaper is (.*?) than (.*)", question)
    if supplier_cheaper_match:
        supplier1 = supplier_cheaper_match.group(1).strip()
        supplier2 = supplier_cheaper_match.group(2).strip()
        
        supplier1_data = df[df['WebsiteSupplier'] == supplier1]
        supplier2_data = df[df['WebsiteSupplier'] == supplier2]
        
        if not supplier1_data.empty and not supplier2_data.empty:
            avg1 = supplier1_data['InclusiveRate'].mean()
            avg2 = supplier2_data['InclusiveRate'].mean()
            
            diff = abs(avg1 - avg2)
            diff_percent = (diff / max(avg1, avg2)) * 100
            
            if avg1 < avg2:
                return f"{supplier1} is ${diff:.2f} cheaper than {supplier2} on average, " \
                       f"which is {diff_percent:.1f}% less (${avg1:.2f} vs ${avg2:.2f})."
            else:
                return f"{supplier1} is actually ${diff:.2f} more expensive than {supplier2} on average, " \
                       f"which is {diff_percent:.1f}% more (${avg1:.2f} vs ${avg2:.2f})."
        else:
            return f"Sorry, I couldn't find data for both {supplier1} and {supplier2}."
    
    # Price differences between websites
    if "price differences between websites" in question:
        websites = df['Website'].unique()
        
        if len(websites) > 1:
            response = "Here are the price differences between websites:\n\n"
            
            website_avgs = {}
            for website in websites:
                website_data = df[df['Website'] == website]
                avg_price = website_data['InclusiveRate'].mean()
                website_avgs[website] = avg_price
            
            # Compare each pair
            for i, website1 in enumerate(websites):
                for website2 in websites[i+1:]:
                    diff = abs(website_avgs[website1] - website_avgs[website2])
                    cheaper = website1 if website_avgs[website1] < website_avgs[website2] else website2
                    diff_percent = (diff / max(website_avgs[website1], website_avgs[website2])) * 100
                    
                    response += f"{website1} vs {website2}: {cheaper} is ${diff:.2f} cheaper ({diff_percent:.1f}%)\n"
            
            return response
        else:
            return "Sorry, I could only find one website in the data, so there's no comparison to make."
    
    # Which supplier offers the best luxury cars
    luxury_supplier_match = re.search(r"which supplier (has|offers) the best (luxury|premium) cars", question)
    if luxury_supplier_match:
        car_type = luxury_supplier_match.group(2).strip()
        
        # Find luxury categories
        luxury_cats = [cat for cat in df['WebsiteCarCategory'].unique() 
                      if car_type.lower() in cat.lower()]
        
        if luxury_cats:
            luxury_data = df[df['WebsiteCarCategory'].isin(luxury_cats)]
            
            if not luxury_data.empty:
                supplier_stats = {}
                for supplier in luxury_data['WebsiteSupplier'].unique():
                    supplier_data = luxury_data[luxury_data['WebsiteSupplier'] == supplier]
                    supplier_stats[supplier] = {
                        'avg_price': supplier_data['InclusiveRate'].mean(),
                        'variety': supplier_data['VehicleName'].nunique()
                    }
                
                # Sort by price (lower is better)
                by_price = sorted(supplier_stats.items(), key=lambda x: x[1]['avg_price'])
                
                # Sort by variety (higher is better)
                by_variety = sorted(supplier_stats.items(), key=lambda x: -x[1]['variety'])
                
                response = f"Best suppliers for {car_type} cars:\n\n"
                response += "By price (lowest first):\n"
                for i, (supplier, stats) in enumerate(by_price[:3]):
                    response += f"{i+1}. {supplier}: ${stats['avg_price']:.2f} avg, {stats['variety']} different models\n"
                
                response += "\nBy variety (most options first):\n"
                for i, (supplier, stats) in enumerate(by_variety[:3]):
                    response += f"{i+1}. {supplier}: {stats['variety']} different models, ${stats['avg_price']:.2f} avg\n"
                
                return response
            else:
                return f"Sorry, I couldn't find any {car_type} cars in the data."
        else:
            return f"Sorry, I couldn't find any car categories matching '{car_type}' in the data."
    
    # Are weekends more expensive than weekdays?
    if "weekends more expensive than weekdays" in question:
        if 'weekend_weekday' in aggs:
            weekend_avg = aggs['weekend_weekday']['weekend']
            weekday_avg = aggs['weekend_weekday']['weekday']
            
            diff = abs(weekend_avg - weekday_avg)
            diff_percent = (diff / min(weekend_avg, weekday_avg)) * 100
            
            if weekend_avg > weekday_avg:
                return f"Yes, weekends are ${diff:.2f} more expensive than weekdays on average, " \
                       f"which is {diff_percent:.1f}% higher (${weekend_avg:.2f} vs ${weekday_avg:.2f})."
            else:
                return f"No, weekends are actually ${diff:.2f} cheaper than weekdays on average, " \
                       f"which is {diff_percent:.1f}% lower (${weekend_avg:.2f} vs ${weekday_avg:.2f})."
        else:
            return "Sorry, I couldn't analyze weekend vs weekday prices from the available data."
    
    # How do prices change throughout April?
    price_change_month_match = re.search(r"how do prices change throughout (.*?)\?", question)
    if price_change_month_match:
        month = price_change_month_match.group(1).strip()
        
        try:
            month_num = pd.to_datetime(month, format='%B').month
            monthly_data = df[df['PickUpDate'].dt.month == month_num]
            
            if not monthly_data.empty:
                # Group by day and calculate average
                daily_avg = monthly_data.groupby(monthly_data['PickUpDate'].dt.day)['InclusiveRate'].mean()
                
                # Find the trend
                days = sorted(daily_avg.index)
                start_price = daily_avg[days[0]]
                end_price = daily_avg[days[-1]]
                
                diff = end_price - start_price
                diff_percent = (diff / start_price) * 100
                
                min_day = daily_avg.idxmin()
                max_day = daily_avg.idxmax()
                
                response = f"Price trends throughout {month}:\n\n"
                
                if diff > 0:
                    response += f"Overall: Prices increase by ${diff:.2f} ({diff_percent:.1f}%) from beginning to end of month\n"
                else:
                    response += f"Overall: Prices decrease by ${-diff:.2f} ({-diff_percent:.1f}%) from beginning to end of month\n"
                
                response += f"Lowest price: ${daily_avg.min():.2f} on the {min_day}th\n"
                response += f"Highest price: ${daily_avg.max():.2f} on the {max_day}th\n"
                
                # Find price pattern by week
                response += "\nWeekly pattern: "
                
                week1_avg = monthly_data[monthly_data['PickUpDate'].dt.day <= 7]['InclusiveRate'].mean()
                week2_avg = monthly_data[(monthly_data['PickUpDate'].dt.day > 7) & 
                                       (monthly_data['PickUpDate'].dt.day <= 14)]['InclusiveRate'].mean()
                week3_avg = monthly_data[(monthly_data['PickUpDate'].dt.day > 14) & 
                                       (monthly_data['PickUpDate'].dt.day <= 21)]['InclusiveRate'].mean()
                week4_avg = monthly_data[monthly_data['PickUpDate'].dt.day > 21]['InclusiveRate'].mean()
                
                week_avgs = [
                    ("Week 1", week1_avg),
                    ("Week 2", week2_avg),
                    ("Week 3", week3_avg),
                    ("Week 4", week4_avg)
                ]
                
                sorted_weeks = sorted(week_avgs, key=lambda x: x[1])
                response += f"{sorted_weeks[0][0]} is cheapest (${sorted_weeks[0][1]:.2f}), " \
                           f"{sorted_weeks[-1][0]} is most expensive (${sorted_weeks[-1][1]:.2f})"
                
                return response
            else:
                return f"Sorry, I don't have data for {month} in the dataset."
        except:
            return f"I couldn't analyze price changes for {month}. Please specify a valid month name."
    
    # Which date has the lowest average price?
    if "which date has the lowest average price" in question:
        if 'avg_by_date' in aggs:
            date_prices = aggs['avg_by_date']
            lowest_date = min(date_prices.items(), key=lambda x: x[1])
            
            # Get day of week for context
            day_of_week = pd.to_datetime(lowest_date[0]).strftime('%A')
            
            return f"The date with the lowest average price is {lowest_date[0]} ({day_of_week}) " \
                   f"at ${lowest_date[1]:.2f} per day."
        else:
            return "Sorry, I couldn't analyze prices by date from the available data."
    
    # Compare first week vs last week of April
    compare_weeks_match = re.search(r"compare first week vs last week of (.*?) prices", question)
    if compare_weeks_match:
        month = compare_weeks_match.group(1).strip()
        
        try:
            month_num = pd.to_datetime(month, format='%B').month
            monthly_data = df[df['PickUpDate'].dt.month == month_num]
            
            if not monthly_data.empty:
                # Define weeks
                first_week = monthly_data[monthly_data['PickUpDate'].dt.day <= 7]
                last_week = monthly_data[monthly_data['PickUpDate'].dt.day >= 22]  # Approximate last week
                
                if not first_week.empty and not last_week.empty:
                    first_week_avg = first_week['InclusiveRate'].mean()
                    last_week_avg = last_week['InclusiveRate'].mean()
                    
                    diff = abs(first_week_avg - last_week_avg)
                    diff_percent = (diff / min(first_week_avg, last_week_avg)) * 100
                    
                    if first_week_avg < last_week_avg:
                        return f"First week of {month} (${first_week_avg:.2f}) is ${diff:.2f} cheaper than " \
                               f"the last week (${last_week_avg:.2f}), a {diff_percent:.1f}% difference."
                    else:
                        return f"Last week of {month} (${last_week_avg:.2f}) is ${diff:.2f} cheaper than " \
                               f"the first week (${first_week_avg:.2f}), a {diff_percent:.1f}% difference."
                else:
                    return f"Sorry, I don't have enough data for both the first and last weeks of {month}."
            else:
                return f"Sorry, I don't have data for {month} in the dataset."
        except:
            return f"I couldn't compare weeks for {month}. Please specify a valid month name."
    
    # If no specific analytical question is matched, return None to let Ollama handle it
    return None

def handle_visualization_request(question, df):
    """Handle requests for visualizations and charts."""
    
    # FIXED: Added more matching patterns and rearranged the order
    
    # Price by car category
    if any(term in question for term in [
        'category', 'car category', 'car categories', 'visualization of prices by car category',
        'price by category', 'category price', 'category prices', 'prices by category',
        'show category'
    ]):
        return {
            'response': "Here's a graph comparing prices across different car categories.",
            'visualization': {
                'type': 'price_by_category'
            }
        }
    
    # Price by supplier
    if any(term in question for term in [
        'supplier', 'supplier price', 'price by supplier', 'supplier comparison', 
        'compare suppliers', 'suppliers price', 'visualize the best deals across suppliers',
        'visualize supplier'
    ]):
        return {
            'response': "I'll show you a graph of average prices by supplier.",
            'visualization': {
                'type': 'price_by_supplier'
            }
        }
    
    # Price trends over time
    if any(term in question for term in [
        'trend', 'time', 'date', 'price trend', 'price over time', 'price by date', 
        'date comparison', 'dates', 'over time', 'plot price trends', 'plot trends'
    ]):
        return {
            'response': "Here's a graph showing how prices trend over different pickup dates.",
            'visualization': {
                'type': 'price_by_date'
            }
        }
    
    # Compare specific suppliers
    supplier_compare_match = re.search(r"compare (.*?) and (.*?) (?:for|on) (.*)", question)
    if supplier_compare_match:
        supplier1 = supplier_compare_match.group(1).strip().title()
        supplier2 = supplier_compare_match.group(2).strip().title()
        category = supplier_compare_match.group(3).strip()
        
        return {
            'response': f"Here's a price comparison between {supplier1} and {supplier2} for {category}.",
            'visualization': {
                'type': 'supplier_comparison',
                'suppliers': [supplier1, supplier2],
                'category': category
            }
        }
    
    # Weekend vs weekday comparison
    if any(term in question for term in ['weekend', 'weekday', 'week day', 'weekend vs weekday', 'weekday vs weekend']):
        return {
            'response': "Here's a comparison of weekend versus weekday pricing.",
            'visualization': {
                'type': 'weekend_weekday_comparison'
            }
        }
    
    # Best deals
    if any(term in question for term in ['best deal', 'best deals', 'top deal', 'top deals', 'good deal']):
        return {
            'response': "Here are the best deals I found across all suppliers and categories.",
            'visualization': {
                'type': 'best_deals'
            }
        }
    
    # Category price differences
    category_diff_match = re.search(r"(plot|show|visualize|graph).*?difference.* (.*?) and (.*?) cars", question)
    if category_diff_match:
        cat1 = category_diff_match.group(2).strip().title()
        cat2 = category_diff_match.group(3).strip().title()
        
        return {
            'response': f"Here's a visual comparison of prices between {cat1} and {cat2} cars.",
            'visualization': {
                'type': 'category_price_difference',
                'categories': [cat1, cat2]
            }
        }
    
    # Weekly comparison
    if any(term in question for term in ['compare week', 'compare weeks', 'weekly', 'first week', 'last week']):
        return {
            'response': "Here's a comparison of prices between the first and last weeks of the data period.",
            'visualization': {
                'type': 'weekly_comparison'
            }
        }
    
    # Fallback for general visualization requests - Most broad case last
    if any(term in question for term in ['graph', 'chart', 'plot', 'visualize', 'visualization', 'visual']):
        return {
            'response': "Here's a graph comparing prices across different car categories.",
            'visualization': {
                'type': 'price_by_category'  # Default to category visualization
            }
        }
    
    # If no specific visualization is matched
    return "I'm not sure what kind of graph you want. Try asking for price by supplier, price trends over time, or price by car category."