from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "AI_Scheduling_Super_Key_2026"

# Database Connection Helper
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ramakrishna@2007",
        database="timetable_db"
    )

# Context processor to make "request" and "session" available in templates
@app.context_processor
def inject_context():
    return dict(session=session)

# Twilio SMS Send Helper (Configurable by admin)
def send_sms_otp(phone, otp):
    TWILIO_ACCOUNT_SID = ""  # Enter Twilio Account SID here
    TWILIO_AUTH_TOKEN = ""   # Enter Twilio Auth Token here
    TWILIO_PHONE_NUMBER = "" # Enter Twilio Phone Number here

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f"Your College Portal Verification Code is {otp}",
                from_=TWILIO_PHONE_NUMBER,
                to=phone
            )
            print(f"Twilio SMS sent to {phone}!")
            return True
        except Exception as e:
            print(f"Twilio SMS Error: {e}")
            return False
    else:
        print(f"Twilio SMS credentials not set. Simulated SMS OTP: {otp}")
        return False

# ----------------- HOME & PORTALS -----------------

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, college_name FROM colleges ORDER BY college_name")
    colleges = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', colleges=colleges)

@app.route('/college_portal/<int:college_id>')
def college_portal(college_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()
    if not college:
        return "College not found", 404
    return render_template('college_portal.html', college=college)

# ----------------- DEVELOPER PORTAL -----------------

@app.route('/developer_register', methods=['GET', 'POST'])
def developer_register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO developers (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            conn.commit()
            return redirect(url_for('developer_login'))
        except mysql.connector.Error as err:
            return render_template('developer_register.html', error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('developer_register.html')

@app.route('/developer_login', methods=['GET', 'POST'])
def developer_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM developers WHERE username = %s AND password = %s", (username, password))
        dev = cursor.fetchone()
        cursor.close()
        conn.close()

        if dev:
            session['developer_logged_in'] = True
            session['dev_username'] = dev['username']
            return redirect(url_for('developer_dashboard'))
        else:
            return render_template('developer_login.html', error="Invalid Developer Credentials")
    return render_template('developer_login.html')

@app.route('/developer_dashboard')
def developer_dashboard():
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges ORDER BY id DESC")
    colleges = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('developer_dashboard.html', colleges=colleges)

@app.route('/developer_college_details/<int:college_id>')
def developer_college_details(college_id):
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))
    
    selected_branch = request.args.get('branch', '')
    selected_section = request.args.get('section_name', '')
    selected_year = request.args.get('year_level', '')
    selected_semester = request.args.get('semester', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # College details
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    
    # Get distinct branches for filter dropdown
    cursor.execute("""
        SELECT DISTINCT branch FROM students WHERE college_id = %s 
        UNION 
        SELECT DISTINCT department FROM faculty WHERE college_id = %s""", 
        (college_id, college_id)
    )
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]

    # Get sections dynamically from DB
    cursor.execute("SELECT * FROM sections WHERE college_id = %s ORDER BY branch, section_name", (college_id,))
    sections = cursor.fetchall()

    # Admins
    cursor.execute("SELECT * FROM admin WHERE college_id = %s", (college_id,))
    admins = cursor.fetchall()

    # Faculty list
    fac_query = "SELECT * FROM faculty WHERE college_id = %s"
    fac_params = [college_id]
    if selected_branch:
        fac_query += " AND department = %s"
        fac_params.append(selected_branch)
    cursor.execute(fac_query, tuple(fac_params))
    faculty_list = cursor.fetchall()

    # Students list
    stud_query = "SELECT * FROM students WHERE college_id = %s"
    stud_params = [college_id]
    if selected_branch:
        stud_query += " AND branch = %s"
        stud_params.append(selected_branch)
    if selected_section:
        stud_query += " AND section_name = %s"
        stud_params.append(selected_section)
    if selected_year:
        stud_query += " AND year_level = %s"
        stud_params.append(int(selected_year))
    if selected_semester:
        stud_query += " AND semester = %s"
        stud_params.append(int(selected_semester))
    cursor.execute(stud_query, tuple(stud_params))
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'developer_college_details.html',
        college=college,
        admins=admins,
        faculty_list=faculty_list,
        students=students,
        branches=branches,
        sections=sections,
        selected_branch=selected_branch,
        selected_section=selected_section,
        selected_year=selected_year,
        selected_semester=selected_semester
    )

@app.route('/developer_logout')
def developer_logout():
    session.pop('developer_logged_in', None)
    session.pop('dev_username', None)
    return redirect(url_for('home'))

# ----------------- COLLEGE ADMINS (SUPER) -----------------

