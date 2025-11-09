from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import random, string
import smtplib
from email.message import EmailMessage
import pywhatkit as kit
import pyautogui
import time
from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()

import os
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=os.getenv("MYSQLPORT")
    )


app = Flask(__name__)
app.secret_key = 'your_secret_key'

SENDER_EMAIL = os.getenv("email")
SENDER_PASSWORD = os.getenv("password")

# ---------------------- DATABASE HELPERS ----------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("database_pass", "4u84sm-MYSQL"),
        database="Airline_Schema"
    )

def insert_user(email, phone, username, password):
    db = get_db_connection()
    cursor = db.cursor()
    query = "INSERT INTO Signup (Email, Phone, Username, Password) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (email, phone, username, password))
    db.commit()
    cursor.close()
    db.close()

def get_user_by_username(username):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT user_id, username, email, phone, air_miles, Password FROM Signup WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    return user

def get_admin_by_username(username):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT admin_id, username, email, full_name, password FROM Admins WHERE username=%s", (username,))
    admin = cursor.fetchone()
    cursor.close()
    db.close()
    return admin

def generate_seats_for_flight(flight_id, economy_seats=60, business_seats=12, first_seats=6):
    """Generate seat layout for a flight"""
    db = get_db_connection()
    cursor = db.cursor()

    seats = []

    # Economy: Rows 1-10, Seats A-F (6 per row)
    for row in range(1, 11):
        for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
            if len([s for s in seats if s[2] == 'Economy']) < economy_seats:
                seats.append((flight_id, f"{row}{seat_letter}", 'Economy'))

    # Business: Rows 11-13, Seats A-D (4 per row)
    for row in range(11, 14):
        for seat_letter in ['A', 'B', 'C', 'D']:
            if len([s for s in seats if s[2] == 'Business']) < business_seats:
                seats.append((flight_id, f"{row}{seat_letter}", 'Business'))

    # First: Rows 14-15, Seats A-C (3 per row)
    for row in range(14, 16):
        for seat_letter in ['A', 'B', 'C']:
            if len([s for s in seats if s[2] == 'First']) < first_seats:
                seats.append((flight_id, f"{row}{seat_letter}", 'First'))

    # Insert all seats
    cursor.executemany(
        "INSERT INTO Seats (flight_id, seat_number, class) VALUES (%s, %s, %s)",
        seats
    )

    db.commit()
    cursor.close()
    db.close()

    print(f"✅ Generated {len(seats)} seats for flight {flight_id}")
