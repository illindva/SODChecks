import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from runners import JsonToHtmlCheckRunner, HtmlToJsonCheckRunner

class DummyHealthCheck:
    def __init__(self, data):
        self.host = "localhost"
        self.search_pattern = data # Data payload (JSON or HTML)

def run_test():
    # 1. Test JSON to HTML
    print("\n--- Running JsonToHtmlCheckRunner ---")
    json_data = '[{"Name": "App1", "Status": "UP"}, {"Name": "App2", "Status": "DOWN"}]'
    print(f"Input JSON: {json_data}")
    
    check_json = DummyHealthCheck(json_data)
    runner_json = JsonToHtmlCheckRunner(check_json)
    
    status_j, message_j, metrics_j = runner_json.run()
    print(f"Status: {status_j}")
    print(f"HTML Output: \n{metrics_j.get('html', 'No HTML output')}")
    
    # 2. Test HTML to JSON
    print("\n--- Running HtmlToJsonCheckRunner ---")
    html_data = "<table><tr><th>Name</th><th>Status</th></tr><tr><td>App1</td><td>UP</td></tr></table>"
    print(f"Input HTML: {html_data}")
    
    check_html = DummyHealthCheck(html_data)
    runner_html = HtmlToJsonCheckRunner(check_html)
    
    status_h, message_h, metrics_h = runner_html.run()
    print(f"Status: {status_h}")
    print(f"JSON Output: \n{metrics_h.get('json', 'No JSON output')}")
    print("Test finished.")

if __name__ == "__main__":
    run_test()
