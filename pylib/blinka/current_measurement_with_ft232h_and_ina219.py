#!/usr/bin/env python3

'''Real-time current measurement via ina219 via ft232h.'''

import datetime, os, random, sys, threading, time
import pyftdi.ftdi

import kcore.common as C


KEEP_GOING = True   # Global for inter-thread coordination


# ---------- input abstraction

class Ina219:
    _ina219 = None

    def __init__(self, max_ma=1000, fake=False):
        if fake: return
        os.environ['BLINKA_FT232H'] = '1'  # Needs to be set before importing 'board'
        import board, digitalio
        from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219
        self._ina219 = INA219(board.I2C())   # uses board.SCL and board.SDA
        self._ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self._ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
        self._ina219.bus_voltage_range = BusVoltageRange.RANGE_16V

        if   max_ma == 5000: self._ina219.set_calibration_16V_5A()      # overflow @ 8A
        elif max_ma == 2000: self._ina219.set_calibration_32V_2A()      # overflow @ 3.2A
        elif max_ma == 1000: self._ina219.set_calibration_32V_1A()      # overflow @ 1.3A
        elif max_ma == 400:  self._ina219.set_calibration_16V_400mA()   # overflow @ 1.6A
        else:
            print(f'unknown max amperage specified ({max_ma}); ignored.', file=sys.stderr)

    def get_label(self):
        return 'current' if self._ina219 else 'current[fake]'

    def get_sample(self):
        return round(self._ina219.current if self._ina219 else random.uniform(0.0, 100.0), 2)


# ---------- output abstractions

class ReportFile:
    def __init__(self, filename, flush_interval_sec=None):
        self._flush_interval_sec = flush_interval_sec
        self._outfile = sys.stdout if filename == '-' else open(filename, 'a')
        self._last_flush = time.time()
        self.add('start')

    def add(self, label, value=None, dt=None):
        if not self._outfile: return
        ts = str(dt or datetime.datetime.now())[:-4]
        print(f'{ts}, {label}, {value}', file=self._outfile)
        now = time.time()
        if now - self._last_flush > self._flush_interval_sec:
            self._outfile.flush()
            self._last_flush = now

    def close(self):
        self.add('stop')
        if self._outfile != sys.stdout: self._outfile.close()


class ReportStdout:
    def __init__(self, min, oneline):
        self._min = min
        self._end = '\r' if oneline else '\n'

    def add(self, label, value=None, dt=None):
        if label.startswith('current') and value <= self._min: return
        ts = (dt or datetime.datetime.now()).strftime("%H:%M:%S.%f")[:-4]
        print(f'{ts}: {label}: {value}', end=self._end, flush=True)

    def close(self): pass


class ReportGraph:
    _xv = []
    _yv = []

    def __init__(self, samples, x_size, y_size, ani_cycle_ms):
        self._samples = samples

        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        self._plt = plt   # make local import visible to other methods
        self._fig, self._ax1 = plt.subplots()
        if x_size > 0: self._fig.set_figwidth(x_size)
        if y_size > 0: self._fig.set_figheight(y_size)
        self._ani = animation.FuncAnimation(self._fig, self._do_animate, interval=ani_cycle_ms)


    # This method must be called for things to start showing up,
    # but does not return until the user quits the interactive graph session (e.g. presses "q")
    # so need to call add() & close() from another thread..
    def show(self): self._plt.show()

    def add(self, label, value=None, dt=None):
        ts = (dt or datetime.datetime.now()).strftime('%H:%M:%S.%f')[:-4]
        if not label.startswith('current'): return  # TOOD: add as labeled item...?
        self._xv.append(ts)
        self._yv.append(value)

    def close(self): self._plt.close()

    def _do_animate(self, iternum):
        if not KEEP_GOING: self.close()
        self._xv = self._xv[-(self._samples):]
        self._yv = self._yv[-(self._samples):]

        self._ax1.clear()
        self._ax1.set_xlim([0, self._samples])
        self._ax1.plot(self._xv, self._yv)

        if len(self._yv) > 0:
            self._plt.text(x=0.1, y=0.1, s=f'{self._yv[-1]:.2f}',
                           transform=self._ax1.transAxes,
                           bbox=dict(boxstyle='circle', facecolor='black', linewidth=2.0, ),
                           fontsize=45, color='white', ha='center')

        self._plt.xticks(rotation=45, ha='right')
        self._plt.ylabel('mA')


