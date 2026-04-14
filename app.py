from flask import Flask, render_template, request, session, jsonify
from datetime import date, datetime
import calendar
from utilities import generate_employees, generate_project_teams

# Generate shared employee pool for both login list and project teams
SHARED_EMPLOYEES = generate_employees(30)  # Generate 30 employees for both features

# Generate sample events for employees
def generate_sample_events():
    events = {}
    sample_event_titles = [
        "Team Meeting", "Project Review", "Client Call", "Training Session",
        "One-on-One", "Department Meeting", "Code Review", "Planning Session",
        "Presentation", "Workshop", "Deadline", "Office Hours"
    ]
    
    for employee in SHARED_EMPLOYEES:
        employee_id = employee['employee_id']
        events[employee_id] = {"name": employee['email'], "events": {}}
        
        # Add 3-5 random events for each employee
        import random
        from datetime import datetime, timedelta
        
        num_events = random.randint(3, 5)
        for i in range(num_events):
            # Random date within current month
            today = datetime.now()
            day = random.randint(1, 28)  # Keep it simple with days 1-28
            hour = random.randint(9, 17)  # Business hours 9-17
            
            date_str = today.replace(day=day, hour=hour, minute=0).strftime("%Y-%m-%d")
            
            if date_str not in events[employee_id]["events"]:
                events[employee_id]["events"][date_str] = []
            
            events[employee_id]["events"][date_str].append({
                "title": random.choice(sample_event_titles),
                "time": f"{hour}:00"
            })
    
    return events

# Initialize employee schedules with sample events
print("DEBUG: Regenerating sample events for current employees...")
employee_schedules = generate_sample_events()
print(f"DEBUG: Generated schedules for {len(employee_schedules)} employees")

# Print sample for debugging
first_employee = list(employee_schedules.keys())[0]
print(f"DEBUG: Sample employee {first_employee} has {len(employee_schedules[first_employee]['events'])} events")

app = Flask(__name__)
app.secret_key = "don't steal our key por favor"

# Simple in-memory storage for demo purposes
# In production, you'd use a database
# employee_schedules is now initialized above with sample events

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

# Employee data and schedules are already initialized at the top of the file

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

