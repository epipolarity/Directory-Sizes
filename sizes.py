import os
import csv
from tqdm import tqdm
from configparser import ConfigParser
import locale
import time
import logging

def get_directory_size(directory, pbar):
    total_size = 0
    file_count = 0
    errors = 0
    last_update = time.time()
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            file_count += 1
            filepath = os.path.join(dirpath, file)
            try:
                total_size += os.path.getsize(filepath)
            except Exception as ex:
                errors += 1
                logging.error(filepath)
                logging.exception(ex)
            if time.time() - last_update >= 1:
                pbar.set_postfix(update="{} files".format(file_count))
                last_update = time.time()
    return total_size


def get_top_level_dir_sizes(root_directory, ignore_directories, check_write, min_dir_size):
    directory_sizes = []
    _, dirnames, _ = next(os.walk(root_directory))
    dirnames = [d for d in dirnames if d not in ignore_directories]
    pbar = tqdm(dirnames, desc='Top-level Directories')
    for item in pbar:        
        pbar.set_description(f"Top-level Directory: {item}")
        item_path = os.path.join(root_directory, item)
        if os.path.isdir(item_path):
            write_access = False
            if check_write:
                try:
                    with open(os.path.join(item_path, '.write_test'), 'w') as test_file:
                        write_access = True
                    os.remove(os.path.join(item_path, '.write_test'))  # Clean up the test file
                except (PermissionError, OSError) as ex:
                    write_access = False
            if write_access or not check_write:
                directory_size = get_directory_size(item_path, pbar)
                csv_row = [item, directory_size, directory_size / (1024 ** 3)]
                if check_write:
                    csv_row.append(write_access)
                directory_sizes.append(csv_row)
                if directory_size / (1024 ** 3) >= min_dir_size:
                    formatted_size = locale.format_string('%0.2f', directory_size / (1024 ** 3), grouping=True)
                    output_str = formatted_size + "GB -> " + item 
                    if check_write:
                        output_str += " write:{}".format(write_access)
                    tqdm.write(output_str)
    return directory_sizes


def export_to_csv(directory_list, csv_filename):
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Directory', 'Size (bytes)', 'Size (Gigabytes)', 'Write Access'])
        writer.writerows(directory_list)
    print(f"Directory list exported to {csv_filename} successfully!")


locale.setlocale(locale.LC_ALL, '')
logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG, encoding='utf-8')

# Read the root_directory from the config.ini file
config = ConfigParser()
config.read('config.ini')
root_directory = config.get('Directories', 'root_directory')
ignore_directories = config.get('Directories', 'ignore_directories').split(',')
check_write = config.get('Access', 'check_for_write_access').lower() == "true"
min_dir_size = float(config.get('Filters', 'min_dir_size'))

# normalise ignore directories to ensure consistent 
ignore_directories = [directory.strip() for directory in ignore_directories]  

csv_filename = "directory_sizes.csv"

directory_list = get_top_level_dir_sizes(root_directory, ignore_directories, check_write, min_dir_size)
export_to_csv(directory_list, csv_filename)
