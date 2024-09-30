from dataclasses import field
from pathlib import Path

import ezmsg.core as ez

from ezmsg.sigproc.synth import NoiseSettings, PinkNoise
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.panel.recorder import Recorder, RecorderSettings
from ezmsg.panel.replay import Replay, ReplaySettings
from ezmsg.panel.timeseriesplot import TimeSeriesPlot, TimeSeriesPlotSettings


class RecordReplaySystemSettings(ez.Settings):
    recorder_settings: RecorderSettings
    replay_settings: ReplaySettings
    synth_settings: NoiseSettings
    app_settings: ApplicationSettings = field(
        default_factory = ApplicationSettings
    )

class RecordReplaySystem(ez.Collection):

    SETTINGS = RecordReplaySystemSettings

    SYNTH = PinkNoise()
    RECORDER = Recorder()
    REPLAY = Replay()
    REPLAY_PLOT = TimeSeriesPlot()
    APP = Application()

    def configure( self ) -> None:
        self.RECORDER.apply_settings( self.SETTINGS.recorder_settings )
        self.SYNTH.apply_settings( self.SETTINGS.synth_settings )
        self.REPLAY.apply_settings( self.SETTINGS.replay_settings )
        self.REPLAY_PLOT.apply_settings( 
            TimeSeriesPlotSettings( time_axis = 'time' ) 
        )
        self.APP.apply_settings( self.SETTINGS.app_settings )

        self.APP.panels = {
            'record': self.RECORDER.panel,
            'replay': self.REPLAY.panel,
            'replay_plot': self.REPLAY_PLOT.panel
        }

    def network( self ) -> ez.NetworkDefinition:
        return ( 
            ( self.SYNTH.OUTPUT_SIGNAL, self.RECORDER.INPUT_MESSAGE ),
            ( self.REPLAY.OUTPUT_MESSAGE, self.REPLAY_PLOT.INPUT_SIGNAL )
        )

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = 'Record Replay Example'
    )

    parser.add_argument(
        '--data-dir',
        type = lambda x: Path( x ),
        help = "Directory for recording message output",
        default = Path.home() / 'record_replay'
    )

    class Args:
        data_dir: Path

    args = parser.parse_args(namespace = Args)

    system = RecordReplaySystem(
        RecordReplaySystemSettings(

            recorder_settings = RecorderSettings(
                name = 'Record',
                data_dir = args.data_dir
            ),

            replay_settings = ReplaySettings(
                name = "Replay",
                data_dir = args.data_dir
            ),

            synth_settings = NoiseSettings(
                n_time = 10,
                fs = 250,
                n_ch = 8,
                dispatch_rate = 'realtime'
            ),

            app_settings = ApplicationSettings(
                name = 'Recorder Test',
                port = 0
            )
        )
    )

    ez.run(RECORDER = system)