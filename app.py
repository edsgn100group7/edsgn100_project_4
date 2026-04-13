from flask import Flask, url_for, render_template

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
