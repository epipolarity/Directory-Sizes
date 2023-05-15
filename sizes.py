import os
import csv
from tqdm import tqdm
from configparser import ConfigParser
import locale

def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            filepath = os.path.join(dirpath, file)
            total_size += os.path.getsize(filepath)
    return total_size


def get_top_level_dir_sizes(root_directory, ignore_directories):
    directory_list = []
    pbar = tqdm(os.listdir(root_directory), desc='Top-level Directories')
    for item in pbar:
        pbar.set_description(f"Top-level Directory: {item}")
        item_path = os.path.join(root_directory, item)
        if os.path.isdir(item_path) and item not in ignore_directories:
            directory_size = get_directory_size(item_path)
            directory_list.append([item, directory_size, directory_size / (1024 ** 3)])
            tqdm.write(item + ": " + '{:n}GB'.format(directory_size / (1024 ** 3)))
    return directory_list


def export_to_csv(directory_list, csv_filename):
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Directory', 'Size (bytes)', 'Size (Gigabytes)'])
        writer.writerows(directory_list)
    print(f"Directory list exported to {csv_filename} successfully!")


locale.setlocale(locale.LC_ALL, '')

# Read the root_directory from the config.ini file
config = ConfigParser()
config.read('config.ini')
root_directory = config.get('Directories', 'root_directory')
ignore_directories = config.get('Directories', 'ignore_directories').split(',')

# normalise ignore directories to ensure consistent 
ignore_directories = [directory.strip() for directory in ignore_directories]  

csv_filename = "directory_sizes.csv"

directory_list = get_top_level_dir_sizes(root_directory, ignore_directories)
export_to_csv(directory_list, csv_filename)
