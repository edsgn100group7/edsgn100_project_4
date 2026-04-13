from faker import Faker 

fake = Faker()

class Employee:
    def __init__(self):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()
        self.email = fake.email()
        self.job_title = fake.job()
        self.department = fake.word().capitalize()
        self.salary = random.randint(40000, 120000)



def generate_employees(n_of_employees):
    for i_e in range(n_of_employees):
        