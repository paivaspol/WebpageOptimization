import os
import subprocess

from argparse import ArgumentParser

def Main():
    for d in os.listdir(args.root_dir):
        path = os.path.join(args.root_dir, d)
        cmd = 'rm {path}/text.*'.format(path=path)
        subprocess.call(cmd, shell=True)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('root_dir')
    args = parser.parse_args()
    Main()
