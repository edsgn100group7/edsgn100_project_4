from faker import Faker 
from random import choice, randint, sample

fake = Faker()

DEPARTMENTS = ['Tree', 'Soldier', 'With', 'Him', 'Roland', 'School', 'Present', 'Deep', 'Pass', 'Central', 'Responsibility', 'Benefit', 'Catch', 'Other', 'Order', 'Space', 'Weight', 'Heavy', 'Traditional', 'Recently', 'Especially', 'Gun', 'Case', 'Performance', 'All', 'Direction']

PROJECT_NAMES = [
    'Phoenix Initiative', 'Thunder Strike', 'Nova Development', 'Quantum Leap', 'Stellar Drive',
    'Apex Project', 'Cosmic Voyage', 'Dragon Scale', 'Titan Shield', 'Vanguard Mission',
    'Odyssey Quest', 'Horizon Explorer', 'Nebula Formation', 'Polaris System', 'Orion Belt',
    'Comet Trail', 'Aurora Borealis', 'Meteor Shower', 'Galaxy Quest', 'Starlight Path',
    'Moonshot Program', 'Solar Flare', 'Black Hole', 'Supernova', 'Asteroid Field'
]

def generate_project_teams(num_teams=8, employees=None):
    teams = []
    
    # If no employees provided, generate them
    if employees is None:
        employees = generate_employees(50)  # Generate more employees for teams
    
    for i in range(num_teams):
        # Generate team size between 3-7 people
        team_size = randint(3, 7)
        
        # Select random employees for this team
        selected_employees = sample(employees, min(team_size, len(employees)))
        
        # Generate team members from selected employees
        members = []
        for emp in selected_employees:
            member = {
                'name': f"{emp['first_name']} {emp['last_name']}",
                'email': emp['email'],
                'role': emp['job_title'],
                'department': emp['department']
            }
            members.append(member)
        
        # Create team object
        team = {
            'id': i + 1,
            'name': choice(PROJECT_NAMES),
            'members': members,
            'created_date': fake.date_between(start_date='-2y', end_date='today').strftime('%B %d, %Y'),
            'status': choice(['Active', 'Planning', 'In Progress', 'Review'])
        }
        teams.append(team)
    
    return teams

class Employee:
    def __init__(self):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()
        self.email = fake.email(0,"psu.edu")
        self.job_title = fake.job()
        self.department = choice(DEPARTMENTS)

def generate_employees(n_of_employees):
    employees = []
    for _ in range(n_of_employees):
        employee = Employee()
        employees.append({
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': employee.email,
            'job_title': employee.job_title,
            'department': employee.department,
            'employee_id': employee.email.split('@')[0]  # Use email as ID
        })
    return employees