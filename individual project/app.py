from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)


app = Flask(__name__)


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '' 
app.config['MYSQL_DB'] = 'marvin'
app.config['SECRET_KEY'] = '78675544'
mysql = MySQL(app)  

# Custom filter for date formatting
@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    return value.strftime(format)

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password)
        
        try:
            # Ensure connection exists
            if not mysql.connection:
                flash('Database connection error', 'danger')
                return redirect(url_for('signup'))
            
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            mysql.connection.commit()
            cur.close()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            if mysql.connection:
                mysql.connection.rollback()
            flash(f'Error creating account: {str(e)}', 'danger')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get employee count for dashboard
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM employees WHERE created_by = %s", (session['user_id'],))
    employee_count = cur.fetchone()[0]
    cur.close()
    
    return render_template('dashboard.html', employee_count=employee_count)

@app.route('/employees')
def employees():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, first_name, last_name, email, department, position, salary, hire_date 
        FROM employees 
        WHERE created_by = %s
        ORDER BY hire_date DESC
    """, (session['user_id'],))
    employees = cur.fetchall()
    cur.close()
    
    return render_template('employees.html', employees=employees)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        department = request.form['department']
        position = request.form['position']
        salary = request.form['salary']
        hire_date = request.form['hire_date']
        
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO employees 
                (first_name, last_name, email, department, position, salary, hire_date, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (first_name, last_name, email, department, position, salary, hire_date, session['user_id']))
            mysql.connection.commit()
            cur.close()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Error adding employee. Email may already exist.', 'danger')
    
    return render_template('add_employee.html')

@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        department = request.form['department']
        position = request.form['position']
        salary = request.form['salary']
        hire_date = request.form['hire_date']
        
        try:
            cur.execute("""
                UPDATE employees 
                SET first_name = %s, last_name = %s, email = %s, department = %s, 
                    position = %s, salary = %s, hire_date = %s
                WHERE id = %s AND created_by = %s
            """, (first_name, last_name, email, department, position, salary, hire_date, 
                 employee_id, session['user_id']))
            mysql.connection.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Error updating employee.', 'danger')
    
    # Get employee data for the form
    cur.execute("""
        SELECT id, first_name, last_name, email, department, position, salary, hire_date
        FROM employees 
        WHERE id = %s AND created_by = %s
    """, (employee_id, session['user_id']))
    employee = cur.fetchone()
    cur.close()
    
    if not employee:
        flash('Employee not found or you do not have permission to edit', 'danger')
        return redirect(url_for('employees'))
    
    return render_template('edit_employee.html', employee=employee)

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            DELETE FROM employees 
            WHERE id = %s AND created_by = %s
        """, (employee_id, session['user_id']))
        mysql.connection.commit()
        cur.close()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error deleting employee.', 'danger')
    
    return redirect(url_for('employees'))

def test_db_connection():
    try:
        conn = mysql.connect
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection successful!")
        cursor.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

# Call this when your app starts
if __name__ == '__main__':
    if test_db_connection():
        app.run(debug=True)
    else:
        print("Cannot start app without database connection")

if __name__ == '__main__':
    app.run(debug=True)