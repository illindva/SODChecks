import multiprocessing

bind = "0.0.0.0:5000"
# Keep 1 worker so APScheduler only has 1 instance running in memory.
# Increase threads for handling multiple concurrent web requests.
workers = 1
threads = 4
timeout = 120
loglevel = "info"
accesslog = "-"
errorlog = "-"
preload_app = True
