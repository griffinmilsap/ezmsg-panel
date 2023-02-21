import asyncio
from functools import partial

import panel
import ezmsg.core as ez
import numpy as np

from ezmsg.util.messages.axisarray import AxisArray

from ezmsg.sigproc.butterworthfilter import (
    ButterworthFilter, 
    ButterworthFilterSettingsMessage,
    ButterworthFilterSettings
)

from bokeh.plotting import figure, Figure
from bokeh.models import ColumnDataSource
from bokeh.models.renderers import GlyphRenderer
from bokeh.models.tickers import AdaptiveTicker
from bokeh.server.contexts import BokehSessionContext

from typing import AsyncGenerator, Dict, Set, Optional

CDS_TIME_DIM = '__time__'

class TimeSeriesPlotSettings( ez.Settings ):
    name: str = 'TimeSeriesPlot'
    time_axis: Optional[str] = None # If not specified, dim 0 is used.

class TimeSeriesPlotGUIState( ez.State ):
    queues: Set[ "asyncio.Queue[AxisArray]" ]
    cur_t: float = 0.0
    cur_fs: float = 1.0

    # Visualization controls
    channelize: panel.widgets.Checkbox
    gain: panel.widgets.FloatInput
    duration: panel.widgets.FloatInput

    # Filtering functionality
    order: panel.widgets.IntInput
    cuton: panel.widgets.FloatInput
    cutoff: panel.widgets.FloatInput
    design_queue: "asyncio.Queue[ ButterworthFilterDesign ]"

    # Signal Properties
    fs: panel.widgets.Number
    n_time: panel.widgets.Number

