-- SIKLAB schema patch to match capstone paper modules
-- Adds: assessment answers, lessons, exercises, recommendations

USE siklab_db;

-- ═════════════════════════════════════════════════════════════════════════════
-- ASSESSMENT RESPONSES
-- Stores the initial assessment described in the paper
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
-- LESSONS
-- Provides structured programming lessons per language/category/level
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS lessons (
  id INT AUTO_INCREMENT PRIMARY KEY,
  language VARCHAR(50) NOT NULL,              -- Python, Java, JavaScript, C#, SQL
  level VARCHAR(30) NOT NULL,                 -- beginner, intermediate, upper-intermediate
  topic VARCHAR(100) NOT NULL,                -- Variables, Loops, Conditionals, etc.
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

-- ═════════════════════════════════════════════════════════════════════════════
-- EXERCISES
-- Supports paper exercise types: code completion, error detection, logic-based problems
-- ═════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS exercises (
  id INT AUTO_INCREMENT PRIMARY KEY,
  lesson_id INT NULL,
  language VARCHAR(50) NOT NULL,
  level VARCHAR(30) NOT NULL,
  exercise_type VARCHAR(30) NOT NULL,         -- completion | error_detection | logic_problem
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
-- Stores rule-based predictive analysis output and dashboard recommendations
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

