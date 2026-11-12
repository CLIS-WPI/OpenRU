"""Minimal ctypes driver for libngspice: run a netlist and dump vectors with wrdata."""
import ctypes, sys
lib = ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libngspice.so.0')
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
quiet = CB(lambda s, i, p: 0)
lib.ngSpice_Init(quiet, quiet, ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)(lambda *a: 0), None, None, None, None)
def cmd(c):
    r = lib.ngSpice_Command(c.encode()); assert r == 0, c
cir, out, vecs = sys.argv[1], sys.argv[2], sys.argv[3:]
cmd(f"source {cir}"); cmd("run"); cmd(f"wrdata {out} " + " ".join(vecs))