@app.route('/college_register', methods=['GET', 'POST'])
def college_register():
    if request.method == 'POST':
        college_name = request.form['college_name']
        college_code = request.form['college_code'].upper().strip()
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO colleges (college_name, college_code, email, password) VALUES (%s, %s, %s, %s)",
                (college_name, college_code, email, password)
            )
            conn.commit()
            # Auto login
            cursor.execute("SELECT id FROM colleges WHERE college_code = %s", (college_code,))
            college_id = cursor.fetchone()[0]
            session['college_id'] = college_id
            return redirect(url_for('college_dashboard'))
        except mysql.connector.Error as err:
            return render_template('college_register.html', error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('college_register.html')

@app.route('/college_login', methods=['GET', 'POST'])
def college_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM colleges WHERE email = %s AND password = %s", (email, password))
        college = cursor.fetchone()
        cursor.close()
        conn.close()

        if college:
            session['college_id'] = college['id']
            return redirect(url_for('college_dashboard'))
        else:
            return render_template('college_login.html', error="Invalid Email or Password")

    return render_template('college_login.html')

@app.route('/college_dashboard')
def college_dashboard():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('college_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get college details
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get local admins
    cursor.execute("SELECT * FROM admin WHERE college_id = %s", (college_id,))
    admins = cursor.fetchall()

    # Statistics
    cursor.execute("SELECT COUNT(*) as count FROM faculty WHERE college_id = %s", (college_id,))
    faculty_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM students WHERE college_id = %s", (college_id,))
    student_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM subjects WHERE college_id = %s", (college_id,))
    subject_count = cursor.fetchone()['count']

    cursor.close()
    conn.close()

    stats = {
        'faculty_count': faculty_count,
        'student_count': student_count,
        'subject_count': subject_count
    }

    return render_template('college_dashboard.html', college=college, admins=admins, stats=stats)

@app.route('/college_logout')
def college_logout():
    session.pop('college_id', None)
    return redirect(url_for('home'))

# ----------------- LOCAL DEPARTMENT ADMINS -----------------

@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College ID Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        branch = request.form['branch'].upper().strip()
        col_id = request.form['college_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admin (college_id, username, password, college_name, branch) VALUES (%s, %s, %s, %s, %s)",
                (col_id, username, password, college['college_name'], branch)
            )
            conn.commit()
            return redirect(url_for('admin_login', college_id=col_id))
        except mysql.connector.Error as err:
            return render_template('admin_register.html', college=college, error=f"Admin registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('admin_register.html', college=college)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College ID Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        col_id = request.form['college_id']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s AND password = %s AND college_id = %s", (username, password, col_id))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            session['local_admin_id'] = admin['id']
            session['admin_branch'] = admin['branch']
            session['college_id'] = col_id
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', college=college, error="Invalid Username or Password")

    return render_template('admin_login.html', college=college)

@app.route('/admin_dashboard')
def admin_dashboard():
    local_admin_id = session.get('local_admin_id')
    college_id = session.get('college_id')
    if not local_admin_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    cursor.execute("SELECT * FROM admin WHERE id = %s", (local_admin_id,))
    admin = cursor.fetchone()

    # Get department stats based on branch
    cursor.execute("SELECT COUNT(*) as count FROM faculty WHERE college_id = %s AND department = %s", (college_id, admin['branch']))
    faculty_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM students WHERE college_id = %s AND branch = %s", (college_id, admin['branch']))
    student_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM subjects WHERE college_id = %s AND branch = %s", (college_id, admin['branch']))
    subject_count = cursor.fetchone()['count']

    cursor.close()
    conn.close()

    stats = {
        'faculty_count': faculty_count,
        'student_count': student_count,
        'subject_count': subject_count
    }

    return render_template('admin_dashboard.html', college=college, admin=admin, stats=stats)

@app.route('/admin_logout')
def admin_logout():
    session.pop('local_admin_id', None)
    session.pop('admin_branch', None)
    session.pop('college_id', None)
    return redirect(url_for('home'))

# ----------------- ADMIN MANAGE SUBJECTS -----------------

@app.route('/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    college_id = session.get('college_id')
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        subject_code = request.form['subject_code'].strip().upper()
        subject_name = request.form['subject_name'].strip()
        # Lock branch to local admin branch if logged in
        branch = admin_branch if admin_branch else request.form['branch'].strip().upper()
        year_level = int(request.form['year_level'])
        semester = int(request.form['semester'])
        periods_per_week = int(request.form['periods_per_week'])

        try:
            cursor.execute(
                """INSERT INTO subjects (college_id, subject_code, subject_name, branch, year_level, semester, periods_per_week) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (college_id, subject_code, subject_name, branch, year_level, semester, periods_per_week)
            )
            conn.commit()
            success_msg = "Subject added successfully!"
        except mysql.connector.Error as err:
            success_msg = None
            error_msg = f"Error: {err.msg}"
            
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Filter subjects if local admin
    if admin_branch:
        cursor.execute("SELECT * FROM subjects WHERE college_id = %s AND branch = %s ORDER BY year_level, semester, subject_code", (college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM subjects WHERE college_id = %s ORDER BY branch, year_level, semester, subject_code", (college_id,))
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    success = locals().get('success_msg')
    error = locals().get('error_msg')

    return render_template(
    'manage_subjects.html',
    college=college,
    admin_branch=admin_branch,
    subjects=subjects,
    success=success,
    error=error
)

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subjects WHERE id = %s AND college_id = %s", (subject_id, college_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('manage_subjects'))

# ----------------- STUDENT PORTAL -----------------

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    # Fetch sections to allow student selection
    cursor.execute("SELECT * FROM sections WHERE college_id = %s ORDER BY branch, year_level, section_name", (college_id,))
    sections = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        branch = request.form['branch'].upper().strip()
        year_level = int(request.form['year_level'])
        semester = int(request.form['semester'])
        section_name = request.form['section_name'].upper().strip()
        roll_no = request.form['roll_no'].upper().strip()
        col_id = int(request.form['college_id'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO students (college_id, full_name, email, password, branch, year_level, semester, section_name, roll_no, phone)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (col_id, full_name, email, password, branch, year_level, semester, section_name, roll_no, phone)
            )
            conn.commit()
            return redirect(url_for('student_login', college_id=col_id))
        except mysql.connector.Error as err:
            return render_template('student_register.html', college=college, sections=sections, error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('student_register.html', college=college, sections=sections)

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        col_id = int(request.form['college_id'])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE email = %s AND password = %s AND college_id = %s", (email, password, col_id))
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        if student:
            session['student_id'] = student['id']
            session['student_email'] = student['email']
            session['college_id'] = col_id
            return redirect(url_for('student_dashboard'))
        else:
            return render_template('student_login.html', college=college, error="Invalid Email or Password")

    return render_template('student_login.html', college=college)

@app.route('/student_dashboard')
def student_dashboard():
    student_id = session.get('student_id')
    college_id = session.get('college_id')
    if not student_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as count FROM stress_forms WHERE student_id = %s", (student_id,))
    stress_completed = cursor.fetchone()['count'] > 0

    cursor.close()
    conn.close()

    return render_template('student_dashboard.html', student=student, college=college, stress_completed=stress_completed)

@app.route('/student_profile')
def student_profile():
    student_id = session.get('student_id')
    college_id = session.get('college_id')
    if not student_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('student_profile.html', student=student, college=college)

@app.route('/stress_form', methods=['GET', 'POST'])
def stress_form():
    student_id = session.get('student_id')
    college_id = session.get('college_id')
    if not student_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        sleep_hours = request.form['sleep_hours']
        feel_fresh = request.form['feel_fresh']
        physically_tired = request.form['physically_tired']
        headache_fatigue = request.form['headache_fatigue']
        health_rating = int(request.form['health_rating'])
        regular_day_stress = int(request.form['regular_day_stress'])
        exam_stress = int(request.form['exam_stress'])
        daily_study_hours = request.form['daily_study_hours']
        most_stress_subject = request.form['most_stress_subject']
        easiest_subject = request.form['easiest_subject']
        preferred_morning_subject = request.form['preferred_morning_subject']
        preferred_afternoon_subject = request.form['preferred_afternoon_subject']
        best_study_time = request.form['best_study_time']
        need_more_breaks = request.form['need_more_breaks']
        scheduling_suggestions = request.form['scheduling_suggestions']
        stress_comments = request.form['stress_comments']

        cursor.execute("DELETE FROM stress_forms WHERE student_id = %s", (student_id,))
        cursor.execute(
            """INSERT INTO stress_forms (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating,
                                        regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject,
                                        preferred_morning_subject, preferred_afternoon_subject, best_study_time, need_more_breaks,
                                        scheduling_suggestions, stress_comments)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating,
             regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject,
             preferred_morning_subject, preferred_afternoon_subject, best_study_time, need_more_breaks,
             scheduling_suggestions, stress_comments)
        )
        conn.commit()
        success_msg = "Stress preferences submitted successfully!"

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    cursor.execute("SELECT * FROM stress_forms WHERE student_id = %s", (student_id,))
    form = cursor.fetchone() or {}

    cursor.close()
    conn.close()

    success = locals().get('success_msg')

    return render_template('stress_form.html', college=college, form=form, success=success)

@app.route('/student_feedback', methods=['GET', 'POST'])
def student_feedback():
    student_id = session.get('student_id')
    college_id = session.get('college_id')
    if not student_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    if request.method == 'POST':
        roll_no = request.form['roll_no']
        message = request.form['message']

        cursor.execute(
            "INSERT INTO feedback (student_id, roll_no, message) VALUES (%s, %s, %s)",
            (student_id, roll_no, message)
        )
        conn.commit()
        success_msg = "Feedback submitted successfully!"

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    success = locals().get('success_msg')

    return render_template('student_feedback.html', student=student, college=college, success=success)

@app.route('/view_timetable')
def view_timetable():
    student_id = session.get('student_id')
    college_id = session.get('college_id')
    if not student_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Query published timetable for student's branch/year/sem/section
    cursor.execute(
        """SELECT * FROM timetable 
           WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s AND section_name = %s AND published = 1
           ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
        (college_id, student['branch'], student['year_level'], student['semester'], student['section_name'])
    )
    timetable = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_timetable.html', student=student, college=college, timetable=timetable)

@app.route('/student_logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_email', None)
    session.pop('college_id', None)
    return redirect(url_for('home'))

# ----------------- FACULTY PORTAL -----------------

@app.route('/faculty_register', methods=['GET', 'POST'])
def faculty_register():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        employee_id = request.form['employee_id'].upper().strip()
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        phone = request.form['phone'].strip()
        department = request.form['department'].upper().strip()
        subject_name = request.form['subject_name'].strip()
        col_id = int(request.form['college_id'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO faculty (college_id, employee_id, full_name, email, password, phone, department, subject_name)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (col_id, employee_id, full_name, email, password, phone, department, subject_name)
            )
            conn.commit()
            return redirect(url_for('faculty_login', college_id=col_id))
        except mysql.connector.Error as err:
            return render_template('faculty_register.html', college=college, error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('faculty_register.html', college=college)

@app.route('/faculty_login', methods=['GET', 'POST'])
def faculty_login():
    college_id = request.args.get('college_id')
    if not college_id:
        return "Missing College Context", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        phone = request.form['phone'].strip()
        col_id = int(request.form['college_id'])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM faculty WHERE phone = %s AND college_id = %s", (phone, col_id))
        faculty = cursor.fetchone()
        cursor.close()
        conn.close()

        if faculty:
            otp = random.randint(1000, 9999)
            session['otp'] = str(otp)
            session['otp_phone'] = phone
            session['otp_college_id'] = col_id
            
            # Call Twilio helper
            send_sms_otp(phone, str(otp))
            
            print("====================================")
            print(f" OTP SECURITY: Code is {otp} ")
            print("====================================")

            return redirect(url_for('verify_otp'))
        else:
            return render_template('faculty_login.html', college=college, error="Phone number is not registered for this college.")

    return render_template('faculty_login.html', college=college)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    otp_college_id = session.get('otp_college_id')
    if not otp_college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (otp_college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()
        if entered_otp == session.get('otp'):
            phone = session.get('otp_phone')
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty WHERE phone = %s AND college_id = %s", (phone, otp_college_id))
            faculty = cursor.fetchone()
            cursor.close()
            conn.close()

            session['faculty_id'] = faculty['id']
            session['college_id'] = otp_college_id
            
            session.pop('otp', None)
            session.pop('otp_phone', None)
            session.pop('otp_college_id', None)

            return redirect(url_for('faculty_dashboard'))
        else:
            return render_template('verify_otp.html', college=college, error="Invalid OTP Code")

    return render_template('verify_otp.html', college=college)

@app.route('/faculty_dashboard')
def faculty_dashboard():
    faculty_id = session.get('faculty_id')
    college_id = session.get('college_id')
    if not faculty_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
    faculty = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('faculty_dashboard.html', faculty=faculty, college=college)

@app.route('/faculty_view_timetable')
def faculty_view_timetable():
    faculty_id = session.get('faculty_id')
    college_id = session.get('college_id')
    if not faculty_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
    faculty = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get published timetables
    cursor.execute(
        """SELECT * FROM timetable 
           WHERE college_id = %s AND published = 1
           ORDER BY branch, section_name, year_level, semester, FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
        (college_id,)
    )
    timetable = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('faculty_view_timetable.html', faculty=faculty, college=college, timetable=timetable)

@app.route('/faculty_experience_form', methods=['GET', 'POST'])
def faculty_experience_form():
    faculty_id = session.get('faculty_id')
    college_id = session.get('college_id')
    if not faculty_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        experience_years = int(request.form['experience_years'])
        preferred_morning_subject = request.form['preferred_morning_subject'].strip()
        preferred_afternoon_subject = request.form['preferred_afternoon_subject'].strip()

        cursor.execute(
            """UPDATE faculty 
               SET experience_years = %s, preferred_morning_subject = %s, preferred_afternoon_subject = %s
               WHERE id = %s""",
            (experience_years, preferred_morning_subject, preferred_afternoon_subject, faculty_id)
        )
        conn.commit()
        success_msg = "Experience and preferences saved successfully!"

    cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
    faculty = cursor.fetchone()

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    cursor.close()
    conn.close()

    success = locals().get('success_msg')

    return render_template('faculty_experience_form.html', faculty=faculty, college=college, success=success)

@app.route('/faculty_logout')
def faculty_logout():
    session.pop('faculty_id', None)
    session.pop('college_id', None)
    return redirect(url_for('home'))

# ----------------- VIEW STUDENT FEEDBACK (ADMIN) -----------------

@app.route('/view_feedbacks')
def view_feedbacks():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    cursor.execute(
        """SELECT f.* FROM feedback f 
           JOIN students s ON f.student_id = s.id 
           WHERE s.college_id = %s ORDER BY f.id DESC""", (college_id,)
    )
    feedbacks = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('view_feedbacks.html', college=college, feedbacks=feedbacks)

# ----------------- DRAFT / PUBLISH TIMETABLE (ADMIN) -----------------

@app.route('/publish_timetable')
def publish_timetable():
    college_id = session.get('college_id')
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get distinct drafted/published branch/section combinations
    if admin_branch:
        cursor.execute(
            """SELECT DISTINCT branch, section_name, year_level, semester, published FROM timetable 
               WHERE college_id = %s AND branch = %s
               ORDER BY branch, section_name, year_level, semester""", (college_id, admin_branch)
        )
    else:
        cursor.execute(
            """SELECT DISTINCT branch, section_name, year_level, semester, published FROM timetable 
               WHERE college_id = %s 
               ORDER BY branch, section_name, year_level, semester""", (college_id,)
        )
    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    success = session.pop('publish_success', None)

    return render_template('publish_timetable.html', college=college, admin_branch=admin_branch,schedules=schedules, success=success)

@app.route('/toggle_publish_timetable', methods=['POST'])
def toggle_publish_timetable():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    branch = request.form['branch']
    section_name = request.form['section_name']
    year_level = int(request.form['year_level'])
    semester = int(request.form['semester'])
    current_published = int(request.form['published'])

    new_published = 0 if current_published == 1 else 1

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE timetable 
           SET published = %s 
           WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s""",
        (new_published, college_id, branch, section_name, year_level, semester)
    )
    conn.commit()
    cursor.close()
    conn.close()

    session['publish_success'] = "Timetable status updated successfully!"
    return redirect(url_for('publish_timetable'))

@app.route('/admin_view_timetable')
def admin_view_timetable():
    college_id = session.get('college_id')
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    selected_branch = admin_branch if admin_branch else request.args.get('branch', '')
    selected_section = request.args.get('section_name', '')
    selected_year = int(request.args.get('year_level', '1'))
    
    valid_sem_a = (selected_year - 1) * 2 + 1
    valid_sem_b = (selected_year - 1) * 2 + 2
    
    selected_semester = request.args.get('semester', '')
    if not selected_semester or int(selected_semester) not in (valid_sem_a, valid_sem_b):
        selected_semester = valid_sem_a
    else:
        selected_semester = int(selected_semester)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get branches
    cursor.execute("SELECT DISTINCT branch FROM subjects WHERE college_id = %s", (college_id,))
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]

    # Get sections
    if selected_branch:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND branch = %s AND year_level = %s ORDER BY section_name", (college_id, selected_branch, int(selected_year)))
    else:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND year_level = %s ORDER BY branch, section_name", (college_id, int(selected_year)))
    sections = cursor.fetchall()

    # Fallback to first available section if none is selected
    if not selected_section and sections:
        selected_section = sections[0]['section_name']
    elif not selected_section:
        selected_section = 'A'

    timetable = None
    if selected_branch:
        cursor.execute(
            """SELECT * FROM timetable 
               WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s
               ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
            (college_id, selected_branch, selected_section, int(selected_year), int(selected_semester))
        )
        timetable = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin_view_timetable.html',
        college=college,
        branches=branches,
        admin_branch=admin_branch,
        sections=sections,
        selected_branch=selected_branch,
        selected_section=selected_section,
        selected_year=int(selected_year),
        selected_semester=int(selected_semester),
        timetable=timetable
    )

