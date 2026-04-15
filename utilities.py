from faker import Faker 
from random import choice, randint, sample

fake = Faker()

DEPARTMENTS = ['Tree', 'Soldier', 'With', 'Him', 'Roland', 'School', 'Present', 'Deep', 'Pass', 'Central', 'Responsibility', 'Benefit', 'Catch', 'Other', 'Order', 'Space', 'Weight', 'Heavy', 'Traditional', 'Recently', 'Especially', 'Gun', 'Case', 'Performance', 'All', 'Direction']

PROJECT_NAMES = [
    'Engineering Lab Initiative', 'Research Development Project', 'STEM Education Program', 'Technical Training System',
    'Curriculum Development Framework', 'Educational Technology Platform', 'Engineering Design Challenge', 'Learning Management System',
    'Research Laboratory Project', 'Technical Documentation System', 'Educational Assessment Tool', 'Engineering Simulation Platform',
    'Academic Research Initiative', 'Technical Skills Development', 'Educational Content Management', 'Engineering Analysis System',
    'Learning Analytics Platform', 'Technical Infrastructure Project', 'Curriculum Design Framework', 'Educational Software Development',
    'Engineering Education Portal', 'Research Data Management', 'Technical Training Module', 'Educational Assessment Framework'
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
        self.middle_name = fake.first_name()
        self.last_name = fake.last_name()
        self.email = self.generate_email()
        self.job_title = fake.job()
        self.department = choice(DEPARTMENTS)
    
    def generate_email(self):
        # Format: first letter of first, middle last name, then 4 numbers, @psu.edu
        # Example: John Henry Mimbole = jhm5384@psu.edu
        first_initial = self.first_name[0].lower()
        middle_initial = self.middle_name[0].lower()
        last_initial = self.last_name[0].lower()
        random_numbers = fake.random_int(min=1000, max=9999)
        return f"{first_initial}{middle_initial}{last_initial}{random_numbers}@psu.edu"

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