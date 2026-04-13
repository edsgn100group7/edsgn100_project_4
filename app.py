from flask import Flask, url_for, render_template

app = Flask(__name__)

from flask import Flask, render_template, request, session, flash

app.secret_key = "don't steal our key por favor"

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

@app.route("/employeepage")
def employeepage():
    return render_template("employeepage.html")

@app.route("/orgpage")
def orgpage():
    return render_template("orgpage.html")

@app.route("/empschedule")
def empschedule():
    return render_template("empschedule.html")


@app.route("/teamschedule")
def teamschedule():
    return render_template("teamschedule.html")

@app.route("/empavailability")
def empavailability():
    return render_template("empavailability.html")

@app.route("/coschedule")
def coschedule():
    return render_template("coschedule.html")

@app.route("/Indschedule")
def Indschedule():
    return render_template("Indschedule.html")

@app.route("/Employeeteams")
def Employeeteams():
    return render_template("Employeeteams.html")


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
