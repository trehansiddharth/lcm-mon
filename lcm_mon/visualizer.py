import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import numpy as np

plt.ion()

class Visualizer:
    def __init__(self, formatter=str):
        self.series = {}
        self.lines = {}
        self._formatter = formatter
        self._ax = None

    def update(self, tag, time, data):
        if tag in self.series.keys():
            self.series[tag][0].append(time)
            self.series[tag][1].append(self._clean(data))
        else:
            self.series[tag] = ([time], [self._clean(data)])
        self.plot()

    def plot(self):
        args = []
        for tag, (times, datas) in self.series.items():
            if tag in self.lines:
                datas = np.array(datas)
                lines = self.lines[tag]
                if len(datas.shape) == 1:
                    line = lines[0]
                    line.set_xdata(times)
                    line.set_ydata(datas)
                    print(times)
                    print(datas)
                else:
                    for line, data in zip(lines, datas.transpose()):
                        line.set_xdata(times)
                        line.set_ydata(data)
            else:
                lines = plt.plot(times, datas)
                for i, line in enumerate(lines):
                    line.set_label(self._formatter(tag, i))
                self.lines[tag] = lines
        plt.pause(0.001)
        if self._ax is None:
            self._ax = plt.gca()
        self._ax.relim()
        self._ax.autoscale_view()
        plt.legend()

    def stop(self):
        self.series = {}
        self.lines = {}
        self._ax = None

    def tags(self):
        return self.series.keys()

    def _clean(self, value):
        try:
            return list(value)
        except TypeError:
            return value