# ---------- primary business logic

def calleach(instance_list, funcname, *args, **kwargs):
    for i in instance_list: getattr(i, funcname)(*args, **kwargs)


def data_loop(ins, outs, cycle_time):
    global KEEP_GOING
    while KEEP_GOING:
        try:
            for i in ins:
                calleach(outs, 'add', i.get_label(), i.get_sample(), datetime.datetime.now())
            time.sleep(cycle_time)
        except pyftdi.ftdi.FtdiError:
            KEEP_GOING = False
            print('USB ERROR!', file=sys.stderr)
        except KeyboardInterrupt:   # only really useful if not in graphical mode...
            return


def default_ins(args): return [Ina219(max_ma=args.max, fake=args.fake)]


def default_outs(args):
    gph = ReportGraph(args.samples, args.size_x, args.size_y, args.cycle_ms) if not args.nograph else None
    outs = [ gph,
        ReportFile(args.report, args.flush_sec) if args.report else None,
        ReportStdout(args.minout, args.oneline) if args.minout is not None else None ]
    outs = [i for i in outs if i is not None]
    return gph, outs


def run(gph, ins, outs, cycle_secs):
    # If using graphical output, start data_loop on another thread, and call matplotlib show().
    # If not using graphical output, just call data_loop from here.
    if gph:
        threading.Thread(target=data_loop, args=(ins, outs, cycle_secs), daemon=True).start()
        gph.show()
    else:
        data_loop(ins, outs, cycle_secs)

    # Either show() or data_loop() returned (via !KEEP_GOING), so close everything down.
    calleach(outs, 'close')


# ---------- main

def parse_args(argv=sys.argv[1:]):
    ap = C.argparse_epilog()
    ap.add_argument('--cycle_ms',  '-c', default=100,          help='ms between sample updates')

    g0 = ap.add_argument_group('current sensing options')
    g0.add_argument('--fake',      '-x', action='store_true',   help='use fake (random) data rather than real HW')
    g0.add_argument('--max',       '-M', type=int, default=1000, help='adjust max mA sensitivity.  Must be one of: {5000, 2000, 1000, 400}.  Smaller values give higher resolution.')

    g1 = ap.add_argument_group('graph output options')
    g1.add_argument('--nograph',   '-g', action='store_true',   help='Turn off real-time graphing')
    g1.add_argument('--samples',   '-s', type=int, default=40,  help='How many x-axis samples to show')
    g1.add_argument('--size_x',    '-sx', type=int, default=20, help='figure x-size (inches)')
    g1.add_argument('--size_y',    '-sy', type=int, default=10, help='figure y-size (inches)')

    g2 = ap.add_argument_group('CSV output options')
    g2.add_argument('--report',    '-r', type=str, default=None, help='Name of csv file to write report to')
    g2.add_argument('--flush_sec', '-f', type=int, default=15,  help='How many secs between flushes of output report file')

    g3 = ap.add_argument_group('stdout options')
    g3.add_argument('--minout',    '-m', type=float, default=None, help='Min number of mA to print current level to stdout.  Default=supress.')
    g3.add_argument('--oneline',   '-1', action='store_true',   help='keep overwriting the same line w/ the output')

    return ap.parse_args(argv)


def main():
    args = parse_args()
    ins = default_ins(args)
    gph, outs = default_outs(args)
    run(gph, ins, outs, args.cycle_ms/1000.0)


if __name__ == "__main__": sys.exit(main())
