# app.py  — SIKLAB Flask Backend (with Flask-SocketIO real-time sync)
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, emit
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from feedback_routes import register_feedback_routes

load_dotenv()

app = Flask(__name__)
CORS(app, origins='*', allow_headers=['Content-Type'], methods=['GET', 'POST', 'PUT', 'DELETE'])

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

DB_CONFIG = {
    'host': os.environ['MYSQL_HOST'],
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ['MYSQL_USER'],
    'password': os.environ['MYSQL_PASSWORD'],
    'database': os.environ['MYSQL_DB'],
    'ssl_ca': os.environ['MYSQL_SSL_CA'],
    'ssl_verify_cert': True,
    'ssl_verify_identity': True,
    'connection_timeout': 15,
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


USER_SELECT = """
    SELECT u.id, u.full_name, u.email, u.password_hash,
           us.total_logic_cycles, us.current_streak, us.avg_precision,
           us.global_rank, us.xp_points, us.completed_challenges
    FROM users AS u
    LEFT JOIN user_stats AS us ON us.user_id = u.id
"""


def get_user_by_id(cur, user_id):
    cur.execute(USER_SELECT + " WHERE u.id = %s", (user_id,))
    return cur.fetchone()


def get_user_by_email(cur, email):
    cur.execute(USER_SELECT + " WHERE u.email = %s", (email,))
    return cur.fetchone()


register_feedback_routes(app, get_db)


def row_to_user(row):
    return {
        'id':                   row['id'],
        'full_name':            row['full_name'],
        'email':                row['email'],
        'total_logic_cycles':   row.get('total_logic_cycles') or 0,
        'current_streak':       row.get('current_streak') or 0,
        'avg_precision':        float(row.get('avg_precision') or 0.0),
        'global_rank':          row.get('global_rank') or 0,
        'xp_points':            row.get('xp_points') or 0,
        'completed_challenges': row.get('completed_challenges') or 0,
    }


def parse_json_field(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default
    return default


def table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        (name,),
    )
    return (cur.fetchone() or {}).get("c", 0) > 0


# ── Helper: broadcast to all devices of same user ─────────────
def sync_to_user(user_id: int, event: str, data: dict):
    socketio.emit(event, data, room=str(user_id))


# ── WebSocket: Join user room on connect ──────────────────────
@socketio.on('join')
def on_join(data):
    user_id = str(data.get('user_id'))
    join_room(user_id)
    emit('status', {'message': f'Joined room {user_id}'})


# ── WebSocket: Leave room on disconnect ───────────────────────
@socketio.on('disconnect')
def on_disconnect():
    pass  # Flask-SocketIO handles cleanup automatically


# ── POST /signup ──────────────────────────────────────────────
@app.route('/signup', methods=['POST'])
def signup():
    body      = request.get_json(silent=True) or {}
    full_name = (body.get('full_name') or '').strip()
    email     = (body.get('email')     or '').strip().lower()
    password  = (body.get('password')  or '').strip()

    if not full_name or not email or not password:
        return jsonify({'success': False,
                        'message': 'full_name, email and password are required.'}), 400

    if len(password) < 6:
        return jsonify({'success': False,
                        'message': 'Password must be at least 6 characters.'}), 400

    pw_hash = generate_password_hash(password)
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cur.fetchone():
            return jsonify({'success': False,
                            'message': 'This email is already registered.'}), 409

        cur.execute(
            'INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)',
            (full_name, email, pw_hash)
        )
        new_id = cur.lastrowid

        cur.execute(
            'INSERT INTO user_stats (user_id, total_logic_cycles, current_streak, avg_precision, global_rank, xp_points, completed_challenges) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (new_id, 0, 0, 0.0000, 0, 0, 0)
        )
        db.commit()

        user = row_to_user(get_user_by_id(cur, new_id))

        return jsonify({'success': True,
                        'message': 'Account created successfully.',
                        'user': user}), 201

    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── POST /login ───────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    body     = request.get_json(silent=True) or {}
    email    = (body.get('email')    or '').strip().lower()
    password = (body.get('password') or '').strip()

    if not email or not password:
        return jsonify({'success': False,
                        'message': 'Email and password are required.'}), 400

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        row = get_user_by_email(cur, email)

        if not row or not check_password_hash(row['password_hash'], password):
            return jsonify({'success': False,
                            'message': 'Invalid email or password.'}), 401

        return jsonify({'success': True,
                        'message': 'Login successful.',
                        'user': row_to_user(row)}), 200

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── GET /profile/<id> ─────────────────────────────────────────
@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'User not found.'}), 404

        cur.execute("""
            SELECT * FROM quiz_attempts
            WHERE user_id = %s
        """, (user_id,))
        attempts = cur.fetchall()

        total_attempts = len(attempts)
        correct_attempts = sum(1 for a in attempts if a['is_correct'])
        avg_precision = (correct_attempts / total_attempts) if total_attempts > 0 else 0

        language_progress = {}
        for lang in ['Java', 'Python', 'C#', 'JavaScript', 'SQL']:
            lang_attempts = [a for a in attempts if a['language'] == lang]
            lang_correct = sum(1 for a in lang_attempts if a['is_correct'])
            progress = (lang_correct / len(lang_attempts) * 100) if lang_attempts else 0
            language_progress[lang] = progress

        streak = 0
        if attempts:
            recent_correct = 0
            for attempt in reversed(attempts[-10:]):
                if attempt['is_correct']:
                    recent_correct += 1
                else:
                    break
            streak = recent_correct

        topic_strengths = {}
        for topic in ['Data Structures', 'Algorithms', 'Systems Design', 'Big-O Notation', 'Recursion']:
            topic_attempts = [a for a in attempts if topic.lower() in a.get('category', '').lower()]
            topic_correct = sum(1 for a in topic_attempts if a['is_correct'])
            strength = (topic_correct / len(topic_attempts)) if topic_attempts else 0
            topic_strengths[topic] = strength

        cur.execute("""
            INSERT INTO user_stats (
                user_id, total_logic_cycles, avg_precision, current_streak,
                xp_points, completed_challenges
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                total_logic_cycles = %s,
                avg_precision = %s,
                current_streak = %s,
                xp_points = %s,
                completed_challenges = %s
        """, (
            user_id, total_attempts, avg_precision, streak,
            correct_attempts * 10, len(set(a['question_id'] for a in attempts)),
            total_attempts, avg_precision, streak, correct_attempts * 10,
            len(set(a['question_id'] for a in attempts)),
        ))
        db.commit()

        user = get_user_by_id(cur, user_id)
        user_data = row_to_user(user)
        user_data['topic_strengths'] = topic_strengths
        user_data['language_progress'] = language_progress

        return jsonify({'success': True, 'user': user_data}), 200

    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── PUT /profile/<id> ─────────────────────────────────────────
