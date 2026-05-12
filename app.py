from flask import Flask, render_template, request
import mysql.connector

app = Flask(__name__)

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ramakrishna@2007",
    database="timetable_db"
)


# ---------------- HOME ---------------- #

@app.route('/')
def home():
    return render_template('index.html')


# ---------------- STUDENT REGISTER ---------------- #

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

        cursor.execute(query, (
            name,
            email,
            password,
            department,
            year,
            section
        ))

        db.commit()

        return "Student Registered Successfully"

    return render_template('student_register.html')


# ---------------- STUDENT LOGIN ---------------- #

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
            return "Student Login Successful"
        else:
            return "Invalid Email or Password"

    return render_template('student_login.html')


# ---------------- ADMIN REGISTER ---------------- #

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


# ---------------- ADMIN LOGIN ---------------- #

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


# ---------------- FACULTY REGISTER ---------------- #

@app.route('/faculty_register', methods=['GET', 'POST'])
def faculty_register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        department = request.form['department']
        subject_handled = request.form['subject_handled']
        availability = request.form['availability']

        cursor = db.cursor()

        query = """
        INSERT INTO faculty
        (name, email, phone, department, subject_handled, availability)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (
            name,
            email,
            phone,
            department,
            subject_handled,
            availability
        ))

        db.commit()

        return "Faculty Registered Successfully"

    return render_template('faculty_register.html')


# ---------------- FACULTY LOGIN ---------------- #

@app.route('/faculty_login', methods=['GET', 'POST'])
def faculty_login():

    if request.method == 'POST':

        email = request.form['email']

        cursor = db.cursor()

        query = "SELECT * FROM faculty WHERE email=%s"

        cursor.execute(query, (email,))

        faculty = cursor.fetchone()

        if faculty:
            return "Faculty Login Successful"
        else:
            return "Invalid Email"

    return render_template('faculty_login.html')


# ---------------- MAIN ---------------- #

if __name__ == '__main__':
    app.run(debug=True)