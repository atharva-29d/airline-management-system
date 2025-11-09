import mysql.connector
from datetime import datetime, timedelta
import random
import os


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("database_pass", "4u84sm-MYSQL"),
        database="Airline_Schema"
    )


def clear_old_flights():
    """Delete all existing flights and their seats"""
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cursor.execute("TRUNCATE TABLE Seats")
    cursor.execute("TRUNCATE TABLE Bookings")
    cursor.execute("TRUNCATE TABLE Flights")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    db.commit()
    cursor.close()
    db.close()
    print("✅ Cleared old flights")


def generate_dynamic_flights():
    """Generate flights for the next 7 days"""
    db = get_db_connection()
    cursor = db.cursor()

    # Flight routes with popular connections
    routes = [
        # (airline_id, flight_no_prefix, source_id, dest_id, duration_mins, base_price_economy)
        (1, '6E', 1, 2, 135, 4500),  # Delhi → Mumbai
        (1, '6E', 2, 1, 135, 4500),  # Mumbai → Delhi
        (1, '6E', 2, 3, 120, 4000),  # Mumbai → Bengaluru
        (1, '6E', 3, 2, 120, 4200),  # Bengaluru → Mumbai
        (1, '6E', 1, 3, 165, 5500),  # Delhi → Bengaluru
        (1, '6E', 3, 1, 165, 5600),  # Bengaluru → Delhi
        (2, 'UK', 1, 4, 155, 5800),  # Delhi → Chennai
        (2, 'UK', 4, 1, 155, 5800),  # Chennai → Delhi
        (2, 'UK', 2, 4, 105, 4800),  # Mumbai → Chennai
        (2, 'UK', 4, 2, 105, 4700),  # Chennai → Mumbai
        (2, 'UK', 3, 4, 65, 3400),  # Bengaluru → Chennai
        (2, 'UK', 4, 3, 65, 3500),  # Chennai → Bengaluru
        (3, 'AI', 1, 5, 140, 5200),  # Delhi → Kolkata
        (3, 'AI', 5, 1, 140, 5300),  # Kolkata → Delhi
        (3, 'AI', 2, 5, 155, 5600),  # Mumbai → Kolkata
        (3, 'AI', 5, 2, 155, 5600),  # Kolkata → Mumbai
        (3, 'AI', 1, 6, 105, 4800),  # Delhi → Hyderabad
        (3, 'AI', 6, 1, 135, 5000),  # Hyderabad → Delhi
        (4, 'SG', 2, 6, 85, 4100),  # Mumbai → Hyderabad
        (4, 'SG', 6, 2, 85, 4100),  # Hyderabad → Mumbai
        (4, 'SG', 3, 6, 60, 3600),  # Bengaluru → Hyderabad
        (4, 'SG', 6, 3, 60, 3600),  # Hyderabad → Bengaluru
        (1, '6E', 1, 7, 95, 4400),  # Delhi → Ahmedabad
        (1, '6E', 7, 1, 95, 4400),  # Ahmedabad → Delhi
        (2, 'UK', 7, 2, 75, 3800),  # Ahmedabad → Mumbai
        (2, 'UK', 2, 7, 75, 3800),  # Mumbai → Ahmedabad
        (1, '6E', 2, 9, 30, 2500),  # Mumbai → Pune
        (1, '6E', 9, 2, 30, 2500),  # Pune → Mumbai
        (3, 'AI', 1, 9, 135, 4600),  # Delhi → Pune
        (3, 'AI', 9, 1, 135, 4600),  # Pune → Delhi
        (1, '6E', 2, 10, 135, 5200),  # Mumbai → Kochi
        (1, '6E', 10, 2, 135, 5200),  # Kochi → Mumbai
        (2, 'UK', 3, 10, 90, 4400),  # Bengaluru → Kochi
        (2, 'UK', 10, 3, 90, 4400),  # Kochi → Bengaluru
        (4, 'SG', 2, 11, 75, 3900),  # Mumbai → Goa
        (4, 'SG', 11, 2, 75, 3900),  # Goa → Mumbai
        (3, 'AI', 1, 11, 150, 5500),  # Delhi → Goa
        (3, 'AI', 11, 1, 150, 5500),  # Goa → Delhi
    ]

    # Departure times (24-hour format)
    departure_times = [
        (6, 0),  # 6:00 AM
        (7, 30),  # 7:30 AM
        (9, 0),  # 9:00 AM
        (10, 30),  # 10:30 AM
        (12, 0),  # 12:00 PM
        (13, 30),  # 1:30 PM
        (15, 0),  # 3:00 PM
        (16, 30),  # 4:30 PM
        (18, 0),  # 6:00 PM
        (19, 30),  # 7:30 PM
    ]

    flight_count = 0
    base_date = datetime.now()

    # Generate flights for next 7 days
    for day_offset in range(1, 8):  # Days 1-7 from today
        flight_date = base_date + timedelta(days=day_offset)

        # For each route
        for airline_id, prefix, source, dest, duration, base_price in routes:
            # Generate 2-3 flights per day for popular routes
            num_flights = random.randint(2, 3)

            for _ in range(num_flights):
                hour, minute = random.choice(departure_times)

                departure = flight_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                arrival = departure + timedelta(minutes=duration)

                # Generate unique flight number
                flight_no = f"{prefix}{random.randint(1000, 9999)}"

                # Add some price variation (±20%)
                price_economy = base_price + random.randint(-500, 500)
                price_business = int(price_economy * 1.7)
                price_first = int(price_economy * 2.5)

                # Random seat availability
                seats_economy = random.randint(60, 120)
                seats_business = random.randint(10, 25)
                seats_first = random.randint(6, 12)

                try:
                    cursor.execute("""
                        INSERT INTO Flights 
                        (airline_id, flight_no, source_airport_id, dest_airport_id, 
                         departure_time, arrival_time, duration,
                         price_economy, price_business, price_first,
                         available_seats_economy, available_seats_business, available_seats_first)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (airline_id, flight_no, source, dest, departure, arrival, duration,
                          price_economy, price_business, price_first,
                          seats_economy, seats_business, seats_first))
                    flight_count += 1
                except mysql.connector.IntegrityError:
                    # Skip if flight number already exists
                    continue

    db.commit()
    cursor.close()
    db.close()

    print(f"✅ Generated {flight_count} dynamic flights for next 7 days")
    return flight_count


if __name__ == "__main__":
    print("🛫 Starting dynamic flight generation...")
    print("⚠️  This will delete all existing flights and bookings!")

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_old_flights()
        generate_dynamic_flights()
        print("✅ Done! All flights are now dynamic.")
    else:
        print("❌ Cancelled")