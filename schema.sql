DROP DATABASE IF EXISTS timetable_db;
CREATE DATABASE timetable_db;
USE timetable_db;

-- 1. Colleges Table
CREATE TABLE colleges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_name VARCHAR(255) NOT NULL,
    college_code VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    photo_path VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Developers Table
CREATE TABLE developers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Developers
INSERT INTO developers (username, email, password) VALUES 
('Faheem Ahamed', 'faheem@smartai.com', 'SmartAI@TimeTable#2026'),
('Ram krishna Reddy', 'ramkrishna@smartai.com', 'SmartAI@TimeTable#2026')
ON DUPLICATE KEY UPDATE password=VALUES(password);

-- 3. Local College Admins Table
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    college_name VARCHAR(255),
    branch VARCHAR(100),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 4. Sections Table
CREATE TABLE sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    section_name VARCHAR(50) NOT NULL,
    UNIQUE KEY unique_section (college_id, branch, year_level, section_name),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 5. Students Table
CREATE TABLE students (
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

-- 6. Faculty Table
CREATE TABLE faculty (
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

-- 7. Subjects Table
CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    subject_code VARCHAR(50) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    semester INT NOT NULL,
    section_name VARCHAR(50) NOT NULL,
    periods_per_week INT DEFAULT 3,
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 8. Student Stress Forms Table
CREATE TABLE stress_forms (
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
    stress_score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 9. Faculty Absence Requests Table
    CREATE TABLE absence_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        faculty_id INT NOT NULL,
        college_id INT NOT NULL,
        absent_date DATE NOT NULL,
        start_period INT NOT NULL,
        end_period INT NOT NULL,
        status VARCHAR(50) DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
        FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
    );

-- 10. Timetable Table
CREATE TABLE timetable (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT NOT NULL,
    branch VARCHAR(100) NOT NULL,
    year_level INT NOT NULL,
    semester INT NOT NULL,
    section_name VARCHAR(50) NOT NULL,
    day_name VARCHAR(50) NOT NULL,
    period1 VARCHAR(255) DEFAULT 'FREE',
    period2 VARCHAR(255) DEFAULT 'FREE',
    period3 VARCHAR(255) DEFAULT 'FREE',
    period4 VARCHAR(255) DEFAULT 'FREE',
    period5 VARCHAR(255) DEFAULT 'FREE',
    period6 VARCHAR(255) DEFAULT 'FREE',
    period7 VARCHAR(255) DEFAULT 'FREE',
    published INT DEFAULT 0,
    ai_reason TEXT,
    UNIQUE KEY unique_timetable_slot (college_id, branch, year_level, semester, section_name, day_name),
    FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
);

-- 11. Student Feedback Table
CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    roll_no VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 12. Stress Reports Summary Table
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

-- 13. Subject Stress Stats Table
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

-- 14. Dashboard Stats Table
CREATE TABLE dashboard_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    college_id INT,
    total_students INT DEFAULT 0,
    low_stress INT DEFAULT 0,
    medium_stress INT DEFAULT 0,
    high_stress INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);