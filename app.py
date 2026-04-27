"""PROWESS — Hybrid Work Scheduling System."""
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from datetime import date, timedelta
import json
import traceback
from models import init_db, reset_db, get_config, set_config, Employee, Preferences, SolverRun, Result
from solver import DEFAULTS as SOLVER_DEFAULTS
from solver import solve as run_solver, DAYS as SOLVER_DAYS
from prowess_demo import generate as generate_prowess_data

app = Flask(__name__)
app.secret_key = "prowess-demo-key"

init_db()

DAYS_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri"]

@app.template_filter('day_names')
def day_names_filter(indices):
    """Convert list of day indices (0-4) to readable names."""
    return ', '.join(DAYS_ABBR[i] for i in (indices or []) if 0 <= i < 5) or 'None'

# ══════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/employee", methods=["GET", "POST"])
def employee_login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return render_template("employee_login.html", error="Please enter your name")

        emp = Employee.get_by_name(name)
        if not emp:
            emp_id = f"emp_{len(Employee.list_all()) + 1:03d}"
            Employee.create(emp_id, name)
            emp = Employee.get_by_name(name)

        session["employee_id"] = emp['id']
        session["employee_name"] = emp['name']
        return redirect(url_for("employee_dashboard"))

    return render_template("employee_login.html")

@app.route("/employee/dashboard")
def employee_dashboard():
    emp_id = session.get("employee_id")
    emp_name = session.get("employee_name")

    if not emp_id:
        return redirect(url_for("employee_login"))

    prefs   = Preferences.get_latest(emp_id)
    results = Result.get_for_employee(emp_id)
    run     = SolverRun.get_latest()

    n_weeks = 2
    if run:
        n_weeks = run['result_json'].get('weeks', 2)

    # Human-readable preference stats
    pref_stats = None
    if results and prefs:
        pref_days = set(prefs.get('preferred_days', []))
        vac_days  = set(prefs.get('vacation_days', []))
        schedule  = results.get('schedule', [])
        remote_hit = remote_total = office_hit = office_total = 0
        for w in range(n_weeks):
            for d in range(5):
                idx = w * 5 + d
                if idx in vac_days:
                    continue
                status = schedule[idx] if idx < len(schedule) else 'home'
                if d in pref_days:
                    remote_total += 1
                    if status == 'home':
                        remote_hit += 1
                else:
                    office_total += 1
                    if status == 'office':
                        office_hit += 1
        pref_stats = {
            'remote_hit': remote_hit, 'remote_total': remote_total,
            'office_hit': office_hit, 'office_total': office_total,
        }

    # Carpool info for this employee
    emp_record  = Employee.get_by_id(emp_id)
    geo_cluster = emp_record.get('geo_cluster', 'Unknown') if emp_record else 'Unknown'
    carpool_info = None
    if run:
        cs = run['result_json'].get('carpool_summary', {}).get(geo_cluster)
        if cs and not cs.get('solo') and len(cs.get('member_names', [])) > 1:
            partner_names = [n for n in cs['member_names'] if n != emp_name]
            my_pairs = {k: v for k, v in cs.get('pair_alignment', {}).items()
                        if emp_name in k}
            carpool_info = {
                'cluster':        geo_cluster,
                'partner_names':  partner_names,
                'pair_alignment': my_pairs,
                'avg_alignment':  cs.get('avg_alignment', 0),
                'n_days':         n_weeks * 5,
            }

    return render_template(
        "employee_dashboard.html",
        employee_id=emp_id,
        employee_name=emp_name,
        preferences=prefs,
        results=results,
        days_abbr=DAYS_ABBR,
        n_weeks=n_weeks,
        pref_stats=pref_stats,
        geo_cluster=geo_cluster,
        carpool_info=carpool_info,
    )

