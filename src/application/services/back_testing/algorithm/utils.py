def schedule(func, cron: str):
    print(f"Scheduled {func.__name__} with CRON {cron}")

def set_runtime(config):
    print("Runtime configuration set:", config)
