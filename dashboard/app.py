"""
dashboard/app.py
==================
Flask web application — the control room dashboard.
Shows live alerts, incident history, stats, and
allows operators to resolve alerts.

Run standalone: python dashboard/app.py
Or via main.py (runs in background thread)
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import os
import sys

# Allow importing from parent folder when run standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager


def create_app(db: DatabaseManager = None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    if db is None:
        db = DatabaseManager()
        db.init_db()

    # ── Pages ──────────────────────────────────────────────

    @app.route("/")
    def index():
        """Main dashboard page."""
        stats   = db.get_stats()
        alerts  = db.get_recent_alerts(limit=10, unresolved_only=True)
        return render_template("index.html", stats=stats, alerts=alerts)

    @app.route("/alerts")
    def alerts_page():
        """All alerts page."""
        alerts = db.get_recent_alerts(limit=100)
        return render_template("alerts.html", alerts=alerts)

    @app.route("/incidents")
    def incidents_page():
        """Incident log page."""
        incidents = db.get_recent_incidents(limit=200)
        return render_template("incidents.html", incidents=incidents)

    # ── API endpoints ──────────────────────────────────────

    @app.route("/api/stats")
    def api_stats():
        """Live stats for dashboard auto-refresh."""
        return jsonify(db.get_stats())

    @app.route("/api/alerts")
    def api_alerts():
        """Recent alerts as JSON."""
        unresolved_only = request.args.get("unresolved", "false").lower() == "true"
        alerts = db.get_recent_alerts(limit=50, unresolved_only=unresolved_only)
        return jsonify(alerts)

    @app.route("/api/incidents")
    def api_incidents():
        """Recent incidents as JSON."""
        incidents = db.get_recent_incidents(limit=100)
        return jsonify(incidents)

    @app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
    def resolve_alert(alert_id):
        """Mark an alert as resolved."""
        operator = request.json.get("operator", "Operator") if request.json else "Operator"
        db.resolve_alert(alert_id, resolved_by=operator)
        return jsonify({"success": True, "message": f"Alert {alert_id} resolved"})

    @app.route("/api/location-stats")
    def location_stats():
        """Alert counts by location for charts."""
        return jsonify(db.get_alerts_by_location())

    @app.route("/snapshots/<path:filename>")
    def serve_snapshot(filename):
        """Serve snapshot images to the dashboard."""
        return send_from_directory(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "snapshots"),
            filename
        )

    return app


if __name__ == "__main__":
    # Run dashboard standalone for testing
    db = DatabaseManager()
    db.init_db()
    app = create_app(db)
    print("🌐 Dashboard running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
