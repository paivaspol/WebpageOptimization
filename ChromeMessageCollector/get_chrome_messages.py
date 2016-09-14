import common_module
import json
import requests
import signal
import subprocess
import sys
import os
import websocket
import shutil

from utils import phone_connection_utils
from utils import navigation_utils
from utils import chrome_utils

from argparse import ArgumentParser
from ConfigParser import ConfigParser   # Parsing configuration file.
from bs4 import BeautifulSoup # Beautify HTML
from time import sleep
from RDPMessageCollector.ChromeRDPWebsocket import ChromeRDPWebsocket # The websocket
from RDPMessageCollector.ChromeRDPWebsocketStreaming import ChromeRDPWebsocketStreaming # The websocket
from RDPMessageCollector.ChromeRDPWithoutTracking import ChromeRDPWithoutTracing

HTTP_PREFIX = 'http://'
WWW_PREFIX = 'www.'
OUTPUT_DIR = None
PAGE_ID = None

def main(device_configuration, url, disable_tracing, reload_page):
    '''
    The main workflow of the script.
    '''
    output_directory = create_output_directory_for_url(url)
    
    if device_configuration[phone_connection_utils.DEVICE_TYPE] != phone_connection_utils.DEVICE_MAC and \
        device_configuration[phone_connection_utils.DEVICE_TYPE] != phone_connection_utils.DEVICE_UBUNTU:
        cpu_chrome_running_on = phone_connection_utils.get_cpu_running_chrome(device_configuration)
        output_cpu_running_chrome(output_directory, cpu_chrome_running_on)

    got_debugging_url = False
    while not got_debugging_url:
        try:
            debugging_url, page_id = chrome_utils.get_debugging_url(device_configuration)
            got_debugging_url = True
        except (requests.exceptions.ConnectionError, KeyError) as e:
            pass

    print 'Connected to Chrome...'
    device_configuration['page_id'] = page_id
    user_agent_str = None
    screen_size_config = None
    if phone_connection_utils.USER_AGENT in device_configuration:
        user_agent_str = device_configuration[phone_connection_utils.USER_AGENT]
    if phone_connection_utils.SCREEN_SIZE in device_configuration:
        screen_size_config = device_configuration[phone_connection_utils.SCREEN_SIZE]

    if args.collect_streaming:
        # First, remove the network file, if it exists
        escaped_url = common_module.escape_page(url)
        network_filename = os.path.join(output_directory, 'network_' + escaped_url)
        print 'network_filename: ' + network_filename
        if os.path.exists(network_filename):
            print 'Removing ' + network_filename
            os.remove(network_filename)

        debugging_socket = ChromeRDPWebsocketStreaming(debugging_url, url, device_configuration, user_agent_str, args.collect_console, callback_on_received_event, callback_on_page_done_streaming)
        if args.get_dependency_baseline:
            def timeout_handler(a, b):
                callback_on_page_done_streaming(debugging_socket)
                sys.exit(0)

            print 'Setting SIGTERM handler'
            signal.signal(signal.SIGTERM, timeout_handler)
        debugging_socket.start()

    elif disable_tracing:
        chrome_rdp_object_without_tracing = ChromeRDPWithoutTracing(debugging_url, url, user_agent_str, screen_size_config)
        start_time, end_time = chrome_rdp_object_without_tracing.navigate_to_page(url, reload_page)
        print str((start_time, end_time)) + ' ' + str((end_time - start_time))
        escaped_url = common_module.escape_page(url)
        print 'output_directory: ' + output_directory
        write_page_start_end_time(escaped_url, output_directory, start_time, end_time)
    else:
        debugging_socket = ChromeRDPWebsocket(debugging_url, url, device_configuration, reload_page, user_agent_str, screen_size_config, callback_on_page_done)
    
def output_cpu_running_chrome(output_directory, cpu_id):
    '''
    Outputs the CPU id that is running chrome.
    '''
    cpu_running_chrome_filename = os.path.join(output_directory, 'cpu_running_chrome.txt')
    with open(cpu_running_chrome_filename, 'wb') as output_file:
        output_file.write(cpu_id)

def create_output_directory_for_url(url):
    '''
    Creates an output directory for the url
    '''
    base_dir = ''
    if OUTPUT_DIR is not None:
        base_dir = os.path.join(base_dir, OUTPUT_DIR)
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
    
    final_url = common_module.escape_page(url)

    base_dir = os.path.join(base_dir, final_url)
    # Create the directory if the directory doesn't exist.
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    return base_dir

def callback_on_received_event(debugging_socket, network_message, network_message_string):
    if 'method' in network_message and network_message['method'].startswith('Network'):
        url = debugging_socket.get_navigation_url()
        base_dir = create_output_directory_for_url(url)
        final_url = common_module.escape_page(url)
        network_filename = os.path.join(base_dir, 'network_' + final_url)
        with open(network_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(json.dumps(network_message_string)))
    elif 'method' in network_message and network_message['method'].startswith('Console'):
        url = debugging_socket.get_navigation_url()
        base_dir = create_output_directory_for_url(url)
        final_url = common_module.escape_page(url)
        network_filename = os.path.join(base_dir, 'console_' + final_url)
        with open(network_filename, 'ab') as output_file:
            output_file.write('{0}\n'.format(json.dumps(network_message_string)))

