import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, url_for, abort
import mysql.connector
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from dotenv import load_dotenv
load_dotenv()  # This loads variables from .env file

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "AI_Scheduling_Super_Key_2026")

app.config.update(
    SESSION_COOKIE_SECURE=False,     # True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

UPLOAD_FOLDER = os.path.join('static', 'images', 'colleges')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.secret_key = os.environ.get("SECRET_KEY", "fallback-key-change-me")

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "timetable_db")
    )

# CSRF Protection Hook
@app.before_request
def csrf_protect():
    if request.method == "POST":
        # Allow disabling CSRF verification via environment variables for testing purposes
        if os.environ.get("DISABLE_CSRF") == "true":
            return
        token = session.get("_csrf_token")
        form_token = request.form.get("_csrf_token")
        if not token or token != form_token:
            abort(403, description="CSRF token missing or invalid")

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(16)
    return session["_csrf_token"]

app.jinja_env.globals["csrf_token"] = generate_csrf_token

@app.template_filter('time_to_str')
def time_to_str_filter(val):
    if not val:
        return "09:00"
    if isinstance(val, str):
        return val[:5]
    if hasattr(val, 'total_seconds'): # timedelta
        total_secs = int(val.total_seconds())
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        return f"{hours:02d}:{mins:02d}"
    if hasattr(val, 'strftime'): # time or datetime object
        return val.strftime("%H:%M")
    return str(val)

def get_timing_settings(college_id=None):
    if not college_id:
        college_id = session.get('college_id')
    
    defaults = {
        'start_time': '09:00:00',
        'period_duration': 60,
        'break_after_period': 3,
        'break_duration': 60
    }
    
    if college_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM timetable_settings WHERE college_id = %s", (college_id,))
            settings = cursor.fetchone()
            cursor.close()
            conn.close()
            if settings:
                return settings
        except Exception as e:
            print(f"Error fetching timetable settings: {e}")
            
    return defaults

def get_period_labels(college_id=None):
    settings = get_timing_settings(college_id)
    start_time_val = settings.get('start_time', '09:00:00')
    period_duration = settings.get('period_duration', 60)
    break_after_period = settings.get('break_after_period', 3)
    break_duration = settings.get('break_duration', 60)

    start_time_str = "09:00:00"
    if isinstance(start_time_val, str):
        start_time_str = start_time_val
    elif hasattr(start_time_val, 'total_seconds'):
        total_secs = int(start_time_val.total_seconds())
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        start_time_str = f"{hours:02d}:{mins:02d}:00"
    elif hasattr(start_time_val, 'strftime'):
        start_time_str = start_time_val.strftime("%H:%M:%S")

    from datetime import datetime, timedelta
    try:
        current_time = datetime.strptime(start_time_str, "%H:%M:%S")
    except ValueError:
        try:
            current_time = datetime.strptime(start_time_str, "%H:%M")
        except ValueError:
            current_time = datetime.strptime("09:00:00", "%H:%M:%S")

    labels = []
    for i in range(1, 8):
        start_label = current_time.strftime("%I:%M %p")
        end_time = current_time + timedelta(minutes=period_duration)
        end_label = end_time.strftime("%I:%M %p")
        labels.append(f"{start_label} - {end_label}")
        
        current_time = end_time
        if i == break_after_period:
            current_time += timedelta(minutes=break_duration)
            
    return labels

# Context processor to make "request" and "session" available in templates
@app.context_processor
def inject_context():
    college_id = session.get('college_id')
    return dict(
        session=session,
        timing_settings=get_timing_settings(college_id),
        period_labels=get_period_labels(college_id)
    )

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
    cursor.execute("SELECT id, college_name, photo_path FROM colleges ORDER BY college_name")
    colleges = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', colleges=colleges)

