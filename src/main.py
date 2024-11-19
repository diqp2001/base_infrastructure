import numpy as np

from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.cross_sectionnal_ML_stock_returns_project_manager import CrossSectionalMLStockReturnsProjectManager
from application.managers.project_managers.test_project.test_project_manager import TestProjectManager

msg = "Roll a dice!"
print(msg)

print(np.random.randint(1,9))


def increment(x):
    return x + 1

def decrement(x):
    return x - 1

#CrossSectionalMLStockReturnsProjectManager().execute_database_management_tasks()

TestProjectManager().save_new_company_stock()
