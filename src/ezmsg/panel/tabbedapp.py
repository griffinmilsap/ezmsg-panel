import abc
import typing

import panel as pn

class Tab(abc.ABC):

    @abc.abstractproperty
    def tab_name(self) -> str:
        raise NotImplementedError
    
    @abc.abstractmethod
    def sidebar(self) -> pn.viewable.Viewable:
        raise NotImplementedError
    
    @abc.abstractmethod
    def content(self) -> pn.viewable.Viewable:
        raise NotImplementedError
    

class TabbedApp:

    @property
    def title(self) -> str:
        return ''

    @property
    def tabs(self) -> typing.List[Tab]:
        return []
    
    @property
    def tab_names(self) -> typing.List[str]:
        return [t.tab_name for t in self.tabs]

    def app(self) -> pn.template.FastListTemplate:
        
        main = pn.Column(
            sizing_mode = 'stretch_both'
        )

        sidebar = pn.Column(
            sizing_mode = 'stretch_both'
        )

        tab_buttons = pn.widgets.RadioButtonGroup(
            name = 'Tab Select',
            options = self.tab_names,
            button_style = 'outline',
            sizing_mode = 'stretch_width',
            orientation = 'vertical',
        )

        @pn.depends(tab_buttons, watch = True)
        def tab_changed(tab: str) -> None:
            tab_idx = self.tab_names.index(tab)
            sidebar.clear()
            sidebar.append(self.tabs[tab_idx].sidebar())
            main.clear()
            main.append(self.tabs[tab_idx].content())

        if len(self.tab_names):
            tab_changed(self.tab_names[0])

        template = pn.template.FastListTemplate(
            title = self.title, 
            sidebar = [tab_buttons, pn.layout.Divider(), sidebar],
            main = [main],
        ) 

        return template