@app.route('/colleges_list')
def colleges_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, college_name, college_code, photo_path FROM colleges ORDER BY college_name")
    colleges = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('colleges_list.html', colleges=colleges)

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
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            return render_template('developer_register.html', error="All fields are required.")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO developers (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_password)
            )
            conn.commit()
            return redirect(url_for('developer_dashboard'))
        except mysql.connector.Error as err:
            return render_template('developer_register.html', error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('developer_register.html')

@app.route('/developer_login', methods=['GET', 'POST'])
def developer_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('developer_login.html', error="Username and password are required.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM developers WHERE username = %s", (username,))
        dev = cursor.fetchone()
        cursor.close()
        conn.close()

        if dev and check_password_hash(dev['password'], password):
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

@app.route('/developer_delete_college/<int:college_id>', methods=['POST'])
def developer_delete_college(college_id):
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM colleges WHERE id = %s", (college_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error deleting college: {err.msg}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('developer_dashboard'))

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
    if not session.get('developer_logged_in'):
        return redirect(url_for('developer_login'))

    if request.method == 'POST':
        college_name = request.form.get('college_name', '').strip()
        college_code = request.form.get('college_code', '').upper().strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not college_name or not college_code or not email or not password:
            return render_template('college_register.html', error="All fields are required.")

        hashed_password = generate_password_hash(password)
        photo_path = None
        if 'college_photo' in request.files:
            file = request.files['college_photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Prefix with timestamp to avoid duplicates
                unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(save_path)
                # Store the relative path for easy URL access
                photo_path = f"images/colleges/{unique_filename}"

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO colleges (college_name, college_code, email, password, photo_path) VALUES (%s, %s, %s, %s, %s)",
                (college_name, college_code, email, hashed_password, photo_path)
            )
            conn.commit()
            return redirect(url_for('developer_dashboard'))
        except mysql.connector.Error as err:
            return render_template('college_register.html', error=f"Registration failed: {err.msg}")
        finally:
            cursor.close()
            conn.close()

    return render_template('college_register.html')

@app.route('/college_login', methods=['GET', 'POST'])
def college_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            return render_template('college_login.html', error="Email and password are required.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM colleges WHERE email = %s", (email,))
        college = cursor.fetchone()
        cursor.close()
        conn.close()

        if college and check_password_hash(college['password'], password):
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

    # Fetch all distinct departments/branches
    cursor.execute("""
        SELECT DISTINCT branch FROM (
            SELECT branch FROM students WHERE college_id = %s
            UNION
            SELECT department AS branch FROM faculty WHERE college_id = %s
            UNION
            SELECT branch FROM admin WHERE college_id = %s
            UNION
            SELECT branch FROM subjects WHERE college_id = %s
            UNION
            SELECT branch FROM sections WHERE college_id = %s
        ) t WHERE branch IS NOT NULL AND branch != ''
    """, (college_id, college_id, college_id, college_id, college_id))
    branches = [row['branch'] for row in cursor.fetchall()]

    selected_branch = request.args.get('branch', '').strip().upper()
    selected_section = request.args.get('section', '').strip().upper()

    sections = []
    admins = []
    faculties = []
    subjects = []
    timetable = []
    stress_data = []
    student_count = 0

    if selected_branch:
        # Get sections of this department
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND branch = %s ORDER BY year_level, section_name", (college_id, selected_branch))
        sections = cursor.fetchall()

        # Get department faculties
        cursor.execute("SELECT * FROM faculty WHERE college_id = %s AND department = %s ORDER BY full_name", (college_id, selected_branch))
        faculties = cursor.fetchall()

        # Get local department admins
        cursor.execute("SELECT * FROM admin WHERE college_id = %s AND branch = %s", (college_id, selected_branch))
        admins = cursor.fetchall()

        if selected_section:
            # Count students in this section
            cursor.execute("SELECT COUNT(*) as count FROM students WHERE college_id = %s AND branch = %s AND section_name = %s", (college_id, selected_branch, selected_section))
            student_count = cursor.fetchone()['count']

            # Get subjects of this section
            cursor.execute("SELECT * FROM subjects WHERE college_id = %s AND branch = %s AND section_name = %s ORDER BY subject_code", (college_id, selected_branch, selected_section))
            subjects = cursor.fetchall()

            # Get published timetable for this section
            cursor.execute("SELECT * FROM timetable WHERE college_id = %s AND branch = %s AND section_name = %s AND published = 1 ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')", (college_id, selected_branch, selected_section))
            timetable = cursor.fetchall()

            # Get stress data
            cursor.execute(
                """SELECT s.full_name, sf.* FROM stress_forms sf 
                   JOIN students s ON sf.student_id = s.id 
                   WHERE s.college_id = %s AND s.branch = %s AND s.section_name = %s""",
                (college_id, selected_branch, selected_section)
            )
            stress_data = cursor.fetchall()

    cursor.close()
    conn.close()

    selected_tab = request.args.get('tab', 'overview').strip().lower()

    return render_template(
        'college_dashboard.html',
        college=college,
        branches=branches,
        selected_branch=selected_branch,
        selected_section=selected_section,
        selected_tab=selected_tab,
        sections=sections,
        admins=admins,
        faculties=faculties,
        subjects=subjects,
        timetable=timetable,
        stress_data=stress_data,
        student_count=student_count
    )

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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        branch = request.form.get('branch', '').upper().strip()
        col_id = request.form.get('college_id', '')

        if not username or not password or not branch or not col_id:
            return render_template('admin_register.html', college=college, error="All fields are required.")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO admin (college_id, username, password, college_name, branch) VALUES (%s, %s, %s, %s, %s)",
                (col_id, username, hashed_password, college['college_name'], branch)
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        col_id = request.form.get('college_id', '')

        if not username or not password or not col_id:
            return render_template('admin_login.html', college=college, error="All fields are required.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username = %s AND college_id = %s", (username, col_id))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin and check_password_hash(admin['password'], password):
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
        subject_code = request.form.get('subject_code', '').strip().upper()
        subject_name = request.form.get('subject_name', '').strip()
        # Lock branch to local admin branch if logged in
        branch = admin_branch if admin_branch else request.form.get('branch', '').strip().upper()
        
        try:
            year_level = int(request.form.get('year_level', '1'))
            semester = int(request.form.get('semester', '1'))
            periods_per_week = int(request.form.get('periods_per_week', '3'))
        except ValueError:
            # We will show error message when rendering the template
            error_msg = "Year level, Semester, and Periods per week must be valid numbers."
            
        section_name = request.form.get('section_name', '').strip().upper()

        if 'error_msg' not in locals():
            if not subject_code or not subject_name or not branch or not section_name:
                error_msg = "All fields are required."
            else:
                try:
                    cursor.execute(
                        """INSERT INTO subjects (college_id, subject_code, subject_name, branch, year_level, semester, section_name, periods_per_week) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (college_id, subject_code, subject_name, branch, year_level, semester, section_name, periods_per_week)
                    )
                    conn.commit()
                    success_msg = "Subject added successfully!"
                except mysql.connector.Error as err:
                    error_msg = f"Database Error: {err.msg}"
            
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Fetch sections for dropdown selection
    if admin_branch:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s AND branch = %s ORDER BY year_level, section_name", (college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM sections WHERE college_id = %s ORDER BY branch, year_level, section_name", (college_id,))
    sections = cursor.fetchall()

    # Filter subjects if local admin
    if admin_branch:
        cursor.execute("SELECT * FROM subjects WHERE college_id = %s AND branch = %s ORDER BY year_level, semester, section_name, subject_code", (college_id, admin_branch))
    else:
        cursor.execute("SELECT * FROM subjects WHERE college_id = %s ORDER BY branch, year_level, semester, section_name, subject_code", (college_id,))
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    success = session.pop('gen_success', None) or locals().get('success_msg')
    error = session.pop('gen_error', None) or locals().get('error_msg')

    return render_template(
        'manage_subjects.html',
        college=college,
        admin_branch=admin_branch,
        sections=sections,
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

@app.route('/save_timing_settings', methods=['POST'])
def save_timing_settings():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))

    start_time = request.form.get('start_time', '09:00')
    period_duration = int(request.form.get('period_duration', '60'))
    break_after_period = int(request.form.get('break_after_period', '3'))
    break_duration = int(request.form.get('break_duration', '60'))

    if len(start_time) == 5:
        start_time_sql = f"{start_time}:00"
    else:
        start_time_sql = start_time

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO timetable_settings (college_id, start_time, period_duration, break_after_period, break_duration)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                start_time = VALUES(start_time),
                period_duration = VALUES(period_duration),
                break_after_period = VALUES(break_after_period),
                break_duration = VALUES(break_duration)
        """, (college_id, start_time_sql, period_duration, break_after_period, break_duration))
        conn.commit()
        session['gen_success'] = "Timing configuration updated successfully!"
    except mysql.connector.Error as err:
        session['gen_error'] = f"Failed to save timing settings: {err.msg}"
    finally:
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
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        branch = request.form.get('branch', '').upper().strip()
        
        try:
            year_level = int(request.form.get('year_level', '1'))
            semester = int(request.form.get('semester', '1'))
            col_id = int(request.form.get('college_id', '0'))
        except ValueError:
            return render_template('student_register.html', college=college, sections=sections, error="Invalid numeric values supplied.")

        section_name = request.form.get('section_name', '').upper().strip()
        roll_no = request.form.get('roll_no', '').upper().strip()

        if not full_name or not email or not password or not phone or not branch or not section_name or not roll_no or not col_id:
            return render_template('student_register.html', college=college, sections=sections, error="All fields are required.")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO students (college_id, full_name, email, password, branch, year_level, semester, section_name, roll_no, phone)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (col_id, full_name, email, hashed_password, branch, year_level, semester, section_name, roll_no, phone)
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
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        try:
            col_id = int(request.form.get('college_id', '0'))
        except ValueError:
            return render_template('student_login.html', college=college, error="Invalid College ID.")

        if not email or not password or not col_id:
            return render_template('student_login.html', college=college, error="Email and password are required.")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE email = %s AND college_id = %s", (email, col_id))
        student = cursor.fetchone()
        cursor.close()
        conn.close()

        if student and check_password_hash(student['password'], password):
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
        sleep_hours = request.form.get('sleep_hours', '').strip()
        feel_fresh = request.form.get('feel_fresh', '').strip()
        physically_tired = request.form.get('physically_tired', '').strip()
        headache_fatigue = request.form.get('headache_fatigue', '').strip()
        
        try:
            health_rating = int(request.form.get('health_rating', '5'))
            regular_day_stress = int(request.form.get('regular_day_stress', '5'))
            exam_stress = int(request.form.get('exam_stress', '5'))
        except ValueError:
            health_rating = 5
            regular_day_stress = 5
            exam_stress = 5

        daily_study_hours = request.form.get('daily_study_hours', '').strip()
        most_stress_subject = request.form.get('most_stress_subject', '').strip()
        easiest_subject = request.form.get('easiest_subject', '').strip()
        preferred_morning_subject = request.form.get('preferred_morning_subject', '').strip()
        preferred_afternoon_subject = request.form.get('preferred_afternoon_subject', '').strip()
        best_study_time = request.form.get('best_study_time', '').strip()
        need_more_breaks = request.form.get('need_more_breaks', '').strip()
        scheduling_suggestions = request.form.get('scheduling_suggestions', '').strip()
        stress_comments = request.form.get('stress_comments', '').strip()

        # Compute stress score: Higher score means more stressed
        # scale: health_rating (1-10, lower health is more stressed, max (10-1)*5 = 45)
        # regular_day_stress (1-10, max 50)
        # exam_stress (1-10, max 50)
        stress_score = (10 - health_rating) * 5 + regular_day_stress * 5 + exam_stress * 5
        if physically_tired == 'Yes':
            stress_score += 10
        if headache_fatigue == 'Yes':
            stress_score += 10
        if feel_fresh == 'No':
            stress_score += 10

        cursor.execute("DELETE FROM stress_forms WHERE student_id = %s", (student_id,))
        cursor.execute(
            """INSERT INTO stress_forms (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating,
                                        regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject,
                                        preferred_morning_subject, preferred_afternoon_subject, best_study_time, need_more_breaks,
                                        scheduling_suggestions, stress_comments, stress_score)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating,
             regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject,
             preferred_morning_subject, preferred_afternoon_subject, best_study_time, need_more_breaks,
             scheduling_suggestions, stress_comments, stress_score)
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
        employee_id = request.form.get('employee_id', '').upper().strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').upper().strip()
        subject_name = request.form.get('subject_name', '').strip()
        
        try:
            col_id = int(request.form.get('college_id', '0'))
        except ValueError:
            return render_template('faculty_register.html', college=college, error="Invalid College ID.")

        if not employee_id or not full_name or not email or not password or not phone or not department or not subject_name or not col_id:
            return render_template('faculty_register.html', college=college, error="All fields are required.")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO faculty (college_id, employee_id, full_name, email, password, phone, department, subject_name)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (col_id, employee_id, full_name, email, hashed_password, phone, department, subject_name)
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
        login_type = request.form.get('login_type', 'otp')
        
        try:
            col_id = int(request.form.get('college_id', '0'))
        except ValueError:
            return render_template('faculty_login.html', college=college, error="Invalid College ID.")

        if login_type == 'otp':
            phone = request.form.get('phone', '').strip()
            if not phone:
                return render_template('faculty_login.html', college=college, error="Phone number is required.")
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
        
        elif login_type == 'password':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

            if not email or not password:
                return render_template('faculty_login.html', college=college, error="Email and password are required.")

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty WHERE email = %s AND college_id = %s", (email, col_id))
            faculty = cursor.fetchone()
            cursor.close()
            conn.close()

            if faculty and check_password_hash(faculty['password'], password):
                session['faculty_id'] = faculty['id']
                session['faculty_name'] = faculty['full_name']
                session['college_id'] = col_id
                return redirect(url_for('faculty_dashboard'))
            else:
                return render_template('faculty_login.html', college=college, error="Invalid email or password.")

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

    # Lock branch/department to faculty's own department
    selected_branch = faculty['department']

    selected_section = request.args.get('section_name', '')
    try:
        selected_year = int(request.args.get('year_level', '1'))
    except ValueError:
        selected_year = 1

    valid_sem_a = (selected_year - 1) * 2 + 1
    valid_sem_b = (selected_year - 1) * 2 + 2

    selected_semester_str = request.args.get('semester', '')
    try:
        selected_semester = int(selected_semester_str)
        if selected_semester not in (valid_sem_a, valid_sem_b):
            selected_semester = valid_sem_a
    except ValueError:
        selected_semester = valid_sem_a

    # Get sections for this branch and year level
    cursor.execute(
        "SELECT * FROM sections WHERE college_id = %s AND branch = %s AND year_level = %s ORDER BY section_name",
        (college_id, selected_branch, selected_year)
    )
    sections = cursor.fetchall()

    # Fallback to first available section if none is selected
    if not selected_section and sections:
        selected_section = sections[0]['section_name']
    elif not selected_section:
        selected_section = 'A'

    # Get published timetable for the selected branch, year, semester, section
    cursor.execute(
        """SELECT * FROM timetable 
           WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s AND published = 1
           ORDER BY FIELD(day_name, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')""",
        (college_id, selected_branch, selected_section, selected_year, selected_semester)
    )
    timetable = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'faculty_view_timetable.html',
        faculty=faculty,
        college=college,
        timetable=timetable,
        sections=sections,
        selected_branch=selected_branch,
        selected_section=selected_section,
        selected_year=selected_year,
        selected_semester=selected_semester
    )


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
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    if admin_branch:
        cursor.execute(
            """SELECT f.* FROM feedback f 
               JOIN students s ON f.student_id = s.id 
               WHERE s.college_id = %s AND s.branch = %s ORDER BY f.id DESC""", (college_id, admin_branch)
        )
    else:
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
    try:
        selected_year = int(request.args.get('year_level', '1'))
    except ValueError:
        selected_year = 1
    
    valid_sem_a = (selected_year - 1) * 2 + 1
    valid_sem_b = (selected_year - 1) * 2 + 2
    
    selected_semester_str = request.args.get('semester', '')
    try:
        selected_semester = int(selected_semester_str)
        if selected_semester not in (valid_sem_a, valid_sem_b):
            selected_semester = valid_sem_a
    except ValueError:
        selected_semester = valid_sem_a

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

    # Fetch distinct branches and sections for filter selects
    cursor.execute("SELECT DISTINCT branch FROM sections WHERE college_id = %s ORDER BY branch", (college_id,))
    branches_rows = cursor.fetchall()
    branches = [b['branch'] for b in branches_rows]

    cursor.execute("SELECT DISTINCT section_name FROM sections WHERE college_id = %s ORDER BY section_name", (college_id,))
    sections_rows = cursor.fetchall()
    sections = [s['section_name'] for s in sections_rows]

    selected_branch = request.args.get('branch')
    if admin_branch:
        selected_branch = admin_branch
    
    selected_year = request.args.get('year_level')
    if selected_year:
        selected_year = int(selected_year)
        
    selected_semester = request.args.get('semester')
    if selected_semester:
        selected_semester = int(selected_semester)
        
    selected_section = request.args.get('section_name')

    # Build dynamic WHERE clause based on filters
    where_parts = ["s.college_id = %s"]
    params = [college_id]

    if selected_branch:
        where_parts.append("s.branch = %s")
        params.append(selected_branch)
    if selected_year:
        where_parts.append("s.year_level = %s")
        params.append(selected_year)
    if selected_semester:
        where_parts.append("s.semester = %s")
        params.append(selected_semester)
    if selected_section:
        where_parts.append("s.section_name = %s")
        params.append(selected_section)

    where_clause = "WHERE " + " AND ".join(where_parts)
    params = tuple(params)

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
        fresh_sleep=fresh_sleep,
        branches=branches,
        sections=sections,
        selected_branch=selected_branch,
        selected_year=selected_year,
        selected_semester=selected_semester,
        selected_section=selected_section
    )

