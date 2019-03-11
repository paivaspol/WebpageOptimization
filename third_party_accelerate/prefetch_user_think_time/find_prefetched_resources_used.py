'''
Another key important question to answer is the number of resources actually
used from prefetching.
'''
from argparse import ArgumentParser
from collections import defaultdict

import common_module
import numpy
import os
import random

PERCENTILES = [ 5, 25, 50, 75, 95 ]

def Main():
    histogram, page_resources, page_resource_sizes = \
            GetHistogramAndPageResourceMapping(args.root_dir)
    # print(len(page_resources.keys()))
    pages = SelectPages(page_resources.keys(), min(args.num_pages, len(page_resources.keys())), args.group_pages)
    if args.output_resource_count is not None:
        with open(args.output_resource_count, 'w') as output_file:
            for p in pages:
                output_file.write('{0} {1}\n'.format(p, len(page_resources[p])))

    sorted_histogram = sorted(histogram.items(), \
                            key=lambda x: (x[1], x[0]), \
                            reverse=True)
    prefetching = set()
    for resource_url, _ in sorted_histogram:
        prefetching.add(resource_url)

        fractions = []
        for p in pages:
            if len(page_resources[p]) == 0:
                continue
            page_intersection = prefetching & page_resources[p]
            fractions.append(
                    1.0 * len(page_intersection) / len(page_resources[p]))

        output = '{0}'.format(len(prefetching))
        for percentile in PERCENTILES:
            output += ' ' + \
                    str(numpy.percentile(fractions, percentile))
        print(output)


def GetHistogramAndPageResourceMapping(crawl_dir):
    histogram = defaultdict(int)
    page_resources = {}
    page_resource_sizes = {}
    base_page = common_module.GetBasePage(args.root_dir)
    for p in os.listdir(args.root_dir):
        network_filename = os.path.join(args.root_dir, p, 'network_' + p)
        if not os.path.exists(network_filename):
            continue
        urls, first_request, resource_sizes = common_module.GetURLsAndResourceSizes(network_filename)

        # This is just the same page...
        if first_request is None or \
            base_page == common_module.EscapeURL(first_request):
            continue

        for u in urls:
            histogram[u] += 1
        page_resources[p] = urls
        page_resource_sizes[p] = resource_sizes
    return histogram, page_resources, page_resource_sizes


def SelectPages(pages, num_pages, group_pages):
    '''
    Returns a list of selected pages.

    The default implementation sorts the pages alphabetically and pick the first
    n pages from the list.
    '''
    random.seed(42)
    pages_list = list(pages)
    if group_pages:
        pages_list = common_module.GetUrlsWithMostCommonPrefix(pages_list)
    print(pages_list)
    return random.sample(pages_list, min(num_pages, len(pages_list)))
    

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir', \
            help='The root directory that  contains the crawl data')
    parser.add_argument('--num-pages', \
                        type=int, \
                        help='The number of pages to consider', \
                        default=50)
    parser.add_argument('--output-resource-count', \
            help='The path to dump the resource count', \
            default=None)
    parser.add_argument('--group-pages', \
            help='Whether to group pages on some common prefix', \
            default=False, action='store_true')
    args = parser.parse_args()
    Main()
