import typing

import ezmsg.core as ez
import panel as pn

class Tab:

    @property
    def tab_name(self) -> str:
        return 'Tab'
    
    @property
    def sidebar(self) -> pn.viewable.Viewable:
        return pn.Card(
            title = f'# {self.tab_name} Sidebar',
        )
    
    def content(self) -> pn.viewable.Viewable:
        return pn.Card(
            title = f'# {self.tab_name} Content',
            sizing_mode = 'expand_both'
        )
    

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

        template_sidebar = [sidebar]

        def populate(tab: str) -> None:
            tab_idx = self.tab_names.index(tab)
            sidebar.clear()
            sidebar.append(self.tabs[tab_idx].sidebar())
            main.clear()
            main.append(self.tabs[tab_idx].content())

        if len(self.tabs) > 1:

            tab_buttons = pn.widgets.RadioButtonGroup(
                name = 'Tab Select',
                options = self.tab_names,
                button_style = 'outline',
                sizing_mode = 'stretch_width',
                orientation = 'vertical',
            )

            @pn.depends(tab_buttons, watch = True)
            def tab_changed(tab: str) -> None:
                populate(tab)

            template_sidebar = [tab_buttons, pn.layout.Divider()] + template_sidebar
        
        if len(self.tab_names):
            populate(self.tab_names[0])

        template = pn.template.FastListTemplate(
            title = self.title, 
            sidebar = template_sidebar,
            main = [main],
        ) 

        return template