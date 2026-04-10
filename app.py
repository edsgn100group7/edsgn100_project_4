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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