class TimeSeriesPlotGUI( ez.Unit ):

    SETTINGS: TimeSeriesPlotSettings
    STATE: TimeSeriesPlotGUIState

    INPUT_SIGNAL = ez.InputStream(AxisArray)
    OUTPUT_FILTER = ez.OutputStream(ButterworthFilterSettingsMessage)

    def initialize( self ) -> None:
        self.STATE.queues = set()
        self.STATE.channelize = panel.widgets.Checkbox( name = 'Channelize', value = True )
        self.STATE.gain = panel.widgets.FloatInput( name = 'Gain', value = 1.0 )
        self.STATE.duration = panel.widgets.FloatInput( name = 'Duration (sec)', value = 4.0, start = 0.0 )

        self.STATE.design_queue = asyncio.Queue()
        self.STATE.order = panel.widgets.IntInput( name = 'Filter Order (0 = "Disabled")', value = 0, start = 0 )
        self.STATE.cuton = panel.widgets.FloatInput( name = 'Filter Cuton (Hz)', value = 1.0, start = 0.0 )
        self.STATE.cutoff = panel.widgets.FloatInput( name = 'Filter Cutoff (Hz)', value = 30.0, start = 0.0 )

        def enqueue_design( _ ):
            self.STATE.design_queue.put_nowait(
                ButterworthFilterSettingsMessage(
                    axis = self.SETTINGS.time_axis,
                    order = self.STATE.order.value,
                    cuton = self.STATE.cuton.value,
                    cutoff = self.STATE.cutoff.value
                )
            )

        self.STATE.order.param.watch( enqueue_design, 'value' )
        self.STATE.cuton.param.watch( enqueue_design, 'value' )
        self.STATE.cutoff.param.watch( enqueue_design, 'value' )

        number_kwargs = dict( title_size = '12pt', font_size = '18pt' )
        self.STATE.fs = panel.widgets.Number( name = 'Sampling Rate', format='{value} Hz', **number_kwargs )
        self.STATE.n_time = panel.widgets.Number( name = "Samples per Message", **number_kwargs )
    

    def panel( self ) -> panel.viewable.Viewable:
        queue: "asyncio.Queue[ Dict[ str, np.ndarray ] ]" = asyncio.Queue()
        cds = ColumnDataSource( { CDS_TIME_DIM: [ self.STATE.cur_t ] } )
        fig = figure( 
            sizing_mode = 'stretch_width', 
            title = self.SETTINGS.name, 
            output_backend = "webgl" 
        )

        lines = {}

        @panel.io.with_lock
        async def _update( 
            fig: Figure,
            cds: ColumnDataSource, 
            queue: "asyncio.Queue[ Dict[ str, np.ndarray ] ]",
            lines: Dict[ str, GlyphRenderer ]
        ) -> None:
            while not queue.empty():
                cds_data: Dict[ str, np.ndarray ] = await queue.get()

                ch_names = [ ch for ch in cds_data.keys() if ch != CDS_TIME_DIM ]
                offsets = np.arange( len( ch_names ) ) if self.STATE.channelize.value else np.zeros( len( ch_names ) )

                cds_data = { 
                    ch: ( arr * self.STATE.gain.value ) + offsets[ ch_names.index( ch ) ] 
                    if ch != CDS_TIME_DIM else arr 
                    for ch, arr in cds_data.items() 
                }

                # Add new lines to plot as necessary
                # TODO: Remove lines from plot as necessary
                for key, arr in cds_data.items():
                    if key not in cds.column_names:
                        cds.add( [ arr[0] ], key )
                        lines[ key ] = fig.line( 
                            x = CDS_TIME_DIM, 
                            y = key, 
                            source = cds 
                        )

                # FIXME: This causes crazy performance issues.  It needs to be done in a callback
                # if self.STATE.channelize.value:
                #     fig.yaxis.ticker = offsets
                #     fig.yaxis.major_label_overrides = dict( enumerate( ch_names ) )
                # else:
                #     fig.yaxis.ticker = AdaptiveTicker()
                #     ch_labels = [ str( idx ) for idx in range( len( ch_names ) ) ]
                #     fig.yaxis.major_label_overrides = dict( enumerate( ch_labels ) )

                cds.stream( cds_data, rollover = int( self.STATE.duration.value * self.STATE.cur_fs ) )
    
        cb = panel.state.add_periodic_callback( 
            partial( _update, fig, cds, queue, lines ), 
            period = 50 
        )

        def remove_queue( _: BokehSessionContext ) -> None:
            self.STATE.queues.remove( queue )
        self.STATE.queues.add( queue )
        panel.state.on_session_destroyed( remove_queue )

        return panel.Row( 
            panel.pane.Bokeh( fig ),
            panel.Column( 
                self.STATE.fs,
                self.STATE.n_time,
                "__Visualization Controls__",
                self.STATE.channelize,
                self.STATE.gain,
                self.STATE.duration,
                "__Butterworth Filter Design__",
                self.STATE.order,
                self.STATE.cuton,
                self.STATE.cutoff,
            )
        )

    @ez.publisher( OUTPUT_FILTER )
    async def change_filter( self ) -> AsyncGenerator:
        while True:
            design = await self.STATE.design_queue.get()
            yield self.OUTPUT_FILTER, design
    
    @ez.subscriber( INPUT_SIGNAL )
    async def on_signal( self, msg: AxisArray ) -> None:
        axis_name = self.SETTINGS.time_axis
        if axis_name is None:
            axis_name = msg.dims[0]
        axis = msg.get_axis(axis_name)
        fs = 1.0 / axis.gain

        with msg.view2d(axis_name) as view:
            
            ch_names = getattr( msg, 'ch_names', None )
            if ch_names is None:
                ch_names = [ f'ch_{i}' for i in range( view.shape[1] ) ]

            t = ( np.arange(view.shape[0]) / fs ) + self.STATE.cur_t
            cds_data = { CDS_TIME_DIM: t }
            for ch_idx, ch_name in enumerate( ch_names ):
                cds_data[ ch_name ] = view[ :, ch_idx ]

            self.STATE.cur_fs = fs
            self.STATE.cur_t += view.shape[0] / fs
            self.STATE.fs.value = fs
            self.STATE.n_time.value = view.shape[0]

            for queue in self.STATE.queues:
                queue.put_nowait( cds_data )


class TimeSeriesPlot( ez.Collection ):
    SETTINGS: TimeSeriesPlotSettings

    INPUT_SIGNAL = ez.InputStream(AxisArray)

    BPFILT = ButterworthFilter()
    GUI = TimeSeriesPlotGUI()

    def configure( self ) -> None:
        self.GUI.apply_settings( self.SETTINGS )
        self.BPFILT.apply_settings(
            ButterworthFilterSettings(
                axis = self.SETTINGS.time_axis
            )
        )

    def network( self ) -> ez.NetworkDefinition:
        return (
            ( self.INPUT_SIGNAL, self.BPFILT.INPUT_SIGNAL ),
            ( self.BPFILT.OUTPUT_SIGNAL, self.GUI.INPUT_SIGNAL ),
            ( self.GUI.OUTPUT_FILTER, self.BPFILT.INPUT_FILTER )
        )