@app.route('/manage_sections', methods=['GET', 'POST'])
def manage_sections():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    local_admin_id = session.get('local_admin_id')
    admin_branch = session.get('admin_branch')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    success = session.pop('section_success', None)
    error = session.pop('section_error', None)

    if request.method == 'POST':
        branch = admin_branch if admin_branch else request.form.get('branch', '').upper().strip()
        year_level = int(request.form.get('year_level', 1))
        section_name = request.form.get('section_name', '').upper().strip()

        if not branch or not section_name:
            error = "Branch and Section Name are required."
        else:
            try:
                # Check for duplicate
                cursor.execute(
                    "SELECT * FROM sections WHERE college_id = %s AND branch = %s AND year_level = %s AND section_name = %s",
                    (college_id, branch, year_level, section_name)
                )
                if cursor.fetchone():
                    error = f"Section '{section_name}' already exists for branch '{branch}' Year {year_level}."
                else:
                    cursor.execute(
                        "INSERT INTO sections (college_id, branch, year_level, section_name) VALUES (%s, %s, %s, %s)",
                        (college_id, branch, year_level, section_name)
                    )
                    conn.commit()
                    success = f"Section '{section_name}' successfully added for branch '{branch}' Year {year_level}."
            except mysql.connector.Error as err:
                error = f"Failed to add section: {err.msg}"

    # Get sections to display
    if admin_branch:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND branch = %s ORDER BY year_level, section_name", (college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s ORDER BY branch, year_level, section_name", (college_id,))
    sections = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
    'manage_sections.html',
    college=college,
    admin_branch=admin_branch,
    sections=sections,
    success=success,
    error=error
)

