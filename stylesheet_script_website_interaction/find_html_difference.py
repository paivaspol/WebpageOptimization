from argparse import ArgumentParser
from bs4 import BeautifulSoup, NavigableString
from collections import defaultdict

import common_module
import os
import re

def process_pages(pages, root_dir, output_dir):
    common_module.create_directory_if_not_exists(output_dir)
    for page in pages:
        print 'processing: ' + page
        escaped_page = common_module.escape_page(page)
        site_directory = os.path.join(root_dir, escaped_page, 'response_body')
        index_filename = os.path.join(site_directory, 'index.html')
        modified_index_filename = os.path.join(site_directory, 'modified_html.html')
        index_tree = get_page_tree_object(index_filename)
        modified_index_tree = get_page_tree_object(modified_index_filename)
        histogram = find_extra_elements(index_tree, modified_index_tree)
        output_filename = os.path.join(output_dir, escaped_page)
        write_histogram(histogram, output_filename)

def write_histogram(histogram, output_filename):
    with open(output_filename, 'wb') as output_file:
        for tag_name, count in histogram.iteritems():
            output_file.write('{0} {1}\n'.format(tag_name, count))

def find_extra_elements(index_html_tree, modified_index_html_tree):
    '''
    The result will be elements that are contained in the modified index tree
    but not in the index tree. Equivalent to difference of mod_index_tree and
    index_tree where we assume that the elements of the mod_index_tree is a 
    superset of index_tree.
    '''
    histogram = defaultdict(lambda: 0)
    process_queue = [ modified_index_html_tree ]
    # Do a BFS on the modified index html tree.
    while len(process_queue) > 0:
        current_element = process_queue.pop(0)
        # Find this element in |index_html_tree|
        if not find_element_in_original_html_tree(index_html_tree, current_element):
            tag_name = current_element.name
            histogram[tag_name] += 1

        if hasattr(current_element, 'children'):
            for child in current_element.children:
                if type(child) != NavigableString:
                    process_queue.append(child)
    return histogram

def find_element_in_original_html_tree(original_html_tree, element_to_find):
    element_found = False
    tag_name = element_to_find.name

    attributes = None
    if hasattr(element_to_find, 'attrs'):
        attributes = element_to_find.attrs
        if 'style' in attributes:
            # Style is unnecessary... TODO: revisit
            del attributes['style']

    content = element_to_find.string
    if attributes is not None:
        find_result = original_html_tree.find_all(tag_name, attrs=attributes)
    else:
        find_result = original_html_tree.find_all(tag_name)

    if content is not None and len(content) > 0:
        for element in find_result:
            if element.string is not None and element.string.strip() == content.strip():
                # print '[Matched with Content] tag: ' + tag_name + ' attributes: ' + str(attributes) + ' found: ' + element.string.strip() + ' and: ' + content.strip()
                element_found = True
                break
    else:
        element_found = True
        # print '[No Content] tag: ' + tag_name + ' attributes: ' + str(attributes) + ' found: ' + str(len(find_result))
    return element_found

def get_page_tree_object(html_filename):
    return BeautifulSoup(open(html_filename), 'html.parser')

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    parser.add_argument('pages_file')
    parser.add_argument('output_dir')
    args = parser.parse_args()
    pages = common_module.parse_pages_file(args.pages_file)
    process_pages(pages, args.root_dir, args.output_dir)
