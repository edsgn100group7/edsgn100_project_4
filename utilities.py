from faker import Faker 
from random import choice

fake = Faker()

DEPARTMENTS = ['Tree', 'Soldier', 'With', 'Him', 'School', 'Present', 'Deep', 'Pass', 'Central', 'Responsibility', 'Benefit', 'Catch', 'Other', 'Order', 'Space', 'Weight', 'Heavy', 'Traditional', 'Recently', 'Especially', 'Gun', 'Case', 'Performance', 'All', 'Direction']

class Employee:
    def __init__(self):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()
        self.email = fake.email(0,"psu.edu")
        self.job_title = fake.job()
        self.department = choice(DEPARTMENTS)

def generate_employees(n_of_employees):
    return [Employee() for _ in range(n_of_employees)]