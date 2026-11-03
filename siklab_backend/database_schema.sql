-- Siklab MySQL schema synced from ../Siklab/database_schema.sql.
-- Includes backend learning modules and active-time storage.
-- Run this file in MySQL Workbench or the mysql client. Existing application
-- records are preserved; CREATE TABLE IF NOT EXISTS only adds missing tables.

-- Create database
CREATE DATABASE IF NOT EXISTS siklab_db;
USE siklab_db;

-- ═════════════════════════════════════════════════════════════════════════════
-- USERS TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- USER STATS TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_logic_cycles INT DEFAULT 0,
    current_streak INT DEFAULT 0,
    avg_precision DECIMAL(5,4) DEFAULT 0.0000,
    global_rank INT DEFAULT 0,
    xp_points INT DEFAULT 0,
    completed_challenges INT DEFAULT 0,
    last_practice_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_stats (user_id),
    INDEX idx_rank (global_rank),
    INDEX idx_xp (xp_points)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- TOPIC STRENGTHS TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS topic_strengths (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic_name VARCHAR(100) NOT NULL,
    mastery_level DECIMAL(5,4) DEFAULT 0.0000,
    questions_attempted INT DEFAULT 0,
    questions_correct INT DEFAULT 0,
    last_practiced TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_topic (user_id, topic_name),
    INDEX idx_mastery (mastery_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- WEAK AREAS TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS weak_areas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    failure_rate DECIMAL(5,4) DEFAULT 0.0000,
    total_attempts INT DEFAULT 0,
    failed_attempts INT DEFAULT 0,
    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_weak (user_id),
    INDEX idx_failure_rate (failure_rate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- CODING VELOCITY TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS coding_velocity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    practice_date DATE NOT NULL,
    challenges_completed INT DEFAULT 0,
    time_spent_minutes INT DEFAULT 0,
    velocity_score DECIMAL(5,4) DEFAULT 0.0000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_date (user_id, practice_date),
    INDEX idx_date (practice_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- MILESTONES TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS milestones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    milestone_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_name VARCHAR(50),
    color VARCHAR(20),
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_achieved BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_milestones (user_id),
    INDEX idx_achieved (achieved_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- QUIZ ATTEMPTS TABLE
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    language VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    question_id VARCHAR(100) NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    time_taken_seconds INT DEFAULT 0,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_attempts (user_id),
    INDEX idx_language_category (language, category),
    INDEX idx_correct (is_correct)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- USER FEEDBACK
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category ENUM('Suggestion', 'Bug report', 'General feedback') NOT NULL,
    message TEXT NOT NULL,
    status ENUM('new', 'in_review', 'resolved') NOT NULL DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_feedback_status_created (status, created_at),
    INDEX idx_feedback_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- AI RELIANCE CHECK-IN TABLE
-- Asked on the Practice page after every 10 correct questions (10, 20, 30 ...).
-- phase 'pre'  = the learner's first answered check-in (baseline)
-- phase 'post' = every later check-in, compared against the baseline
-- q1, q2 = frequency (1 Never ... 5 Always); q3, q4 = confidence (1 Not at all ... 5 Extremely)
-- reliance_index = ((Q1 + Q2 + (6-Q3) + (6-Q4)) / 4 - 1) / 4 * 100   (0-100, higher = more AI reliance)
-- language / category = where the learner was when the check-in appeared
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ai_reliance_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    phase ENUM('pre', 'post') NOT NULL,
    correct_count INT NOT NULL,
    language VARCHAR(50) NOT NULL DEFAULT '',
    category VARCHAR(50) NOT NULL DEFAULT '',
    q1_ai_generates_code TINYINT NOT NULL,
    q2_copies_without_understanding TINYINT NOT NULL,
    q3_confident_basic_without_ai TINYINT NOT NULL,
    q4_confident_understand_correct TINYINT NOT NULL,
    reliance_index DECIMAL(5,1) NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_checkpoint (user_id, correct_count),
    INDEX idx_ai_feedback_phase (phase),
    CONSTRAINT chk_ai_q1 CHECK (q1_ai_generates_code BETWEEN 1 AND 5),
    CONSTRAINT chk_ai_q2 CHECK (q2_copies_without_understanding BETWEEN 1 AND 5),
    CONSTRAINT chk_ai_q3 CHECK (q3_confident_basic_without_ai BETWEEN 1 AND 5),
    CONSTRAINT chk_ai_q4 CHECK (q4_confident_understand_correct BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- ASSESSMENT RESPONSES
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS assessment_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    experience_level_score INT NOT NULL DEFAULT 0,
    logic_confidence_score INT NOT NULL DEFAULT 0,
    learning_goal VARCHAR(100) NULL,
    weekly_time_score INT NOT NULL DEFAULT 0,
    preferred_language VARCHAR(50) NULL,
    ai_reliance_score INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_assessment (user_id),
    INDEX idx_pref_lang (preferred_language),
    CONSTRAINT fk_assessment_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- LESSONS, SECTIONS, AND EXERCISES
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    language VARCHAR(50) NOT NULL,
    level VARCHAR(30) NOT NULL,
    topic VARCHAR(100) NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_lesson_lang_level (language, level),
    INDEX idx_lesson_topic (topic)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lesson_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lesson_id INT NOT NULL,
    section_order INT NOT NULL,
    heading VARCHAR(150) NULL,
    body TEXT NOT NULL,
    code_filename VARCHAR(120) NULL,
    code_block TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_section_lesson (lesson_id, section_order),
    CONSTRAINT fk_sections_lesson
        FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS exercises (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lesson_id INT NULL,
    language VARCHAR(50) NOT NULL,
    level VARCHAR(30) NOT NULL,
    exercise_type VARCHAR(30) NOT NULL,
    title VARCHAR(150) NOT NULL,
    prompt TEXT NOT NULL,
    starter_code TEXT NULL,
    expected_answer TEXT NOT NULL,
    explanation TEXT NULL,
    hint TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ex_lang_level (language, level),
    INDEX idx_ex_type (exercise_type),
    INDEX idx_ex_lesson (lesson_id),
    CONSTRAINT fk_exercise_lesson
        FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- RECOMMENDATIONS
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    recommended_language VARCHAR(50) NOT NULL,
    recommended_level VARCHAR(30) NOT NULL,
    recommended_topic VARCHAR(100) NOT NULL,
    reason TEXT NULL,
    score DECIMAL(6,3) DEFAULT 0.000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rec_user (user_id, created_at),
    CONSTRAINT fk_recommendations_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- ACTIVE TIME
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_active_time (
    user_id INT PRIMARY KEY,
    total_seconds BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_active_time_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═════════════════════════════════════════════════════════════════════════════
-- SKILL LEVELS TABLE (Reference table)
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS skill_levels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL UNIQUE,
    min_xp INT DEFAULT 0,
    max_xp INT DEFAULT 0,
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default skill levels
INSERT INTO skill_levels (level_name, min_xp, max_xp, description) VALUES
('Beginner', 0, 999, 'Just starting your coding journey'),
('Intermediate Developer', 1000, 4999, 'Building solid fundamentals'),
('Advanced Developer', 5000, 14999, 'Mastering complex concepts'),
('Expert Developer', 15000, 29999, 'Solving challenging problems'),
('Master Coder', 30000, 999999, 'Elite programming skills')
ON DUPLICATE KEY UPDATE
    min_xp = VALUES(min_xp),
    max_xp = VALUES(max_xp),
    description = VALUES(description);

-- ═════════════════════════════════════════════════════════════════════════════
-- VIEWS FOR COMMON QUERIES
-- ═════════════════════════════════════════════════════════════════════════════

-- View: Complete User Profile
CREATE OR REPLACE VIEW user_profile_view AS
SELECT 
    u.id,
    u.full_name,
    u.email,
    u.created_at as member_since,
    us.total_logic_cycles,
    us.current_streak,
    us.avg_precision,
    us.global_rank,
    us.xp_points,
    us.completed_challenges,
    sl.level_name as skill_level
FROM users u
LEFT JOIN user_stats us ON u.id = us.user_id
LEFT JOIN skill_levels sl ON us.xp_points BETWEEN sl.min_xp AND sl.max_xp;

-- View: User Analytics Summary
CREATE OR REPLACE VIEW user_analytics_view AS
SELECT 
    u.id as user_id,
    us.total_logic_cycles,
    us.current_streak,
    us.avg_precision,
    us.global_rank,
    us.xp_points,
    us.completed_challenges,
    sl.level_name as skill_level,
    (
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT(
                'topic', ts.topic_name,
                'value', ts.mastery_level,
                'color', 
                    CASE 
                        WHEN ts.topic_name LIKE '%data%' OR ts.topic_name LIKE '%structure%' THEN 'cyan'
                        WHEN ts.topic_name LIKE '%algorithm%' THEN 'purple'
                        WHEN ts.topic_name LIKE '%design%' OR ts.topic_name LIKE '%system%' THEN 'orange'
                        WHEN ts.topic_name LIKE '%big-o%' OR ts.topic_name LIKE '%complexity%' THEN 'success'
                        ELSE 'cyan'
                    END
            )
        )
        FROM topic_strengths ts
        WHERE ts.user_id = u.id
    ) as topic_mastery,
    (
        SELECT JSON_ARRAYAGG(wa.area_name)
        FROM weak_areas wa
        WHERE wa.user_id = u.id AND wa.is_resolved = FALSE
        LIMIT 5
    ) as weak_areas,
    (
        SELECT JSON_ARRAYAGG(
            JSON_OBJECT(
                'icon', m.icon_name,
                'title', m.milestone_name,
                'description', m.description,
                'color', m.color
            )
        )
        FROM milestones m
        WHERE m.user_id = u.id AND m.is_achieved = TRUE
        ORDER BY m.achieved_at DESC
        LIMIT 5
    ) as milestones,
    (
        SELECT JSON_ARRAYAGG(cv.velocity_score)
        FROM coding_velocity cv
        WHERE cv.user_id = u.id
        ORDER BY cv.practice_date DESC
        LIMIT 7
    ) as velocity
FROM users u
LEFT JOIN user_stats us ON u.id = us.user_id
LEFT JOIN skill_levels sl ON us.xp_points BETWEEN sl.min_xp AND sl.max_xp;

-- ═════════════════════════════════════════════════════════════════════════════
-- STORED PROCEDURES
-- ═════════════════════════════════════════════════════════════════════════════

DELIMITER //

-- Procedure: Update user stats after quiz completion
DROP PROCEDURE IF EXISTS update_stats_after_quiz //
CREATE PROCEDURE update_stats_after_quiz(
    IN p_user_id INT,
    IN p_is_correct BOOLEAN,
    IN p_time_taken INT
)
BEGIN
    DECLARE current_xp INT;
    DECLARE current_completed INT;
    DECLARE current_cycles INT;
    DECLARE current_correct INT;
    DECLARE current_attempts INT;
    DECLARE new_precision DECIMAL(5,4);
    
    -- Get current stats
    SELECT xp_points, completed_challenges, total_logic_cycles 
    INTO current_xp, current_completed, current_cycles
    FROM user_stats 
    WHERE user_id = p_user_id;
    
    -- Update stats
    IF p_is_correct THEN
        UPDATE user_stats 
        SET 
            total_logic_cycles = current_cycles + 1,
            current_streak = current_streak + 1,
            xp_points = current_xp + 10,
            completed_challenges = current_completed + 1,
            last_practice_date = CURDATE()
        WHERE user_id = p_user_id;
    ELSE
        UPDATE user_stats 
        SET 
            total_logic_cycles = current_cycles + 1,
            current_streak = 0,
            last_practice_date = CURDATE()
        WHERE user_id = p_user_id;
    END IF;
    
    -- Recalculate precision
    SELECT 
        COUNT(CASE WHEN is_correct THEN 1 END) as correct,
        COUNT(*) as total
    INTO current_correct, current_attempts
    FROM quiz_attempts 
    WHERE user_id = p_user_id;
    
    IF current_attempts > 0 THEN
        SET new_precision = current_correct / current_attempts;
        UPDATE user_stats 
        SET avg_precision = new_precision 
        WHERE user_id = p_user_id;
    END IF;
    
    -- Update global rank using window function (MySQL 8.0+)
    UPDATE user_stats us
    JOIN (
        SELECT user_id, ROW_NUMBER() OVER (ORDER BY xp_points DESC) as rank_num
        FROM user_stats
    ) ranked ON us.user_id = ranked.user_id
    SET us.global_rank = ranked.rank_num;
END //

-- Procedure: Update topic strength
DROP PROCEDURE IF EXISTS update_topic_strength //
CREATE PROCEDURE update_topic_strength(
    IN p_user_id INT,
    IN p_topic_name VARCHAR(100),
    IN p_is_correct BOOLEAN
)
BEGIN
    DECLARE current_attempts INT;
    DECLARE current_correct INT;
    DECLARE new_mastery DECIMAL(5,4);
    
    -- Insert or update topic strength
    INSERT INTO topic_strengths (user_id, topic_name, questions_attempted, questions_correct, mastery_level, last_practiced)
    VALUES (p_user_id, p_topic_name, 1, IF(p_is_correct, 1, 0), IF(p_is_correct, 1.0, 0.0), NOW())
    ON DUPLICATE KEY UPDATE
        questions_attempted = questions_attempted + 1,
        questions_correct = questions_correct + IF(p_is_correct, 1, 0),
        mastery_level = questions_correct / questions_attempted,
        last_practiced = NOW();
END //

-- Procedure: Record quiz attempt
DROP PROCEDURE IF EXISTS record_quiz_attempt //
CREATE PROCEDURE record_quiz_attempt(
    IN p_user_id INT,
    IN p_language VARCHAR(50),
    IN p_category VARCHAR(50),
    IN p_question_id VARCHAR(100),
    IN p_is_correct BOOLEAN,
    IN p_time_taken INT,
    IN p_topic_name VARCHAR(100)
)
BEGIN
    -- Record the attempt
    INSERT INTO quiz_attempts (user_id, language, category, question_id, is_correct, time_taken_seconds)
    VALUES (p_user_id, p_language, p_category, p_question_id, p_is_correct, p_time_taken);
    
    -- Update stats
    CALL update_stats_after_quiz(p_user_id, p_is_correct, p_time_taken);
    
    -- Update topic strength
    CALL update_topic_strength(p_user_id, p_topic_name, p_is_correct);
    
    -- Update coding velocity for today
    INSERT INTO coding_velocity (user_id, practice_date, challenges_completed, time_spent_minutes, velocity_score)
    VALUES (p_user_id, CURDATE(), 1, FLOOR(p_time_taken / 60), IF(p_is_correct, 1.0, 0.5))
    ON DUPLICATE KEY UPDATE
        challenges_completed = challenges_completed + 1,
        time_spent_minutes = time_spent_minutes + FLOOR(p_time_taken / 60),
        velocity_score = challenges_completed / (time_spent_minutes + 1);
END //

DELIMITER ;

-- ═════════════════════════════════════════════════════════════════════════════
-- No test-user/sample analytics rows are inserted by this schema.
-- ═════════════════════════════════════════════════════════════════════════════

-- ═════════════════════════════════════════════════════════════════════════════
-- END OF SCHEMA
-- ═════════════════════════════════════════════════════════════════════════════
