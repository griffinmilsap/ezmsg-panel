import typing

import ezmsg.core as ez
import panel as pn

from bokeh.plotting import figure
from bokeh.model import Model
from bokeh.models import ColumnDataSource
from bokeh.server.contexts import BokehSessionContext
from panel.io.callbacks import PeriodicCallback

from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.testing.lfo import LFO, LFOSettings

class BokehFigure:

    fig: Model
    cds: Model
    cb: PeriodicCallback

    new_data: typing.List[typing.Tuple[float, float]]
    rollover: int

    def __init__(self, rollover: int, update_period_ms: int = 50) -> None:
        self.fig = figure()
        self.cds = ColumnDataSource(data = {'x': [], 'y': []})
        self.fig.line(x = 'x', y = 'y', source = self.cds)

        self.cb = pn.state.add_periodic_callback(self.update, period = update_period_ms)
        self.new_data = []
        self.rollover = rollover

    def add_point(self, x: float, y: float) -> None:
        self.new_data.append((x, y))

    # NOTE: async callbacks broken in recent panel/param
    @pn.io.with_lock
    def update(self):
        ez.logger.info(f'{self.cb=}')
        if len(self.new_data):
            x, y = zip(*self.new_data)
            self.cds.stream({'x': x, 'y': y}, rollover = self.rollover)
        self.new_data.clear()

    @property
    def figure(self) -> Model:
        return self.fig


class BokehExampleSettings(ez.Settings):
    rollover: int = 100

class BokehExampleState(ez.State):
    cur_x: float = 0.0
    figures: typing.Set[BokehFigure] 

class BokehExample(ez.Unit):
    SETTINGS: BokehExampleSettings
    STATE: BokehExampleState

    INPUT = ez.InputStream(float)

    async def initialize(self):
        self.STATE.figures = set()

    @ez.subscriber(INPUT)
    async def on_number(self, num: float) -> None:
        ez.logger.info(f'Updating {len(self.STATE.figures)} figures')
        for figure in self.STATE.figures:
            figure.add_point(self.STATE.cur_x, num)
        self.STATE.cur_x += 1.0
        
    def panel(self) -> pn.viewable.Viewable:
        """ This method is called once for each client that requests this panel """

        # We have to create Bokeh models per-client and keep track of them individually
        # This is the only way we can update/stream content to/from these models
        fig = BokehFigure(self.SETTINGS.rollover)
        # fig = self.STATE.fig

        # We only want to service this figure as long as this session is active
        # So we ask panel to keep remove this figure from the STATE once session is destroyed
        # This won't happen immediately once the client disconnects; there's a ~50 second timeout
        # that keeps the session alive.
        def remove_queue(_: BokehSessionContext) -> None:
            self.STATE.figures.remove(fig)
        self.STATE.figures.add(fig)
        pn.state.on_session_destroyed(remove_queue)

        return pn.Column(
            "# Bokeh Example",
            fig.figure,
        )

if __name__ == '__main__':

    lfo = LFO(LFOSettings(freq = 0.2, update_rate = 2.0))
    example = BokehExample()

    app = Application(
        ApplicationSettings(
            port = 0,
            name = 'Bokeh Example'
        )
    )

    app.panels = {
        'example': example.panel
    }

    ez.run(
        LFO = lfo,
        EXAMPLE = example,
        APP = app,
        connections = (
            (lfo.OUTPUT, example.INPUT),
        )
    )
