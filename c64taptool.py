#!/usr/bin/python3

"""
c64taptool by Lars Ole Pontoppidan, 2023

A tool for analysis and processing of C64 TAP Files

This script needs Python v3 and has no dependencies
"""

SCRIPT_VERSION = "v1.0.0"
GITHUB = "https://github.com/larspontoppidan/c64taptool"

class BytesReader():
    def __init__(self, data, byte_order="big"):
        self.data = data
        self.index = 0
        self.byteOrder = byte_order # "big" or "little"

    def getUint8(self) -> int:
        x = self.data[self.index]
        self.index += 1
        return x

    def getUint16(self) -> int:
        x = int.from_bytes(self.data[self.index:self.index + 2], 
                    byteorder=self.byteOrder, signed=False)
        self.index += 2
        return x

    def getUint32(self) -> int:
        x = int.from_bytes(self.data[self.index:self.index + 4], 
                    byteorder=self.byteOrder, signed=False)
        self.index += 4
        return x

    def getInt8(self) -> int:
        x = int.from_bytes(self.data[self.index:self.index + 1], 
                    byteorder=self.byteOrder, signed=True)
        self.index += 1
        return x

    def getInt16(self) -> int:
        x = int.from_bytes(self.data[self.index:self.index + 2], 
                    byteorder=self.byteOrder, signed=True)
        self.index += 2
        return x

    def getInt32(self) -> int:
        x = int.from_bytes(self.data[self.index:self.index + 4], 
                    byteorder=self.byteOrder, signed=True)
        self.index += 4
        return x

    def getString(self, length:int) -> str:
        raw = self.data[self.index: self.index + length]
        self.index += length
        return raw.decode()

    def bytesLeft(self) -> int:
        return len(self.data) - self.index 


class BytesWriter():
    def __init__(self, data, byte_order="big"):
        self.data = data
        self.byteOrder = byte_order # "big" or "little"

    def writeUint8(self, x):
        self.data.append(x)

    def writeUint16(self, x):
        self.data.extend((x).to_bytes(2, byteorder=self.byteOrder, signed=False))

    def writeUint32(self, x):
        self.data.extend((x).to_bytes(4, byteorder=self.byteOrder, signed=False))

    def writeInt8(self, x):
        self.data.extend((x).to_bytes(1, byteorder=self.byteOrder, signed=True))

    def writeInt16(self, x):
        self.data.extend((x).to_bytes(2, byteorder=self.byteOrder, signed=True))

    def writeInt32(self, x):
        self.data.extend((x).to_bytes(4, byteorder=self.byteOrder, signed=True))

    def writeAsciiString(self, x):
        # Only send ascii chars, ignore non-ascii
        self.data.extend(x.encode("ascii", "ignore"))
        

def _decodeOptions(options:list[str], value:int):
    if value >= 0 and value < len(options):
        return "%s (%d)" % (options[value], value)
    else:
        return "Unknown value (%d)" % value

class Tap:
    def __init__(self, br:BytesReader):
        br.index = 0
        self.magic = br.getString(12)
        self.version = br.getUint8()
        self.platform = br.getUint8()
        self.platformStr = _decodeOptions(["C64", "VIC", "C16"], self.platform)
        self.video = br.getUint8()
        self.videoStr = _decodeOptions(["PAL", "NTSC"], self.video)
        self.res = br.getUint8()
        self.length = br.getUint32()        
        if self.length != br.bytesLeft():
            raise Exception("Header length mismatch: %d not equal to actual bytes in file: %d" % (
                             self.length, br.bytesLeft()))
        self.pulses = []
        while br.bytesLeft() > 0:
            pl = br.getUint8()
            if pl == 0:
                pl = br.getUint8()
                pl = pl * 256 + br.getUint8()
                pl = pl * 256 + br.getUint8()
            self.pulses.append(pl)

    def crop(self, cut_start, cut_end):
        self.pulses = self.pulses[cut_start:cut_end]
        # Calc new raw length
        rawLen = 0
        for p in self.pulses:
            if p > 255:
                rawLen += 4
            else:
                rawLen += 1
        self.length = rawLen

    def append(self, tap:'Tap'):
        self.pulses.extend(tap.pulses)
        self.length += tap.length

    def estimateDuration(self) -> float:
        clk_frq = 985248 # PAL clock frequency is always used for actual pulse lengths, it seems
        short_scaler = (1.0 / clk_frq) * 8.0
        long_scaler = (1.0 / clk_frq)
        dur = 0.0
        for pl in self.pulses:
            if pl <= 255:
                dur += pl * short_scaler
            else:
                dur += pl * long_scaler
        return dur

    def scale(self, ratio:float):
        # Scale pulse lengths making sure we don't change between single and multi byte pulses
        for i in range(len(self.pulses)):
            pl = self.pulses[i]
            if pl <= 255:
                pl = round(float(pl) * ratio)
                if pl > 255:                    
                    pl = 255
            else:
                pl = round(float(pl) * ratio)
                if pl <= 255:
                    pl = 256
            self.pulses[i] = pl    

    def write(self, bw:BytesWriter):
        bw.writeAsciiString(self.magic)
        bw.writeUint8(self.version)
        bw.writeUint8(self.platform)
        bw.writeUint8(self.video)
        bw.writeUint8(0) # reserved
        bw.writeUint32(self.length)
        for pl in self.pulses:
            if pl > 255:
                bw.writeUint8(0)
                bw.writeUint8((pl >> 16) & 0xFF)
                bw.writeUint8((pl >> 8) & 0xFF)
                bw.writeUint8(pl & 0xFF)
            else:
                bw.writeUint8(pl)                
                
    def printHeader(self):
        print("""  Magic:     %s
  Version:   %d
  Platform:  %s
  Video:     %s
  Reserved:  %d
  Length:    %d (bytes) %d (pulses)""" % (
            self.magic, self.version, self.platformStr, 
            self.videoStr, self.res, self.length, len(self.pulses)))
        
    def printPulseHistogram(self):
        histogram = [0] * 256
        histogramFirst = [0] * 256
        shortest = None
        longest = None
        longPulses = []
        for i, pl in enumerate(self.pulses):
            if pl < 256:
                if histogram[pl] == 0:
                    histogramFirst[pl] = i
                histogram[pl] += 1
                if longest is None or pl > longest:
                    longest = pl
                if shortest is None or pl < shortest:
                    shortest = pl
            else:
                longPulses.append((i, pl))

        print("\nNormal pulses:")
        for i in range(shortest, longest + 1):
            if histogram[i] > 0:
                print("  %3d:  %d  (first, index: %d)" % (i, histogram[i], histogramFirst[i]))
            else:
                print("  %3d:  %d" % (i, histogram[i]))
        print("\nLong pulses:")
        for (i, pl) in longPulses:
            print("  Index: %d   len: %d (raw)" % (i, pl))
        print("")


