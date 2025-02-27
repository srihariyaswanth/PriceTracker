# from flask import Flask, request, render_template
# import requests as r
# import bs4

# app = Flask(__name__)  # Corrected initialization
# @app.route('/')
# def home():
#     return render_template('index.html')  # Your HTML file name

# @app.route('/add-to-tracking', methods=['POST'])
# def scrape():
#     # Get data from the form
#     product_url = request.form['product_url']
#     target_price = float(request.form['target_price'])
#     email = request.form['email']

#     # Scraping logic
#     headers = {
#         'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#     }
#     product_response = r.get(product_url, headers=headers)
#     soup = bs4.BeautifulSoup(product_response.text, 'lxml')
    
#     try:
#         # Extract price
#         price_lines = soup.find_all(class_='a-price-whole')
#         if not price_lines:
#             return "Price not found on the product page."
        
#         final_price = price_lines[0].get_text(strip=True).replace(',', '')
#         final_price = float(final_price)

#         # Check if the price is within the target range
#         if final_price <= target_price:
#             return f"Good news! The product is available for ₹{final_price}, which is below your target price of ₹{target_price}."
#         else:
#             return f"The current price is ₹{final_price}, which is higher than your target price of ₹{target_price}."

#     except Exception as e:
#         return f"An error occurred while scraping: {e}"

# if __name__ == "__main__":  # Corrected name
#     app.run(debug=True)




from flask import Flask, request, render_template
import requests as r
import bs4
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Tracking list for storing products
tracking_list = []

# Scheduler for background scraping
try:
    scheduler = BackgroundScheduler()
    scheduler.start()
    print("Scheduler initialized successfully.")
except Exception as e:
    print(f"Error initializing scheduler: {e}")

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Route to add product to tracking and display current price
@app.route('/add-to-tracking', methods=['POST'])
def add_to_tracking():
    product_url = request.form['product_url']
    target_price = float(request.form['target_price'])
    email = request.form['email']

    # Scrape the price immediately
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    product_response = r.get(product_url, headers=headers)
    soup = bs4.BeautifulSoup(product_response.text, 'lxml')

    try:
        price_lines = soup.find_all(class_='a-price-whole')
        if not price_lines:
            return render_template('error.html', message="Price not found on the product page.")

        final_price = price_lines[0].get_text(strip=True).replace(',', '')
        final_price = float(final_price)

        # Add the product to the tracking list
        tracking_list.append({
            'product_url': product_url,
            'target_price': target_price,
            'email': email,
        })
        print(f"Tracking list updated: {tracking_list}")

        return render_template(
            'price_display.html',
            product_url=product_url,
            final_price=final_price,
            target_price=target_price
        )

    except Exception as e:
        return render_template('error.html', message=f"An error occurred: {e}")

# Background job to check prices periodically
def periodic_scrape():
    print("Periodic scrape started...")
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    for product in tracking_list:
        print(f"Scraping for product: {product['product_url']}")
        try:
            product_response = r.get(product['product_url'], headers=headers)
            soup = bs4.BeautifulSoup(product_response.text, 'lxml')
            price_lines = soup.find_all(class_='a-price-whole')

            if not price_lines:
                print(f"Price not found for {product['product_url']}")
                continue

            final_price = price_lines[0].get_text(strip=True).replace(',', '')
            final_price = float(final_price)

            if final_price <= product['target_price']:
                print(
                    f"Good news! The product at {product['product_url']} is available for ₹{final_price}, "
                    f"below the target price of ₹{product['target_price']}."
                )
            else:
                print(
                    f"The product at {product['product_url']} is still priced at ₹{final_price}, "
                    f"above the target price of ₹{product['target_price']}."
                )
        except Exception as e:
            print(f"Error while scraping {product['product_url']}: {e}")

# Schedule the periodic scrape job
scheduler.add_job(func=periodic_scrape, trigger="interval", minutes=5)

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)







