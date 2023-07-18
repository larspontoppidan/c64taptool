# c64taptool

A simple Python script for modifying and analysing C64 TAP tape files.

```text
Usage:
    c64taptool OPTION [OPTION] ...
          
Options:
    -h             Show this help
    -r FILE        Read FILE as input (required)
    -p             Print pulse length analysis and histogram
    -cs START      Crop starting pulses. Pulses before index START are removed
    -ce END        Crop ending pulses. Pulses after, including index END are removed
    -a FILE        Append pulses from FILE
    -s RATIO       Scale pulse lengths, eg. -s 0.9 would make all pulses 90% length
    -w FILE        Write result to FILE
```
