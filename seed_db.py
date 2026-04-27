"""Seed the database with demo data."""
import json
from models import init_db, Employee, Preferences, SolverRun, Result
from prowess_demo import generate as generate_prowess_data
from solver import solve as run_solver, DAYS as SOLVER_DAYS

def seed():
    """Create demo data in database."""
    init_db()

    # Generate demo data
    demo_data = generate_prowess_data(n_employees=12, n_groups=3, n_weeks=2, seed=42)

    # Add employees to database
    for emp in demo_data['employees']:
        Employee.create(emp['id'], emp['name'], emp['geo_cluster'])
        # Add their initial preferences
        Preferences.save(
            emp['id'],
            preferred_days=emp.get('preferred_days', []),
            vacation_days=emp.get('vacation_days', []),
            min_office=emp.get('min_office_days_per_week', 2),
            max_office=emp.get('max_office_days_per_week', 4)
        )

    # Run solver
    result = run_solver(demo_data)
    result['weeks'] = demo_data['org'].get('weeks', 2)
    result['org'] = demo_data['org']
    result['input_groups'] = demo_data.get('groups', [])

    # Store solver run
    run_id = SolverRun.create(
        status=result['status'],
        feasible=result['feasible'],
        objective=result.get('objective'),
        result_json=result
    )

    # Store individual results
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
            }
        )

    print(f"[OK] Seeded database with {len(demo_data['employees'])} employees")
    print(f"[OK] Solver run {run_id}: {result['status']} (feasible: {result['feasible']})")

if __name__ == "__main__":
    seed()
