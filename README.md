# kpgTools
Currently, the only script in this repository is kpgCheck.  More tools may be developed here in the future.

# Installation
kpgTools is not currently a full package availble through PyPi.  So, follow these steps to install:
1. install Python
2. download and extract the latest zip (the green button on the repo home page)
3. open a terminal and go to the directory that you unzipped to
4. pip install -r requirements.txt
5. if running on Windows, install a recent version of WinMerge (2.16.0 or later)

## kpgCheck
    python kpgCheck.py <file1> [<file2>]
    
Parse and inspect .htm file(s) exported from KPG-D1N.  (Handling of .htm export from other KPG- tools may be added in the future.)

- Internal consistency checks will be run on each specified file.
- A .csv file containing channel data will be generated corresponding to each specified file.
- If two files are specified, kpgCheck will also compare the two generated .csv files, summarize the differnces, and attempt to invoke WinMerge.
