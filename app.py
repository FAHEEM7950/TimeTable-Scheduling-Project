from flask import Flask, render_template, request, redirect, session
import mysql.connector
import random


app = Flask(__name__)
app.secret_key = "Ramakrishna_project_key"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ramakrishna@2007",
    database="timetable_db"
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        year = request.form['year']
        section = request.form['section']

        cursor = db.cursor()

        query = """
        INSERT INTO students
        (name, email, password, department, year, section)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (name, email, password, department, year, section))
        db.commit()

        return "Student Registered Successfully"

    return render_template('student_register.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()
        query = "SELECT * FROM students WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        user = cursor.fetchone()

        if user:
            return redirect('/student_dashboard')
        else:
            return "Invalid Email or Password"

    return render_template('student_login.html')

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')

@app.route('/student_profile')
def student_profile():
    return "Student Profile"

@app.route('/stress_form')
def stress_form():
    return "Stress Form"

@app.route('/view_timetable')
def view_timetable():
    return "Student Timetable"

@app.route('/student_feedback')
def student_feedback():
    return "Feedback Page"

@app.route('/student_logout')
def student_logout():
    session.clear()
    return redirect('/student_login')

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()

        query = "INSERT INTO admin (username, password) VALUES (%s,%s)"
        cursor.execute(query, (username, password))
        db.commit()

        return "Admin Registered Successfully"

    return render_template('admin_register.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()

        query = "SELECT * FROM admin WHERE username=%s AND password=%s"
        cursor.execute(query, (username, password))

        admin = cursor.fetchone()

        if admin:
            return "Admin Login Successful"
        else:
            return "Invalid Username or Password"

    return render_template('admin_login.html')

@app.route('/faculty_register', methods=['GET', 'POST'])
def faculty_register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        age = request.form['age']
        experience = request.form['experience']
        department = request.form['department']
        subject = request.form['subject']
        availability = request.form['availability']

        cursor = db.cursor()

        query = """
        INSERT INTO faculty
        (name, email, phone, age, experience, department, subject_handled, availability)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            name,
            email,
            phone,
            age,
            experience,
            department,
            subject,
            availability
        )

        cursor.execute(query, values)

        db.commit()
        cursor.close()

        return redirect('/faculty_login')

    return render_template('faculty_register.html')

@app.route('/faculty_login', methods=['GET', 'POST'])
def faculty_login():

    if request.method == 'POST':
        phone = request.form['phone']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM faculty WHERE phone=%s", (phone,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            otp = random.randint(1000, 9999)

            session['otp'] = str(otp)
            session['phone'] = phone

            print("OTP is:", otp)

            return redirect('/verify_otp')

        else:
            return "Phone number not registered"

    return render_template('faculty_login.html')

@app.route('/faculty_dashboard')
def faculty_dashboard():
    return "Welcome Faculty Dashboard"

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():

    if request.method == 'POST':
        entered_otp = request.form['otp']

        if entered_otp == session['otp']:
            return redirect('/faculty_dashboard')
        else:
            return "Invalid OTP"

    return render_template('verify_otp.html')
if __name__ == '__main__':
    app.run(debug=True)