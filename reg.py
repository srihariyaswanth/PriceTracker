from flask import Flask, render_template, request, redirect, url_for,jsonify
import pymysql
import mysql.connector
from mysql.connector import Error
import requests as r
import bs4
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
@app.route('/')
def home():
    return render_template('login.html')

# Email credentials
sender_email = "srihariyashwanth07@gmail.com"
sender_password = "weyx vdsi gqpy mbnz"

# Tracking list
tracking_list = []

# Background scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Database connection details
def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='12345',
            database='newr'
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()
            
            if role == "admin":
                query = "SELECT * FROM admin WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                admin = cursor.fetchone()

                if admin:
                    return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
                else:
                    return "Invalid admin credentials, please try again."
            
            else:
                query = "SELECT * FROM user WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                user = cursor.fetchone()

                if user:
                    return redirect(url_for('index'))  # Redirect to user page
                else:
                    return "Invalid credentials, please try again."

            cursor.close()
            connection.close()
        return "Failed to connect to the database."

    return render_template('login.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        username = request.form['username']
        email = request.form['email']
        pwd1 = request.form['pwd1']
        pwd2 = request.form['pwd2']

        if pwd1 != pwd2:
            return "Passwords do not match, please try again."

        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()
            try:
                query = "INSERT INTO user (fname, lname, username, email, password) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (fname, lname, username, email, pwd1))
                connection.commit()
                return redirect(url_for('login'))  # Redirect to login page after successful registration
            except Error as e:
                return f"Error: {e}"
            finally:
                cursor.close()
                connection.close()
        else:
            return "Failed to connect to the database."

    return render_template('Registration.html')

# Admin Dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()
        query = "SELECT * FROM user"
        cursor.execute(query)
        user = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('admin_dashboard.html', user=user)

# Index route (after login)
@app.route('/index')
def index():
    return render_template('index.html')

# Add to tracking route (scraping logic)
@app.route('/add-to-tracking', methods=['POST'])
def add_to_tracking():
    product_url = request.form['product_url']
    target_price = float(request.form['target_price'])
    email = request.form['email']

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    product_response = r.get(product_url, headers=headers)
    soup = bs4.BeautifulSoup(product_response.text, 'lxml')

    try:
        price_lines = soup.find_all(class_='a-price-whole')
        if not price_lines:
            return render_template('error.html', message="Sorry for the inconvenience This is the problem of Anti-Scrapping Please wait for a while or  refresh the page.")
        
        current_price = price_lines[0].get_text(strip=True).replace(',', '')
        current_price = float(current_price)

        tracking_list.append({
            'product_url': product_url,
            'target_price': target_price,
            'email': email,
        })
        connection = connect_to_db()
        if connection:
            cursor = connection.cursor()
            query = "INSERT INTO tracking (product_url, target_price, email) VALUES (%s, %s, %s)"
            cursor.execute(query, (product_url, target_price, email))
            connection.commit()
            cursor.close()
            connection.close()

        if target_price >= current_price:
            send_email(
                to_email=email,
                subject="Price Match or Drop Alert!",
                body=f"The product at {product_url} is now available for ₹{current_price}, which is within or below your target price of ₹{target_price}!"
            )

        return render_template(
            'price_display.html',
            product_url=product_url,
            final_price=current_price,
            target_price=target_price
        )
    except Exception as e:
        return render_template('error.html', message=f"An error occurred: {e}")

# Function to send email alert
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

# Periodic scraping job
def periodic_scrape():
    print("Running periodic scrape...")

    for product in tracking_list:
        try:
            product_response = r.get(product['product_url'], headers={'user-agent': 'Mozilla/5.0'})
            soup = bs4.BeautifulSoup(product_response.text, 'lxml')
            price_lines = soup.find_all(class_='a-price-whole')

            if price_lines:
                current_price = float(price_lines[0].get_text(strip=True).replace(',', ''))
                if current_price <= product['target_price']:
                    send_email(
                        to_email=product['email'],
                        subject="Price Drop Alert!",
                        body=f"The product at {product['product_url']} is now available for ₹{current_price}, below your target price of ₹{product['target_price']}!"
                    )
        except Exception as e:
            print(f"Error during scraping: {e}")

# Scheduler to periodically check for price drops
scheduler.add_job(func=periodic_scrape, trigger="interval", minutes=5)



















@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()
        query = "SELECT  created_at,target_price FROM tracking"
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        connection.close()
        graph_data = [
            {"created_at": row[0].strftime("%Y-%m-%d %H:%M:%S"), "target_price": float(row[1])} 
            for row in data
        ]

        return render_template('analysis.html', graph_data=graph_data)
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)



















