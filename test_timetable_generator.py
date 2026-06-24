import mysql.connector
import sys

# Database connection credentials from app.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '@Faheem7950',
    'database': 'timetable_db'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def setup_test_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    print("--- 1. Cleaning up previous test data for test college 'TEST01' ---")
    # Delete college with code TEST01 which cascades to other tables
    cursor.execute("DELETE FROM colleges WHERE college_code = %s", ('TEST01',))
    conn.commit()

    print("--- 2. Creating Test College and Admin ---")
    cursor.execute(
        "INSERT INTO colleges (college_name, college_code, email, password) VALUES (%s, %s, %s, %s)",
        ("Test Engineering College", "TEST01", "admin@testcol.edu", "password123")
    )
    college_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO admin (college_id, username, password, college_name, branch) VALUES (%s, %s, %s, %s, %s)",
        (college_id, "test_cse_admin", "password123", "Test Engineering College", "CSE")
    )
    
    print("--- 3. Creating Sections (Section A and Section B) ---")
    # CSE, Year 3, Section A & B
    cursor.execute(
        "INSERT INTO sections (college_id, branch, year_level, section_name) VALUES (%s, %s, %s, %s)",
        (college_id, "CSE", 3, "A")
    )
    cursor.execute(
        "INSERT INTO sections (college_id, branch, year_level, section_name) VALUES (%s, %s, %s, %s)",
        (college_id, "CSE", 3, "B")
    )

    print("--- 4. Registering Faculty Members ---")
    # Let's register 4 teachers with different profiles
    faculties = [
        ("Dr. Alan Turing", "TUR01", "alan@testcol.edu", "CSE", "Theory of Computation", 15, "Theory of Computation", None),
        ("Dr. Grace Hopper", "HOP01", "grace@testcol.edu", "CSE", "Compiler Design", 12, None, "Compiler Design"),
        ("Prof. John von Neumann", "NEU01", "john@testcol.edu", "CSE", "Computer Architecture", 10, "Computer Architecture", None),
        ("Mrs. Ada Lovelace", "LOV01", "ada@testcol.edu", "CSE", "Python Programming", 5, "Python Programming", None),
        ("Mr. Richard Stallman", "STA01", "richard@testcol.edu", "CSE", "Open Source Systems", 4, None, None)
    ]
    
    faculty_ids = {}
    for f in faculties:
        cursor.execute(
            """INSERT INTO faculty 
               (college_id, employee_id, full_name, email, password, phone, department, subject_name, experience_years, preferred_morning_subject, preferred_afternoon_subject)
               VALUES (%s, %s, %s, %s, 'pass123', '1234567890', %s, %s, %s, %s, %s)""",
            (college_id, f[1], f[0], f[2], f[3], f[4], f[5], f[6], f[7])
        )
        faculty_ids[f[4]] = cursor.lastrowid

    print("--- 5. Creating Subjects for Section A and Section B ---")
    # Dynamic allocation: some subjects are common and some are specific, taught by the same or different faculty
    # Section A subjects
    subjects_data_a = [
        ("CS301", "Theory of Computation", "CSE", 3, 5, "A", 3),
        ("CS302", "Compiler Design", "CSE", 3, 5, "A", 3),
        ("CS303", "Computer Architecture", "CSE", 3, 5, "A", 3),
        ("CS304", "Python Programming", "CSE", 3, 5, "A", 3),
        ("CS305", "Open Source Systems", "CSE", 3, 5, "A", 2),
    ]
    
    # Section B subjects
    subjects_data_b = [
        ("CS301", "Theory of Computation", "CSE", 3, 5, "B", 3),
        ("CS302", "Compiler Design", "CSE", 3, 5, "B", 3),
        ("CS303", "Computer Architecture", "CSE", 3, 5, "B", 3),
        ("CS304", "Python Programming", "CSE", 3, 5, "B", 3),
        ("CS305", "Open Source Systems", "CSE", 3, 5, "B", 2),
    ]
    
    for sub in subjects_data_a + subjects_data_b:
        cursor.execute(
            """INSERT INTO subjects 
               (college_id, subject_code, subject_name, branch, year_level, semester, section_name, periods_per_week)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (college_id, sub[0], sub[1], sub[2], sub[3], sub[4], sub[5], sub[6])
        )

    print("--- 6. Creating Students & Stress Form Votes ---")
    # Section A student
    cursor.execute(
        """INSERT INTO students 
           (college_id, full_name, email, password, branch, year_level, semester, section_name, roll_no, phone)
           VALUES (%s, 'Alice A', 'alice@testcol.edu', 'pass', 'CSE', 3, 5, 'A', 'CSE-A-01', '111')""",
        (college_id,)
    )
    student_a_id = cursor.lastrowid

    # Section B student
    cursor.execute(
        """INSERT INTO students 
           (college_id, full_name, email, password, branch, year_level, semester, section_name, roll_no, phone)
           VALUES (%s, 'Bob B', 'bob@testcol.edu', 'pass', 'CSE', 3, 5, 'B', 'CSE-B-01', '222')""",
        (college_id,)
    )
    student_b_id = cursor.lastrowid

    # Let's seed stress forms
    # Alice votes Theory of Computation as highly stressful
    cursor.execute(
        """INSERT INTO stress_forms 
           (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating, regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject, stress_score)
           VALUES (%s, '6', 'No', 'Yes', 'Yes', 3, 4, 5, '3', 'Theory of Computation', 'Open Source Systems', 85)""",
        (student_a_id,)
    )
    
    # Bob votes Compiler Design as highly stressful
    cursor.execute(
        """INSERT INTO stress_forms 
           (student_id, sleep_hours, feel_fresh, physically_tired, headache_fatigue, health_rating, regular_day_stress, exam_stress, daily_study_hours, most_stress_subject, easiest_subject, stress_score)
           VALUES (%s, '5', 'No', 'Yes', 'Yes', 2, 5, 5, '4', 'Compiler Design', 'Open Source Systems', 90)""",
        (student_b_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()
    return college_id

def run_timetable_generation(college_id, branch, year_level, semester, section_name):
    # This is the exact algorithm from generate_timetable in app.py
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch subjects
    cursor.execute(
        "SELECT * FROM subjects WHERE college_id = %s AND branch = %s AND year_level = %s AND semester = %s AND section_name = %s",
        (college_id, branch, year_level, semester, section_name)
    )
    subjects = cursor.fetchall()

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

    # Sort faculties by matching priority and experience
    subject_faculty_map = {}
    for sub in subjects:
        matched_facs = []
        for f in faculties:
            if sub['subject_name'].lower() in f['subject_name'].lower() or f['subject_name'].lower() in sub['subject_name'].lower():
                matched_facs.append((f, 2))
            elif sub['branch'].lower() in f['department'].lower() or f['department'].lower() in sub['branch'].lower():
                matched_facs.append((f, 1))
        
        matched_facs.sort(key=lambda x: (x[1], x[0].get('experience_years', 0)), reverse=True)
        subject_faculty_map[sub['id']] = [item[0] for item in matched_facs]

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    slots_needed = {sub['id']: sub['periods_per_week'] for sub in subjects}
    schedule = {day: {f'period{p}': 'FREE' for p in range(1, 8)} for day in days}

    # Checks if faculty is busy in another branch/section at that day/period
    def is_faculty_busy(fac_name, day, period):
        check_conn = get_connection()
        chk_cursor = check_conn.cursor()
        # Query checks if the faculty is already assigned in ANY other section's timetable for this college/day/period
        # We check if the period contains the faculty name (e.g. "Theory of Computation (Dr. Alan Turing)")
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
            
            # Period placement logic
            if fac_pref_morning or is_stressful:
                periods_pool = ['period1', 'period2', 'period3', 'period4', 'period5', 'period6', 'period7']
            elif fac_pref_afternoon:
                periods_pool = ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']
            else:
                periods_pool = ['period4', 'period5', 'period6', 'period7', 'period1', 'period2', 'period3']

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

    # Save to Database
    save_conn = get_connection()
    save_cursor = save_conn.cursor()
    save_cursor.execute(
        "DELETE FROM timetable WHERE college_id = %s AND branch = %s AND section_name = %s AND year_level = %s AND semester = %s",
        (college_id, branch, section_name, year_level, semester)
    )
    
    for day in days:
        query = """INSERT INTO timetable 
                   (college_id, branch, section_name, year_level, semester, day_name, period1, period2, period3, period4, period5, period6, period7, published)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)"""
        save_cursor.execute(query, (
            college_id, branch, section_name, year_level, semester, day,
            schedule[day]['period1'], schedule[day]['period2'], schedule[day]['period3'],
            schedule[day]['period4'], schedule[day]['period5'], schedule[day]['period6'], schedule[day]['period7']
        ))
    save_conn.commit()
    save_cursor.close()
    save_conn.close()
    print(f"-> Successfully generated & saved timetable for Section {section_name}")

def verify_and_analyze(college_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM timetable WHERE college_id = %s ORDER BY section_name, day_name", (college_id,))
    rows = cursor.fetchall()
    
    # Structure of timetables: {section: {day: [period1...period7]}}
    timetable_map = {}
    for r in rows:
        sec = r['section_name']
        day = r['day_name']
        if sec not in timetable_map:
            timetable_map[sec] = {}
        timetable_map[sec][day] = [r[f'period{p}'] for p in range(1, 8)]
        
    print("\n==============================================================")
    print("                  TIMETABLE VERIFICATION REPORT               ")
    print("==============================================================")
    
    # Check 1: Overlap / Conflict check
    conflict_count = 0
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    for day in days:
        for p_idx in range(7):
            p_name = f"Period {p_idx+1}"
            sec_a_val = timetable_map['A'][day][p_idx]
            sec_b_val = timetable_map['B'][day][p_idx]
            
            # Extract teacher names
            teacher_a = sec_a_val.split('(')[-1].replace(')', '') if '(' in sec_a_val else None
            teacher_b = sec_b_val.split('(')[-1].replace(')', '') if '(' in sec_b_val else None
            
            if teacher_a and teacher_b and teacher_a == teacher_b and teacher_a != "TBD":
                print(f"[CONFLICT DETECTED] {day} {p_name}: '{teacher_a}' is scheduled in BOTH Section A ({sec_a_val}) and Section B ({sec_b_val})!")
                conflict_count += 1

    if conflict_count == 0:
        print("[SUCCESS] Conflict Check: 0 faculty collisions detected! No teacher is double-booked.")
    else:
        print(f"[FAILED] Conflict Check: Found {conflict_count} faculty collision(s)!")

    # Check 2: Stress-aware placement validation
    # TOC was voted high stress by Section A, Compiler Design by Section B.
    # Check if they are mostly placed in morning slots (periods 1, 2, or 3)
    stress_check_a = [p for d in days for p in timetable_map['A'][d][:3] if "Theory of Computation" in p]
    stress_check_b = [p for d in days for p in timetable_map['B'][d][:3] if "Compiler Design" in p]
    
    print("\n--- Heuristic / Stress-Aware Performance ---")
    print(f"Section A - 'Theory of Computation' (High Stress) periods in morning (Periods 1-3): {len(stress_check_a)} times.")
    print(f"Section B - 'Compiler Design' (High Stress) periods in morning (Periods 1-3): {len(stress_check_b)} times.")
    
    # Display the final timetables
    for sec in sorted(timetable_map.keys()):
        print(f"\nTimetable for Section {sec}:")
        print(f"{'Day':<10} | {'P1':<30} | {'P2':<30} | {'P3':<30} | {'P4':<30} | {'P5':<30} | {'P6':<30} | {'P7':<30}")
        print("-" * 230)
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            p_cols = [f"{p[:27]}..." if len(p) > 27 else p for p in timetable_map[sec][day]]
            print(f"{day:<10} | {p_cols[0]:<30} | {p_cols[1]:<30} | {p_cols[2]:<30} | {p_cols[3]:<30} | {p_cols[4]:<30} | {p_cols[5]:<30} | {p_cols[6]:<30}")
            
    cursor.close()
    conn.close()

if __name__ == "__main__":
    college_id = setup_test_data()
    print("\n--- 7. Generating Timetable for Section A ---")
    run_timetable_generation(college_id, "CSE", 3, 5, "A")
    print("\n--- 8. Generating Timetable for Section B ---")
    run_timetable_generation(college_id, "CSE", 3, 5, "B")
    
    verify_and_analyze(college_id)
