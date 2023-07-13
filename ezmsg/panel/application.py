from dataclasses import field

import panel
import ezmsg.core as ez

from typing import TYPE_CHECKING, Mapping, Union, Callable, Optional, Dict, Any

if TYPE_CHECKING:
    from panel.template.base import BaseTemplate
    from panel.viewable import Viewable, Viewer

    TViewable = Union[Viewable, Viewer, BaseTemplate]
    TViewableOrFunc = Union[TViewable, Callable[[], TViewable]]

class ApplicationSettings(ez.Settings):
    port: Optional[ int ] = None # None => disable server, 0 => choose open port
    name: str = 'ezmsg Panel'
    serve_kwargs: Dict[ str, Any ] = field( default_factory = dict )


class Application( ez.Unit ):
    SETTINGS: ApplicationSettings

    panels: Mapping[ str, 'TViewableOrFunc' ]

    @ez.task
    async def serve( self ) -> None:
        if self.SETTINGS.port is not None:
            if hasattr( self, 'panels' ):

                def create_app():
                    template = panel.template.FastGridTemplate(
                        title="EEG Demo",
                        prevent_collision=True,
                        save_layout=True,
                        theme_toggle=False,
                        theme='dark',
                        row_height=320
                    )
                    for i, pane in enumerate(self.panels.values()):
                        template.main[i*2:(i+1)*2,:] = pane()
                    return template

                panel.serve( 
                    create_app,
                    port = self.SETTINGS.port,
                    title = self.SETTINGS.name,
                    websocket_origin = '*',
                    **self.SETTINGS.serve_kwargs
                )
            else:
                ez.logger.warning( "Panel application has no panels set. " + \
                    "Did you forget to configure the panels attribute?"
                )