@app.route('/profile/<int:user_id>', methods=['PUT'])
def update_profile(user_id):
    body = request.get_json(silent=True) or {}

    user_fields = ('full_name', 'email')
    stats_fields = (
        'total_logic_cycles', 'current_streak', 'avg_precision', 'global_rank',
        'xp_points', 'completed_challenges',
    )
    user_updates = {
        key: body[key] for key in user_fields
        if key in body and body[key] is not None
    }
    stats_updates = {
        key: body[key] for key in stats_fields
        if key in body and body[key] is not None
    }

    if 'password' in body and body['password']:
        if len(body['password']) < 6:
            return jsonify({'success': False,
                            'message': 'Password must be at least 6 characters.'}), 400
        user_updates['password_hash'] = generate_password_hash(body['password'])

    if not user_updates and not stats_updates:
        return jsonify({'success': False, 'message': 'No valid fields provided.'}), 400

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'User not found.'}), 404

        if user_updates:
            set_clause = ', '.join(f'`{key}` = %s' for key in user_updates)
            cur.execute(
                f'UPDATE users SET {set_clause} WHERE id = %s',
                list(user_updates.values()) + [user_id],
            )

        if stats_updates:
            columns = ', '.join(f'`{key}`' for key in stats_updates)
            placeholders = ', '.join(['%s'] * len(stats_updates))
            updates = ', '.join(
                f'`{key}` = VALUES(`{key}`)' for key in stats_updates
            )
            cur.execute(
                f"""
                INSERT INTO user_stats (user_id, {columns})
                VALUES (%s, {placeholders})
                ON DUPLICATE KEY UPDATE {updates}
                """,
                [user_id] + list(stats_updates.values()),
            )

        db.commit()
        return jsonify({'success': True,
                        'message': 'Profile updated.',
                        'user': row_to_user(get_user_by_id(cur, user_id))}), 200

    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── GET /health ───────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'message': 'API is running.'}), 200