@app.route('/delete_section/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    local_admin_id = session.get('local_admin_id')
    admin_branch = session.get('admin_branch')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if admin_branch:
        cursor.execute("SELECT * FROM sections WHERE id = %s AND college_id = %s AND branch = %s", (section_id, college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM sections WHERE id = %s AND college_id = %s", (section_id, college_id))
    
    section = cursor.fetchone()
    if section:
        cursor.execute("DELETE FROM sections WHERE id = %s", (section_id,))
        conn.commit()
        session['section_success'] = f"Section '{section['section_name']}' deleted successfully."
    else:
        session['section_error'] = "Section not found or unauthorized access."

    cursor.close()
    conn.close()
    return redirect(url_for('manage_sections'))

@app.route('/stress_dashboard')
def stress_dashboard():
    college_id = session.get('college_id')
    param_college_id = request.args.get('college_id')
    if param_college_id and session.get('developer_logged_in'):
        college_id = param_college_id

    if not college_id:
        return redirect(url_for('home'))

    admin_branch = session.get('admin_branch')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Build WHERE clause based on admin branch
    if admin_branch:
        where_clause = "WHERE s.college_id = %s AND s.branch = %s"
        params = (college_id, admin_branch)
    else:
        where_clause = "WHERE s.college_id = %s"
        params = (college_id,)

    # 1. Stress Stats — using explicit named keys
    cursor.execute(f"""
        SELECT AVG(sf.regular_day_stress) as avg_regular, AVG(sf.exam_stress) as avg_exam
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause}
    """, params)
    stress_stats_row = cursor.fetchone()
    avg_regular = round(float(stress_stats_row['avg_regular']), 1) if stress_stats_row and stress_stats_row['avg_regular'] else 0.0
    avg_exam = round(float(stress_stats_row['avg_exam']), 1) if stress_stats_row and stress_stats_row['avg_exam'] else 0.0
    stress_stats = {'avg_regular': avg_regular, 'avg_exam': avg_exam}

    # 2. Hardest Subjects — use explicit named keys: 'subject' and 'cnt'
    cursor.execute(f"""
        SELECT sf.most_stress_subject AS subject, COUNT(*) AS cnt
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause} AND sf.most_stress_subject IS NOT NULL AND sf.most_stress_subject != ''
        GROUP BY sf.most_stress_subject
        ORDER BY cnt DESC
        LIMIT 8
    """, params)
    rows = cursor.fetchall()
    hardest_subjects = {
        'labels': [str(r['subject']) for r in rows],
        'values': [int(r['cnt']) for r in rows]
    }

    # 3. Easiest Subjects
    cursor.execute(f"""
        SELECT sf.easiest_subject AS subject, COUNT(*) AS cnt
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause} AND sf.easiest_subject IS NOT NULL AND sf.easiest_subject != ''
        GROUP BY sf.easiest_subject
        ORDER BY cnt DESC
        LIMIT 8
    """, params)
    rows = cursor.fetchall()
    easiest_subjects = {
        'labels': [str(r['subject']) for r in rows],
        'values': [int(r['cnt']) for r in rows]
    }

    # 4. Sleep Hours distribution
    cursor.execute(f"""
        SELECT sf.sleep_hours AS label, COUNT(*) AS cnt
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause} AND sf.sleep_hours IS NOT NULL AND sf.sleep_hours != ''
        GROUP BY sf.sleep_hours
        ORDER BY cnt DESC
    """, params)
    rows = cursor.fetchall()
    sleep_hours = {
        'labels': [str(r['label']) for r in rows],
        'values': [int(r['cnt']) for r in rows]
    }

    # 5. Peak Productivity (best study time)
    cursor.execute(f"""
        SELECT sf.best_study_time AS label, COUNT(*) AS cnt
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause} AND sf.best_study_time IS NOT NULL AND sf.best_study_time != ''
        GROUP BY sf.best_study_time
        ORDER BY cnt DESC
    """, params)
    rows = cursor.fetchall()
    productivity = {
        'labels': [str(r['label']) for r in rows],
        'values': [int(r['cnt']) for r in rows]
    }

    # 6. Feel fresh after sleep
    cursor.execute(f"""
        SELECT sf.feel_fresh AS label, COUNT(*) AS cnt
        FROM stress_forms sf
        JOIN students s ON sf.student_id = s.id
        {where_clause} AND sf.feel_fresh IS NOT NULL AND sf.feel_fresh != ''
        GROUP BY sf.feel_fresh
        ORDER BY cnt DESC
    """, params)
    rows = cursor.fetchall()
    fresh_sleep = {
        'labels': [str(r['label']) for r in rows],
        'values': [int(r['cnt']) for r in rows]
    }

    cursor.close()
    conn.close()

    return render_template(
        'stress_dashboard.html',
        college=college,
        admin_branch=admin_branch,
        stress_stats=stress_stats,
        hardest_subjects=hardest_subjects,
        easiest_subjects=easiest_subjects,
        sleep_hours=sleep_hours,
        productivity=productivity,
        fresh_sleep=fresh_sleep
    )

@app.route('/manage_periods')
def manage_periods():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    admin_branch = session.get('admin_branch')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get distinct branches configured in subjects
    cursor.execute("SELECT DISTINCT branch FROM subjects WHERE college_id = %s", (college_id,))
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]

    # Query sections
    if admin_branch:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND branch = %s ORDER BY section_name", (college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s ORDER BY branch, section_name", (college_id,))
    sections = cursor.fetchall()

    cursor.close()
    conn.close()

    success = session.pop('gen_success', None)
    error = session.pop('gen_error', None)

    return  render_template('manage_periods.html', college=college, admin_branch=admin_branch,branches=branches, sections=sections, success=success, error=error)

# ----------------- AI ENGINE: TIMETABLE GENERATION -----------------

@app.route('/generate_timetable', methods=['POST'])
def generate_timetable():
    college_id = session.get('college_id')
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    branch = admin_branch if admin_branch else request.form['branch']
    section_name = request.form['section_name'].upper().strip()
    year_level = int(request.form['year_level'])
    semester = int(request.form['semester'])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch subjects
    cursor.execute(
        "SELECT * FROM subjects WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s",
        (college_id, branch, year_level, semester)
    )
    subjects = cursor.fetchall()

    if not subjects:
        session['gen_error'] = "No subjects registered for the selected configuration!"
        cursor.close()
        conn.close()
        return redirect(url_for('manage_periods'))

    # Fetch faculties
    cursor.execute("SELECT * FROM faculty WHERE college_id = %s", (college_id,))
    faculties = cursor.fetchall()

    # Fetch student stress factors
    cursor.execute(
        """SELECT sf.most_stress_subject, COUNT(*) as count 
           FROM stress_forms sf 
           JOIN students s ON sf.student_id = s.id 
           WHERE s.college_id = %s AND s.branch = %s AND s.year_level = %s AND s.semester = %s AND s.section_name = %s
           GROUP BY sf.most_stress_subject""",
        (college_id, branch, year_level, semester, section_name)
    )
    stress_stats = {row['most_stress_subject'].lower(): row['count'] for row in cursor.fetchall() if row['most_stress_subject']}
    cursor.close()

    # Sort faculties by experience
    subject_faculty_map = {}
    for sub in subjects:
        matched_facs = [f for f in faculties if sub['subject_name'].lower() in f['subject_name'].lower() or sub['branch'].lower() in f['department'].lower()]
        matched_facs.sort(key=lambda x: x['experience_years'], reverse=True)
        subject_faculty_map[sub['id']] = matched_facs

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slots_needed = {sub['id']: sub['periods_per_week'] for sub in subjects}
    schedule = {day: {f'period{p}': 'FREE' for p in range(1, 8)} for day in days}

    # Checks if faculty is busy in another branch/section at that day/period
    def is_faculty_busy(fac_name, day, period):
        check_conn = get_db_connection()
        chk_cursor = check_conn.cursor()
        query = f"SELECT {period} FROM timetable WHERE college_id = %s AND day_name = %s"
        chk_cursor.execute(query, (college_id, day))
        rows = chk_cursor.fetchall()
        chk_cursor.close()
        check_conn.close()
        for r in rows:
            if r[0] and fac_name in r[0]:
                return True
        return False

    # Sort subjects by stress level
    sorted_subs = sorted(subjects, key=lambda x: stress_stats.get(x['subject_name'].lower(), 0), reverse=True)

    for sub in sorted_subs:
        periods_to_fill = slots_needed[sub['id']]
        fac_list = subject_faculty_map.get(sub['id'], [])
        assigned_fac = fac_list[0]['full_name'] if fac_list else "TBD"

        is_stressful = stress_stats.get(sub['subject_name'].lower(), 0) > 0
        scheduled_count = 0
        
        for day in days:
            if scheduled_count >= periods_to_fill:
                break
            
            # Stressful subjects get morning slots
            periods_pool = ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7'] if is_stressful else ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']

            for period in periods_pool:
                if schedule[day][period] == 'FREE':
                    if assigned_fac != "TBD" and is_faculty_busy(assigned_fac, day, period):
                        continue
                    schedule[day][period] = f"{sub['subject_name']} ({assigned_fac})"
                    scheduled_count += 1
                    break

        # Fallback if slots not filled
        if scheduled_count < periods_to_fill:
            for day in days:
                if scheduled_count >= periods_to_fill:
                    break
                for period in ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7']:
                    if schedule[day][period] == 'FREE':
                        if assigned_fac != "TBD" and is_faculty_busy(assigned_fac, day, period):
                            continue
                        schedule[day][period] = f"{sub['subject_name']} ({assigned_fac})"
                        scheduled_count += 1
                        if scheduled_count >= periods_to_fill:
                            break

    save_conn = get_db_connection()
    save_cursor = save_conn.cursor()
    # Delete old timetable for this section
    save_cursor.execute(
        "DELETE FROM timetable WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s",
        (college_id, branch, section_name, year_level, semester)
    )
    
    # Save new draft rows
    for day in days:
        query = """INSERT INTO timetable 
                   (college_id, branch, section_name, year_level, semester, day_name, period1, period2, period3, period4, period5, period6, period7, published)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
        save_cursor.execute(query, (
            college_id, branch, section_name, year_level, semester, day,
            schedule[day]['period1'], schedule[day]['period2'], schedule[day]['period3'],
            schedule[day]['period4'], schedule[day]['period5'], schedule[day]['period6'], schedule[day]['period7']
        ))
    save_conn.commit()
    save_cursor.close()
    save_conn.close()

    session['gen_success'] = f"AI Schedule Generated for {branch} Section {section_name} (Draft)!"
    return redirect(url_for('manage_periods'))

# ----------------- AI ENGINE: DYNAMIC LEAVE SUBSTITUTION & SWAPPING -----------------

@app.route('/absence_request', methods=['GET', 'POST'])
def absence_request():
    faculty_id = session.get('faculty_id')
    college_id = session.get('college_id')
    if not faculty_id or not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        absent_date_str = request.form['absent_date']
        start_period = int(request.form['start_period'])
        end_period = int(request.form['end_period'])
        
        absent_date = datetime.strptime(absent_date_str, "%Y-%m-%d")
        day_of_week = absent_date.strftime('%A')

        cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
        absent_faculty = cursor.fetchone()

        cursor.execute("SELECT * FROM faculty WHERE id != %s AND college_id = %s", (faculty_id, college_id))
        other_faculties = cursor.fetchall()

        cursor.execute("SELECT * FROM timetable WHERE college_id = %s", (college_id,))
        timetables = cursor.fetchall()

        updated_swaps = 0
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        for p_idx in range(start_period, end_period + 1):
            period_col = f'period{p_idx}'
            
            for t_row in timetables:
                if t_row['day_name'] == day_of_week:
                    current_session = t_row[period_col]
                    
                    if current_session and absent_faculty['full_name'] in current_session:
                        subj_part = current_session.split(" (")[0]
                        substitute_found = False
                        
                        # 1. SAME-DAY SAME-SUBJECT SUBSTITUTE (prioritizing experience)
                        potential_substitutes = [f for f in other_faculties if absent_faculty['subject_name'].lower() in f['subject_name'].lower() or absent_faculty['department'].lower() in f['department'].lower()]
                        potential_substitutes.sort(key=lambda x: x['experience_years'], reverse=True)

                        for alt_fac in potential_substitutes:
                            chk_conn = get_db_connection()
                            chk_cursor = chk_conn.cursor()
                            chk_cursor.execute(
                                """SELECT COUNT(*) FROM absence_requests 
                                   WHERE faculty_id = %s AND absent_date = %s AND %s BETWEEN start_period AND end_period""",
                                (alt_fac['id'], absent_date_str, p_idx)
                            )
                            is_absent = chk_cursor.fetchone()[0] > 0
                            
                            # check if alt_fac is teaching in any section
                            query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {period_col} LIKE %s"
                            chk_cursor.execute(query, (college_id, day_of_week, f"%{alt_fac['full_name']}%"))
                            is_busy = chk_cursor.fetchone()[0] > 0
                            
                            chk_cursor.close()
                            chk_conn.close()

                            if not is_absent and not is_busy:
                                # Substitute swap
                                new_session_text = f"{subj_part} ({alt_fac['full_name']})"
                                update_conn = get_db_connection()
                                update_cursor = update_conn.cursor()
                                update_cursor.execute(
                                    f"UPDATE timetable SET {period_col} = %s WHERE id = %s",
                                    (new_session_text, t_row['id'])
                                )
                                update_conn.commit()
                                update_cursor.close()
                                update_conn.close()
                                substitute_found = True
                                updated_swaps += 1
                                break

                        # 2. NEXT-DAY REVERSE SWAP (Same Subject)
                        if not substitute_found:
                            # Search schedules of the same class (branch, year, semester, section) for another day's period
                            # that has another teacher teaching the same subject or same department
                            search_conn = get_db_connection()
                            search_cursor = search_conn.cursor(dictionary=True)
                            search_cursor.execute(
                                """SELECT * FROM timetable 
                                   WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s""",
                                (college_id, t_row['branch'], t_row['section_name'], t_row['year_level'], t_row['semester'])
                            )
                            class_rows = search_cursor.fetchall()
                            search_cursor.close()
                            search_conn.close()
                            
                            reverse_done = False
                            for c_row in class_rows:
                                if reverse_done:
                                    break
                                for p_num in range(1, 8):
                                    test_col = f'period{p_num}'
                                    target_sess = c_row[test_col]
                                    
                                    # Don't swap on the same leave day
                                    if c_row['day_name'] == day_of_week:
                                        continue
                                        
                                    if target_sess and target_sess != 'FREE':
                                        t_subj = target_sess.split(" (")[0]
                                        t_fac_name = target_sess.split(" (")[1].replace(")", "")
                                        
                                        # Let's find this other teacher's faculty record
                                        fac_conn = get_db_connection()
                                        fac_cursor = fac_conn.cursor(dictionary=True)
                                        fac_cursor.execute("SELECT * FROM faculty WHERE full_name = %s AND college_id = %s", (t_fac_name, college_id))
                                        t_fac = fac_cursor.fetchone()
                                        fac_cursor.close()
                                        fac_conn.close()
                                        
                                        if t_fac:
                                            # Verify if t_fac is free on the leave day/period
                                            chk_conn = get_db_connection()
                                            chk_cursor = chk_conn.cursor()
                                            query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {period_col} LIKE %s"
                                            chk_cursor.execute(query, (college_id, day_of_week, f"%{t_fac_name}%"))
                                            t_fac_busy = chk_cursor.fetchone()[0] > 0
                                            chk_cursor.close()
                                            chk_conn.close()
                                            
                                            # Verify if absent faculty is free on the next day at period p_num
                                            chk_conn = get_db_connection()
                                            chk_cursor = chk_conn.cursor()
                                            query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {test_col} LIKE %s"
                                            chk_cursor.execute(query, (college_id, c_row['day_name'], f"%{absent_faculty['full_name']}%"))
                                            absent_fac_busy = chk_cursor.fetchone()[0] > 0
                                            chk_cursor.close()
                                            chk_conn.close()
                                            
                                            if not t_fac_busy and not absent_fac_busy:
                                                # Reverse swap!
                                                update_conn = get_db_connection()
                                                update_cursor = update_conn.cursor()
                                                
                                                # Set absent slot to the target session
                                                update_cursor.execute(
                                                    f"UPDATE timetable SET {period_col} = %s WHERE id = %s",
                                                    (target_sess, t_row['id'])
                                                )
                                                # Set target slot to the absent session
                                                update_cursor.execute(
                                                    f"UPDATE timetable SET {test_col} = %s WHERE id = %s",
                                                    (current_session, c_row['id'])
                                                )
                                                update_conn.commit()
                                                update_cursor.close()
                                                update_conn.close()
                                                
                                                reverse_done = True
                                                substitute_found = True
                                                updated_swaps += 1
                                                break

                        # 3. NEXT-DAY FREE SLOT SWAP
                        if not substitute_found:
                            search_conn = get_db_connection()
                            search_cursor = search_conn.cursor(dictionary=True)
                            search_cursor.execute(
                                """SELECT * FROM timetable 
                                   WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s""",
                                (college_id, t_row['branch'], t_row['section_name'], t_row['year_level'], t_row['semester'])
                            )
                            class_rows = search_cursor.fetchall()
                            search_cursor.close()
                            search_conn.close()
                            
                            swap_done = False
                            for c_row in class_rows:
                                if swap_done:
                                    break
                                for p_num in range(1, 8):
                                    test_col = f'period{p_num}'
                                    if c_row[test_col] == 'FREE' and c_row['day_name'] != day_of_week:
                                        # Check if absent teacher is free on this next day at period p_num
                                        chk_conn = get_db_connection()
                                        chk_cursor = chk_conn.cursor()
                                        query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {test_col} LIKE %s"
                                        chk_cursor.execute(query, (college_id, c_row['day_name'], f"%{absent_faculty['full_name']}%"))
                                        absent_fac_busy = chk_cursor.fetchone()[0] > 0
                                        chk_cursor.close()
                                        chk_conn.close()
                                        
                                        if not absent_fac_busy:
                                            # Swap
                                            update_conn = get_db_connection()
                                            update_cursor = update_conn.cursor()
                                            update_cursor.execute(
                                                f"UPDATE timetable SET {test_col} = %s WHERE id = %s",
                                                (current_session, c_row['id'])
                                            )
                                            update_cursor.execute(
                                                f"UPDATE timetable SET {period_col} = 'FREE' WHERE id = %s",
                                                (t_row['id'],)
                                            )
                                            update_conn.commit()
                                            update_cursor.close()
                                            update_conn.close()
                                            swap_done = True
                                            substitute_found = True
                                            updated_swaps += 1
                                            break

                        # 4. DIFFERENT GUEST FACULTY/SUBJECT SUBSTITUTE
                        if not substitute_found:
                            for guest in other_faculties:
                                chk_conn = get_db_connection()
                                chk_cursor = chk_conn.cursor()
                                # Is guest free today?
                                query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {period_col} LIKE %s"
                                chk_cursor.execute(query, (college_id, day_of_week, f"%{guest['full_name']}%"))
                                guest_busy = chk_cursor.fetchone()[0] > 0
                                chk_cursor.close()
                                chk_conn.close()
                                
                                if not guest_busy:
                                    new_session_text = f"{guest['subject_name']} ({guest['full_name']})"
                                    update_conn = get_db_connection()
                                    update_cursor = update_conn.cursor()
                                    update_cursor.execute(
                                        f"UPDATE timetable SET {period_col} = %s WHERE id = %s",
                                        (new_session_text, t_row['id'])
                                    )
                                    update_conn.commit()
                                    update_cursor.close()
                                    update_conn.close()
                                    substitute_found = True
                                    updated_swaps += 1
                                    break
        
        status_text = 'Swapped' if updated_swaps > 0 else 'Declined'
        cursor.execute(
            "INSERT INTO absence_requests (faculty_id, college_id, absent_date, start_period, end_period, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (faculty_id, college_id, absent_date_str, start_period, end_period, status_text)
        )
        conn.commit()
        
        if updated_swaps > 0:
            success_msg = f"Absence request processed! AI substituted/swapped {updated_swaps} sessions."
        else:
            success_msg = None
            error_msg = "Absence submitted. However, no alternate faculty, reverse swap, or guest slots were free."

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
    faculty = cursor.fetchone()

    cursor.execute("SELECT * FROM absence_requests WHERE faculty_id = %s ORDER BY id DESC", (faculty_id,))
    requests = cursor.fetchall()

    cursor.close()
    conn.close()

    success = locals().get('success_msg')
    error = locals().get('error_msg')

    return render_template('absence_request.html', college=college, faculty=faculty, requests=requests, success=success, error=error)

# ----------------- BOOTSTRAP RUNNER -----------------

if __name__ == '__main__':
    app.run(debug=True)