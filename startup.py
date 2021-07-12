#!/usr/bin/env python3

import subprocess
import argparse


class ProcessRunner:
    def __init__(self, processes_to_run):
        self._processes_to_run = processes_to_run

    def run(self):
        popen_objects_list = []
        for command in self._processes_to_run:
            popen_object = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            popen_objects_list.append(popen_object.args)
        return popen_objects_list


def parse_args():
    parser = argparse.ArgumentParser(description='This script runs the application.')
    parser.add_argument('config_path', help='Path to config file', type=str)
    return parser.parse_args()


def main():
    path_to_config = vars(parse_args())['config_path']
    runner = ProcessRunner(processes_to_run=[f"./controller.py {path_to_config}",
                                             f"./installer.py {path_to_config}"])
    running_processes = runner.run()
    print('\n'.join([f'Starting up {x}...' for x in running_processes]))


if __name__ == '__main__':
    main()
