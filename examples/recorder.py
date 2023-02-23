from dataclasses import dataclass, field
from pathlib import Path

import ezmsg.core as ez

from ezmsg.sigproc.synth import NoiseSettings, PinkNoise
from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.panel.recorder import Recorder, RecorderSettings

class TestRecorderSystemSettings(ez.Settings):
    recorder_settings: RecorderSettings
    synth_settings: NoiseSettings
    app_settings: ApplicationSettings = field(
        default_factory = ApplicationSettings
    )

class TestRecorderSystem(ez.Collection):

    SETTINGS: TestRecorderSystemSettings

    SYNTH = PinkNoise()
    RECORDER = Recorder()
    APP = Application()

    def configure( self ) -> None:
        self.RECORDER.apply_settings( self.SETTINGS.recorder_settings )
        self.SYNTH.apply_settings( self.SETTINGS.synth_settings )
        self.APP.apply_settings( self.SETTINGS.app_settings )

        self.APP.panels = {
            'recorder': self.RECORDER.GUI.panel
        }

    def network( self ) -> ez.NetworkDefinition:
        return ( 
            ( self.SYNTH.OUTPUT_SIGNAL, self.RECORDER.INPUT_MESSAGE ),
        )

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = 'MessageRecorder Test'
    )

    parser.add_argument(
        '--data-dir',
        type = lambda x: Path( x ),
        help = "Directory for recording message output",
        default = Path.home() / 'messagerecorder_test'
    )

    class Args:
        data_dir: Path

    args = parser.parse_args(namespace = Args)

    system = TestRecorderSystem(
        TestRecorderSystemSettings(

            recorder_settings = RecorderSettings(
                name = 'RecorderTest',
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

    ez.run_system( system )