@app.route('/health/db', methods=['GET'])
def database_health():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT DATABASE()")
        database_name = cur.fetchone()[0]
        cur.close()
        db.close()

        return jsonify({
            'success': True,
            'message': 'Database connection successful.',
            'database': database_name
        }), 200

    except Exception:
        return jsonify({
            'success': False,
            'message': 'Database connection failed.'
        }), 500

# ── POST /assessment/<id> ─────────────────────────────────────
@app.route('/assessment/<int:user_id>', methods=['POST'])
def save_assessment(user_id):
    body = request.get_json(silent=True) or {}

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "assessment_responses"):
            return jsonify({
                "success": False,
                "message": "assessment_responses table not found. Apply database_schema.sql first."
            }), 500

        exp = int(body.get("experience_level_score") or 0)
        logic = int(body.get("logic_confidence_score") or 0)
        goal = (body.get("learning_goal") or "").strip()[:100] or None
        weekly = int(body.get("weekly_time_score") or 0)
        pref = (body.get("preferred_language") or "").strip()[:50] or None
        ai = int(body.get("ai_reliance_score") or 0)

        cur.execute(
            """
            INSERT INTO assessment_responses
              (user_id, experience_level_score, logic_confidence_score, learning_goal,
               weekly_time_score, preferred_language, ai_reliance_score)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              experience_level_score = VALUES(experience_level_score),
              logic_confidence_score = VALUES(logic_confidence_score),
              learning_goal = VALUES(learning_goal),
              weekly_time_score = VALUES(weekly_time_score),
              preferred_language = VALUES(preferred_language),
              ai_reliance_score = VALUES(ai_reliance_score),
              updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, exp, logic, goal, weekly, pref, ai),
        )
        db.commit()
        return jsonify({"success": True, "message": "Assessment saved."}), 201
    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── GET /lessons ──────────────────────────────────────────────
@app.route('/lessons', methods=['GET'])
def list_lessons():
    language = (request.args.get("language") or "").strip()
    level = (request.args.get("level") or "").strip()

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "lessons"):
            return jsonify({
                "success": False,
                "message": "lessons table not found. Apply database_schema.sql first."
            }), 500

        where = []
        params = []
        if language:
            where.append("language = %s")
            params.append(language)
        if level:
            where.append("level = %s")
            params.append(level)

        sql = "SELECT id, language, level, topic, title, description FROM lessons"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY language, FIELD(level,'beginner','intermediate','upper-intermediate'), topic, id"

        cur.execute(sql, tuple(params))
        return jsonify({"success": True, "lessons": cur.fetchall()}), 200
    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── GET /lessons/<id> ─────────────────────────────────────────
@app.route('/lessons/<int:lesson_id>', methods=['GET'])
def get_lesson(lesson_id):
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "lessons") or not table_exists(cur, "lesson_sections"):
            return jsonify({
                "success": False,
                "message": "lesson tables not found. Apply database_schema.sql first."
            }), 500

        cur.execute(
            "SELECT id, language, level, topic, title, description FROM lessons WHERE id = %s",
            (lesson_id,),
        )
        lesson = cur.fetchone()
        if not lesson:
            return jsonify({"success": False, "message": "Lesson not found."}), 404

        cur.execute(
            """
            SELECT section_order, heading, body, code_filename, code_block
            FROM lesson_sections
            WHERE lesson_id = %s
            ORDER BY section_order ASC
            """,
            (lesson_id,),
        )
        lesson["sections"] = cur.fetchall()
        return jsonify({"success": True, "lesson": lesson}), 200
    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── GET /exercises ────────────────────────────────────────────
@app.route('/exercises', methods=['GET'])
def list_exercises():
    language = (request.args.get("language") or "").strip()
    level = (request.args.get("level") or "").strip()
    exercise_type = (request.args.get("type") or "").strip()
    lesson_id = request.args.get("lesson_id")

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "exercises"):
            return jsonify({
                "success": False,
                "message": "exercises table not found. Apply database_schema.sql first."
            }), 500

        where = []
        params = []
        if language:
            where.append("language = %s")
            params.append(language)
        if level:
            where.append("level = %s")
            params.append(level)
        if exercise_type:
            where.append("exercise_type = %s")
            params.append(exercise_type)
        if lesson_id:
            where.append("lesson_id = %s")
            params.append(int(lesson_id))

        sql = """
        SELECT id, lesson_id, language, level, exercise_type, title, prompt, starter_code, hint
        FROM exercises
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id ASC"

        cur.execute(sql, tuple(params))
        return jsonify({"success": True, "exercises": cur.fetchall()}), 200
    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── POST /evaluate ────────────────────────────────────────────
@app.route('/evaluate', methods=['POST'])
def evaluate_exercise():
    body = request.get_json(silent=True) or {}
    exercise_id = body.get("exercise_id")
    submitted = (body.get("submitted") or "").strip()

    if not exercise_id or submitted == "":
        return jsonify({"success": False, "message": "exercise_id and submitted are required."}), 400

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "exercises"):
            return jsonify({
                "success": False,
                "message": "exercises table not found. Apply database_schema.sql first."
            }), 500

        cur.execute(
            "SELECT expected_answer, explanation FROM exercises WHERE id = %s",
            (int(exercise_id),),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Exercise not found."}), 404

        expected = (row.get("expected_answer") or "").strip()
        normalized_sub = " ".join([l.strip() for l in submitted.splitlines() if l.strip()])
        normalized_exp = " ".join([l.strip() for l in expected.splitlines() if l.strip()])

        is_correct = normalized_sub.lower() == normalized_exp.lower()
        return jsonify({
            "success": True,
            "result": {
                "is_correct": is_correct,
                "explanation": row.get("explanation") or "",
            }
        }), 200
    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── GET /recommendations/<id> ─────────────────────────────────
@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)
        if not table_exists(cur, "recommendations"):
            return jsonify({
                "success": False,
                "message": "recommendations table not found. Apply database_schema.sql first."
            }), 500

        cur.execute(
            """
            SELECT recommended_language, recommended_level, recommended_topic, reason, score, created_at
            FROM recommendations
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (user_id,),
        )
        return jsonify({"success": True, "recommendations": cur.fetchall()}), 200
    except mysql.connector.Error as e:
        return jsonify({"success": False, "message": f"Database error: {e}"}), 500
    finally:
        db.close()


# ── GET /analytics/<id> ───────────────────────────────────────
@app.route('/analytics/<int:user_id>', methods=['GET'])
def get_analytics(user_id):
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        try:
            cur.execute(
                '''
                SELECT *
                FROM user_analytics_view
                WHERE user_id = %s
                ''',
                (user_id,)
            )
            row = cur.fetchone()
        except mysql.connector.Error:
            row = None

        if row:
            analytics = {
                'skill_level': row.get('skill_level') or 'Beginner',
                'topic_mastery': parse_json_field(row.get('topic_mastery'), []),
                'weak_areas': parse_json_field(row.get('weak_areas'), []),
                'milestones': parse_json_field(row.get('milestones'), []),
                'velocity': list(reversed(parse_json_field(row.get('velocity'), []))),
            }
            return jsonify({
                'success': True,
                'message': 'Analytics fetched.',
                'analytics': analytics
            }), 200

        cur.execute(
            '''
            SELECT us.xp_points,
                   COALESCE(sl.level_name, 'Beginner') AS skill_level
            FROM user_stats us
            LEFT JOIN skill_levels sl ON us.xp_points BETWEEN sl.min_xp AND sl.max_xp
            WHERE us.user_id = %s
            ''',
            (user_id,)
        )
        stat_row = cur.fetchone()
        if not stat_row:
            return jsonify({'success': False, 'message': 'User analytics not found.'}), 404

        cur.execute(
            '''
            SELECT topic_name AS topic, mastery_level AS value
            FROM topic_strengths
            WHERE user_id = %s
            ORDER BY mastery_level DESC
            LIMIT 5
            ''',
            (user_id,)
        )
        mastery_rows = cur.fetchall()
        topic_mastery = []
        for row in mastery_rows:
            topic_mastery.append({
                'topic': row['topic'],
                'value': float(row.get('value') or 0),
                'color': 'cyan'
            })

        cur.execute(
            '''
            SELECT area_name
            FROM weak_areas
            WHERE user_id = %s AND is_resolved = FALSE
            ORDER BY failure_rate DESC
            LIMIT 5
            ''',
            (user_id,)
        )
        weak_areas = [r['area_name'] for r in cur.fetchall()]

        cur.execute(
            '''
            SELECT icon_name, milestone_name, description, color
            FROM milestones
            WHERE user_id = %s AND is_achieved = TRUE
            ORDER BY achieved_at DESC
            LIMIT 5
            ''',
            (user_id,)
        )
        milestones = [{
            'icon': r.get('icon_name') or 'star',
            'title': r.get('milestone_name') or 'Milestone',
            'description': r.get('description') or '',
            'color': r.get('color') or 'cyan'
        } for r in cur.fetchall()]

        cur.execute(
            '''
            SELECT velocity_score
            FROM coding_velocity
            WHERE user_id = %s
            ORDER BY practice_date DESC
            LIMIT 7
            ''',
            (user_id,)
        )
        velocity = [float(r.get('velocity_score') or 0) for r in reversed(cur.fetchall())]

        return jsonify({
            'success': True,
            'message': 'Analytics fetched.',
            'analytics': {
                'skill_level': stat_row.get('skill_level') or 'Beginner',
                'topic_mastery': topic_mastery,
                'weak_areas': weak_areas,
                'milestones': milestones,
                'velocity': velocity,
            }
        }), 200

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── POST /quiz-attempt ────────────────────────────────────────
@app.route('/quiz-attempt', methods=['POST'])
def record_quiz_attempt():
    body = request.get_json(silent=True) or {}

    user_id = body.get('user_id')
    language = (body.get('language') or '').strip()
    category = (body.get('category') or '').strip()
    question_id = (body.get('question_id') or '').strip()
    topic_name = (body.get('topic_name') or language or 'General').strip()
    is_correct = bool(body.get('is_correct', False))
    time_taken = int(body.get('time_taken_seconds') or 0)

    if not user_id or not language or not category or not question_id:
        return jsonify({
            'success': False,
            'message': 'user_id, language, category, and question_id are required.'
        }), 400

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        cur.execute(
            '''
            INSERT INTO quiz_attempts (user_id, language, category, question_id, is_correct, time_taken_seconds)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (user_id, language, category, question_id, is_correct, time_taken)
        )

        cur.execute(
            '''
            INSERT INTO user_stats (user_id)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE user_id = user_id
            ''',
            (user_id,)
        )

        if is_correct:
            cur.execute(
                '''
                UPDATE user_stats
                SET total_logic_cycles = total_logic_cycles + 1,
                    current_streak = current_streak + 1,
                    xp_points = xp_points + 10,
                    completed_challenges = completed_challenges + 1,
                    last_practice_date = CURDATE()
                WHERE user_id = %s
                ''',
                (user_id,)
            )
        else:
            cur.execute(
                '''
                UPDATE user_stats
                SET total_logic_cycles = total_logic_cycles + 1,
                    current_streak = 0,
                    last_practice_date = CURDATE()
                WHERE user_id = %s
                ''',
                (user_id,)
            )

        cur.execute(
            '''
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN is_correct = TRUE THEN 1 ELSE 0 END) AS correct
            FROM quiz_attempts
            WHERE user_id = %s
            ''',
            (user_id,)
        )
        precision_row = cur.fetchone() or {}
        total = int(precision_row.get('total') or 0)
        correct = int(precision_row.get('correct') or 0)
        precision = (correct / total) if total > 0 else 0

        cur.execute(
            '''
            UPDATE user_stats
            SET avg_precision = %s
            WHERE user_id = %s
            ''',
            (precision, user_id)
        )

        cur.execute(
            '''
            INSERT INTO topic_strengths (user_id, topic_name, questions_attempted, questions_correct, mastery_level, last_practiced)
            VALUES (%s, %s, 1, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                questions_attempted = questions_attempted + 1,
                questions_correct = questions_correct + VALUES(questions_correct),
                mastery_level = (questions_correct + VALUES(questions_correct)) / (questions_attempted + 1),
                last_practiced = NOW()
            ''',
            (user_id, topic_name, 1 if is_correct else 0, 1.0 if is_correct else 0.0)
        )

        cur.execute(
            '''
            INSERT INTO coding_velocity (user_id, practice_date, challenges_completed, time_spent_minutes, velocity_score)
            VALUES (%s, CURDATE(), 1, %s, %s)
            ON DUPLICATE KEY UPDATE
                challenges_completed = challenges_completed + 1,
                time_spent_minutes = time_spent_minutes + VALUES(time_spent_minutes),
                velocity_score = (challenges_completed + 1) / (time_spent_minutes + VALUES(time_spent_minutes) + 1)
            ''',
            (user_id, max(1, time_taken // 60), 1.0 if is_correct else 0.5)
        )

        db.commit()

        # ── Real-time sync: broadcast quiz progress to other devices ──
        sync_to_user(user_id, 'sync_progress', {
            'language': language,
            'is_correct': is_correct,
        })

        return jsonify({'success': True, 'message': 'Quiz attempt recorded.'}), 201

    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── POST /users/<id>/active-time ──────────────────────────────
@app.route('/users/<int:user_id>/active-time', methods=['POST'])
def save_active_time(user_id):
    body = request.get_json(silent=True) or {}
    total_seconds = body.get('total_seconds', 0)

    if not isinstance(total_seconds, (int, float)) or total_seconds < 0:
        return jsonify({'success': False, 'message': 'total_seconds must be a non-negative number.'}), 400

    if total_seconds > 31_536_000:
        return jsonify({'success': False, 'message': 'total_seconds value is unreasonably large.'}), 400

    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        cur.execute(
            '''
            INSERT INTO user_active_time (user_id, total_seconds, updated_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                total_seconds = VALUES(total_seconds),
                updated_at = NOW()
            ''',
            (user_id, int(total_seconds))
        )
        db.commit()

        # ── Real-time sync: broadcast active time to other devices ────
        sync_to_user(user_id, 'sync_active_time', {
            'total_seconds': int(total_seconds)
        })

        return jsonify({'success': True, 'message': 'Active time saved.'}), 201

    except mysql.connector.Error as e:
        db.rollback()
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ── GET /users/<id>/active-time ───────────────────────────────
@app.route('/users/<int:user_id>/active-time', methods=['GET'])
def get_active_time(user_id):
    db = get_db()
    try:
        cur = db.cursor(dictionary=True)

        cur.execute(
            '''
            SELECT total_seconds, updated_at
            FROM user_active_time
            WHERE user_id = %s
            ''',
            (user_id,)
        )
        row = cur.fetchone()

        if not row:
            return jsonify({'success': True, 'total_seconds': 0, 'updated_at': None}), 200

        return jsonify({
            'success': True,
            'total_seconds': row.get('total_seconds', 0),
            'updated_at': str(row.get('updated_at', ''))
        }), 200

    except mysql.connector.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Starting SIKLAB API on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)