# ---------------------- EMAIL / WHATSAPP ----------------------
def send_email(receiver_email, subject, body):
    if not SENDER_EMAIL or "your_email" in SENDER_EMAIL:
        print("⚠️ Email not configured. Skipping email.")
        return
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {receiver_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def send_whatsapp_msg(phone):
    try:
        kit.sendwhatmsg_instantly(f"+91{phone}", "🎉 Welcome to Airline Management System!")
        time.sleep(5)
        pyautogui.press("enter")
        print(f"✅ WhatsApp message sent to {phone}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp message: {e}")

# ---------------------- ROUTES ----------------------
@app.route('/')
def sign_up_form():
    return render_template('Signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    phone = request.form['phone']
    username = request.form['username']
    password = generate_password_hash(request.form['password'])

    try:
        insert_user(email, phone, username, password)
        session['username'] = username

        # Send welcome email
        send_email(email, "Welcome to Airline Management System!",
                   f"Hi {username},\n\nThank you for signing up!\n\n-Airline Team")
        # send_whatsapp_msg(phone)  # Optional

        return redirect(url_for('dashboard'))
    except mysql.connector.IntegrityError as e:
        flash("⚠️ Email or username already exists.")
        return redirect(url_for('sign_up_form'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user['Password'], password):
            session['username'] = username
            send_email(user['email'], "Login Notification",
                       f"Hi {username},\n\nNew login detected.\n\n-Airline Team")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/Dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = get_user_by_username(session['username'])
    if not user:
        flash("Error fetching user data. Please log in again.")
        return redirect(url_for('logout'))

    return render_template('Dashboard.html', user=user)

# ---------------------- API ENDPOINTS ----------------------
@app.route("/api/bookings")
def get_bookings():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    user = get_user_by_username(session['username'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.booking_id, b.pnr, b.status, b.class, b.price, b.seat_no,
               f.flight_no, f.departure_time, f.arrival_time,
               a.name AS airline,
               ap1.city AS source, ap2.city AS destination
        FROM Bookings b
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        JOIN Airlines a ON f.airline_id = a.airline_id
        JOIN Airports ap1 ON f.source_airport_id = ap1.airport_id
        JOIN Airports ap2 ON f.dest_airport_id = ap2.airport_id
        WHERE p.user_id=%s
        ORDER BY f.departure_time DESC
    """, (user['user_id'],))
    all_bookings = cursor.fetchall()
    cursor.close()
    db.close()

    upcoming, past = [], []
    now = datetime.now()
    for b in all_bookings:
        dep_time = b['departure_time']
        if not isinstance(dep_time, datetime):
            dep_time = datetime.fromisoformat(str(dep_time))
        if dep_time > now and b['status'] == 'Confirmed':
            upcoming.append(b)
        else:
            past.append(b)

    return jsonify({"upcoming": upcoming, "past": past})

# ---------------------- FLIGHT SEARCH ----------------------
@app.route('/api/flights')
def get_flights():
    source_code = request.args.get('source')  # e.g., 'DEL'
    dest_code = request.args.get('dest')      # e.g., 'BOM'

    if not source_code or not dest_code:
        return jsonify([])

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get airport IDs from codes
        cursor.execute("SELECT airport_id FROM Airports WHERE code=%s", (source_code,))
        source = cursor.fetchone()
        cursor.execute("SELECT airport_id FROM Airports WHERE code=%s", (dest_code,))
        dest = cursor.fetchone()

        if not source or not dest:
            return jsonify([])  # No matching airport

        source_id = source['airport_id']
        dest_id = dest['airport_id']

        # Fetch flights
        query = """
            SELECT f.flight_id, f.flight_no, f.departure_time, f.arrival_time,
                   f.price_economy, f.price_business, f.price_first,
                   f.available_seats_economy, f.available_seats_business, f.available_seats_first,
                   a.name AS airline, s.code AS source, d.code AS destination
            FROM Flights f
            JOIN Airlines a ON f.airline_id = a.airline_id
            JOIN Airports s ON f.source_airport_id = s.airport_id
            JOIN Airports d ON f.dest_airport_id = d.airport_id
            WHERE f.source_airport_id=%s AND f.dest_airport_id=%s
        """
        cursor.execute(query, (source_id, dest_id))
        flights = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(flights)

    except Error as e:
        print("Error fetching flights:", e)
        return jsonify([])


# ---------------------- BOOKING ----------------------

@app.route("/select-seat/<int:flight_id>")
def select_seat(flight_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    selected_class = request.args.get("class", "economy")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT flight_no FROM Flights WHERE flight_id = %s", (flight_id,))
    flight = cursor.fetchone()

    cursor.close()
    db.close()

    if not flight:
        return "Flight not found!", 404

    return render_template("seat_selection.html",
                           flight_id=flight_id,
                           flight_no=flight['flight_no'],
                           selected_class=selected_class.capitalize())


@app.route("/book/<int:flight_id>", methods=["GET", "POST"])
def book_ticket(flight_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    user = get_user_by_username(session['username'])
    if not user:
        flash("User not found. Please login again.")
        return redirect(url_for('login'))

    selected_class = request.args.get("class", "economy")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    price_column = f"price_{selected_class}"
    seat_column = f"available_seats_{selected_class}"

    cursor.execute(f"""
        SELECT flight_id, flight_no, departure_time, arrival_time, 
               {price_column} AS price, {seat_column} AS available_seats
        FROM Flights WHERE flight_id = %s
    """, (flight_id,))
    flight = cursor.fetchone()

    if not flight:
        cursor.close()
        db.close()
        return "Flight not found!", 404

    if flight['available_seats'] <= 0:
        cursor.close()
        db.close()
        flash("Selected class is sold out. Please choose another class.")
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        print("=== BOOKING STARTED ===")
        full_name = request.form["full_name"]
        aadhaar_no = request.form["aadhaar_no"]
        print(f"Name: {full_name}, Aadhaar: {aadhaar_no}")

        # Insert passenger if not exists
        cursor.execute("SELECT passenger_id FROM Passengers WHERE aadhaar_no = %s", (aadhaar_no,))
        passenger = cursor.fetchone()
        if passenger:
            passenger_id = passenger['passenger_id']
            print(f"Existing passenger: {passenger_id}")
        else:
            cursor.execute("INSERT INTO Passengers (user_id, full_name, aadhaar_no) VALUES (%s, %s, %s)",
                           (user['user_id'], full_name, aadhaar_no))
            passenger_id = cursor.lastrowid
            print(f"New passenger created: {passenger_id}")

        # Generate PNR
        pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Get seat from URL parameter or generate random
        seat_no = request.args.get('seat')
        if not seat_no:
            seat_no = f"{random.randint(1, 30)}{random.choice('ABCDEF')}"

        print(f"PNR: {pnr}, Seat: {seat_no}, Price: {flight['price']}")

        try:
            # Insert Booking
            cursor.execute("""
                INSERT INTO Bookings (passenger_id, flight_id, pnr, seat_no, status, class, price) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (passenger_id, flight_id, pnr, seat_no, 'Confirmed', selected_class, flight['price']))
            booking_id = cursor.lastrowid
            print("Booking inserted successfully")

            # Mark seat as booked in Seats table
            cursor.execute("""
                UPDATE Seats 
                SET is_booked = TRUE, booking_id = %s 
                WHERE flight_id = %s AND seat_number = %s
            """, (booking_id, flight_id, seat_no))
            print(f"Seat {seat_no} marked as booked")

            # Reduce seat count
            cursor.execute(f"UPDATE Flights SET {seat_column} = {seat_column} - 1 WHERE flight_id = %s", (flight_id,))
            print("Seat count updated")

            # Add air miles (1 mile per ₹100 spent)
            miles_earned = int(flight['price'] / 100)
            cursor.execute("UPDATE Signup SET air_miles = air_miles + %s WHERE user_id = %s",
                           (miles_earned, user['user_id']))
            print(f"Air miles added: {miles_earned}")

            db.commit()
            print("=== BOOKING COMPLETED ===")

            flash(f"✅ Booking confirmed! Your PNR is {pnr}. Seat: {seat_no}. You earned {miles_earned} air miles!")

            cursor.close()
            db.close()
            return redirect(url_for("dashboard"))

        except Exception as e:
            print(f"ERROR: {e}")
            db.rollback()
            cursor.close()
            db.close()
            flash(f"❌ Booking failed: {str(e)}")
            return redirect(url_for("dashboard"))

    cursor.close()
    db.close()
    return render_template("book_ticket.html", flight=flight, selected_class=selected_class)

# ---------------------- CANCEL TICKET  ----------------------
@app.route("/cancel/<int:booking_id>", methods=["POST"])
def cancel_ticket(booking_id):
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    user = get_user_by_username(session['username'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Verify booking belongs to user
    cursor.execute("""
        SELECT b.*, f.departure_time, b.class, b.flight_id
        FROM Bookings b
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        WHERE b.booking_id = %s AND p.user_id = %s
    """, (booking_id, user['user_id']))

    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        db.close()
        return jsonify({"error": "Booking not found"}), 404

    if booking['status'] == 'Cancelled':
        cursor.close()
        db.close()
        return jsonify({"error": "Booking already cancelled"}), 400

    # Check if flight is in the future
    dep_time = booking['departure_time']
    if not isinstance(dep_time, datetime):
        dep_time = datetime.fromisoformat(str(dep_time))

    if dep_time <= datetime.now():
        cursor.close()
        db.close()
        return jsonify({"error": "Cannot cancel past flights"}), 400

    try:
        print(f"=== CANCELLING BOOKING {booking_id} ===")

        # Update booking status
        cursor.execute("UPDATE Bookings SET status = 'Cancelled' WHERE booking_id = %s", (booking_id,))
        print("Booking status updated to Cancelled")

        # Restore seat availability
        seat_column = f"available_seats_{booking['class'].lower()}"
        cursor.execute(f"UPDATE Flights SET {seat_column} = {seat_column} + 1 WHERE flight_id = %s",
                       (booking['flight_id'],))
        print(f"Seat restored in {booking['class']}")

        db.commit()
        cursor.close()
        db.close()

        print("=== CANCELLATION COMPLETED ===")
        return jsonify({"success": True, "message": "Booking cancelled successfully"})

    except Exception as e:
        print(f"ERROR during cancellation: {e}")
        db.rollback()
        cursor.close()
        db.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/airports')
def get_airports():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT code, city, name FROM Airports ORDER BY city")
        airports = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(airports)
    except Error as e:
        print(e)
        return jsonify([])



# ---------------------- PROFILE SETTINGS ----------------------
@app.route("/api/profile", methods=["GET", "PUT"])
def profile():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    user = get_user_by_username(session['username'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    if request.method == "GET":
        return jsonify({
            "username": user['username'],
            "email": user['email'],
            "phone": user['phone'],
            "air_miles": user['air_miles']
        })

    if request.method == "PUT":
        data = request.json
        email = data.get('email')
        phone = data.get('phone')

        if not email or not phone:
            return jsonify({"error": "Email and phone are required"}), 400

        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.execute("UPDATE Signup SET email = %s, phone = %s WHERE user_id = %s",
                           (email, phone, user['user_id']))
            db.commit()
            cursor.close()
            db.close()
            return jsonify({"success": True, "message": "Profile updated successfully"})
        except mysql.connector.IntegrityError:
            cursor.close()
            db.close()
            return jsonify({"error": "Email already exists"}), 400


# ---------------------- SEAT MATRIX ----------------------

@app.route("/admin/generate-seats")
def admin_generate_seats():
    """Generate seats for all flights that don't have seats yet"""
    if 'username' not in session:
        return "Please login first"

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get all flights
    cursor.execute("SELECT flight_id, flight_no FROM Flights")
    flights = cursor.fetchall()

    results = []
    for flight in flights:
        # Check if seats already exist
        cursor.execute("SELECT COUNT(*) as count FROM Seats WHERE flight_id = %s", (flight['flight_id'],))
        seat_count = cursor.fetchone()['count']

        if seat_count == 0:
            # Generate seats for this flight
            cursor.close()
            db.close()
            generate_seats_for_flight(flight['flight_id'])
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            results.append(f"✅ Generated seats for {flight['flight_no']}")
        else:
            results.append(f"⏭️ Skipped {flight['flight_no']} (already has {seat_count} seats)")

    cursor.close()
    db.close()

    return "<br>".join(results) + "<br><br><a href='/Dashboard'>Back to Dashboard</a>"


@app.route("/api/seats/<int:flight_id>")
def get_seats(flight_id):
    """Get seat map for a flight"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    selected_class = request.args.get('class', 'economy').capitalize()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT seat_id, seat_number, class, is_booked 
        FROM Seats 
        WHERE flight_id = %s AND class = %s
        ORDER BY seat_number
    """, (flight_id, selected_class))

    seats = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify(seats)

#-----------------------REFRESH ROUTES-------------------
@app.route("/admin/refresh-flights")
def refresh_flights():
    """Regenerate all flights - Admin function"""
    if 'username' not in session:
        return redirect(url_for('login'))

    import subprocess
    import sys

    try:
        # Run the generate_flights.py script
        result = subprocess.run(
            [sys.executable, 'generate_flights.py'],
            capture_output=True,
            text=True,
            input='yes\n'
        )

        # Generate seats for new flights
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT flight_id FROM Flights")
        flights = cursor.fetchall()

        for flight in flights:
            cursor.execute("SELECT COUNT(*) as count FROM Seats WHERE flight_id = %s", (flight['flight_id'],))
            if cursor.fetchone()['count'] == 0:
                cursor.close()
                db.close()
                generate_seats_for_flight(flight['flight_id'])
                db = get_db_connection()
                cursor = db.cursor(dictionary=True)

        cursor.close()
        db.close()

        flash("✅ Flights refreshed successfully!")
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f"❌ Error refreshing flights: {str(e)}")
        return redirect(url_for('dashboard'))


# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print(f"=== ADMIN LOGIN ATTEMPT ===")
        print(f"Username: {username}")
        print(f"Password: {password}")

        admin = get_admin_by_username(username)

        if admin:
            print(f"Admin found: {admin['username']}")
            print(f"Stored hash: {admin['password']}")

            if check_password_hash(admin['password'], password):
                print("✅ Password match!")
                session['admin_username'] = username
                session['is_admin'] = True
                flash(f"Welcome back, {admin['full_name']}!")
                return redirect(url_for('admin_dashboard'))
            else:
                print("❌ Password does not match")
                flash("Invalid password")
        else:
            print("❌ Admin not found")
            flash("Admin user not found")

        return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    session.pop('is_admin', None)
    flash("Logged out successfully")
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_username' not in session or not session.get('is_admin'):
        flash("Please login as admin first")
        return redirect(url_for('admin_login'))

    admin = get_admin_by_username(session['admin_username'])

    # Get statistics
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Total flights
    cursor.execute("SELECT COUNT(*) as total FROM Flights")
    total_flights = cursor.fetchone()['total']

    # Total bookings
    cursor.execute("SELECT COUNT(*) as total FROM Bookings WHERE status='Confirmed'")
    total_bookings = cursor.fetchone()['total']

    # Total revenue
    cursor.execute("SELECT SUM(price) as revenue FROM Bookings WHERE status='Confirmed'")
    revenue_result = cursor.fetchone()
    total_revenue = revenue_result['revenue'] if revenue_result['revenue'] else 0

    # Total users
    cursor.execute("SELECT COUNT(*) as total FROM Signup")
    total_users = cursor.fetchone()['total']

    # Recent bookings
    cursor.execute("""
        SELECT b.booking_id, b.pnr, b.booking_date, b.status, b.price,
               p.full_name as passenger_name,
               f.flight_no,
               al.name as airline
        FROM Bookings b
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Airlines al ON f.airline_id = al.airline_id
        ORDER BY b.booking_date DESC
        LIMIT 10
    """)
    recent_bookings = cursor.fetchall()

    cursor.close()
    db.close()

    stats = {
        'total_flights': total_flights,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_users': total_users
    }

    return render_template('admin_dashboard.html',
                           admin=admin,
                           stats=stats,
                           recent_bookings=recent_bookings)


@app.route('/admin/setup')
def admin_setup():
    """One-time admin setup"""
    from werkzeug.security import generate_password_hash

    db = get_db_connection()
    cursor = db.cursor()

    # Delete existing admin
    cursor.execute("DELETE FROM Admins WHERE username = 'admin'")

    # Create new admin with proper hash
    hashed = generate_password_hash('admin123')
    cursor.execute("""
        INSERT INTO Admins (username, email, password, full_name) 
        VALUES (%s, %s, %s, %s)
    """, ('admin', 'admin@airline.com', hashed, 'System Administrator'))

    db.commit()
    cursor.close()
    db.close()

    return "✅ Admin created successfully!<br><br>Login at <a href='/admin/login'>/admin/login</a><br>Username: <b>admin</b><br>Password: <b>admin123</b>"


# ==================== ADMIN API ROUTES ====================

# Get all flights for admin
@app.route('/admin/api/flights')
def admin_get_flights():
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT f.flight_id, f.flight_no, f.departure_time, f.arrival_time, f.duration,
               f.price_economy, f.price_business, f.price_first,
               f.available_seats_economy, f.available_seats_business, f.available_seats_first,
               al.name as airline,
               ap1.city as source_city, ap1.code as source_code,
               ap2.city as dest_city, ap2.code as dest_code
        FROM Flights f
        JOIN Airlines al ON f.airline_id = al.airline_id
        JOIN Airports ap1 ON f.source_airport_id = ap1.airport_id
        JOIN Airports ap2 ON f.dest_airport_id = ap2.airport_id
        ORDER BY f.departure_time DESC
        LIMIT 100
    """)

    flights = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify(flights)


# Delete flight
@app.route('/admin/api/flights/<int:flight_id>', methods=['DELETE'])
def admin_delete_flight(flight_id):
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Check if flight has bookings
        cursor.execute("SELECT COUNT(*) as count FROM Bookings WHERE flight_id = %s AND status = 'Confirmed'",
                       (flight_id,))
        booking_count = cursor.fetchone()[0]

        if booking_count > 0:
            cursor.close()
            db.close()
            return jsonify({"error": f"Cannot delete flight with {booking_count} confirmed bookings"}), 400

        # Delete flight
        cursor.execute("DELETE FROM Flights WHERE flight_id = %s", (flight_id,))
        db.commit()
        cursor.close()
        db.close()

        return jsonify({"success": True, "message": "Flight deleted successfully"})

    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({"error": str(e)}), 500


# Get all bookings for admin
@app.route('/admin/api/bookings')
def admin_get_bookings():
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.booking_id, b.pnr, b.seat_no, b.booking_date, b.status, b.class, b.price,
               p.full_name as passenger_name, p.aadhaar_no,
               f.flight_no, f.departure_time, f.arrival_time,
               al.name as airline,
               ap1.city as source_city, ap2.city as dest_city,
               u.email as user_email, u.phone as user_phone
        FROM Bookings b
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Airlines al ON f.airline_id = al.airline_id
        JOIN Airports ap1 ON f.source_airport_id = ap1.airport_id
        JOIN Airports ap2 ON f.dest_airport_id = ap2.airport_id
        JOIN Signup u ON p.user_id = u.user_id
        ORDER BY b.booking_date DESC
        LIMIT 200
    """)

    bookings = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify(bookings)


# Cancel booking (admin)
@app.route('/admin/api/bookings/<int:booking_id>/cancel', methods=['POST'])
def admin_cancel_booking(booking_id):
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Get booking details
        cursor.execute("SELECT * FROM Bookings WHERE booking_id = %s", (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            cursor.close()
            db.close()
            return jsonify({"error": "Booking not found"}), 404

        if booking['status'] == 'Cancelled':
            cursor.close()
            db.close()
            return jsonify({"error": "Booking already cancelled"}), 400

        # Update booking status
        cursor.execute("UPDATE Bookings SET status = 'Cancelled' WHERE booking_id = %s", (booking_id,))

        # Restore seat
        seat_column = f"available_seats_{booking['class'].lower()}"
        cursor.execute(f"UPDATE Flights SET {seat_column} = {seat_column} + 1 WHERE flight_id = %s",
                       (booking['flight_id'],))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({"success": True, "message": "Booking cancelled successfully"})

    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({"error": str(e)}), 500


# Get all users for admin
@app.route('/admin/api/users')
def admin_get_users():
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.user_id, s.username, s.email, s.phone, s.air_miles,
               COUNT(DISTINCT b.booking_id) as total_bookings,
               COALESCE(SUM(CASE WHEN b.status = 'Confirmed' THEN b.price ELSE 0 END), 0) as total_spent
        FROM Signup s
        LEFT JOIN Passengers p ON s.user_id = p.user_id
        LEFT JOIN Bookings b ON p.passenger_id = b.passenger_id
        GROUP BY s.user_id
        ORDER BY total_spent DESC
    """)

    users = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify(users)


# Get user details with bookings
@app.route('/admin/api/users/<int:user_id>')
def admin_get_user_details(user_id):
    if 'admin_username' not in session or not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get user info
    cursor.execute("SELECT user_id, username, email, phone, air_miles FROM Signup WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        db.close()
        return jsonify({"error": "User not found"}), 404

    # Get user's bookings
    cursor.execute("""
        SELECT b.booking_id, b.pnr, b.booking_date, b.status, b.price, b.class,
               f.flight_no, f.departure_time,
               al.name as airline,
               ap1.city as source, ap2.city as destination
        FROM Bookings b
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Airlines al ON f.airline_id = al.airline_id
        JOIN Airports ap1 ON f.source_airport_id = ap1.airport_id
        JOIN Airports ap2 ON f.dest_airport_id = ap2.airport_id
        WHERE p.user_id = %s
        ORDER BY b.booking_date DESC
    """, (user_id,))

    bookings = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify({"user": user, "bookings": bookings})


#---------------------FLIGHT FILTER---------------------
@app.route('/api/flights/search', methods=['POST'])
def search_flights_advanced():
    """Advanced flight search with filters"""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    source_code = data.get('source')
    dest_code = data.get('dest')
    date = data.get('date')  # Format: YYYY-MM-DD
    airline = data.get('airline')
    min_price = data.get('min_price', 0)
    max_price = data.get('max_price', 999999)
    sort_by = data.get('sort_by', 'price')  # price, duration, departure

    if not source_code or not dest_code:
        return jsonify([])

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get airport IDs
        cursor.execute("SELECT airport_id FROM Airports WHERE code=%s", (source_code,))
        source = cursor.fetchone()
        cursor.execute("SELECT airport_id FROM Airports WHERE code=%s", (dest_code,))
        dest = cursor.fetchone()

        if not source or not dest:
            return jsonify([])

        source_id = source['airport_id']
        dest_id = dest['airport_id']

        # Build query with filters
        query = """
            SELECT f.flight_id, f.flight_no, f.departure_time, f.arrival_time, f.duration,
                   f.price_economy, f.price_business, f.price_first,
                   f.available_seats_economy, f.available_seats_business, f.available_seats_first,
                   a.name AS airline, a.airline_id, s.code AS source, d.code AS destination
            FROM Flights f
            JOIN Airlines a ON f.airline_id = a.airline_id
            JOIN Airports s ON f.source_airport_id = s.airport_id
            JOIN Airports d ON f.dest_airport_id = d.airport_id
            WHERE f.source_airport_id=%s AND f.dest_airport_id=%s
        """
        params = [source_id, dest_id]

        # Date filter
        if date:
            query += " AND DATE(f.departure_time) = %s"
            params.append(date)

        # Airline filter
        if airline and airline != 'all':
            query += " AND a.airline_id = %s"
            params.append(airline)

        # Price filter (economy class)
        query += " AND f.price_economy BETWEEN %s AND %s"
        params.extend([min_price, max_price])

        # Sorting
        if sort_by == 'price':
            query += " ORDER BY f.price_economy ASC"
        elif sort_by == 'duration':
            query += " ORDER BY f.duration ASC"
        elif sort_by == 'departure':
            query += " ORDER BY f.departure_time ASC"

        cursor.execute(query, params)
        flights = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(flights)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify([])



#------------------------SEND PDF--------------------



@app.route('/download-ticket/<int:booking_id>')
def download_ticket(booking_id):
    """Generate and download PDF ticket"""
    if 'username' not in session:
        flash("Please login first")
        return redirect(url_for('login'))

    user = get_user_by_username(session['username'])
    if not user:
        return "User not found", 404

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get booking details
    cursor.execute("""
        SELECT b.booking_id, b.pnr, b.seat_no, b.booking_date, b.status, b.class, b.price,
               p.full_name, p.aadhaar_no,
               f.flight_no, f.departure_time, f.arrival_time, f.duration,
               al.name as airline,
               ap1.name as source_airport, ap1.city as source_city, ap1.code as source_code,
               ap2.name as dest_airport, ap2.city as dest_city, ap2.code as dest_code
        FROM Bookings b
        JOIN Passengers p ON b.passenger_id = p.passenger_id
        JOIN Flights f ON b.flight_id = f.flight_id
        JOIN Airlines al ON f.airline_id = al.airline_id
        JOIN Airports ap1 ON f.source_airport_id = ap1.airport_id
        JOIN Airports ap2 ON f.dest_airport_id = ap2.airport_id
        WHERE b.booking_id = %s AND p.user_id = %s
    """, (booking_id, user['user_id']))

    booking = cursor.fetchone()
    cursor.close()
    db.close()

    if not booking:
        return "Booking not found", 404

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#dc2626'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12
    )

    # Title
    title = Paragraph("✈️ E-TICKET", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Booking Status
    status_color = colors.green if booking['status'] == 'Confirmed' else colors.red
    status_text = f"<b>Status: <font color='{status_color.hexval()}'>{booking['status']}</font></b>"
    elements.append(Paragraph(status_text, styles['Normal']))
    elements.append(Spacer(1, 20))

    # PNR Section
    pnr_data = [
        ['PNR Number:', booking['pnr']],
        ['Booking Date:', booking['booking_date'].strftime('%d %b %Y, %I:%M %p')]
    ]
    pnr_table = Table(pnr_data, colWidths=[2 * inch, 4 * inch])
    pnr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fee2e2')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dc2626')),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(pnr_table)
    elements.append(Spacer(1, 20))

    # Passenger Details
    elements.append(Paragraph("Passenger Information", header_style))
    passenger_data = [
        ['Name:', booking['full_name']],
        ['Aadhaar:', booking['aadhaar_no']],
        ['Email:', user['email']],
        ['Phone:', user['phone']]
    ]
    passenger_table = Table(passenger_data, colWidths=[2 * inch, 4 * inch])
    passenger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(passenger_table)
    elements.append(Spacer(1, 20))

    # Flight Details
    elements.append(Paragraph("Flight Information", header_style))
    flight_data = [
        ['Airline:', booking['airline']],
        ['Flight Number:', booking['flight_no']],
        ['Class:', booking['class']],
        ['Seat Number:', booking['seat_no']],
        ['', ''],
        ['From:', f"{booking['source_city']} ({booking['source_code']})"],
        ['', booking['source_airport']],
        ['Departure:', booking['departure_time'].strftime('%d %b %Y, %I:%M %p')],
        ['', ''],
        ['To:', f"{booking['dest_city']} ({booking['dest_code']})"],
        ['', booking['dest_airport']],
        ['Arrival:', booking['arrival_time'].strftime('%d %b %Y, %I:%M %p')],
        ['', ''],
        ['Duration:', f"{booking['duration']} minutes"],
    ]
    flight_table = Table(flight_data, colWidths=[2 * inch, 4 * inch])
    flight_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('SPAN', (0, 4), (1, 4)),
        ('SPAN', (0, 8), (1, 8)),
        ('SPAN', (0, 12), (1, 12)),
    ]))
    elements.append(flight_table)
    elements.append(Spacer(1, 20))

    # Payment Details
    elements.append(Paragraph("Payment Information", header_style))
    payment_data = [
        ['Fare:', f"₹{booking['price']:,.2f}"],
        ['Tax & Fees:', '₹0.00'],
        ['Total Amount:', f"₹{booking['price']:,.2f}"],
    ]
    payment_table = Table(payment_data, colWidths=[2 * inch, 4 * inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#fee2e2')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTSIZE', (0, 2), (1, 2), 13),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(payment_table)
    elements.append(Spacer(1, 30))

    # Important Notes
    elements.append(Paragraph("Important Information", header_style))
    notes = """
    • Please arrive at the airport at least 2 hours before departure<br/>
    • Carry a valid government-issued photo ID<br/>
    • Check baggage allowance for your ticket class<br/>
    • Web check-in opens 48 hours before departure<br/>
    • For any queries, contact customer support
    """
    elements.append(Paragraph(notes, styles['Normal']))
    elements.append(Spacer(1, 20))

    # Footer
    footer_text = "<i>This is a computer-generated ticket and does not require a signature.</i>"
    elements.append(Paragraph(footer_text, styles['Normal']))

    # Build PDF
    doc.build(elements)

    # Get PDF from buffer
    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()

    # Send file
    from flask import send_file, make_response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=ticket_{booking["pnr"]}.pdf'

    return response


# ---------------------- MAIN ----------------------
if __name__ == '__main__':
    print("Server running at http://127.0.0.1:5000")
    print("Admin server at http://127.0.0.1:5000/admin/login")
    app.run(debug=True)
