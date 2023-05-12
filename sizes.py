import os
import csv
from tqdm import tqdm
from configparser import ConfigParser


def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            filepath = os.path.join(dirpath, file)
            total_size += os.path.getsize(filepath)
    return total_size


def show_top_level_directories(root_directory):
    directory_list = []
    pbar = tqdm(os.listdir(root_directory), desc='Top-level Directories')
    for item in pbar:
        item_path = os.path.join(root_directory, item)
        if os.path.isdir(item_path):
            directory_size = get_directory_size(item_path)
            directory_list.append([item, directory_size, directory_size / (1024 ** 3)])
            pbar.set_postfix({'Size': f"{directory_size} bytes"})
            pbar.set_description(f"Top-level Directory: {item}")
    return directory_list


def export_to_csv(directory_list, csv_filename):
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Directory', 'Size (bytes)', 'Size (Gigabytes)'])
        writer.writerows(directory_list)
    print(f"Directory list exported to {csv_filename} successfully!")


# Read the root_directory from the config.ini file
config = ConfigParser()
config.read('config.ini')
root_directory = config.get('Directories', 'root_directory')

csv_filename = "directory_sizes.csv"

directory_list = show_top_level_directories(root_directory)
export_to_csv(directory_list, csv_filename)
