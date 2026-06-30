"""
api.py

Flask API wrapper for the AI Student Success Mentor.
Provides:
  - A static file hosting handler to serve index.html, style.css, app.js.
  - A POST /analyze endpoint that accepts student profiles, parses and validates inputs,
    runs the pipeline orchestrator, and returns results in JSON.
"""

import os
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from orchestrator import Orchestrator

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app = Flask(__name__, static_folder=static_dir, static_url_path='')
CORS(app)  # Enable CORS for convenience in testing and deployment

# Serve frontend main index.html at root
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Endpoint to analyze student profile and run orchestrator pipeline
@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload received"}), 400

        # Extract values
        name = data.get("name", "").strip() or "Student"
        degree = data.get("degree", "").strip() or "Computer Science"
        
        # Safe type conversions
        try:
            semester = int(data.get("semester", 4))
        except (ValueError, TypeError):
            semester = 4

        try:
            cgpa = float(data.get("cgpa", 3.0))
        except (ValueError, TypeError):
            cgpa = 3.0

        # Helper to convert input (which could be list or comma-separated string) to a list of strings
        def sanitize_list(value):
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            return []

        skills = sanitize_list(data.get("skills", []))
        interests = sanitize_list(data.get("interests", []))

        # Basic validation
        if not skills:
            return jsonify({"error": "Please provide at least one skill."}), 400
        if not interests:
            return jsonify({"error": "Please provide at least one interest."}), 400

        student_profile = {
            "name": name,
            "degree": degree,
            "semester": semester,
            "cgpa": cgpa,
            "skills": skills,
            "interests": interests
        }

        # Instantiate orchestrator and run pipeline
        orchestrator = Orchestrator()
        results = orchestrator.run(student_profile)

        # Return results along with echoed back profile for context
        return jsonify({
            "success": True,
            "profile": student_profile,
            "results": results
        })

    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({
            "error": "An unexpected error occurred during the analysis pipeline.",
            "details": str(exc)
        }), 500

if __name__ == '__main__':
    # Determine port from env or fallback to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