@app.route("/view_employee_schedule", methods=["POST"])
def view_employee_schedule():
    print("DEBUG: view_employee_schedule route called")
    employee_email = request.form.get("employee_email")
    print(f"DEBUG: Received email: {employee_email}")
    
    if not employee_email:
        print("DEBUG: No email provided")
        return jsonify({"error": "Employee email is required"}), 400
    
    print(f"DEBUG: Total employee schedules: {len(employee_schedules)}")
    print(f"DEBUG: Available employee IDs: {list(employee_schedules.keys())[:5]}")
    
    # Find employee in shared employees list
    employee_id = employee_email.split('@')[0]
    employee_name = None
    
    print(f"DEBUG: Looking for email: {employee_email}")
    print(f"DEBUG: Available employees: {[emp['email'] for emp in SHARED_EMPLOYEES[:5]]}")  # Show first 5 for debugging
    
    for emp in SHARED_EMPLOYEES:
        if emp['email'] == employee_email:
            employee_name = f"{emp['first_name']} {emp['last_name']}"
            print(f"DEBUG: Found employee: {employee_name}")
            break
    
    if not employee_name:
        print(f"DEBUG: Employee not found for email: {employee_email}")
        error_response = {
            "error": "Employee not found",
            "message": f"The email {employee_email} does not exist in the employee list. Please check the email and try again.",
            "available_emails": [emp['email'] for emp in SHARED_EMPLOYEES[:10]]  # Show first 10 as examples
        }
        print(f"DEBUG: Returning error response: {error_response}")
        return jsonify(error_response), 404
    
    # Get employee's schedule
    employee_schedule = employee_schedules.get(employee_id, {"name": employee_email, "events": {}})
    print(f"DEBUG: Employee ID: {employee_id}")
    print(f"DEBUG: Employee schedule keys: {list(employee_schedules.keys())[:5]}")
    print(f"DEBUG: Employee found in schedules: {employee_id in employee_schedules}")
    
    if employee_id in employee_schedules:
        print(f"DEBUG: Employee events: {employee_schedules[employee_id]['events']}")
        print(f"DEBUG: Number of events: {len(employee_schedules[employee_id]['events'])}")
    else:
        print(f"DEBUG: Employee {employee_id} not found in schedules")
    
    # Get current month and year for calendar
    today = date.today()
    year = request.form.get("year", today.year)
    month = request.form.get("month", today.month)
    print(f"DEBUG: Year: {year}, Month: {month}")
    
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = today.year
        month = today.month
    
    # Generate calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Build calendar days with events
    calendar_days = []
    print(f"DEBUG: Building calendar for {len(cal)} weeks")
    
    for week_idx, week in enumerate(cal):
        week_days = []
        print(f"DEBUG: Processing week {week_idx}")
        
        for day in week:
            if day == 0:
                week_days.append({"day": "", "events": []})
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                events = employee_schedule.get("events", {}).get(date_str, [])
                
                # Debug first few days with events
                if events and len(calendar_days) == 0:
                    print(f"DEBUG: Found events on {date_str}: {events}")
                elif len(calendar_days) < 3:  # Debug first few days even if no events
                    print(f"DEBUG: No events on {date_str}, checking available dates: {list(employee_schedule.get('events', {}).keys())[:3]}")
                
                week_days.append({"day": day, "date": date_str, "events": events})
        calendar_days.append(week_days)
    
    print(f"DEBUG: Total calendar days generated: {len(calendar_days)}")
    
    # Count total events
    total_events = 0
    for week in calendar_days:
        for day in week:
            total_events += len(day.get("events", []))
    print(f"DEBUG: Total events in calendar: {total_events}")
    
    # Generate simple HTML calendar directly
    print("DEBUG: Generating simple HTML calendar")
    
    calendar_html = f"""
    <div class="employee-schedule-view">
        <div class="schedule-header">
            <h3>{employee_name}'s Schedule</h3>
            <p class="schedule-email">{employee_email}</p>
            <div class="calendar-nav">
                <button class="nav-btn" onclick="navigateMonth(-1)">Previous</button>
                <span class="current-month">{month_name} {year}</span>
                <button class="nav-btn" onclick="navigateMonth(1)">Next</button>
            </div>
        </div>
        
        <div class="calendar-grid">
            <div class="calendar-weekdays">
                <div class="weekday">Sun</div>
                <div class="weekday">Mon</div>
                <div class="weekday">Tue</div>
                <div class="weekday">Wed</div>
                <div class="weekday">Thu</div>
                <div class="weekday">Fri</div>
                <div class="weekday">Sat</div>
            </div>
    """
    
    # Add calendar weeks
    for week in calendar_days:
        calendar_html += '<div class="calendar-week">'
        for day in week:
            if day["day"]:
                events_html = ""
                for event in day["events"]:
                    events_html += f'<div class="event-item"><span class="event-title">{event["title"]}</span>'
                    if event.get("time"):
                        events_html += f' <span class="event-time">{event["time"]}</span>'
                    events_html += '</div>'
                
                calendar_html += f'''
                <div class="calendar-day has-day" data-date="{day["date"]}">
                    <div class="day-number">{day["day"]}</div>
                    <div class="day-events">{events_html}</div>
                </div>
                '''
            else:
                calendar_html += '<div class="calendar-day"></div>'
        calendar_html += '</div>'
    
    # Add summary
    total_events = sum(len(day["events"]) for week in calendar_days for day in week)
    calendar_html += f'''
        </div>
        <div class="schedule-summary">
            <p class="summary-text">Total events this month: <span class="event-count">{total_events}</span></p>
        </div>
    </div>
    '''
    
    print("DEBUG: Simple calendar HTML generated successfully")
    print(f"DEBUG: Returning HTML with length: {len(calendar_html)}")
    return calendar_html

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
