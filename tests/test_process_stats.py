import sys
import os

# Add the parent directory to the python path so we can import runners
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runners import ProcessCheckRunner

class DummyHealthCheck:
    """
    A mock health check object to simulate what comes from the database.
    """
    def __init__(self):
        self.host = "localhost" # 'localhost' ensures it runs locally without SSH
        
        # Target the current python process running this script by getting its PID
        self.target_path = str(os.getpid()) 

def run_test():
    # 1. Initialize our mock check and the runner
    check = DummyHealthCheck()
    runner = ProcessCheckRunner(check)
    
    # 2. Execute the runner
    print(f"\n--- Running ProcessCheckRunner ---")
    print(f"Target Process ID: {check.target_path}")
    status, message, metrics = runner.run()
    
    # 3. Print the results
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
