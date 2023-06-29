import os
import csv
import locale
import time
import logging
import re

from tqdm import tqdm
from configparser import ConfigParser
from concurrent.futures import ThreadPoolExecutor


def calculate_file_size(filepath):
    """
    Calculates the size of a file specified by the given filepath.
    Args:
        filepath (str): The path to the file.
    Returns:
        int: The size of the file in bytes.
    Raises:
        OSError: If an error occurs while accessing the file.
    """
    try:
        return os.path.getsize(filepath)
    except OSError as e:
        logging.exception("An error occurred while calculating file size: %s", filepath)
        return 0
    

def get_directory_size(directory, pbar, num_threads, path_len_threshold):
    """
    Retrieves the total size and number of files in the specified directory.
    Args:
        directory (str): The path to the directory.
        pbar (ProgressBar): An instance of the progress bar for displaying updates.
        num_threads (int): The number of threads to use for concurrent file size calculation.
        path_len_threshold: Threshold for path length, over which to report the file path. -1 = no reporting
    Returns:
        tuple: A tuple containing the total size (in bytes) and the number of files.
        list: A list of paths with length exceeding the threshold
    """
    total_size = 0
    last_update = time.time()
    long_paths = []

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        size_futures = []
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if path_len_threshold >= 0 and len(filepath) > 255:
                    long_paths.append(filepath)
                size_futures.append(executor.submit(calculate_file_size, filepath))
                if time.time()-last_update > 1:
                    last_update = time.time()
                    pbar.set_postfix(update=f"Found {format_thousands(len(size_futures))} files")
        
        pbar.set_postfix(update=f"Found {format_thousands(len(size_futures))} files")
        for future in size_futures:
            total_size += future.result()
            if time.time()-last_update > 1:
                last_update = time.time()
                pbar.set_postfix(update=f"Found {format_gigabytes(total_size)} gigabytes")

    pbar.set_postfix(update=f"Found {format_gigabytes(total_size)} gigabytes")
    return total_size, len(size_futures), long_paths


def folder_writable(folder_path):
    """
    Checks if the specified folder has write access.
    Args:
        folder_path (str): The path to the folder.
    Returns:
        bool: True if write access is available, False otherwise.
    """
    write_access = False
    try:
        with open(os.path.join(folder_path, '.write_test'), 'w') as test_file:
            write_access = True
        os.remove(os.path.join(folder_path, '.write_test'))  # Clean up the test file
    except (PermissionError, OSError) as ex:
        write_access = False
    return write_access


def format_thousands(num):
    """
    Formats a number by adding thousands separators, using locale specific format.
    Args:
        num (int or float): The number to be formatted.
    Returns:
        str: The formatted number with thousands separators.
    """
    return locale.format_string('%.0f', num, grouping=True)


def format_gigabytes(bytes):
    """
    Formats a number representing bytes as gigabytes with a decimal precision of 2
    and adds thousands separators, using locale specific format
    Args:
        bytes (int or float): The number of bytes to be converted and formatted.
    Returns:
        str: The formatted number of gigabytes with decimal precision and thousands separators.
    """
    return locale.format_string('%0.2f', bytes / (1024 ** 3), grouping=True)


def get_top_level_dir_sizes(config):
    """
    Retrieves the sizes and information of top-level directories based on the provided configuration.
    Args:
        config (dict): A dictionary containing the configuration parameters.
    Returns:
        list: A list of rows containing information about each top-level directory.
        list: A list of paths exceeding config path len threshold for path length.
    """
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
                directory_size, file_count, long_paths = get_directory_size(full_path, pbar, config['num_threads'], config['path_len_threshold'])
                csv_row = csv_data_row(config, toplevel_subdir, directory_size, file_count, write_access)
                directory_sizes.append(csv_row)
                if directory_size / (1024 ** 3) >= config['min_dir_size']:
                    output_str = format_gigabytes(directory_size) + "GB -> " + toplevel_subdir 
                    if check_write:
                        output_str += " write:{}".format(write_access)
                    tqdm.write(output_str)
    return directory_sizes, long_paths


def top_level_subdir_names(root_directory, config):
    """
    Retrieves the names of the top-level subdirectories within the specified root directory,
    excluding directories listed in config to specifically ignore, and matching any
    regular expression provided in config
    Args:
        root_directory (str): The path to the root directory.
        config (dict): A dictionary containing the configuration parameters.        
    Returns:
        list: A list of names of the top-level subdirectories.
    """
    _, dirnames, _ = next(os.walk(root_directory))
    dirnames = [d for d in dirnames if d not in config['ignore_directories']]
    if config['re_pattern']:
        dirnames = [d for d in dirnames if re.match(config['re_pattern'], d)]    
    return dirnames


