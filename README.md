# Directory-Sizes
Create a nice simple CSV list of top level directory sizes

# Usage
Rename config.ini.template to config.ini and change root_directory to the directory you want to analyse.

Run python sizes.py

This will use os.walk on all directories within the top level of the specified 'root' directory, recursively totalling up the size of every file contained within.

Results are saved to directory_sizes.py in the current directory, and contain columns for
1. Directory name
2. Size (bytes)
3. Size (gigabytes)
