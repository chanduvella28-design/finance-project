from flask import Flask, render_template, request
from datetime import datetime, timedelta
import mysql.connector

app = Flask(__name__)

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="finance_db"
)

cursor = conn.cursor()


@app.route('/')
def home():

    # Total Customers
    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    # Active Customers
    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
        WHERE status='ACTIVE'
    """)
    active_customers = cursor.fetchone()[0]

    # Closed Customers
    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
        WHERE status='CLOSED'
    """)
    closed_customers = cursor.fetchone()[0]

    # Due Customers Today
    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
        WHERE status='ACTIVE'
        AND due_date <= CURDATE()
    """)
    due_customers = cursor.fetchone()[0]

    return render_template(
        '01_index.html',
        total_customers=total_customers,
        active_customers=active_customers,
        closed_customers=closed_customers,
        due_customers=due_customers
    )


@app.route('/add_customer')
def add_customer():
    return render_template('02_add_customer.html')


@app.route('/save_customer', methods=['POST'])
def save_customer():

    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']

    amount = float(request.form['amount'])
    rate = float(request.form['rate'])

    loan_date = request.form['loan_date']
    duration_type = request.form['duration_type']

    loan_date_obj = datetime.strptime(loan_date, "%Y-%m-%d")

    if duration_type == "DAILY":
        due_date_obj = loan_date_obj + timedelta(days=1)

    elif duration_type == "MONTHLY":
        due_date_obj = loan_date_obj + timedelta(days=30)

    elif duration_type == "YEARLY":
        due_date_obj = loan_date_obj + timedelta(days=365)

    else:
        due_date_obj = loan_date_obj

    due_date = due_date_obj.strftime("%Y-%m-%d")

    query = """
    INSERT INTO customers
    (
        name,
        mobile,
        address,
        principal_amount,
        interest_rate,
        loan_date,
        duration_type,
        due_date,
        principal_paid,
        status
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        name,
        mobile,
        address,
        amount,
        rate,
        loan_date,
        duration_type,
        due_date,
        0,
        "ACTIVE"
    )

    cursor.execute(query, values)
    conn.commit()

    return f"Customer {name} Saved Successfully"


@app.route('/active_customers')
def active_customers():

    cursor.execute("""
        SELECT
            id,
            name,
            mobile,
            principal_amount,
            interest_rate,
            duration_type,
            status
        FROM customers
        WHERE status='ACTIVE'
    """)

    customers = cursor.fetchall()

    return render_template(
        'active_customer.html',
        customers=customers
    )


@app.route('/close_loan/<int:customer_id>')
def close_loan(customer_id):

    cursor.execute("""
        UPDATE customers
        SET
            principal_paid = 1,
            status = 'CLOSED'
        WHERE id=%s
    """, (customer_id,))

    conn.commit()

    return "Loan Closed Successfully"


@app.route('/reminders')
def reminders():

    cursor.execute("""
        SELECT
            id,
            name,
            principal_amount,
            interest_rate,
            due_date,
            (principal_amount * interest_rate / 100) AS interest_amount
        FROM customers
        WHERE status='ACTIVE'
    """)

    customers = cursor.fetchall()

    return render_template(
        'reminders.html',
        customers=customers
    )


@app.route('/collect_interest/<int:customer_id>')
def collect_interest(customer_id):

    cursor.execute("""
        SELECT
            interest_rate,
            principal_amount,
            duration_type,
            due_date
        FROM customers
        WHERE id=%s
    """, (customer_id,))

    customer = cursor.fetchone()

    if not customer:
        return "Customer Not Found"

    rate = float(customer[0])
    principal = float(customer[1])
    duration = customer[2]
    due_date = customer[3]

    interest_amount = principal * rate / 100

    cursor.execute("""
        INSERT INTO interest_payments
        (customer_id, payment_date, interest_amount)
        VALUES (%s, CURDATE(), %s)
    """, (customer_id, interest_amount))

    if duration == "DAILY":
        next_due = due_date + timedelta(days=1)

    elif duration == "MONTHLY":
        next_due = due_date + timedelta(days=30)

    elif duration == "YEARLY":
        next_due = due_date + timedelta(days=365)

    else:
        next_due = due_date

    cursor.execute("""
        UPDATE customers
        SET due_date=%s
        WHERE id=%s
    """, (next_due, customer_id))

    conn.commit()

    return "Interest Collected Successfully"
@app.route('/payment_history')
def payment_history():

    cursor.execute("""
        SELECT
            payment_id,
            customer_id,
            payment_date,
            interest_amount
        FROM interest_payments
        ORDER BY payment_id DESC
    """)

    payments = cursor.fetchall()

    return render_template(
        'payment_history.html',
        payments=payments
    )
@app.route('/customer/<int:customer_id>')
def customer_details(customer_id):

    cursor.execute("""
        SELECT *
        FROM customers
        WHERE id=%s
    """, (customer_id,))

    customer = cursor.fetchone()

    cursor.execute("""
        SELECT
            payment_date,
            interest_amount
        FROM interest_payments
        WHERE customer_id=%s
        ORDER BY payment_date DESC
    """, (customer_id,))

    payments = cursor.fetchall()

    return render_template(
        'customer_details.html',
        customer=customer,
        payments=payments
    )

if __name__ == '__main__':
    app.run(debug=True)