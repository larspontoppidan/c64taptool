# c64taptool

A simple Python script for modifying and analysing C64 TAP tape files.

```text
Usage:
    c64taptool OPTION [OPTION] ...
          
Options:
    -h                  Show this help
    -i FILE             Read TAP file and use as input (required)
    --hist              Print pulse length analysis and histogram
    --crop-start START  Remove pulses before index START
    --crop-end END      Remove pulses after index END (including)
    --append FILE       Append pulses from TAP file
    --scale RATIO       Scale pulse lengths, eg. -s 0.9 would make all pulses 90% length
    -o FILE             Write result (output) to TAP file
```

### Installation

On a Linux platform the script may simply be placed in `/usr/bin` like this:

```text
cd TEMP-FOLDER
git clone https://github.com/larspontoppidan/c64taptool
cd c64taptool
chmod +x c64taptool.py
sudo cp c64taptool.py /usr/bin/c64taptool
```

Uninstall with:

```text
sudo rm /usr/bin/c64taptool
```

