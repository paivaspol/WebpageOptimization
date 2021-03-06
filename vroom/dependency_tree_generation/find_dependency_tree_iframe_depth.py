from argparse import ArgumentParser

import common_module
import os
import simplejson as json

def main(root_dir):
    pages = os.listdir(root_dir)
    for page in pages:
        dependency_tree_filename = os.path.join(root_dir, page)
        page = get_page_name(page)
        try:
            tree_depth = find_dependency_tree_depth(dependency_tree_filename, page)
            if tree_depth > 0:
                print '{0} {1}'.format(page, tree_depth)
        except RuntimeError as e:
            pass

def find_dependency_tree_depth(dependency_tree_filename, page):
    with open(dependency_tree_filename, 'rb') as input_file:
        dependency_tree = json.load(input_file)
    root_node = find_root_node(page, dependency_tree)
    if root_node is not None:
        return bfs(dependency_tree, root_node, 0)
    return -1

def bfs(dependency_tree, current_node, current_depth):
    children = current_node['children']
    max_depth = current_depth
    for child in children:
        child_node = dependency_tree[child]
        next_depth = current_depth + 1 if child_node['type'] == 'Document' else current_depth
        current_tree_depth = bfs(dependency_tree, child_node, next_depth)
        max_depth = max(max_depth, current_tree_depth)
    return max_depth

def find_root_node(page, dependency_tree):
    for node in dependency_tree:
        escaped_page = common_module.escape_url(node)
        if escaped_page == page:
            return dependency_tree[node]
    return None

def get_page_name(page_with_json_suffix):
    return page_with_json_suffix[:len(page_with_json_suffix) - len('.json')]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    args = parser.parse_args()
    main(args.root_dir)