@app.route("/employee/logout")
def employee_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/team")
def team_view():
    employees = Employee.list_all()
    run = SolverRun.get_latest()

    team_data = []
    for emp in employees:
        prefs = Preferences.get_latest(emp['id'])
        results = Result.get_for_employee(emp['id'])
        team_data.append({
            'employee': emp,
            'preferences': prefs,
            'results': results,
        })

    n_weeks = 2
    groups = []
    if run:
        rj = run['result_json']
        n_weeks = rj.get('weeks', 2)
        groups = rj.get('input_groups', [])

    # Build grouped structure — each employee assigned to first group they appear in
    by_id = {item['employee']['id']: item for item in team_data}
    seen  = set()
    grouped = []
    for grp in groups:
        members = []
        for emp_id in grp.get('members', []):
            if emp_id not in seen and emp_id in by_id:
                members.append(by_id[emp_id])
                seen.add(emp_id)
        if members:
            grouped.append({
                'group_id':   grp['id'],
                'group_name': grp['name'],
                'members':    members,
            })

    ungrouped = [item for item in team_data if item['employee']['id'] not in seen]
    if ungrouped:
        grouped.append({'group_id': None, 'group_name': 'Other', 'members': ungrouped})
    if not grouped:
        grouped = [{'group_id': None, 'group_name': None, 'members': team_data}]

    # Group overlap summary from last run
    group_summary = {}
    if run:
        group_summary = run['result_json'].get('group_overlap_summary', {})
        group_scores  = run['result_json'].get('scores', {}).get('group', {})
        for gid, gs in group_scores.items():
            if gid in group_summary:
                group_summary[gid]['score'] = gs.get('score', 0)

    # Carpool summary from last run
    carpool_summary = {}
    if run:
        carpool_summary = run['result_json'].get('carpool_summary', {})

    return render_template(
        "team_view.html",
        grouped=grouped,
        team_data=team_data,
        group_summary=group_summary,
        carpool_summary=carpool_summary,
        run=run,
        days_abbr=DAYS_ABBR,
        n_weeks=n_weeks,
    )

@app.route("/admin")
def admin_view():
    employees = Employee.list_all()
    run = SolverRun.get_latest()

    # Start from config defaults, then overlay with last run if available
    cfg_org = get_config('org', {})
    org_data = {
        'max_seats':           cfg_org.get('max_seats', 10),
        'min_daily_in_person': cfg_org.get('min_daily_in_person', 4),
        'weeks':               cfg_org.get('weeks', 2),
        'priority_employees':  cfg_org.get('priority_employees', 0.30),
        'priority_groups':     cfg_org.get('priority_groups', 0.55),
        'priority_niceties':   cfg_org.get('priority_niceties', 0.15),
    }

    if run:
        rj = run['result_json']
        if rj.get('org'):
            org_data.update({
                'max_seats':           rj['org'].get('max_seats',           org_data['max_seats']),
                'min_daily_in_person': rj['org'].get('min_daily_in_person', org_data['min_daily_in_person']),
            })
        org_data['weeks'] = rj.get('weeks', org_data['weeks'])

    # Groups: prefer last run, then config (from reseed), then fallback split
    groups_for_solver = []
    if run:
        groups_for_solver = run['result_json'].get('input_groups', [])
    if not groups_for_solver:
        groups_for_solver = get_config('groups', [])

    emp_data = []
    for emp in employees:
        prefs = Preferences.get_latest(emp['id'])
        emp_data.append({
            'id': emp['id'],
            'name': emp['name'],
            'geo_cluster': emp.get('geo_cluster', 'Downtown'),
            'preferred_days': prefs['preferred_days'] if prefs else [],
            'vacation_days': prefs['vacation_days'] if prefs else [],
            'min_office_days_per_week': prefs['min_office_days'] if prefs else 2,
            'max_office_days_per_week': prefs['max_office_days'] if prefs else 4,
        })

    # Last-resort fallback: 2-group split
    if not groups_for_solver and emp_data:
        half = len(emp_data) // 2
        groups_for_solver = [
            {
                'id': 'grp_00', 'name': 'Team A',
                'members': [e['id'] for e in emp_data[:half]],
                'min_overlap_days_per_week': 2, 'overlap_weight': 1.0, 'subgroups': [],
            },
            {
                'id': 'grp_01', 'name': 'Team B',
                'members': [e['id'] for e in emp_data[half:]],
                'min_overlap_days_per_week': 2, 'overlap_weight': 1.0, 'subgroups': [],
            },
        ]

    # Solver tuning params (from config or defaults)
    solver_params = get_config('solver_params', dict(SOLVER_DEFAULTS))

    # Build cluster groups from current employee data
    cluster_groups: dict = {}
    for emp in emp_data:
        cl = emp.get('geo_cluster', 'Downtown')
        cluster_groups.setdefault(cl, []).append(emp)

    # Carpool summary from last run
    carpool_summary = {}
    if run:
        carpool_summary = run['result_json'].get('carpool_summary', {})

    return render_template(
        "admin_view.html",
        employees=emp_data,
        org_data=org_data,
        run=run,
        days_abbr=DAYS_ABBR,
        groups_for_solver=groups_for_solver,
        solver_params=solver_params,
        cluster_groups=cluster_groups,
        carpool_summary=carpool_summary,
        geo_clusters=['North', 'South', 'East', 'West', 'Downtown'],
    )

# ══════════════════════════════════════════════════════════════
# API Endpoints
# ══════════════════════════════════════════════════════════════

