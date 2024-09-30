import typing

import ezmsg.core as ez
import panel as pn

from bokeh.plotting import figure
from bokeh.model import Model
from bokeh.models import ColumnDataSource

from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.testing.lfo import LFO, LFOSettings

# Dealing with widgets in panel is easy and straight-forward!
# Unfortunately, streaming data to/updating Bokeh figures is NOT.
# Bokeh figures need to be created/updated per-session, which 
# causes some unfortunate headaches. This example is here to 
# demonstrate a scalable pattern for live Bokeh plots in ezmsg/panel  

class SimpleFigure:
    fig: Model
    cds: Model
    new_data: typing.List[typing.Tuple[float, float]]
    rollover: int

    def __init__(self, rollover: int) -> None:
        self.fig = figure()
        self.cds = ColumnDataSource(data = {'x': [], 'y': []})
        self.fig.line(x = 'x', y = 'y', source = self.cds)
    
        self.new_data = []
        self.rollover = rollover

    def add_point(self, x: float, y: float) -> None:
        self.new_data.append((x, y))

    # NOTE: async callbacks broken in recent panel/param
    # https://github.com/holoviz/panel/issues/5986
    # Once this is fixed; this should be updated to be async
    @pn.io.with_lock
    def update(self):
        if len(self.new_data):
            x, y = zip(*self.new_data)
            self.cds.stream({'x': x, 'y': y}, rollover = self.rollover)
        self.new_data.clear()


class BokehExampleSettings(ez.Settings):
    rollover: int = 100

class BokehExampleState(ez.State):
    cur_x: float = 0.0
    figures: typing.Set[SimpleFigure] 

class BokehExample(ez.Unit):
    SETTINGS = BokehExampleSettings
    STATE = BokehExampleState

    INPUT = ez.InputStream(float)

    async def initialize(self):
        self.STATE.figures = set()

    @ez.subscriber(INPUT)
    async def on_number(self, num: float) -> None:
        """ Called every time there's a new data point for our figure """

        # Here, we manually update every client with new data
        ez.logger.debug(f'Updating {len(self.STATE.figures)} figures')
        for figure in self.STATE.figures:
            figure.add_point(self.STATE.cur_x, num)
        self.STATE.cur_x += 1.0
        
    def panel(self) -> pn.viewable.Viewable:
        """ This method is called once for each client that requests this panel """

        # We have to create Bokeh models per-client and keep track of them individually
        # This is the only way we can update/stream content to/from these models
        plot = SimpleFigure(self.SETTINGS.rollover)
        pn.state.add_periodic_callback(plot.update, period = 100) # ms
        self.STATE.figures.add(plot)
        pn.state.on_session_destroyed(lambda _: self.STATE.figures.remove(plot))

        return pn.Column(
            "# Bokeh Example",
            plot.fig,
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
