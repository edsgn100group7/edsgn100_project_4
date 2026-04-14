from flask import Flask, url_for, render_template, request, session, flash, jsonify
from datetime import date, timedelta, datetime
import calendar
import json
from utilities import generate_employees, generate_project_teams

app = Flask(__name__)
app.secret_key = "don't steal our key por favor"

# Simple in-memory storage for demo purposes
# In production, you'd use a database
employee_schedules = {}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/org")
def org():
    return render_template("org.html")

@app.route("/employee")
def employee():
    return render_template("employee.html")

@app.route("/backend")
def backend():
    return render_template("backend.html")

@app.route("/employeepage", methods=["GET", "POST"])
def employeepage():
    if request.method == "POST":
        email = request.form.get("employee-email")
        password = request.form.get("employee-password")
        
        # Store employee info in session
        session["employee_email"] = email
        session["logged_in"] = True
        
        # For demo purposes, create employee ID from email
        session["employee_id"] = email.split("@")[0] if email else "unknown"
        
    return render_template("employeepage.html", employee_email=session.get("employee_email"))

@app.route("/orgpage")
def orgpage():
    return render_template("orgpage.html")

@app.route("/empschedule")
def empschedule():
    # Check if employee is logged in
    if not session.get("logged_in"):
        return render_template("employee.html")
    
    employee_id = session.get("employee_id")
    employee_email = session.get("employee_email")
    
    # Get month and year from query params or use current date
    year = int(request.args.get("year", date.today().year))
    month = int(request.args.get("month", date.today().month))
    
    # Generate calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Get employee's existing schedule or create empty one
    if employee_id not in employee_schedules:
        employee_schedules[employee_id] = {
            "name": employee_email,
            "events": {}
        }
    
    # Format calendar for template
    calendar_weeks = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": "", "events": []})
            else:
                day_date = date(year, month, day)
                date_str = day_date.strftime("%Y-%m-%d")
                events = employee_schedules[employee_id]["events"].get(date_str, [])
                week_data.append({"day": day, "date": date_str, "events": events})
        calendar_weeks.append(week_data)
    
    return render_template("empschedule.html", 
                         calendar_weeks=calendar_weeks,
                         month_name=month_name,
                         year=year,
                         employee_name=employee_email or "None",
                         employee_id=employee_id)

@app.route("/add_event", methods=["POST"])
def add_event():
    if not session.get("logged_in"):
        return jsonify({"error": "Not logged in"}), 401
    
    employee_id = session.get("employee_id")
    event_date = request.form.get("date")
    event_title = request.form.get("title")
    event_time = request.form.get("time", "")
    
    if employee_id not in employee_schedules:
        employee_schedules[employee_id] = {
            "name": session.get("employee_email"),
            "events": {}
        }
    
    if event_date not in employee_schedules[employee_id]["events"]:
        employee_schedules[employee_id]["events"][event_date] = []
    
    employee_schedules[employee_id]["events"][event_date].append({
        "title": event_title,
        "time": event_time
    })
    
    return jsonify({"success": True})

@app.route("/get_events/<date_str>")
def get_events(date_str):
    if not session.get("logged_in"):
        return jsonify({"error": "Not logged in"}), 401
    
    employee_id = session.get("employee_id")
    events = []
    
    if employee_id in employee_schedules:
        events = employee_schedules[employee_id]["events"].get(date_str, [])
    
    return jsonify({"events": events})

@app.route("/delete_event", methods=["POST"])
def delete_event():
    if not session.get("logged_in"):
        return jsonify({"error": "Not logged in"}), 401
    
    employee_id = session.get("employee_id")
    event_date = request.form.get("date")
    event_title = request.form.get("title")
    event_time = request.form.get("time", "")
    
    if employee_id in employee_schedules and event_date in employee_schedules[employee_id]["events"]:
        events = employee_schedules[employee_id]["events"][event_date]
        # Remove the event matching title and time
        employee_schedules[employee_id]["events"][event_date] = [
            event for event in events 
            if not (event["title"] == event_title and event["time"] == event_time)
        ]
        
        # Remove empty date entries
        if not employee_schedules[employee_id]["events"][event_date]:
            del employee_schedules[employee_id]["events"][event_date]
    
    return jsonify({"success": True})

# Generate shared employee pool for both login list and project teams
SHARED_EMPLOYEES = generate_employees(30)  # Generate 30 employees for both features

@app.route("/employee_list")
def employee_list():
    # Use shared employees for login list
    sample_employees = SHARED_EMPLOYEES[:15]  # Show first 15 for login list
    
    # Print generated data for debugging
    print("Generated Employees for Login List:")
    for emp in sample_employees:
        print(f"  Name: {emp['first_name']} {emp['last_name']}")
        print(f"  Email: {emp['email']}")
        print(f"  Job: {emp['job_title']}")
        print(f"  Department: {emp['department']}")
        print(f"  ID: {emp['employee_id']}")
        print("---")
    
    return render_template("employee_list.html", employees=sample_employees)

@app.route("/employee_login", methods=["POST"])
def employee_login():
    email = request.form.get("employee_email")
    employee_id = request.form.get("employee_id")
    
    # Store employee info in session
    session["employee_email"] = email
    session["employee_id"] = employee_id
    session["logged_in"] = True
    
    # Initialize empty schedule for this employee
    if employee_id not in employee_schedules:
        employee_schedules[employee_id] = {
            "name": email,
            "events": {}
        }
    
    return render_template("employeepage.html", employee_email=email)


@app.route("/teamschedule")
def teamschedule():
    return render_template("teamschedule.html")

@app.route("/empavailability")
def empavailability():
    ranks = get_state()
    
    # Get current week information
    today = date.today()
    current_week = today.isocalendar()[1]  # ISO week number
    current_year = today.year
    
    # Calculate week start and end dates
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=4)  # Monday to Friday
    
    return render_template("empavailability.html", 
                         days=DAYS, 
                         ranks=ranks, 
                         limit=ALLOCATION_LIMIT,
                         current_week=current_week,
                         current_year=current_year,
                         week_start=week_start.strftime("%B %d"),
                         week_end=week_end.strftime("%B %d"))

@app.route("/coschedule")
def coschedule():
    return render_template("coschedule.html")

@app.route("/Indschedule")
def Indschedule():
    return render_template("Indschedule.html")

@app.route("/Employeeteams")
def Employeeteams():
    # Generate project teams using shared employees
    project_teams = generate_project_teams(8, SHARED_EMPLOYEES)
    
    return render_template("Employeeteams.html", teams=project_teams)

ALLOCATION_LIMIT = 5
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def get_state():
    # Store as a list of day names in order of preference
    # Example: ["Wednesday", "Monday"] means Wed is Rank 1, Mon is Rank 2
    if 'ranks' not in session:
        session['ranks'] = []
    return session['ranks']

@app.route('/schedule')
def index():
    ranks = get_state()
    return render_template('scheduler.html', days=DAYS, ranks=ranks, limit=ALLOCATION_LIMIT)

@app.route('/toggle/<day>', methods=['POST'])
def toggle_day(day):
    ranks = get_state()
    
    if day in ranks:
        # If already ranked, remove it (and others shift up automatically)
        ranks.remove(day)
    else:
        # If not ranked and we have room in the budget, add to end
        if len(ranks) < ALLOCATION_LIMIT:
            ranks.append(day)
    
    session.modified = True
    
    # We need to re-render the whole grid because changing one rank 
    # (e.g. removing Rank 1) changes the numbers on all other ranked days.
    return render_template('scheduler.html', days=DAYS, ranks=ranks, limit=ALLOCATION_LIMIT, partial=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
