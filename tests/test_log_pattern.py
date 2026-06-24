import sys
import os

# Add the parent directory to the python path so we can import runners
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runners import LogPatternCheckRunner

class DummyHealthCheck:
    """
    A mock health check object to simulate what comes from the database.
    """
    def __init__(self):
        self.host = "localhost" # 'localhost' ensures it runs locally without SSH
        self.search_pattern = "ERROR" # What we are looking for
        self.target_path = "dummy_test.log" # The log file to search in

def run_test():
    # 1. Create a dummy log file to test against
    print(f"Creating dummy log file: dummy_test.log")
    with open("dummy_test.log", "w") as f:
        f.write("INFO: Application started successfully\n")
        f.write("DEBUG: Checking configurations...\n")
        f.write("ERROR: Database connection failed (simulated error)\n")
    
    # 2. Initialize our mock check and the runner
    check = DummyHealthCheck()
    runner = LogPatternCheckRunner(check)
    
    # 3. Execute the runner
    print(f"\n--- Running LogPatternCheckRunner ---")
    print(f"Looking for pattern '{check.search_pattern}' in '{check.target_path}'")
    status, message, metrics = runner.run()
    
    # 4. Print the results
    print(f"\n--- Results ---")
    print(f"Status: {status}")
    print(f"Message: {message}")
    print(f"Metrics: {metrics}")
    
    # 5. Cleanup the dummy file
    print(f"\nCleaning up dummy log file...")
    os.remove("dummy_test.log")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
