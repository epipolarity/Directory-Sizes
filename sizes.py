import os
import csv
import locale
import time
import logging

from tqdm import tqdm
from configparser import ConfigParser
from concurrent.futures import ThreadPoolExecutor


def calculate_file_size(filepath):
    try:
        return os.path.getsize(filepath)
    except OSError as e:
        logging.exception("An error occurred while calculating file size: %s", filepath)
        return 0
    

def get_directory_size(directory, pbar, num_threads):
    total_size = 0
    last_update = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                futures.append(executor.submit(calculate_file_size, filepath))
                if time.time()-last_update > 1:
                    last_update = time.time()
                    pbar.set_postfix(update=f"Found {format_thousands(len(futures))} files")
        
        pbar.set_postfix(update=f"Found {format_thousands(len(futures))} files")
        for future in futures:
            total_size += future.result()
            if time.time()-last_update > 1:
                last_update = time.time()
                pbar.set_postfix(update=f"Found {format_gigabytes(total_size)} gigabytes")

    pbar.set_postfix(update=f"Found {format_gigabytes(total_size)} gigabytes")
    return total_size


def folder_writable(folder_path):
    write_access = False
    try:
        with open(os.path.join(folder_path, '.write_test'), 'w') as test_file:
            write_access = True
        os.remove(os.path.join(folder_path, '.write_test'))  # Clean up the test file
    except (PermissionError, OSError) as ex:
        write_access = False
    return write_access


def format_thousands(num):
    return locale.format_string('%.0f', num, grouping=True)


def format_bytes(bytes):
    return locale.format_string('%0.2f', bytes, grouping=True)


def format_gigabytes(bytes):
    return locale.format_string('%0.2f', bytes / (1024 ** 3), grouping=True)


def get_top_level_dir_sizes(config):
    root_directory = config['root_directory']
    check_write = config['check_write']
    directory_sizes = []
    dirnames = top_level_subdir_names(root_directory, config)    
    pbar = tqdm(dirnames, desc='Top-level Directories')
    for toplevel_subdir in pbar:        
        pbar.set_description(f"Top-level Directory: {toplevel_subdir}")
        full_path = os.path.join(root_directory, toplevel_subdir)
        if os.path.isdir(full_path):
            write_access = False
            if check_write:
                write_access = folder_writable(full_path)
            if write_access or not check_write:
                directory_size = get_directory_size(full_path, pbar, config['num_threads'])
                csv_row = csv_data_row(config, toplevel_subdir, directory_size, write_access)
                directory_sizes.append(csv_row)
                if directory_size / (1024 ** 3) >= config['min_dir_size']:
                    output_str = format_gigabytes(directory_size) + "GB -> " + toplevel_subdir 
                    if check_write:
                        output_str += " write:{}".format(write_access)
                    tqdm.write(output_str)
    return directory_sizes


def top_level_subdir_names(root_directory, config):
    _, dirnames, _ = next(os.walk(root_directory))
    dirnames = [d for d in dirnames if d not in config['ignore_directories']]
    return dirnames


def csv_data_row(config, directory, bytes, write_access):
    data_row = [directory]
    if config['report_bytes']: data_row.append(bytes)
    if config['report_gb']: data_row.append(bytes / (1024 ** 3))
    if config['check_write']: data_row.append(write_access)
    return data_row


def csv_header_row(config):
    header_row = ['Directory']
    if config['report_bytes']: header_row.append('Size (bytes)')
    if config['report_gb']: header_row.append('Size (Gigabytes)')
    if config['check_write']: header_row.append('Write Access')
    return header_row


def export_to_csv(directory_list, config):
    try:
        with open(config['csv_file'], 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_header_row(config))
            writer.writerows(directory_list)
        print(f"Directory list exported to {config['csv_file']} successfully!")
    except Exception as ex:
        print(ex)


def get_config():
    config = {}
    config_reader = ConfigParser()
    config_reader.read('config.ini')
    config['root_directory'] = config_reader.get('Directories', 'root_directory')
    config['ignore_directories'] = config_reader.get('Directories', 'ignore_directories').split(',')
    config['ignore_directories'] = [directory.strip() for directory in config['ignore_directories']]  
    config['check_write'] = config_reader.get('Access', 'check_for_write_access').lower() == "true"
    config['min_dir_size'] = float(config_reader.get('Filters', 'min_dir_size'))
    config['report_bytes'] = config_reader.get('Reporting', 'bytes').lower() == "true"
    config['report_gb'] = config_reader.get('Reporting', 'gigabytes').lower() == "true"
    config['csv_file'] = config_reader.get('Reporting', 'csv_file')
    config['num_threads'] = int(config_reader.get('Performance', 'num_threads'))
    return config


locale.setlocale(locale.LC_ALL, '')
logging.basicConfig(filename='error.log', filemode='w', level=logging.DEBUG, encoding='utf-8')

config_ini = get_config()
directory_list = get_top_level_dir_sizes(config_ini)
export_to_csv(directory_list, config_ini)