@app.route("/api/preferences", methods=["POST"])
def save_preferences():
    emp_id = session.get("employee_id")
    if not emp_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    Preferences.save(
        emp_id,
        preferred_days=data.get('preferred_days', []),
        vacation_days=data.get('vacation_days', []),
        min_office=data.get('min_office_days', 2),
        max_office=data.get('max_office_days', 4),
    )
    return jsonify({"success": True})

@app.route("/api/solve", methods=["POST"])
def solve():
    try:
        data = request.get_json()

        if not data.get('employees') or not data.get('org'):
            return jsonify({"error": "Invalid data"}), 400

        result = run_solver(data)

        n_weeks = data['org'].get('weeks', 1)
        result['day_labels']   = [f"W{w+1} {day}" for w in range(n_weeks) for day in SOLVER_DAYS]
        result['weeks']        = n_weeks
        result['org']          = data['org']
        result['input_groups'] = data.get('groups', [])

        # Persist solver params so admin page restores them
        if data.get('solver_params'):
            set_config('solver_params', data['solver_params'])

        run_id = SolverRun.create(
            status=result['status'],
            feasible=result['feasible'],
            objective=result.get('objective'),
            result_json=result,
        )

        if result.get('feasible'):
            total_score = result.get('scores', {}).get('total', 0)
            for emp_id, schedule_data in result.get('schedules', {}).items():
                emp_scores = result.get('scores', {}).get('employee', {}).get(emp_id, {})
                Result.save(
                    run_id,
                    emp_id,
                    schedule=schedule_data['schedule'],
                    scores={
                        'name': schedule_data['name'],
                        'office_days_total': schedule_data['office_days_total'],
                        'employee': emp_scores,
                        'total': total_score,
                    },
                )

        result['run_id'] = run_id
        return jsonify(result)

    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return jsonify({"error": str(e), "detail": tb}), 500

@app.route("/api/reseed", methods=["POST"])
def reseed():
    """Wipe and regenerate demo employees + preferences (does not run solver)."""
    try:
        data = request.get_json() or {}
        n_employees = max(4, min(50,  int(data.get('n_employees', 12))))
        n_groups    = max(1, min(n_employees // 2, int(data.get('n_groups', 3))))
        n_weeks     = max(1, min(4,   int(data.get('n_weeks', 2))))
        seed        = data.get('seed', None)
        if seed is not None:
            seed = int(seed)
        max_seats_override = data.get('max_seats', None)
        if max_seats_override is not None:
            max_seats_override = max(1, int(max_seats_override))

        reset_db()
        init_db()  # re-create tables if needed

        demo_data = generate_prowess_data(
            n_employees=n_employees,
            n_groups=n_groups,
            n_weeks=n_weeks,
            seed=seed,
            max_seats=max_seats_override,
        )

        for emp in demo_data['employees']:
            Employee.create(emp['id'], emp['name'], emp['geo_cluster'])
            Preferences.save(
                emp['id'],
                preferred_days=emp.get('preferred_days', []),
                vacation_days=emp.get('vacation_days', []),
                min_office=emp.get('min_office_days_per_week', 2),
                max_office=emp.get('max_office_days_per_week', 4),
            )

        # Persist the generated groups so the solver picks them up next run
        set_config('groups', demo_data.get('groups', []))
        set_config('org', demo_data.get('org', {}))

        session.clear()  # log out any stale employee session
        return jsonify({
            'success': True,
            'n_employees': n_employees,
            'names': [e['name'] for e in demo_data['employees']],
        })
    except Exception as e:
        tb = traceback.format_exc()
        print(tb)
        return jsonify({"error": str(e)}), 500

@app.route("/api/employee/<emp_id>/cluster", methods=["POST"])
def update_employee_cluster(emp_id):
    data    = request.get_json() or {}
    cluster = data.get('geo_cluster', 'Downtown')
    ok      = Employee.update_cluster(emp_id, cluster)
    return jsonify({"success": ok})

@app.route("/api/results")
def get_results():
    run = SolverRun.get_latest()
    if not run:
        return jsonify({"error": "No results available"}), 404

    all_results = Result.get_all_for_run(run['id'])
    return jsonify({
        'run': {
            'id': run['id'],
            'run_date': run['run_date'],
            'status': run['status'],
            'feasible': run['feasible'],
            'objective': run['objective'],
        },
        'results': [
            {
                'employee_id': r['employee_id'],
                'schedule': r['schedule'],
                'scores': r['scores'],
            }
            for r in all_results
        ],
    })

if __name__ == "__main__":
    print("\n  PROWESS - Hybrid Work Scheduling System")
    print("  Running at http://localhost:8000\n")
    app.run(host="0.0.0.0", port=8000, debug=True)