def csv_data_row(config, directory, bytes, filecount, write_access):
    """
    Constructs a data row for a CSV file based on the provided configuration and information about a directory.
    Args:
        config (dict): A dictionary containing the configuration parameters.
        directory (str): The name of the directory.
        bytes (int): The size of the directory in bytes.
        filecount (int): The number of files in the directory.
        write_access (bool): Indicates whether the directory has write access.
    Returns:
        list: A list representing a row of data for the CSV file.
    """
    data_row = [directory]
    if config['report_bytes']: data_row.append(bytes)
    if config['report_gb']: data_row.append(bytes / (1024 ** 3))
    if config['report_fcount']: data_row.append(filecount)
    if config['check_write']: data_row.append(write_access)
    return data_row


def csv_header_row(config):
    """
    Constructs the header row for a CSV file based on the provided configuration.
    Args:
        config (dict): A dictionary containing the configuration parameters.
    Returns:
        list: A list representing the header row of the CSV file.
    """
    header_row = ['Directory']
    if config['report_bytes']: header_row.append('Size (bytes)')
    if config['report_gb']: header_row.append('Size (Gigabytes)')
    if config['report_fcount']: header_row.append('File Count')
    if config['check_write']: header_row.append('Write Access')
    return header_row


def export_to_csv(directory_list, config):
    """
    Exports a directory list to a CSV file based on the provided configuration.
    Args:
        directory_list (list): A list of directory data rows to be exported.
        config (dict): A dictionary containing the configuration parameters.
    Returns:
        None
    """
    try:
        with open(config['csv_file'], 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(csv_header_row(config))
            writer.writerows(directory_list)
        print(f"Directory list exported to {config['csv_file']} successfully!")
    except Exception as ex:
        print(ex)
        

def get_config():
    """
    Retrieves the configuration parameters from the 'config.ini' file.
    Returns:
        dict: A dictionary containing the configuration parameters.
    Raises:
        FileNotFoundError: If the 'config.ini' file is not found.
        KeyError: If there are missing keys in the configuration file.
        ValueError: If there are missing or invalid configuration values.
    """
    try:
        config = {}
        config_reader = ConfigParser()
        config_reader.read('config.ini')

        # Directories Section
        if 'Directories' not in config_reader:
            raise ValueError("Missing 'Directories' section in the config file.")
        
        config['root_directory'] = config_reader.get('Directories', 'root_directory')

        ignore_directories = config_reader.get('Directories', 'ignore_directories')
        config['ignore_directories'] = [directory.strip() for directory in ignore_directories.split(',')]
        config['re_pattern'] = config_reader.get('Directories', 'top_level_regex')

        # Access Section
        if 'Access' not in config_reader:
            raise ValueError("Missing 'Access' section in the config file.")

        config['check_write'] = config_reader.getboolean('Access', 'check_for_write_access')

        # Filters Section
        if 'Filters' not in config_reader:
            raise ValueError("Missing 'Filters' section in the config file.")

        config['min_dir_size'] = config_reader.getfloat('Filters', 'min_dir_size')

        # Reporting Section
        if 'Reporting' not in config_reader:
            raise ValueError("Missing 'Reporting' section in the config file.")

        config['report_bytes'] = config_reader.getboolean('Reporting', 'bytes')
        config['report_gb'] = config_reader.getboolean('Reporting', 'gigabytes')
        config['report_fcount'] = config_reader.getboolean('Reporting', 'filecount')
        config['csv_file'] = config_reader.get('Reporting', 'csv_file')
        config['path_len_threshold'] = int(config_reader.get('Reporting', 'paths_over_len'))

        # Performance Section
        if 'Performance' not in config_reader:
            raise ValueError("Missing 'Performance' section in the config file.")

        config['num_threads'] = config_reader.getint('Performance', 'num_threads')

        return config

    except (FileNotFoundError, KeyError, ValueError) as ex:
        raise ex


locale.setlocale(locale.LC_ALL, '')
logging.basicConfig(filename='error.log', filemode='w', level=logging.DEBUG, encoding='utf-8')

try:
    config_ini = get_config()
    directory_list, long_paths = get_top_level_dir_sizes(config_ini)
    for lp in long_paths:
        print(f"{len(lp)}: {lp}")
    export_to_csv(directory_list, config_ini)
except FileNotFoundError:
    print("The 'config.ini' file was not found.")
except (KeyError, ValueError) as ex:
    print(f"Invalid or missing configuration: {ex}")
