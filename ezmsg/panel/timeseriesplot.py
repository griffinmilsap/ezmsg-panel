import asyncio
from dataclasses import replace

import panel
import ezmsg.core as ez

from ezmsg.util.messages.axisarray import AxisArray

from ezmsg.sigproc.butterworthfilter import (
    ButterworthFilter, 
    ButterworthFilterSettingsMessage,
    ButterworthFilterSettings
)

from param.parameterized import Event

from typing import AsyncGenerator, List

from .scrollinglineplot import (
    ScrollingLinePlot, 
    ScrollingLinePlotSettings, 
)


class ButterworthFilterControlState(ez.State):
    queue: "asyncio.Queue[ButterworthFilterSettingsMessage]"

    # Controls for Butterworth Filter
    order: panel.widgets.IntInput
    cuton: panel.widgets.FloatInput
    cutoff: panel.widgets.FloatInput


class ButterworthFilterControl(ez.Unit):
    SETTINGS: ButterworthFilterSettings
    STATE: ButterworthFilterControlState

    OUTPUT_SETTINGS = ez.OutputStream(ButterworthFilterSettingsMessage)

    def initialize(self) -> None:
        self.STATE.queue = asyncio.Queue()

        # Spectrum Settings
        self.STATE.order = panel.widgets.IntInput( 
            name = 'Filter Order (0 = "Disabled")', 
            value = 0, 
            start = 0 
        )

        self.STATE.cuton = panel.widgets.FloatInput( 
            name = 'Filter Cuton (Hz)', 
            value = 1.0, 
            start = 0.0 
        )

        self.STATE.cutoff = panel.widgets.FloatInput( 
            name = 'Filter Cutoff (Hz)', 
            value = 30.0, 
            start = 0.0 
        )

        def enqueue_design(*events: Event) -> None:
            self.STATE.queue.put_nowait(replace( 
                self.SETTINGS,
                order = self.STATE.order.value,
                cuton = self.STATE.cuton.value,
                cutoff = self.STATE.cutoff.value
            ))

        self.STATE.order.param.watch(enqueue_design, 'value')
        self.STATE.cuton.param.watch(enqueue_design, 'value')
        self.STATE.cutoff.param.watch(enqueue_design, 'value')


    @ez.publisher(OUTPUT_SETTINGS)
    async def pub_settings(self) -> AsyncGenerator:
        while True:
            settings = await self.STATE.queue.get()
            yield self.OUTPUT_SETTINGS, settings

    @property
    def controls(self) -> List[panel.viewable.Viewable]:
        return [
            self.STATE.order,
            self.STATE.cuton,
            self.STATE.cutoff,
        ]


TimeSeriesPlotSettings = ScrollingLinePlotSettings

class TimeSeriesPlot(ez.Collection):
    SETTINGS: TimeSeriesPlotSettings

    INPUT_SIGNAL = ez.InputStream(AxisArray)

    BPFILT = ButterworthFilter()
    BPFILT_CONTROL = ButterworthFilterControl()
    PLOT = ScrollingLinePlot()

    def configure(self) -> None:
        self.PLOT.apply_settings(self.SETTINGS)

        filter_settings = ButterworthFilterSettings(
            axis = self.SETTINGS.time_axis
        )

        self.BPFILT_CONTROL.apply_settings(filter_settings)
        self.BPFILT.apply_settings(filter_settings)

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.BPFILT_CONTROL.OUTPUT_SETTINGS, self.BPFILT.INPUT_FILTER),
            (self.INPUT_SIGNAL, self.BPFILT.INPUT_SIGNAL),
            (self.BPFILT.OUTPUT_SIGNAL, self.PLOT.INPUT_SIGNAL),
        )

    def panel(self) -> panel.viewable.Viewable:
        return panel.Row(
            self.PLOT.plot(),
            panel.Column(
                "__Scrolling Line Plot Controls__",
                *self.PLOT.controls,
                "__Visualization Filter Controls__",
                *self.BPFILT_CONTROL.controls
            )
        )
