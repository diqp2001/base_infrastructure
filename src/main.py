import numpy as np
from cProfile import Profile
from pstats import SortKey, Stats
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
'''with Profile() as profile:
    TestProjectManager().save_new_company_stock()
    (
        Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
    )
'''