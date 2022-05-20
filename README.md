# kpgTools
Currently, the only script in this repository is kpgCheck.  More tools may be developed here in the future.

## kpgCheck
    python kpgCheck.py <file1> [<file2>]
    
Parse and inspect .htm file(s) exported from KPG-D1N.  (Handling of .htm export from other KPG- tools may be added in the future.)

- Internal consistency checks will be run on each specified file.
- If two files are specified, kpgCheck will also compare the two files, summarize the differnces, and invoke tkdiff or WinMerge on the two files.
