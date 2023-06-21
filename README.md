# Directory-Sizes
Create a nice simple CSV list of top level directory sizes

# Usage
- Rename config.ini.template to config.ini
- Change root_directory to the directory you want to analyse.
- Specify names of top level folders to ignore, separated by commas
- Specify number of threads to use - seems to work best when equal to number of physical cores
- Specify whether to only iterrogate folders to which you have write access.
- Specify a minimum directory size in GB for console output (0=output all).
- Specify the csv file to generate
- Specify whether to report in bytes, gigabytes or both
- Specify whether to report count of files
- Specify whether to report (in terminal, not csv) paths above a certain length... -1 to ignore path length

Run python sizes.py

This will use os.walk on all directories within the top level of the specified 'root' directory, totalling up the size of every file contained within every subdirectory, all the way down.

Results are saved to directory_sizes.csv in the current directory, and contain columns for
1. Directory name
2. Size (bytes) (optional)
3. Size (gigabytes) (optional)
4. File Count (optional)
4. Write Access (optional)
