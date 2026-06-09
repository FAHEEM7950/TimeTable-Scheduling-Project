CREATE DATABASE IF NOT EXISTS timetable_db;
USE timetable_db;

-- 1. Colleges Table
CREATE TABLE IF NOT EXISTS colleges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_name VARCHAR(255) NOT NULL,
    college_code VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Local College Admins Table
CREATE TABLE IF NOT EXISTS admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    college_name VARCHAR(255),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 3. Students Table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    semester INT NOT NULL,
    section_name VARCHAR(50),
    roll_no VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 4. Faculty Table
CREATE TABLE IF NOT EXISTS faculty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    employee_id VARCHAR(100) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    department VARCHAR(100) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    experience_years INT DEFAULT 0,
    preferred_morning_subject VARCHAR(150),
    preferred_afternoon_subject VARCHAR(150),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 5. Subjects Table
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    subject_code VARCHAR(50) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    semester INT NOT NULL,
    periods_per_week INT DEFAULT 3,
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 6. Student Stress Forms Table
CREATE TABLE IF NOT EXISTS stress_forms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    sleep_hours VARCHAR(50),
    feel_fresh VARCHAR(100),
    physically_tired VARCHAR(100),
    headache_fatigue VARCHAR(100),
    health_rating INT,
    regular_day_stress INT,
    exam_stress INT,
    daily_study_hours VARCHAR(50),
    most_stress_subject VARCHAR(150),
    easiest_subject VARCHAR(150),
    preferred_morning_subject VARCHAR(150),
    preferred_afternoon_subject VARCHAR(150),
    best_study_time VARCHAR(100),
    need_more_breaks VARCHAR(100),
    scheduling_suggestions TEXT,
    stress_comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 7. Faculty Absence Requests Table
CREATE TABLE IF NOT EXISTS absence_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    college_id INT NOT NULL,
    absent_date DATE NOT NULL,
    start_period INT NOT NULL, -- e.g., 1 to 7
    end_period INT NOT NULL,   -- e.g., 1 to 7
    status VARCHAR(50) DEFAULT 'Pending', -- Pending, Swapped, Declined
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 8. Timetable Table
CREATE TABLE IF NOT EXISTS timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    semester INT NOT NULL,
    day_name VARCHAR(50) NOT NULL,
    period1 VARCHAR(255) DEFAULT 'FREE',
    period2 VARCHAR(255) DEFAULT 'FREE',
    period3 VARCHAR(255) DEFAULT 'FREE',
    period4 VARCHAR(255) DEFAULT 'FREE',
    period5 VARCHAR(255) DEFAULT 'FREE',
    period6 VARCHAR(255) DEFAULT 'FREE',
    period7 VARCHAR(255) DEFAULT 'FREE',
    published INT DEFAULT 0, -- 0 = Draft, 1 = Published
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 9. Student Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    roll_no VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
--10
ALTER TABLE stress_forms
ADD COLUMN stress_score INT DEFAULT 0;
--11
ALTER TABLE timetable
ADD COLUMN ai_reason TEXT;
--12
CREATE TABLE stress_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,

    college_id INT NOT NULL,

    branch VARCHAR(100),
    year_level INT,
    semester INT,

    total_students INT DEFAULT 0,

    low_stress_count INT DEFAULT 0,
    medium_stress_count INT DEFAULT 0,
    high_stress_count INT DEFAULT 0,

    low_percentage DECIMAL(5,2),
    medium_percentage DECIMAL(5,2),
    high_percentage DECIMAL(5,2),

    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);
--13
CREATE TABLE subject_stress_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,

    college_id INT NOT NULL,

    branch VARCHAR(100),
    year_level INT,
    semester INT,

    subject_name VARCHAR(200),

    stress_votes INT DEFAULT 0,

    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);
--14
CREATE TABLE dashboard_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,

    college_id INT,

    total_students INT DEFAULT 0,
    low_stress INT DEFAULT 0,
    medium_stress INT DEFAULT 0,
    high_stress INT DEFAULT 0,

    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);