from typing import Any, List, Optional, Union
import flet as ft
import datetime


FONT_SIZE_FACTOR = 0.6

class Data_row(ft.UserControl):
    def __init__(self, column_names, values) -> None:
        super().__init__()
        self.column_names = column_names
        self.values = values
    
    def build(self):
        button_remove = ft.FloatingActionButton(
            icon=ft.icons.REMOVE,
            height=40*FONT_SIZE_FACTOR+5,
            width=30,
            bgcolor=ft.colors.RED_ACCENT,
            on_click=date_on_focus # TODO
        )
        self.body = []
        for column_name in self.column_names:
            if column_name == '日期':
                text = ft.TextField(
                    read_only=True,
                    # label=column_name,
                    value=self.values[column_name],
                    dense=True, 
                    height=40*FONT_SIZE_FACTOR+5, 
                    cursor_height=20*FONT_SIZE_FACTOR, 
                    content_padding = 10*FONT_SIZE_FACTOR,
                    width=90,
                )
            else:
                text = ft.TextField(
                    read_only=True,
                    # label=column_name,
                    value=self.values[column_name],
                    dense=True, 
                    height=40*FONT_SIZE_FACTOR+5, 
                    cursor_height=20*FONT_SIZE_FACTOR, 
                    content_padding = 10*FONT_SIZE_FACTOR,
                    expand=True
                )
            
            self.body.append(text)

        self.body.append(button_remove)
        
        return ft.Row(controls=self.body)

class Data_table(ft.UserControl):
    def __init__(self, table_name, column_controls: list) -> None:
        super().__init__()
        self.table_name = table_name
        if type(column_controls) != list:
            self.column_controls = [column_controls]
        else:
            self.column_controls = column_controls
        
        self.column_names = self.get_column_names()
        
        self.data = [ # FIXME
            {
                "id": 4,
                'hisno': '0000',
                "日期": "20230601",
                "處置": "IVIE",
                "側別": "OD",
                "Note": "increase SRF"
            },
            {
                "id": 3,
                'hisno': '0000',
                "日期": "20235031",
                "處置": "IVIE",
                "側別": "OD",
                "Note": "increase SRF"
            },
            {
                "id": 2,
                'hisno': '0000',
                "日期": "20230528",
                "處置": "IVIE",
                "側別": "OD",
                "Note": "increase SRF"
            },
            {
                "id": 1,
                'hisno': '0000',
                "日期": "20230527",
                "處置": "IVIE",
                "側別": "OD",
                "Note": "increase SRF"
            },
        ]
        self.data_append = []
        self.data_remove = []

    def build(self):
        button_add = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            height=40*FONT_SIZE_FACTOR+5,
            width=30,
            on_click=date_on_focus # TODO
        )

        self.body_input = ft.Row(
            controls=self.column_controls
        )

        self.body_input.controls.append(button_add)
        self.body_rows = []
        for data in self.data: # FIXME
            self.body_rows.append(Data_row(self.column_names, data))
        
        return ft.Column(controls= [
            self.body_input,
            ft.Divider(height=0, thickness=3),
            *self.body_rows
        ])

    def get_column_names(self):
        column_names = []
        for control in self.column_controls:
            column_names.append(control.label)
        return column_names

    # def datatable_add(self, e=None):
    #     # 資料驗證
        
    #     # datable資料新增
    #     self.body.append(
    #         Data_row()
    #     )
    #     # 清除輸入框
    #     pass

    # def datatable_remove(self, e=None):
    #     # ? 
    #     pass

    


def date_on_focus(e=None):
    e.control.value = ''
    e.control.update()


def main(page: ft.Page):
    d = Data_table(
        table_name="IVI_treatment",
        column_controls=[
            ft.TextField(
                label="日期",
                value=datetime.date.today().strftime("%Y%m%d"),
                tooltip=f"輸入處置時間(格式:{datetime.date.today().strftime('%Y%m%d')})",
                on_focus=date_on_focus,

                dense=True, 
                height=40*FONT_SIZE_FACTOR+5, 
                cursor_height=20*FONT_SIZE_FACTOR, 
                content_padding = 10*FONT_SIZE_FACTOR,
                width=90,
            ),
            ft.Dropdown(
                label="處置",
                options=[
                    ft.dropdown.Option("IVIE"),
                    ft.dropdown.Option("IVIL"),
                    ft.dropdown.Option("IVIF"),
                    ft.dropdown.Option("IVIB"),
                ],
                # width=max_length*8+40,
                dense=True,
                height=40*FONT_SIZE_FACTOR+5,
                content_padding=6,
                text_size=15,
                expand=True
            ),
            ft.Dropdown(
                label="側別",
                options=[
                    ft.dropdown.Option("OD"),
                    ft.dropdown.Option("OS"),
                    ft.dropdown.Option("OU"),
                ],
                # width=max_length*8+40,
                dense=True,
                height=40*FONT_SIZE_FACTOR+5,
                content_padding=6,
                text_size=15,
                expand=True
            ),
            ft.TextField(
                label="Note",
                
                dense=True, 
                # height=40*FONT_SIZE_FACTOR+5, 
                cursor_height=20*FONT_SIZE_FACTOR, 
                content_padding = 10*FONT_SIZE_FACTOR,
                multiline=True,
                expand=True,
            )
        ]
    )

    page.add(d)


ft.app(target=main)