def readTap(filename):
    print("Reading file: " + filename)
    with open(filename, "rb") as f:
        byts = f.read()
    br = BytesReader(byts, "little")
    tap = Tap(br)
    tap.printHeader()
    if tap.magic != "C64-TAPE-RAW":
        raise Exception("Unexpected file signature")
    if tap.version != 1:
        raise Exception("Only TAP version 1 is supported")
    
    print("  Estimated duration: %0.2f sec" % tap.estimateDuration())
    return tap

def writeTap(tap:Tap, fileout):
    print("Writing file: " + fileout)
    tap.printHeader()
    print("  Estimated duration: %0.2f sec" % tap.estimateDuration())
    ba = bytearray()
    bw = BytesWriter(ba, "little")
    tap.write(bw)
    with open(fileout, "wb") as f:
        f.write(ba)

# ----

def welcome():
    print("c64taptool %s  ---  GitHub: %s" % (SCRIPT_VERSION, GITHUB))

def usage():
    print("""
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
""")

def processParams(params:'Params'):
    if params.Strings["-i"] is None:
        print("-i option is required")
    else:
        tap = readTap(params.Strings["-i"])
        if params.Flags["--hist"] == True:
            tap.printPulseHistogram()
        if params.Ints["--crop-start"] != 0 or params.Ints["--crop-end"] != -1:
            start, end = params.Ints["--crop-start"], params.Ints["--crop-end"]
            print("Cropping pulses to interval [%d, %d]" % (start, end))
            tap.crop(start, end)
        if params.Strings["--append"] is not None:
            append_tap = readTap(params.Strings["--append"])
            print("Appending pulses")
            tap.append(append_tap)
        if params.Floats["--scale"] is not None:
            ratio = params.Floats["--scale"]
            print("Scaling pulses with ratio: %f" % ratio)
            tap.scale(ratio)
        if params.Strings["-o"] is not None:
            writeTap(tap, params.Strings["-o"])

class ShowHelpException(Exception):
    pass

class Params:
    def __init__(self):
        self.Flags = {"--hist":False}
        self.Ints = {"--crop-start":0, "--crop-end":-1}
        self.Strings = {"-i":None, "--append":None, "-o":None}
        self.Floats = {"--scale":None}

    @staticmethod
    def parse(cmds:list):
        p = Params()
        while len(cmds) > 0 and cmds[0].startswith("-"):
            if cmds[0] == "-h" or cmds[0] == "-H":
                raise ShowHelpException
            elif cmds[0] in p.Flags:
                p.Flags[cmds[0]] = True
            elif cmds[0] in p.Floats:
                p.Floats[cmds[0]] = float(cmds[1])
                cmds.pop(0)
            elif cmds[0] in p.Ints:
                p.Ints[cmds[0]] = int(cmds[1])
                cmds.pop(0)
            elif cmds[0] in p.Strings:
                p.Strings[cmds[0]] = cmds[1]
                cmds.pop(0)
            else:
                raise ValueError("Unknown option: " + cmds[0])
            cmds.pop(0)
        if len(cmds) != 0:
            raise ValueError("Wrong number of arguments")
        return p

def main(args):
    welcome()
    try:
        if len(args) == 0:
            raise ShowHelpException
        processParams(Params.parse(args))
    except ShowHelpException as e:
        usage()
    except Exception as e:
        print(str(e))

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
