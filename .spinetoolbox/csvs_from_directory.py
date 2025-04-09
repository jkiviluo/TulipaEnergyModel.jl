import os
import sys
import shutil
import argparse

def copy_csv_files(source_dir, target_dir="tulipa_orig_input"):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    csv_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.csv')]
    
    for file in csv_files:
        source_path = os.path.join(source_dir, file)
        target_path = os.path.join(target_dir, file)
        shutil.copy2(source_path, target_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    args = parser.parse_args()
    
    copy_csv_files(args.source_dir)