# ----------------- VENUE MANAGEMENT -----------------

@app.route('/manage_venues', methods=['GET', 'POST'])
def manage_venues():
    college_id = session.get('college_id')
    admin_branch = session.get('admin_branch')
    if not college_id:
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    success_msg = None
    error_msg = None

    if request.method == 'POST':
        building_name  = request.form.get('building_name', '').strip()
        room_number    = request.form.get('room_number', '').strip()
        room_type      = request.form.get('room_type', '').strip()
        department     = admin_branch if admin_branch else request.form.get('department', '').strip()
        floor_number   = request.form.get('floor_number', '').strip()
        max_capacity   = request.form.get('max_capacity', '0').strip()
        room_status    = request.form.get('room_status', 'Available').strip()
        remarks        = request.form.get('remarks', '').strip()
        has_projector  = 1 if request.form.get('has_projector') else 0
        has_ac         = 1 if request.form.get('has_ac') else 0
        has_smart_board = 1 if request.form.get('has_smart_board') else 0
        is_wifi_available = 1 if request.form.get('is_wifi_available') else 0

        if not building_name or not room_number or not room_type or not department or not floor_number or not max_capacity:
            error_msg = "All required fields must be filled."
        else:
            try:
                cursor.execute(
                    """INSERT INTO venues
                       (college_id, building_name, room_number, room_type, department, floor_number,
                        max_capacity, has_projector, has_ac, has_smart_board, is_wifi_available, room_status, remarks)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (college_id, building_name, room_number, room_type, department, floor_number,
                     int(max_capacity), has_projector, has_ac, has_smart_board, is_wifi_available,
                     room_status, remarks or None)
                )
                conn.commit()
                success_msg = f"Classroom '{building_name} - {room_number}' added successfully!"
            except mysql.connector.Error as err:
                error_msg = f"Database Error: {err.msg}"

    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()

    # Fetch venues
    if admin_branch:
        cursor.execute(
            "SELECT * FROM venues WHERE college_id = %s AND (department = %s OR department = 'Common (Shared)') ORDER BY building_name, room_number",
            (college_id, admin_branch)
        )
    else:
        cursor.execute("SELECT * FROM venues WHERE college_id = %s ORDER BY building_name, room_number", (college_id,))
    venues = cursor.fetchall()

    # Fetch subjects for assignment dropdown (filtered by admin branch)
    if admin_branch:
        cursor.execute(
            """SELECT s.*, v.building_name, v.room_number
               FROM subjects s
               LEFT JOIN venues v ON s.venue_id = v.id
               WHERE s.college_id = %s AND s.branch = %s
               ORDER BY s.year_level, s.semester, s.section_name, s.subject_name""",
            (college_id, admin_branch)
        )
    else:
        cursor.execute(
            """SELECT s.*, v.building_name, v.room_number
               FROM subjects s
               LEFT JOIN venues v ON s.venue_id = v.id
               WHERE s.college_id = %s
               ORDER BY s.branch, s.year_level, s.semester, s.section_name, s.subject_name""",
            (college_id,)
        )
    subjects = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'manage_venues.html',
        college=college,
        admin_branch=admin_branch,
        venues=venues,
        subjects=subjects,
        success=success_msg,
        error=error_msg
    )


@app.route('/delete_venue/<int:venue_id>', methods=['POST'])
def delete_venue(venue_id):
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor()
    # Unassign subjects using this venue first
    cursor.execute("UPDATE subjects SET venue_id = NULL WHERE venue_id = %s AND college_id = %s", (venue_id, college_id))
    cursor.execute("DELETE FROM venues WHERE id = %s AND college_id = %s", (venue_id, college_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('manage_venues'))


@app.route('/assign_venue_to_subject', methods=['POST'])
def assign_venue_to_subject():
    college_id = session.get('college_id')
    if not college_id:
        return redirect(url_for('home'))
    subject_id = request.form.get('subject_id', '').strip()
    venue_id   = request.form.get('venue_id', '').strip()
    # Allow unassigning (venue_id = '')
    venue_val = int(venue_id) if venue_id else None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE subjects SET venue_id = %s WHERE id = %s AND college_id = %s",
        (venue_val, subject_id, college_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('manage_venues'))


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

    # Fetch subjects with assigned venue (if any)
    cursor.execute(
        """SELECT s.*, v.room_number AS venue_room
           FROM subjects s
           LEFT JOIN venues v ON s.venue_id = v.id
           WHERE s.college_id = %s AND s.branch = %s AND s.year_level = %s AND s.semester = %s AND s.section_name = %s""",
        (college_id, branch, year_level, semester, section_name)
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

    # Fetch student stress factors and morning/afternoon preference votes
    cursor.execute(
        """SELECT sf.most_stress_subject, sf.preferred_morning_subject, sf.preferred_afternoon_subject, sf.best_study_time, COUNT(*) as count 
           FROM stress_forms sf 
           JOIN students s ON sf.student_id = s.id 
           WHERE s.college_id = %s AND s.branch = %s AND s.year_level = %s AND s.semester = %s AND s.section_name = %s
           GROUP BY sf.most_stress_subject, sf.preferred_morning_subject, sf.preferred_afternoon_subject, sf.best_study_time""",
        (college_id, branch, year_level, semester, section_name)
    )
    db_rows = cursor.fetchall()
    
    stress_stats = {}
    morning_prefs = {}
    afternoon_prefs = {}
    
    for row in db_rows:
        if row['most_stress_subject']:
            stress_stats[row['most_stress_subject'].lower()] = stress_stats.get(row['most_stress_subject'].lower(), 0) + row['count']
        if row['preferred_morning_subject']:
            morning_prefs[row['preferred_morning_subject'].lower()] = morning_prefs.get(row['preferred_morning_subject'].lower(), 0) + row['count']
        if row['preferred_afternoon_subject']:
            afternoon_prefs[row['preferred_afternoon_subject'].lower()] = afternoon_prefs.get(row['preferred_afternoon_subject'].lower(), 0) + row['count']

    cursor.close()

    # Sort faculties by matching priority and experience
    subject_faculty_map = {}
    for sub in subjects:
        matched_facs = []
        for f in faculties:
            # check if subject matches
            if sub['subject_name'].lower() in f['subject_name'].lower() or f['subject_name'].lower() in sub['subject_name'].lower():
                matched_facs.append((f, 2))
            elif sub['branch'].lower() in f['department'].lower() or f['department'].lower() in sub['branch'].lower():
                matched_facs.append((f, 1))
        
        # Sort by priority (highest first) then experience_years (highest first)
        matched_facs.sort(key=lambda x: (x[1], x[0].get('experience_years', 0)), reverse=True)
        subject_faculty_map[sub['id']] = [item[0] for item in matched_facs]

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slots_needed = {sub['id']: sub['periods_per_week'] for sub in subjects}
    schedule = {day: {f'period{p}': 'FREE' for p in range(1, 8)} for day in days}

    # Checks if faculty is busy in another branch/section at that day/period (ignoring current section being regenerated)
    def is_faculty_busy(fac_name, day, period):
        check_conn = get_db_connection()
        chk_cursor = check_conn.cursor()
        query = f"""SELECT {period} FROM timetable 
                    WHERE college_id = %s AND day_name = %s 
                    AND NOT (branch = %s AND section_name = %s AND year_level = %s AND semester = %s)"""
        chk_cursor.execute(query, (college_id, day, branch, section_name, year_level, semester))
        rows = chk_cursor.fetchall()
        chk_cursor.close()
        check_conn.close()
        for r in rows:
            if r[0] and fac_name in r[0]:
                return True
        return False

    # Sort subjects by stress level (most stressful first)
    sorted_subs = sorted(subjects, key=lambda x: stress_stats.get(x['subject_name'].lower(), 0), reverse=True)

    for sub in sorted_subs:
        periods_to_fill = slots_needed[sub['id']]
        fac_list = subject_faculty_map.get(sub['id'], [])
        assigned_fac = fac_list[0]['full_name'] if fac_list else "TBD"

        is_stressful = stress_stats.get(sub['subject_name'].lower(), 0) > 0
        student_pref_morning = morning_prefs.get(sub['subject_name'].lower(), 0) > afternoon_prefs.get(sub['subject_name'].lower(), 0)
        student_pref_afternoon = afternoon_prefs.get(sub['subject_name'].lower(), 0) > morning_prefs.get(sub['subject_name'].lower(), 0)

        fac_pref_morning = False
        fac_pref_afternoon = False

        if fac_list:
            fac_obj = fac_list[0]
            if fac_obj.get('preferred_morning_subject') and fac_obj['preferred_morning_subject'].lower() in sub['subject_name'].lower():
                fac_pref_morning = True
            if fac_obj.get('preferred_afternoon_subject') and fac_obj['preferred_afternoon_subject'].lower() in sub['subject_name'].lower():
                fac_pref_afternoon = True

        scheduled_count = 0
        
        for day in days:
            if scheduled_count >= periods_to_fill:
                break
            
            # Period placement: stressful or morning preference -> morning slots; afternoon preference -> afternoon slots
            if fac_pref_morning or is_stressful or student_pref_morning:
                periods_pool = ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7']
            elif fac_pref_afternoon or student_pref_afternoon:
                periods_pool = ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']
            else:
                periods_pool = ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']

            for period in periods_pool:
                # Prevent scheduling the same subject twice on the same day if possible
                day_already_has_subject = any(sub['subject_name'] in schedule[day][p] for p in schedule[day] if schedule[day][p] != 'FREE')
                if day_already_has_subject:
                    break # Try next day

                if schedule[day][period] == 'FREE':
                    if assigned_fac != "TBD" and is_faculty_busy(assigned_fac, day, period):
                        continue
                    venue_label = f" @ {sub['venue_room']}" if sub.get('venue_room') else ""
                    schedule[day][period] = f"{sub['subject_name']} ({assigned_fac}){venue_label}"
                    scheduled_count += 1
                    break

        # Fallback if slots not filled (relax duplicate day restriction)
        if scheduled_count < periods_to_fill:
            for day in days:
                if scheduled_count >= periods_to_fill:
                    break
                for period in ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7']:
                    if schedule[day][period] == 'FREE':
                        if assigned_fac != "TBD" and is_faculty_busy(assigned_fac, day, period):
                            continue
                        venue_label = f" @ {sub['venue_room']}" if sub.get('venue_room') else ""
                        schedule[day][period] = f"{sub['subject_name']} ({assigned_fac}){venue_label}"
                        scheduled_count += 1
                        if scheduled_count >= periods_to_fill:
                            break

    total_needed = sum(sub['periods_per_week'] for sub in subjects)
    total_available = len(days) * 7
    warnings = []
    if total_needed > total_available:
        warnings.append(f"Warning: Need {total_needed} slots but only {total_available} are available. Reduce periods_per_week on subjects.")
        
    for sub in subjects:
        filled = sum(1 for d in days for p in range(1, 8) if sub['subject_name'] in schedule[d][f'period{p}'])
        if filled < sub['periods_per_week']:
            warnings.append(f"Warning: {sub['subject_name']} only scheduled for {filled}/{sub['periods_per_week']} required slots!")

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

    if warnings:
        session['gen_success'] = f"AI Schedule Generated for {branch} Section {section_name} (Draft) with warnings: " + " | ".join(warnings)
    else:
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
        absent_date_str = request.form.get('absent_date', '').strip()
        
        try:
            start_period = int(request.form.get('start_period', '1'))
            end_period = int(request.form.get('end_period', '1'))
        except ValueError:
            # Fetch common data to render error properly
            cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
            faculty = cursor.fetchone()
            cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
            college = cursor.fetchone()
            cursor.execute("""
                SELECT ar.*, f.full_name FROM absence_requests ar 
                JOIN faculty f ON ar.faculty_id = f.id 
                WHERE ar.faculty_id = %s ORDER BY ar.id DESC""", (faculty_id,))
            my_requests = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('absence_request.html', college=college, faculty=faculty, my_requests=my_requests, error="Periods must be integers")
        
        try:
            absent_date = datetime.strptime(absent_date_str, "%Y-%m-%d")
        except ValueError:
            cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
            faculty = cursor.fetchone()
            cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
            college = cursor.fetchone()
            cursor.execute("""
                SELECT ar.*, f.full_name FROM absence_requests ar 
                JOIN faculty f ON ar.faculty_id = f.id 
                WHERE ar.faculty_id = %s ORDER BY ar.id DESC""", (faculty_id,))
            my_requests = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('absence_request.html', college=college, faculty=faculty, my_requests=my_requests, error="Invalid date format. Use YYYY-MM-DD")

        day_of_week = absent_date.strftime('%A')

        cursor.execute("SELECT * FROM faculty WHERE id = %s", (faculty_id,))
        absent_faculty = cursor.fetchone()

        cursor.execute("SELECT * FROM faculty WHERE id != %s AND college_id = %s", (faculty_id, college_id))
        other_faculties = cursor.fetchall()

        cursor.execute("SELECT * FROM timetable WHERE college_id = %s AND published = 1", (college_id,))
        timetables = cursor.fetchall()

        updated_swaps = 0
        
        for p_idx in range(start_period, end_period + 1):
            period_col = f'period{p_idx}'
            
            for t_row in timetables:
                if t_row['day_name'] == day_of_week:
                    current_session = t_row[period_col]
                    
                    if current_session and absent_faculty['full_name'] in current_session:
                        subj_part = current_session.split(" (")[0]
                        
                        # Filter faculties in same department
                        dept_facs = [f for f in other_faculties if absent_faculty['department'].lower() in f['department'].lower()]
                        
                        # Find which of these same-department faculties are actually free right now
                        free_substitutes = []
                        for alt_fac in dept_facs:
                            chk_conn = get_db_connection()
                            chk_cursor = chk_conn.cursor()
                            # Check if alt_fac is on leave
                            chk_cursor.execute(
                                """SELECT COUNT(*) FROM absence_requests 
                                   WHERE faculty_id = %s AND absent_date = %s AND %s BETWEEN start_period AND end_period AND status != 'Declined'""",
                                (alt_fac['id'], absent_date_str, p_idx)
                            )
                            is_absent = chk_cursor.fetchone()[0] > 0
                            
                            # Check if alt_fac is teaching in any section in published timetable at this slot
                            query = f"SELECT COUNT(*) FROM timetable WHERE college_id = %s AND day_name = %s AND {period_col} LIKE %s AND published = 1"
                            chk_cursor.execute(query, (college_id, day_of_week, f"%{alt_fac['full_name']}%"))
                            is_busy = chk_cursor.fetchone()[0] > 0
                            
                            chk_cursor.close()
                            chk_conn.close()
                            
                            if not is_absent and not is_busy:
                                free_substitutes.append(alt_fac)
                        
                        if free_substitutes:
                            # Divide into same subject and other subjects
                            same_subject_facs = []
                            other_subject_facs = []
                            
                            for f in free_substitutes:
                                if absent_faculty['subject_name'].lower() in f['subject_name'].lower() or f['subject_name'].lower() in absent_faculty['subject_name'].lower():
                                    same_subject_facs.append(f)
                                else:
                                    other_subject_facs.append(f)
                            
                            # Sort both groups by experience
                            same_subject_facs.sort(key=lambda x: x.get('experience_years', 0), reverse=True)
                            other_subject_facs.sort(key=lambda x: x.get('experience_years', 0), reverse=True)
                            
                            substitute = None
                            if same_subject_facs:
                                substitute = same_subject_facs[0]
                            elif other_subject_facs:
                                substitute = other_subject_facs[0]
                                
                            if substitute:
                                new_session_text = f"{subj_part} ({substitute['full_name']})"
                                update_conn = get_db_connection()
                                update_cursor = update_conn.cursor()
                                update_cursor.execute(
                                    f"UPDATE timetable SET {period_col} = %s WHERE id = %s",
                                    (new_session_text, t_row['id'])
                                )
                                update_conn.commit()
                                update_cursor.close()
                                update_conn.close()
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