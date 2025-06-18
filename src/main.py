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
from application.managers.project_managers.momentum_ML_project.momentum_ML_project import MomentumMLProjectManager
from application.managers.project_managers.test_project.test_project_manager import TestProjectManager

def increment(x: int) -> int:
    return x + 1

if __name__ == '__main__':

    
    
    #consolidated_df = download_and_consolidate_csv()
    #CrossSectionalMLStockReturnsProjectManager().execute_database_management_tasks()
    #TestProjectManager().save_new_company_stock()
    with Profile() as profile:
        #MomentumMLProjectManager().test_single_future()
        (
            Stats(profile).strip_dirs().sort_stats(SortKey.CALLS).print_stats()
        )
   


    