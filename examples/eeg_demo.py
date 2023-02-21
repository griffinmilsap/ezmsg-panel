from dataclasses import dataclass, field

import ezmsg.core as ez

from ezmsg.panel.application import Application, ApplicationSettings
from ezmsg.panel.spectrum import SpectrumPlot, SpectrumPlotSettings
from ezmsg.panel.timeseriesplot import TimeSeriesPlot, TimeSeriesPlotSettings
from ezmsg.sigproc.synth import EEGSynth, EEGSynthSettings

@dataclass
class EEGSpectrumSettingsMessage:
    eeg_settings: EEGSynthSettings = field(
        default_factory = EEGSynthSettings
    )
    app_settings: ApplicationSettings = field(
        default_factory = ApplicationSettings
    )


class EEGSpectrumSettings(ez.Settings, EEGSpectrumSettingsMessage):
    ...


class EEGSpectrum(ez.Collection):
    SETTINGS: EEGSpectrumSettings

    APP = Application()
    EEG = EEGSynth()
    TIMESERIES_PLOT = TimeSeriesPlot()
    SPECTRUM_PLOT = SpectrumPlot()

    def configure(self) -> None:

        self.APP.apply_settings(self.SETTINGS.app_settings)
        self.EEG.apply_settings(self.SETTINGS.eeg_settings)

        self.SPECTRUM_PLOT.apply_settings(
            SpectrumPlotSettings(
                name = 'EEG Spectrum',
                time_axis = 'time'
            )
        )

        self.TIMESERIES_PLOT.apply_settings(
            TimeSeriesPlotSettings(
                name = "EEG Timeseries",
                time_axis = 'time'
            )
        )

        self.APP.panels = {
            'Timeseries': self.TIMESERIES_PLOT.panel,
            'Spectra': self.SPECTRUM_PLOT.panel
        }

    def network(self) -> ez.NetworkDefinition:
        return (
            (self.EEG.OUTPUT_SIGNAL, self.SPECTRUM_PLOT.INPUT_SIGNAL),
            (self.EEG.OUTPUT_SIGNAL, self.TIMESERIES_PLOT.INPUT_SIGNAL)
        )

if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description = 'EEG Spectrum Example'
    )

    parser.add_argument(
        '--fs',
        type = float,
        help = 'Base sampling rate for EEG synth',
        default = 500.0
    )

    parser.add_argument(
        '--blocksize',
        type = int,
        help = "Number of EEG samples to output per message",
        default = 100
    )

    parser.add_argument(
        '--alpha',
        type = float,
        help = 'Frequency for alpha rhythm in EEG synth',
        default = 10.5
    )

    parser.add_argument(
        '--channels',
        type = int,
        help = "Number of EEG channels to simulate",
        default = 8
    )

    parser.add_argument(
        '--port',
        type = int,
        help = 'Port to host visualization on. [0 = Any port]',
        default = 0
    )

    class Args:
        fs: float
        channels: int
        blocksize: int
        alpha: float
        port: int

    args = parser.parse_args(namespace = Args)

    eeg_spectrum = EEGSpectrum(
        EEGSpectrumSettings(
            eeg_settings = EEGSynthSettings(
                fs = args.fs,
                n_time = args.blocksize,
                alpha_freq = args.alpha,
                n_ch = args.channels
            ),

            app_settings = ApplicationSettings(
                port = args.port,
                name = 'EEG Spectrum Example'
            )
        )
    )

    ez.run(eeg_spectrum)