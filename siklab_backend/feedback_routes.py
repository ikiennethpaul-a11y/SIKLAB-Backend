"""Feedback endpoints to register with the Siklab Flask app."""

# In app.py, after defining get_db():
#   from feedback_routes import register_feedback_routes
#   register_feedback_routes(app, get_db)
#
# Configure SIKLAB_ADMIN_FEEDBACK_TOKEN on the server before starting Flask.

import hmac
import os

from flask import jsonify, request
import mysql.connector


_FEEDBACK_CATEGORIES = {
    "Suggestion",
    "Bug report",
    "General feedback",
}
_FEEDBACK_STATUSES = {"new", "in_review", "resolved"}


def register_feedback_routes(app, get_db):
    """Register user submission and bearer-token-protected admin endpoints."""

    def require_admin_token():
        configured_token = os.environ.get("SIKLAB_ADMIN_FEEDBACK_TOKEN", "")
        authorization = request.headers.get("Authorization", "")
        scheme, _, supplied_token = authorization.partition(" ")
        if (
            not configured_token
            or scheme.lower() != "bearer"
            or not supplied_token
            or not hmac.compare_digest(supplied_token, configured_token)
        ):
            return jsonify({"success": False, "message": "Unauthorized."}), 401
        return None

    @app.route("/feedback", methods=["POST"])
    def submit_feedback():
        body = request.get_json(silent=True) or {}
        user_id = body.get("user_id")
        category = body.get("category")
        message = body.get("message")

        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            return jsonify({"success": False, "message": "A valid user_id is required."}), 400
        if category not in _FEEDBACK_CATEGORIES:
            return jsonify({"success": False, "message": "A valid feedback category is required."}), 400
        if not isinstance(message, str) or not message.strip():
            return jsonify({"success": False, "message": "Feedback message is required."}), 400
        if len(message.strip()) > 2000:
            return jsonify({"success": False, "message": "Feedback must be 2,000 characters or fewer."}), 400

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                """
                INSERT INTO user_feedback (user_id, category, message)
                VALUES (%s, %s, %s)
                """,
                (user_id, category, message.strip()),
            )
            db.commit()
            feedback_id = cur.lastrowid
            return jsonify({
                "success": True,
                "message": "Feedback submitted.",
                "feedback_id": feedback_id,
                "status": "new",
            }), 201
        except mysql.connector.Error:
            db.rollback()
            app.logger.exception("Could not save user feedback")
            return jsonify({"success": False, "message": "Could not save feedback."}), 500
        finally:
            db.close()

    @app.route("/admin/feedback", methods=["GET"])
    def list_feedback():
        auth_error = require_admin_token()
        if auth_error:
            return auth_error

        status = request.args.get("status")
        if status and status not in _FEEDBACK_STATUSES:
            return jsonify({"success": False, "message": "Invalid feedback status."}), 400
        try:
            limit = min(max(int(request.args.get("limit", "100")), 1), 500)
            offset = max(int(request.args.get("offset", "0")), 0)
        except ValueError:
            return jsonify({"success": False, "message": "limit and offset must be integers."}), 400

        db = get_db()
        try:
            cur = db.cursor(dictionary=True)
            query = """
                SELECT f.id, f.user_id, u.full_name, u.email, f.category,
                       f.message, f.status, f.created_at, f.updated_at
                FROM user_feedback AS f
                JOIN users AS u ON u.id = f.user_id
            """
            params = []
            if status:
                query += " WHERE f.status = %s"
                params.append(status)
            query += " ORDER BY f.created_at DESC, f.id DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            cur.execute(query, tuple(params))
            feedback = cur.fetchall()
            return jsonify({"success": True, "feedback": feedback}), 200
        except mysql.connector.Error:
            app.logger.exception("Could not load user feedback")
            return jsonify({"success": False, "message": "Could not load feedback."}), 500
        finally:
            db.close()

    @app.route("/admin/feedback/<int:feedback_id>", methods=["PUT"])
    def update_feedback_status(feedback_id):
        auth_error = require_admin_token()
        if auth_error:
            return auth_error

        body = request.get_json(silent=True) or {}
        status = body.get("status")
        if status not in _FEEDBACK_STATUSES:
            return jsonify({"success": False, "message": "Invalid feedback status."}), 400

        db = get_db()
        try:
            cur = db.cursor()
            cur.execute(
                "UPDATE user_feedback SET status = %s WHERE id = %s",
                (status, feedback_id),
            )
            if cur.rowcount == 0:
                db.rollback()
                return jsonify({"success": False, "message": "Feedback not found."}), 404
            db.commit()
            return jsonify({"success": True, "status": status}), 200
        except mysql.connector.Error:
            db.rollback()
            app.logger.exception("Could not update feedback status")
            return jsonify({"success": False, "message": "Could not update feedback."}), 500
        finally:
            db.close()
