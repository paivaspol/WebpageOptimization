from argparse import ArgumentParser

import common_module
import subprocess
import os

def find_utilizations(root_dir, threshold):
    for path, dirs, filenames in os.walk(root_dir):
        if len(filenames) == 0:
            continue
        print path
        url = common_module.extract_url_from_path(path)
        if url == 'cnn.com':
            pcap_filename = os.path.join(path, 'output.pcap')
            network_filename = os.path.join(path, 'network_{0}'.format(url))
            start_end_time_filename = os.path.join(path, 'start_end_time_{0}'.format(url))
            page_request_size_filename = os.path.join(path, 'request_sizes.txt')
            command = 'python cdf_utilization_periods_requests_less_than_x.py {0} {1} {2} {3} {4} --output-dir {5}'.format(pcap_filename, network_filename, start_end_time_filename, page_request_size_filename, threshold, path)
            subprocess.call(command, shell=True)

def aggregate_utilizations(root_dir):
    less_than_x = []
    greater_than_x = []
    for path, dirs, filenames in os.walk(root_dir):
        if len(filenames) == 0:
            continue
        print path
        url = common_module.extract_url_from_path(path)
        less_than_x.extend(read_from_file(os.path.join(path, 'utilization_less_than_eq_x.txt')))
        greater_than_x.extend(read_from_file(os.path.join(path, 'utilization_greater_than_x.txt')))
    less_than_x.sort()
    greater_than_x.sort()
    return less_than_x, greater_than_x

def aggregate_request_sizes(root_dir, output_dir, filenames):
    for filename in filenames:
        result = []
        for path, dirs, filenames in os.walk(root_dir):
            if len(filenames) == 0:
                continue
            full_path = os.path.join(path, filename)
            with open(full_path, 'rb') as input_file:
                for raw_line in input_file:
                    result.append(float(raw_line.strip()))
        result.sort()
        output_to_file(result, os.path.join(output_dir, filename))

def read_from_file(filename):
    result = []
    with open(filename, 'rb') as input_file:
        for raw_line in input_file:
            utilization = raw_line.strip()
            result.append(float(utilization))
    return result

def output_to_file(utilizations, output_filename):
    with open(output_filename, 'wb') as output_file:
        for utilization in utilizations:
            output_file.write('{0}\n'.format(utilization))

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    parser.add_argument('threshold', type=int)
    parser.add_argument('--compute-utilizations', default=False, action='store_true')
    parser.add_argument('--output-dir', default='.')
    args = parser.parse_args()
    if args.compute_utilizations:
        find_utilizations(args.root_dir, args.threshold)
    less_than_x, greater_than_x = aggregate_utilizations(args.root_dir)
    output_to_file(less_than_x, os.path.join(args.output_dir, 'utilization_less_than_eq_x.txt'))
    output_to_file(greater_than_x, os.path.join(args.output_dir, 'utilization_greater_than_x.txt'))

    request_size_filenames = ['median_request_sizes_intervals_greater.txt', 'max_request_sizes_intervals_greater.txt', \
                            'median_request_sizes_intervals_less.txt', 'max_request_sizes_intervals_less.txt']
    aggregate_request_sizes(args.root_dir, args.output_dir, request_size_filenames)
