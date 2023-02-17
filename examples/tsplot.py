from dataclasses import field

import ezmsg.core as ez
from ezmsg.sigproc.synth import NoiseSettings, PinkNoise
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.panel.timeseriesplot import TimeSeriesPlot, TimeSeriesPlotSettings

class TestTSMessagePlotterSystemSettings( ez.Settings ):
    plot_settings: TimeSeriesPlotSettings
    synth_settings: NoiseSettings
    app_settings: ApplicationSettings = field(
        default_factory = ApplicationSettings
    )

class TestTSMessagePlotterSystem( ez.Collection ):

    SETTINGS: TestTSMessagePlotterSystemSettings

    SYNTH = PinkNoise()
    PLOT = TimeSeriesPlot()
    APP = Application()

    def configure( self ) -> None:
        self.PLOT.apply_settings( self.SETTINGS.plot_settings )
        self.SYNTH.apply_settings( self.SETTINGS.synth_settings )
        self.APP.apply_settings( self.SETTINGS.app_settings )

        self.APP.panels = {
            'TimeSeriesPlot': self.PLOT.GUI.panel
        }

    def network( self ) -> ez.NetworkDefinition:
        return ( 
            ( self.SYNTH.OUTPUT_SIGNAL, self.PLOT.INPUT_SIGNAL ),
        )

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = 'TimeSeriesPlot Test Script'
    )

    parser.add_argument(
        '--channels',
        type = int,
        help = "Number of EEG channels to simulate",
        default = 8
    )

    class Args:
        channels: int

    args = parser.parse_args(namespace = Args)

    system = TestTSMessagePlotterSystem(
        TestTSMessagePlotterSystemSettings(

            plot_settings = TimeSeriesPlotSettings(
                name = 'TimeSeriesPlot',
            ),

            synth_settings = NoiseSettings(
                n_time = 10,
                fs = 250,
                n_ch = args.channels,
                dispatch_rate = 'realtime'
            ),

            app_settings = ApplicationSettings(
                name = 'TimeSeriesPlot Test',
                port = 0,
            )
        )
    )

    ez.run( system )