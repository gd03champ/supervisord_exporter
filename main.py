import argparse
import logging
import time
from xmlrpc.client import ServerProxy
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST


# Command line arguments
parser = argparse.ArgumentParser(description='Supervisor Exporter')
parser.add_argument('--supervisord-url', default='http://localhost:9001/RPC2', help='Supervisord XML-RPC URL')
parser.add_argument('--listen-address', default=':9101', help='Address to listen for HTTP requests')
parser.add_argument('--metrics-path', default='/metrics', help='Path under which to expose metrics')
parser.add_argument('--version', action='store_true', help='Displays application version')
args = parser.parse_args()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics definition
processes_metric = Gauge(
    'supervisor_process_info', 
    'Supervisor process information', [
        'pid',
        'name', 
        'group', 
        'state',    
        'start_time',
        'stop_time',
        'now_time',
        'description',
        'exit_status'
        ])
supervisor_process_uptime = Gauge('supervisor_process_uptime', 'Uptime of Supervisor processes', ['name', 'group'])
supervisord_up = Gauge('supervisord_up', 'Supervisord XML-RPC connection status (1 if up, 0 if down)')

# Fetch Supervisor process info
def fetch_supervisor_process_info(supervisord_url):
    try:
        proxy = ServerProxy(supervisord_url)
        result = proxy.supervisor.getAllProcessInfo()
        #print(result)
        #logger.debug(f"Supervisor process info: {result}")
        supervisord_up.set(1)

        # Create a map to store the latest process information for each unique combination of name and group
        latest_info = {}

        for data in result:
            name = data['name']
            group = data['group']

            # Generate a unique key for the combination of name and group
            key = name + group

            # Check if the latest information for this combination already exists
            if key in latest_info:
                existing_start_time = latest_info[key]['start']
                new_start_time = data['start']

                # If the new information is more recent, update the latest_info map
                if new_start_time > existing_start_time:
                    latest_info[key] = data
            else:
                # If no previous information exists for this combination, add it to the map
                latest_info[key] = data

        # Clear the previous metric values
        processes_metric._metrics.clear()
        supervisor_process_uptime._metrics.clear()

        for data in latest_info.values():
            pid = data['pid']
            name = data['name']
            group = data['group']
            state = data['statename']
            exit_status = data['exitstatus']
            start_time = data['start']

            stop_time = data['stop']
            now_time = data['now']
            description = data['description']

            value = 0 if state != 'RUNNING' else 1
            processes_metric.labels(
                pid=pid, 
                name=name, 
                group=group, 
                state=state, 
                start_time=str(start_time),
                stop_time=str(stop_time),
                now_time=str(now_time),
                description=description,
                exit_status=str(exit_status)).set(value)

            # Calculate uptime and set the supervisor_process_uptime metric
            if value == 1:
                uptime = time.time() - start_time
                supervisor_process_uptime.labels(name=name, group=group).set(uptime)

    except Exception as e:
        logger.error(f"Error fetching Supervisor process info: {e}")
        supervisord_up.set(0)
        processes_metric._metrics.clear()
        supervisor_process_uptime._metrics.clear()

# HTTP request handler
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == args.metrics_path:
            fetch_supervisor_process_info(args.supervisord_url)
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            data = generate_latest()
            if isinstance(data, str):
                data = data.encode()
            self.wfile.write(data)
        else:
            self.send_error(404, 'Not Found')

# Main function
def main():
    if args.version:
        print("Supervisor Exporter v0.1")
        return
#    if args.listen_address.split(':')[0] != 'localhost':
#        print("Working on it. Contact ganish.n_int@external.swiggy.in in meantime.")
#        return

    try:
        # Start HTTP server
        with HTTPServer(('localhost', int(args.listen_address.split(':')[1])), RequestHandler) as server:
            logger.info(f"Listening on {args.listen_address}")
            server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
