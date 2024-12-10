import subprocess
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



    # Step 1: Set up the Dask cluster and client
    cluster = LocalCluster(n_workers=0, scheduler_port=8786,threads_per_worker=2)
    # Start the scheduler
    scheduler = cluster.scheduler # Scheduler port
    scheduler_address = scheduler.address

   
    # Start the first Dask worker
    subprocess.Popen(["dask", "worker", "127.0.0.1:8786", "--worker-port", "12400", "--host", "127.0.0.1"])
    subprocess.Popen(["dask", "worker", "127.0.0.1:8786", "--worker-port", "12400", "--host", "127.0.0.2"])
    subprocess.Popen(["dask", "worker", "127.0.0.1:8786", "--worker-port", "12400", "--host", "127.0.0.3"])
    subprocess.Popen(["dask", "worker", "127.0.0.1:8786", "--worker-port", "12400", "--host", "127.0.0.4"])
    # Connect a client
    client = Client(cluster)
  
    # Get worker addresses
    worker_addresses =[myworker.listen_address for key,myworker in cluster.workers.items()]
    machines = ','.join([addr.split('://')[1] for addr in worker_addresses])


    # Step 2: Generate synthetic training and testing data
    def generate_data(n_samples, n_features):
        X, y = make_classification(
            n_samples=n_samples,
            n_features=n_features,
            n_informative=int(n_features * 0.6),
            n_redundant=int(n_features * 0.2),
            random_state=42
        )
        df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(n_features)])
        df['label'] = y
        return df

    # Convert to Dask DataFrames
    train_df = dd.from_pandas(generate_data(100, 10), npartitions=4)
    test_df = dd.from_pandas(generate_data(20, 10), npartitions=2)

    # Split features and target
    train_X = train_df.iloc[:, :-1]
    train_y = train_df['label']
    test_X = test_df.iloc[:, :-1]
    test_y = test_df['label']

    # Step 3: Train the Dask-LightGBM model
    params = {
        'objective': 'binary',
        'boosting_type': 'gbdt',
        'metric': 'binary_logloss',
        'n_estimators': 3,
        'num_leaves': 31,
        'learning_rate': 0.1,
        'local_listen_port': 12400,
        #'machines': machines,
        'verbosity': 3
    }

    # Train the model
    #model = DaskLGBMClassifier(**params, client=client)
    model = DaskLGBMClassifier(**params)
    model.fit( X=train_X, y=train_y)

    # Step 4: Make predictions
    predictions = model.predict(test_X)

    # Gather predictions to a single pandas DataFrame for evaluation
    predictions_df = predictions.compute()
    print("Predictions:", predictions_df)

    # Step 5: Evaluate the model
    from sklearn.metrics import accuracy_score
    test_y_true = test_y.compute()
    accuracy = accuracy_score(test_y_true, predictions_df)
    print(f"Accuracy: {accuracy:.4f}")

    # Shutdown the client and cluster
    client.close()
    cluster.close()