import subprocess
import time
import numpy as np
import pandas as pd
from cProfile import Profile
from pstats import SortKey, Stats
from dask.distributed import Client, LocalCluster,Scheduler, Worker, Nanny
import dask.dataframe as dd
from sklearn.datasets import make_classification
from lightgbm.dask import DaskLGBMClassifier

from application.managers.api_managers.api_cboe.api_cboe_manager import download_and_consolidate_csv
from application.managers.project_managers.cross_sectionnal_ML_stock_returns_project.cross_sectionnal_ML_stock_returns_project_manager import CrossSectionalMLStockReturnsProjectManager
from application.managers.project_managers.test_project.test_project_manager import TestProjectManager


if __name__ == '__main__':

    msg = "Roll a dice!"
    print(msg)

    print(np.random.randint(1,9))


    def increment(x):
        return x + 1

    def decrement(x):
        return x - 1
    
    #consolidated_df = download_and_consolidate_csv()
    #CrossSectionalMLStockReturnsProjectManager().execute_database_management_tasks()
    #TestProjectManager().save_new_company_stock()
    '''with Profile() as profile:
        TestProjectManager().save_new_company_stock()
        (
            Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
        )
    '''


    