
import sys
import os
import json

sys.path.append(os.getcwd())

import Core.data_loader_v5 as loader

def check_keys():
    rotations = loader.extract_json_from_md("Data/사이클_로테이션_마스터.md")
    print("Available keys in rotations:")
    for key in rotations.keys():
        print(f"'{key}'")

if __name__ == "__main__":
    check_keys()