def callback_on_page_done_streaming(debugging_socket):
    debugging_socket.close_connection()
    print 'Closed debugging socket connection'

    sleep(2)
    url = debugging_socket.get_navigation_url()
    debugging_url = debugging_socket.get_debugging_url()
    final_url = common_module.escape_page(url)
    base_dir = create_output_directory_for_url(url)
    
    new_debugging_websocket = websocket.create_connection(debugging_url)
    # Get the start and end time of the execution
    start_time, end_time = navigation_utils.get_start_end_time_with_socket(new_debugging_websocket)
    # print 'output dir: ' + base_dir
    print 'Load time: ' + str((start_time, end_time)) + ' ' + str((end_time - start_time))
    write_page_start_end_time(final_url, base_dir, start_time, end_time, -1, -1)
    new_debugging_websocket.close()
    # chrome_utils.close_tab(debugging_socket.device_configuration, debugging_socket.device_configuration['page_id'])

def callback_on_page_done(debugging_socket, network_messages, timeline_messages, original_request_ts, load_event_ts, request_ids, device_configuration):
    '''
    Sets up the call back once the page is done loading.
    '''
    print 'Page load done. len(request_ids): ' + str(len(request_ids))
    # First, close the connection.
    debugging_socket.close_connection()
    url = debugging_socket.get_navigation_url()
    debugging_url = debugging_socket.get_debugging_url()
    final_url = common_module.escape_page(url)
    base_dir = create_output_directory_for_url(url)
    
    debugging_websocket = websocket.create_connection(debugging_url)

    if args.record_content:
        output_dir = os.path.join(base_dir, 'response_body')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        output_response_body(debugging_websocket, request_ids, output_dir)
        modified_html = navigation_utils.get_modified_html(debugging_websocket)
        modified_html_filename = os.path.join(output_dir, 'modified_html.html')
        with open(modified_html_filename, 'wb') as output_file:
            output_file.write(beautify_html(modified_html))

    # Get the start and end time of the execution
    start_time, end_time = navigation_utils.get_start_end_time_with_socket(debugging_websocket)
    # print 'output dir: ' + base_dir
    write_page_start_end_time(final_url, base_dir, start_time, end_time, original_request_ts, load_event_ts)
    
    network_filename = os.path.join(base_dir, 'network_' + final_url)
    timeline_filename = os.path.join(base_dir, 'timeline_' + final_url)
    with open(network_filename, 'wb') as output_file:
        for message in network_messages:
            output_file.write('{0}\n'.format(json.dumps(message)))
    # Output timeline objects
    if len(timeline_messages) > 0:
        with open(timeline_filename, 'wb') as output_file:
            for message in timeline_messages:
                output_file.write('{0}\n'.format(json.dumps(message)))
    # get_resource_tree(debugging_url)

    chrome_utils.close_tab(debugging_socket.device_configuration, debugging_socket.device_configuration['page_id'])

def beautify_html(original_html):
    return BeautifulSoup(original_html, 'html.parser').prettify().encode('utf-8')

def write_page_start_end_time(escaped_url, base_dir, start_time, end_time, original_request_ts=-1, load_event_ts=-1):
    start_end_time_filename = os.path.join(base_dir, 'start_end_time_' + escaped_url)
    with open(start_end_time_filename, 'wb') as output_file:
        output_file.write('{0} {1} {2} {3} {4}\n'.format(escaped_url, start_time, end_time, original_request_ts, load_event_ts))

def output_response_body(debugging_websocket, request_ids, output_dir):
    '''
    Writes the responses of all the requests to files. Also write the mapping
    between request id to url to another file.
    '''
    responses_output_dir = output_dir 
    request_id_mapping_filename = os.path.join(responses_output_dir, 'request_id_to_url.txt')
    with open(request_id_mapping_filename, 'wb') as output_file:
        for request_id in request_ids:
            request_id, url, response_body, is_request_to_index = request_ids[request_id]
            output_file.write('{0} {1}\n'.format(request_id, url))
            response_filename = os.path.join(responses_output_dir, request_id)
            if is_request_to_index:
                response_filename = os.path.join(responses_output_dir, 'index.html')
                
            with open(response_filename, 'wb') as response_output_file:
                response_output_file.write(beautify_html(response_body))

def get_resource_tree(debugging_url):
    try:
        ws = websocket.create_connection(debugging_url)
        get_resource_tree = json.dumps({ "id": 6, "method": "Page.getResourceTree", "params": { }})
        # print 'navigation starts: ' + str(navigation_starts)
        ws.send(get_resource_tree)
        resource_tree = json.loads(ws.recv())
        # print 'start time: ' + str(nav_starts_result)
        print resource_tree
    except Exception as e:
        pass
    finally:
        ws.close()

def clear_directory(directory):
    files = os.listdir(directory)
    for f in files:
        if os.isfile(f):
            os.remove(os.path.join(directory, f))


if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('config_filename')
    argparser.add_argument('device', help='The device name e.g. Nexus_6')
    argparser.add_argument('url', help='The URL to navigate to e.g. http://apple.com')
    argparser.add_argument('--output-dir', help='The output directory of the generated files', default=None)
    argparser.add_argument('--disable-tracing', default=False, action='store_true')
    argparser.add_argument('--reload-page', default=False, action='store_true')
    argparser.add_argument('--record-content', default=False, action='store_true')
    argparser.add_argument('--collect-streaming', default=False, action='store_true')
    argparser.add_argument('--collect-console', default=False, action='store_true')
    argparser.add_argument('--get-chromium-logs', default=False, action='store_true')
    argparser.add_argument('--get-dependency-baseline', default=False, action='store_true')
    args = argparser.parse_args()

    # Setup the config filename
    config_reader = ConfigParser()
    config_reader.read(args.config_filename)
    OUTPUT_DIR = args.output_dir

    print 'collect streaming: ' + str(args.collect_streaming)

    # Get the device configuration.
    device_config = phone_connection_utils.get_device_configuration(config_reader, args.device)
    main(device_config, args.url, args.disable_tracing, args.reload_page)
