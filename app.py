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
@app.route('/college_register', methods=['GET', 'POST'])
def college_register():

    if request.method == 'POST':

        college_name = request.form['college_name']
        college_code = request.form['college_code']
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()

        query = """
        INSERT INTO colleges
        (college_name, college_code, email, password)
        VALUES (%s,%s,%s,%s)
        """

        cursor.execute(query, (
            college_name,
            college_code,
            email,
            password
        ))

        db.commit()
        cursor.close()

        return redirect('/college_login')

    return render_template('college_register.html')
@app.route('/college_login', methods=['GET', 'POST'])
def college_login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()

        query = """
        SELECT * FROM colleges
        WHERE email=%s AND password=%s
        """

        cursor.execute(query, (email, password))

        college = cursor.fetchone()

        cursor.close()

        if college:
            return redirect('/college_dashboard')
        else:
            return "Invalid Email or Password"

    return render_template('college_login.html')
@app.route('/college_dashboard')
def college_dashboard():
    return render_template('college_dashboard.html')
@app.route('/college_logout')
def college_logout():
    session.clear()
    return redirect('/college_login')
@app.route('/view_students')
def view_students():
    return "Students List"
@app.route('/view_faculty')
def view_faculty():
    return "Faculty List"
@app.route('/view_admins')
def view_admins():
    return "Admins List"

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():

    if request.method == 'POST':

        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        college_name = request.form['college_name']
        branch = request.form['branch']
        year_level = request.form['year_level']
        semester = request.form['semester']
        section_name = request.form['section_name']
        roll_no = request.form['roll_no']
        phone = request.form['phone']

        cursor = db.cursor()

        query = """
        INSERT INTO students
        (full_name, email, password, college_name,
         branch, year_level, semester,
         section_name, roll_no, phone)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (
            full_name,
            email,
            password,
            college_name,
            branch,
            year_level,
            semester,
            section_name,
            roll_no,
            phone
        ))

        db.commit()
        cursor.close()

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
             session['student_email'] = email
             return redirect('/student_dashboard')
         
        else:
            return "Invalid Email or Password"

    return render_template('student_login.html')

@app.route('/student_dashboard')
def student_dashboard():
    return render_template('student_dashboard.html')
@app.route('/student_profile')
def student_profile():

    email = session.get('student_email')

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM students WHERE email=%s",
        (email,)
    )

    student = cursor.fetchone()

    cursor.close()

    return render_template(
        'student_profile.html',
        student=student
    )


@app.route('/stress_form', methods=['GET', 'POST'])
def stress_form():

    if request.method == 'POST':

        student_id = request.form['student_id']
        sleep_hours = request.form['sleep_hours']
        feel_fresh = request.form['feel_fresh']
        physically_tired = request.form['physically_tired']
        headache_fatigue = request.form['headache_fatigue']
        health_rating = request.form['health_rating']
        regular_day_stress = request.form['regular_day_stress']
        exam_stress = request.form['exam_stress']
        daily_study_hours = request.form['daily_study_hours']
        most_stress_subject = request.form['most_stress_subject']
        easiest_subject = request.form['easiest_subject']
        preferred_morning_subject = request.form['preferred_morning_subject']
        preferred_afternoon_subject = request.form['preferred_afternoon_subject']
        best_study_time = request.form['best_study_time']
        need_more_breaks = request.form['need_more_breaks']
        scheduling_suggestions = request.form['scheduling_suggestions']
        stress_comments = request.form['stress_comments']

        cursor = db.cursor()

        query = """
        INSERT INTO stress_forms
        (
            student_id,
            sleep_hours,
            feel_fresh,
            physically_tired,
            headache_fatigue,
            health_rating,
            regular_day_stress,
            exam_stress,
            daily_study_hours,
            most_stress_subject,
            easiest_subject,
            preferred_morning_subject,
            preferred_afternoon_subject,
            best_study_time,
            need_more_breaks,
            scheduling_suggestions,
            stress_comments
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (
            student_id,
            sleep_hours,
            feel_fresh,
            physically_tired,
            headache_fatigue,
            health_rating,
            regular_day_stress,
            exam_stress,
            daily_study_hours,
            most_stress_subject,
            easiest_subject,
            preferred_morning_subject,
            preferred_afternoon_subject,
            best_study_time,
            need_more_breaks,
            scheduling_suggestions,
            stress_comments
        ))

        db.commit()
        cursor.close()

        return "Stress Form Submitted Successfully"

    return render_template('stress_form.html')
@app.route('/view_timetable')
def view_timetable():

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM timetable")

    timetable = cursor.fetchall()

    cursor.close()

    return render_template(
        'view_timetable.html',
        timetable=timetable
    )
@app.route('/student_feedback', methods=['GET','POST'])
def student_feedback():

    if request.method == 'POST':

        student_id = request.form['student_id']
        roll_no = request.form['roll_no']
        message = request.form['message']

        cursor = db.cursor()

        cursor.execute("""
        INSERT INTO feedback
        (student_id, roll_no, message)
        VALUES (%s,%s,%s)
        """, (
            student_id,
            roll_no,
            message
        ))

        db.commit()
        cursor.close()

        return "Feedback Submitted Successfully"

    return render_template('student_feedback.html')

@app.route('/student_logout')
def student_logout():
    session.clear()
    return redirect('/student_login')

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        college_name = request.form['college_name']

        cursor = db.cursor()

        query = """
        INSERT INTO admin
        (username, password, college_name)
        VALUES (%s,%s,%s)
        """

        cursor.execute(query, (
            username,
            password,
            college_name
        ))

        db.commit()
        cursor.close()

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
            return redirect('/admin_dashboard')
        else:
            return "Invalid Username or Password"

    return render_template('admin_login.html')
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/manage_periods')
def manage_periods():
    return render_template('manage_periods.html')


@app.route('/publish_timetable')
def publish_timetable():
    return render_template('publish_timetable.html')


@app.route('/admin_view_timetable')
def admin_view_timetable():
    return render_template('admin_view_timetable.html')

@app.route('/admin_logout')
def admin_logout():
    session.clear()
    return redirect('/admin_login')
@app.route('/admin_profile')
def admin_profile():
    return "Admin Profile"

@app.route('/faculty_register', methods=['GET', 'POST'])
def faculty_register():

    if request.method == 'POST':

        employee_id = request.form['employee_id']
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        college_name = request.form['college_name']
        department = request.form['department']
        subject_name = request.form['subject_name']

        cursor = db.cursor()

        query = """
        INSERT INTO faculty
        (employee_id, full_name, email, password,
         phone, college_name, department, subject_name)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        cursor.execute(query, (
            employee_id,
            full_name,
            email,
            password,
            phone,
            college_name,
            department,
            subject_name
        ))

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
    return render_template('faculty_dashboard.html')

@app.route('/faculty_profile')
def faculty_profile():
    return "Faculty Profile"


@app.route('/absence_request')
def absence_request():
    return render_template('absence_request.html')


@app.route('/faculty_experience_form')
def faculty_experience_form():
    return render_template('faculty_experience_form.html')


@app.route('/faculty_view_timetable')
def faculty_view_timetable():
    return render_template('faculty_view_timetable.html')
@app.route('/faculty_logout')
def faculty_logout():
    session.clear()
    return redirect('/faculty_login')


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