from ConfigParser import ConfigParser
from utils import phone_connection_utils
from utils import chrome_utils

import requests
import os

def convert_to_ms_precision(timestamp):
    '''
    Converts the timestamp to millisecond precision.
    '''
    return timestamp * 1000

def extract_url_from_path(path):
    '''
    Extracts the url from the path.
    '''
    if path.endswith('/'):
        path = path[:len(path) - 1]
    last_delim_index = -1
    for i in range(0, len(path)):
        if path[i] == '/':
            last_delim_index = i
    url = path[last_delim_index + 1:].replace('/', '_')
    return url

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'
WWW_PREFIX = 'www.'
def escape_page(url):
    if url.endswith('/'):
        url = url[:len(url) - 1]
    if url.startswith(HTTPS_PREFIX):
        url = url[len(HTTPS_PREFIX):]
    elif url.startswith(HTTP_PREFIX):
        url = url[len(HTTP_PREFIX):]
    if url.startswith(WWW_PREFIX):
        url = url[len(WWW_PREFIX):]
    return url.replace('/', '_')


def parse_pages_to_ignore(pages_to_ignore_filename):
    pages = set()
    if pages_to_ignore_filename is not None:
        with open(pages_to_ignore_filename, 'rb') as input_file:
            for raw_line in input_file:
                line = raw_line.strip()
                pages.add(escape_page(line))
    print pages
    return pages

def parse_page_start_end_time(filename):
    with open(filename, 'rb') as input_file:
        line = input_file.readline().strip().split()
        web_perf_nav_start = float(line[1])
        web_perf_load_event = float(line[2])
        chrome_ts_nav_start = float(line[3])
        chrome_ts_load_event = float(line[4])
        return (line[0], (web_perf_nav_start, web_perf_load_event), (chrome_ts_nav_start, chrome_ts_load_event))

NEXUS_6_CONFIG = '../device_config/nexus6.cfg'
NEXUS_6 = 'Nexus_6'
NEXUS_6_CHROMIUM_CONFIG = '../device_config/nexus6_chromium.cfg'
NEXUS_6_CHROMIUM = 'Nexus_6_chromium'
NEXUS_6_2_CONFIG = '../device_config/nexus6_2.cfg'
NEXUS_6_2 = 'Nexus_6_2'
NEXUS_6_2_CHROMIUM_CONFIG = '../device_config/nexus6_2_chromium.cfg'
NEXUS_6_2_CHROMIUM = 'Nexus_6_2_chromium'
NEXUS_5_CONFIG = '../device_config/nexus5.cfg'
NEXUS_5 = 'Nexus_5'
MAC_CONFIG = '../device_config/mac.cfg'
MAC = 'mac'
UBUNTU_CONFIG = '../device_config/ubuntu.cfg'
UBUNTU = 'ubuntu'

def get_device_config(device):
    device_config_filename = ''
    device_config_object = None
    if device == NEXUS_6:
        device = NEXUS_6
        device_config_filename = NEXUS_6_CONFIG
    elif device == NEXUS_6_2:
        device = NEXUS_6_2
        device_config_filename = NEXUS_6_2_CONFIG
    elif device == NEXUS_5:
        device = NEXUS_5
        device_config_filename = NEXUS_5_CONFIG
    elif device == MAC:
        device = MAC
        device_config_filename = MAC_CONFIG
    elif device == NEXUS_6_CHROMIUM:
        device = NEXUS_6_CHROMIUM
        device_config_filename = NEXUS_6_CHROMIUM_CONFIG
    elif device == NEXUS_6_2_CHROMIUM:
        device = NEXUS_6_2_CHROMIUM
        device_config_filename = NEXUS_6_2_CHROMIUM_CONFIG
    elif device == UBUNTU:
        device = UBUNTU
        device_config_filename = UBUNTU_CONFIG
    else:
        print 'available devices: {0}, {1}, {2}, {3}, {4}, {5}'.format(NEXUS_6, NEXUS_6_2, NEXUS_5, NEXUS_6_CHROMIUM, NEXUS_6_2_CHROMIUM, MAC, UBUNTU)
        exit(1)
    config_reader = ConfigParser()
    config_reader.read(device_config_filename)
    device_config_obj = phone_connection_utils.get_device_configuration(config_reader, device)
    return device, device_config_filename, device_config_obj

def initialize_browser(device_info):
    # Get the device configuration
    print 'initializing browser...'
    phone_connection_utils.wake_phone_up(device_info[2])
    print 'Stopping Chrome...'
    phone_connection_utils.stop_chrome(device_info[2])
    print 'Starting Chrome...'
    phone_connection_utils.start_chrome(device_info[2])
    closed_tabs = False
    while not closed_tabs:
        try:
            chrome_utils.close_all_tabs(device_info[2])
            closed_tabs = True
        except requests.exceptions.ConnectionError as e:
            pass

def check_previous_page_load(current_run_index, base_output_dir, raw_line):
    if current_run_index > 0:
        url = escape_page(raw_line.strip())
        output_dir_prev_run = os.path.join(os.path.join(base_output_dir, str(current_run_index - 1)), url)
        prev_run_start_end_time = os.path.join(output_dir_prev_run, 'start_end_time_' + url)
        output_dir_cur_run = os.path.join(os.path.join(base_output_dir, str(current_run_index)), url)
        cur_run_start_end_time = os.path.join(output_dir_cur_run, 'start_end_time_' + url)
        if not os.path.exists(prev_run_start_end_time) or not os.path.exists(cur_run_start_end_time):
            return False
        with open(prev_run_start_end_time, 'rb') as input_file:
            prev_line = input_file.readline()
        with open(cur_run_start_end_time, 'rb') as input_file:
            cur_line = input_file.readline()
        return prev_line == cur_line
    return False

def get_start_end_time(current_run_index, base_output_dir, page_url):
    url = escape_page(page_url.strip())
    output_dir_cur_run = os.path.join(os.path.join(base_output_dir, str(current_run_index)), url)
    cur_run_start_end_time = os.path.join(output_dir_cur_run, 'start_end_time_' + url)
    if not os.path.exists(cur_run_start_end_time):
        return -1, -1

    with open(cur_run_start_end_time, 'rb') as input_file:
        cur_line = input_file.readline().strip().split()
        start_time = int(cur_line[1])
        end_time = int(cur_line[2])
    return start_time, end_time

def get_pages(pages_file):
    pages = []
    with open(pages_file, 'rb') as input_file:
        for raw_line in input_file:
            if not raw_line.startswith('#'):
                line = raw_line.strip().split()
                pages.append(line[len(line) - 1])
    return pages
