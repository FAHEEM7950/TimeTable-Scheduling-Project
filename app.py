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

# ----------------- HOME & PORTALS -----------------

@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/developer_login', methods=['GET', 'POST'])
def developer_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'developer' and password == 'devpass':
            session['developer_logged_in'] = True
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
    selected_year = request.args.get('year_level', '')
    selected_semester = request.args.get('semester', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # College details
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    
    # Get distinct branches for filter dropdown
    cursor.execute("SELECT DISTINCT branch FROM students WHERE college_id = %s UNION SELECT DISTINCT department FROM faculty WHERE college_id = %s", (college_id, college_id))
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]

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
        selected_branch=selected_branch,
        selected_year=selected_year,
        selected_semester=selected_semester
    )

@app.route('/developer_logout')
def developer_logout():
    session.pop('developer_logged_in', None)
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
            # Auto login the registered college admin
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

# ----------------- LOCAL ADMINS -----------------

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
        col_id = request.form['college_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admin (college_id, username, password, college_name) VALUES (%s, %s, %s, %s)",
                (col_id, username, password, college['college_name'])
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

    cursor.execute("SELECT * FROM admin WHERE college_id = %s", (college_id,))
    admins = cursor.fetchall()

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

    return render_template('admin_dashboard.html', college=college, admins=admins, stats=stats)

@app.route('/admin_logout')
def admin_logout():
    session.pop('local_admin_id', None)
    session.pop('college_id', None)
    return redirect(url_for('home'))

# ----------------- ADMIN MANAGE SUBJECTS -----------------

@app.route('/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        subject_code = request.form['subject_code'].strip().upper()
        subject_name = request.form['subject_name'].strip()
        branch = request.form['branch'].strip().upper()
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

    cursor.execute("SELECT * FROM subjects WHERE college_id = %s ORDER BY branch, year_level, semester, subject_code", (college_id,))
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    success = locals().get('success_msg')
    error = locals().get('error_msg')

    return render_template('manage_subjects.html', college=college, subjects=subjects, success=success, error=error)

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
            return render_template('student_register.html', college=college, error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('student_register.html', college=college)

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

        # Delete existing if any, then insert
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

    # Query timetable for this student's branch/year/sem, must be published (published=1)
    cursor.execute(
        """SELECT * FROM timetable 
           WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s AND published = 1
           ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
        (college_id, student['branch'], student['year_level'], student['semester'])
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
            
            # Print simulated OTP to console
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
            
            # Clear temporary OTP session vars
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

    # Get timetables where this faculty teaches
    cursor.execute(
        """SELECT * FROM timetable 
           WHERE college_id = %s AND published = 1
           ORDER BY branch, year_level, semester, FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
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
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get distinct drafted/published branches, year, sem combinations
    cursor.execute(
        """SELECT DISTINCT branch, year_level, semester, published FROM timetable 
           WHERE college_id = %s 
           ORDER BY branch, year_level, semester""", (college_id,)
    )
    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    success = session.pop('publish_success', None)

    return render_template('publish_timetable.html', college=college, schedules=schedules, success=success)

@app.route('/toggle_publish_timetable', methods=['POST'])
def toggle_publish_timetable():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    branch = request.form['branch']
    year_level = int(request.form['year_level'])
    semester = int(request.form['semester'])
    current_published = int(request.form['published'])

    new_published = 0 if current_published == 1 else 1

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE timetable 
           SET published = %s 
           WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s""",
        (new_published, college_id, branch, year_level, semester)
    )
    conn.commit()
    cursor.close()
    conn.close()

    session['publish_success'] = "Timetable status updated successfully!"
    return redirect(url_for('publish_timetable'))

@app.route('/admin_view_timetable')
def admin_view_timetable():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    selected_branch = request.args.get('branch', '')
    selected_year = request.args.get('year_level', '1')
    selected_semester = request.args.get('semester', '1')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get branches
    cursor.execute("SELECT DISTINCT branch FROM subjects WHERE college_id = %s", (college_id,))
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]

    timetable = None
    if selected_branch:
        cursor.execute(
            """SELECT * FROM timetable 
               WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s
               ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
            (college_id, selected_branch, int(selected_year), int(selected_semester))
        )
        timetable = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin_view_timetable.html',
        college=college,
        branches=branches,
        selected_branch=selected_branch,
        selected_year=int(selected_year),
        selected_semester=int(selected_semester),
        timetable=timetable
    )

@app.route('/manage_periods')
def manage_periods():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Get distinct branches configured in subjects
    cursor.execute("SELECT DISTINCT branch FROM subjects WHERE college_id = %s", (college_id,))
    branches = [row['branch'] for row in cursor.fetchall() if row['branch']]
    cursor.close()
    conn.close()

    success = session.pop('gen_success', None)
    error = session.pop('gen_error', None)

    return render_template('manage_periods.html', college=college, branches=branches, success=success, error=error)

# ----------------- AI ENGINE: TIMETABLE GENERATION -----------------

@app.route('/generate_timetable', methods=['POST'])
def generate_timetable():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    branch = request.form['branch']
    year_level = int(request.form['year_level'])
    semester = int(request.form['semester'])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch all subjects for this configuration
    cursor.execute(
        "SELECT * FROM subjects WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s",
        (college_id, branch, year_level, semester)
    )
    subjects = cursor.fetchall()

    if not subjects:
        session['gen_error'] = "No subjects registered for the selected Branch/Year/Sem!"
        cursor.close()
        conn.close()
        return redirect(url_for('manage_periods'))

    # 2. Fetch all faculty members in this college
    cursor.execute("SELECT * FROM faculty WHERE college_id = %s", (college_id,))
    faculties = cursor.fetchall()

    # 3. Fetch student stress factors to detect hardest/stressful subjects
    cursor.execute(
        """SELECT sf.most_stress_subject, COUNT(*) as count 
           FROM stress_forms sf 
           JOIN students s ON sf.student_id = s.id 
           WHERE s.college_id = %s AND s.branch = %s AND s.year_level = %s AND s.semester = %s
           GROUP BY sf.most_stress_subject""",
        (college_id, branch, year_level, semester)
    )
    stress_stats = {row['most_stress_subject'].lower(): row['count'] for row in cursor.fetchall() if row['most_stress_subject']}

    cursor.close()

    # Map subjects to teaching faculties
    # Sort faculties by teaching experience (highest first)
    subject_faculty_map = {}
    for sub in subjects:
        # Match faculty whose specialization matches the subject
        matched_facs = [f for f in faculties if sub['subject_name'].lower() in f['subject_name'].lower() or sub['branch'].lower() in f['department'].lower()]
        # Sort by experience
        matched_facs.sort(key=lambda x: x['experience_years'], reverse=True)
        subject_faculty_map[sub['id']] = matched_facs

    # Generate grid: 5 days (Mon-Fri), 7 periods per day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slots_needed = {sub['id']: sub['periods_per_week'] for sub in subjects}
    
    # Initialize schedule
    schedule = {day: {f'period{p}': 'FREE' for p in range(1, 8)} for day in days}

    # Helper: Check if a faculty is already scheduled in another class at a specific day/period in this college
    def is_faculty_busy(fac_name, day, period):
        check_conn = get_db_connection()
        chk_cursor = check_conn.cursor()
        # Search all timetable rows for this college on this day
        query = f"SELECT {period} FROM timetable WHERE college_id = %s AND day_name = %s"
        chk_cursor.execute(query, (college_id, day))
        rows = chk_cursor.fetchall()
        chk_cursor.close()
        check_conn.close()
        for r in rows:
            if r[0] and fac_name in r[0]:
                return True
        return False

    # AI Priority Scheduling Logic:
    # Highly stressful subjects should be spaced out (max 1 per day) and placed in morning periods (1, 2, 3)
    # Sort subjects by stress level
    sorted_subs = sorted(subjects, key=lambda x: stress_stats.get(x['subject_name'].lower(), 0), reverse=True)

    for sub in sorted_subs:
        periods_to_fill = slots_needed[sub['id']]
        fac_list = subject_faculty_map.get(sub['id'], [])
        if not fac_list:
            # Fallback: assign subject without faculty if none registered
            assigned_fac = "TBD"
        else:
            assigned_fac = fac_list[0]['full_name']

        # Determine if subject is highly stressful (exists in stress list)
        is_stressful = stress_stats.get(sub['subject_name'].lower(), 0) > 0

        # Try to schedule the periods
        scheduled_count = 0
        
        # We attempt to space out: place at most 1 session of this subject per day
        for day in days:
            if scheduled_count >= periods_to_fill:
                break
            
            # Determine preferred periods based on stress level
            # Stressful subjects prefer periods 1, 2, 3 (morning)
            if is_stressful:
                periods_pool = ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7']
            else:
                # Easiest subjects/labs prefer afternoon periods (4, 5, 6, 7)
                periods_pool = ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']

            for period in periods_pool:
                # Check if slot is FREE
                if schedule[day][period] == 'FREE':
                    # Check if the faculty is busy teaching in another department at this day/period
                    if assigned_fac != "TBD" and is_faculty_busy(assigned_fac, day, period):
                        continue # Skip to avoid clash
                    
                    schedule[day][period] = f"{sub['subject_name']} ({assigned_fac})"
                    scheduled_count += 1
                    break # Go to next day

        # If we couldn't space it out completely (e.g. required 5 periods but couldn't fit due to clashes), 
        # allow scheduling more than 1 per day as fallback
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

    # Save to database (timetable table)
    save_conn = get_db_connection()
    save_cursor = save_conn.cursor()
    # Delete old draft/published schedule for this configuration
    save_cursor.execute(
        "DELETE FROM timetable WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s",
        (college_id, branch, year_level, semester)
    )
    
    # Insert new rows
    for day in days:
        query = """INSERT INTO timetable 
                   (college_id, branch, year_level, semester, day_name, period1, period2, period3, period4, period5, period6, period7, published)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
        save_cursor.execute(query, (
            college_id, branch, year_level, semester, day,
            schedule[day]['period1'], schedule[day]['period2'], schedule[day]['period3'],
            schedule[day]['period4'], schedule[day]['period5'], schedule[day]['period6'], schedule[day]['period7']
        ))
    save_conn.commit()
    save_cursor.close()
    save_conn.close()

    session['gen_success'] = f"AI Schedule Generated successfully for {branch} (Draft)!"
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
        day_of_week = absent_date.strftime('%A') # e.g. "Monday"

        # Fetch details of the absent faculty
        cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
        absent_faculty = cursor.fetchone()

        # Fetch all other faculty members in this college
        cursor.execute("SELECT * FROM faculty WHERE id != %s AND college_id = %s", (faculty_id, college_id))
        other_faculties = cursor.fetchall()

        # Step 1: Find all class sessions where this faculty member is scheduled on that day of the week
        cursor.execute("SELECT * FROM timetable WHERE college_id = %s", (college_id,))
        timetables = cursor.fetchall()

        updated_swaps = 0
        
        # Loop through periods to substitute
        for p_idx in range(start_period, end_period + 1):
            period_col = f'period{p_idx}'
            
            for t_row in timetables:
                if t_row['day_name'] == day_of_week:
                    current_session = t_row[period_col]
                    
                    # If this absent faculty is teaching this session
                    if current_session and absent_faculty['full_name'] in current_session:
                        # Extract the subject name
                        subj_part = current_session.split(" (")[0]
                        
                        # AI Replacement Strategy:
                        # Find a faculty member who teaches the same subject/department, is FREE at this day/period,
                        # and has NOT requested absence for that date.
                        substitute_found = False
                        
                        # Sort alternative teachers by teaching experience (highest first)
                        potential_substitutes = [f for f in other_faculties if absent_faculty['subject_name'].lower() in f['subject_name'].lower() or absent_faculty['department'].lower() in f['department'].lower()]
                        potential_substitutes.sort(key=lambda x: x['experience_years'], reverse=True)

                        for alt_fac in potential_substitutes:
                            # Verify if alt_fac has submitted an absence request on this date covering this period
                            chk_conn = get_db_connection()
                            chk_cursor = chk_conn.cursor()
                            chk_cursor.execute(
                                """SELECT COUNT(*) FROM absence_requests 
                                   WHERE faculty_id = %s AND absent_date = %s AND %s BETWEEN start_period AND end_period""",
                                (alt_fac['id'], absent_date_str, p_idx)
                            )
                            is_absent = chk_cursor.fetchone()[0] > 0
                            
                            # Verify if alt_fac is busy teaching another class at this specific day/period
                            query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {period_col} LIKE %s"
                            chk_cursor.execute(query, (college_id, day_of_week, f"%{alt_fac['full_name']}%"))
                            is_busy = chk_cursor.fetchone()[0] > 0
                            
                            chk_cursor.close()
                            chk_conn.close()

                            if not is_absent and not is_busy:
                                # Found valid substitute! Swap them in the timetable
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
                                break # Substitute found for this class, move to next timetable row

                        # Dynamic Swap Strategy (Fallback):
                        # If no alternate teacher is free, swap this period with a 'FREE' slot in the weekly schedule
                        # where the absent faculty (or an alternate) teaches, moving it to another day.
                        if not substitute_found:
                            # Let's search the same timetable for a FREE slot on a different day
                            search_conn = get_db_connection()
                            search_cursor = search_conn.cursor(dictionary=True)
                            search_cursor.execute(
                                "SELECT * FROM timetable WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s",
                                (college_id, t_row['branch'], t_row['year_level'], t_row['semester'])
                            )
                            branch_rows = search_cursor.fetchall()
                            search_cursor.close()
                            search_conn.close()
                            
                            swap_done = False
                            for br_row in branch_rows:
                                if swap_done:
                                    break
                                for p_num in range(1, 8):
                                    test_col = f'period{p_num}'
                                    # If that slot is FREE
                                    if br_row[test_col] == 'FREE':
                                        # Swap: Monday Period 2 becomes FREE, and (Tuesday Period 4) becomes the class
                                        update_conn = get_db_connection()
                                        update_cursor = update_conn.cursor()
                                        
                                        # Move class to the free slot
                                        update_cursor.execute(
                                            f"UPDATE timetable SET {test_col} = %s WHERE id = %s",
                                            (current_session, br_row['id'])
                                        )
                                        # Clear the current slot
                                        update_cursor.execute(
                                            f"UPDATE timetable SET {period_col} = 'FREE' WHERE id = %s",
                                            (t_row['id'],)
                                        )
                                        update_conn.commit()
                                        update_cursor.close()
                                        update_conn.close()
                                        
                                        swap_done = True
                                        updated_swaps += 1
                                        break
        
        # Save request to absence_requests table
        status_text = 'Swapped' if updated_swaps > 0 else 'Declined'
        cursor.execute(
            "INSERT INTO absence_requests (faculty_id, college_id, absent_date, start_period, end_period, status) VALUES (%s, %s, %s, %s, %s, %s)",
            (faculty_id, college_id, absent_date_str, start_period, end_period, status_text)
        )
        conn.commit()
        
        if updated_swaps > 0:
            success_msg = f"Absence processed successfully! AI substituted or rescheduled {updated_swaps} classes."
        else:
            success_msg = None
            error_msg = "Absence submitted. However, no alternate faculty or free slots were available to swap."

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