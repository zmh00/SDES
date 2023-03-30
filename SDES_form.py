import flet as ft
from flet import Page
import datetime
# import bot_gui
import time
from typing import Union
import sqlalchemy


DATE_MODE = 1


def format_today(mode=DATE_MODE):
    if mode == 1: # 西元紀年
        today = datetime.datetime.today().strftime("%Y%m%d")
    elif mode == 2: # 民國紀年
        today = str(datetime.datetime.today().year-1911) + datetime.datetime.today().strftime("%m%d") 
    elif mode == 3: # 西元紀年，兩位數
        today = str(datetime.datetime.today().year-2000) + datetime.datetime.today().strftime("%m%d")
    return today


class Measurement(ft.UserControl):
    def __init__(self, label: str, control_type: ft.Control, item_list: list): # 接受參數用
        super().__init__()
        self.label = label # 辨識必須: 後續加入form內的measurement都需要label
        self.control_type = control_type # 未使用考慮可以移除
        self.head = None
        self.body = {}
        if type(item_list) is not list:
            self.item_list = [item_list]
        else:
            self.item_list = item_list

    def __repr__(self) -> str:
        return f"{self.label}||{super().__repr__()}"

    def build(self): # 初始化UI
        pass # 需要客製化: 因為元件設計差異大，Method overriding after inheritence

    def clear_body(self, e=None): # 清除
        pass

    def set_default(self, e=None): # 恢復預設值
        pass
    
    def format_text(self, e=None): # 帶入門診病例的格式
        pass

    def get_values(self, e=None) -> dict :  #將內部資料輸出: dict( {self.label}_{item_name} : value )
        values = {}
        for item in self.item_list:
            key = f"{self.label}_{item}".replace(' ','_') # 把空格處理掉 => 減少後續辨識錯誤
            values[key] = self.body[item].value
        return values


class Measurement_Text(Measurement):
    def __init__(self, label: str, item_list: list = None, multiline = False, format_func = None, default: dict = None):
        super().__init__(label, ft.TextField, item_list)
        self.multiline = multiline
        self.format_func = format_func
        self.default = default # {item_keys: default_value}
        if item_list is None:
            self.item_list = ['OD', 'OS'] # 預設是雙眼的資料
        
    # specific to textbox
    def set_multiline(self):
        for item in self.body:
            self.body[item].multiline = True
            self.body[item].height = None
        # self.row.update() # 建立時就指定應該不用update

    def add_before_build(self, data_row: dict):
        for keys in data_row:
            self.item_list.append(keys)
            self.body[keys] = data_row[keys]
    
    def add_after_build(self, data_row: dict):
        for keys in data_row:
            self.item_list.append(keys)
            self.body[keys] = data_row[keys]
            self.row.controls.append(self.body[keys])
        self.update()


    def build(self):
        self.head = ft.Text(self.label, text_align='center', style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.W_400, color=ft.colors.BLACK)
        style_textfield = dict(
            dense=True, 
            height=40, 
            cursor_height=20, 
            content_padding = 10, 
            expand=True
        )
        if len(self.item_list) == 1:
            self.body[self.item_list[0]] = ft.TextField(autofocus=True, **style_textfield)
        else:
            for i, item_name in enumerate(self.item_list):
                if self.body.get(item_name, None) != None:
                    continue
                if i == 0:
                    self.body[item_name] = ft.TextField(label=item_name, autofocus=True, **style_textfield)
                else:
                    self.body[item_name] = ft.TextField(label=item_name, **style_textfield)
        
        # UI呈現的載體，資料操作可以針對body
        self.row = ft.Row(
            # expand=True, 
            controls=[
                self.head,  
            ]
        )

        # 這段能確保顯示的順序和建立時一致
        for item_name in self.item_list:
            self.row.controls.append(self.body[item_name])
        
        # set_multiline if True
        if self.multiline == True:
            self.set_multiline()

        # 使用預設值初始化
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]    

        return self.row
    

    def clear_body(self, e=None):
        for item_name in self.body:
            self.body[item_name].value = ''
        self.update()


    def set_default(self, e=None):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用
        

    def format_text(self, e=None):
        if self.format_func == None:
            format_text = ''
            data_exist = 0
            for i in self.body:
                if i == 'OD' or i == 'OS':
                    if self.body[i].value.strip() != '':
                        if data_exist:
                            format_text = format_text + f", {self.body[i].value} {i}"
                        else:
                            format_text = format_text + f"{self.body[i].value} {i}"
                        data_exist = 1
                else:
                    # TODO 以下兩行是給IOP的偵測模式用的，但這樣不通用，需要再考慮
                    if data_exist:
                        format_text = format_text + f"({self.body[i].value})" 
            
            if data_exist: # 只輸出有資料的
                today = format_today()
                format_text = f"{today} {self.label}:{format_text}"
        else:
            format_text = self.format_func() # EXO、IOP需要客製化

        return format_text


class Measurement_Check(Measurement):
    def __init__(self, label: str, item_list: list, width_list: Union[list[int], int] = 70, format_func = None, default: dict = None, compact = False):
        super().__init__(label, ft.Checkbox, item_list)
        self.default = default # {item_keys: default_value}
        self.format_func = format_func
        self.compact = compact
        if type(width_list) ==  list:
            if len(width_list) != len(item_list):
                raise Exception("Not match between width_list and item_list")
            self.checkbox_width = width_list
        else:
            self.checkbox_width = [width_list] * len(item_list)
        
    
    def build(self):
        self.head = ft.Text(self.label, text_align='center', style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.W_400, color=ft.colors.BLACK)
        for i, item_name in enumerate(self.item_list):
            self.body[item_name] = ft.Checkbox(label=item_name, value=False, width=self.checkbox_width[i])
        
        self.row = ft.Row(
            controls=[],
            spacing=1,
            run_spacing=1,
            wrap=True,
        )
        
        # 這段能確保顯示的順序和建立時一致
        for item_name in self.item_list: 
            self.row.controls.append(self.body[item_name])

        # 使用預設值初始化
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]

        # 決定輸出緊密程度
        if self.compact:
            return ft.Row(controls=[self.head, self.row], wrap=True)
        else:
            return ft.Column(controls=[self.head, self.row]) # 讓head換行後接著checkboxes
    

    def clear_body(self, e=None):
        for item_name in self.body:
            self.body[item_name].value = False
        self.update()


    def set_default(self, e=None):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用


    def format_text(self, e=None):
        if self.format_func == None:
            format_text = ''
            data_exist = 0
            for item_name in self.body:
                if self.body[item_name].value != False:
                    if data_exist:
                        format_text = format_text + f",{item_name}"
                    else:
                        format_text = format_text + f"{item_name}"
                    data_exist = 1
            
            if data_exist: # 只輸出有資料的
                today = format_today()
                format_text = f"{today} {self.label}:{format_text}"
        else:
            format_text = self.format_func() # 保留客製化需求?

        return format_text


class Form(ft.Tab): #目的是擴增Tab的功能
    def __init__(self, label, measurement_list: list[Measurement]):
        super().__init__()
        self.label = label # 資料儲存
        self.measurement_list = measurement_list # 資料儲存
        # self.measurements = dict() # 先留著備案，耗記憶體但快速
        # for m in measurement_list:
        #     self.measurements[m.label] = m
        
        self.text = self.label # 呈現用途
        self.content = ft.Container( # 呈現用途
            content=ft.Column(
                controls=self.measurement_list,
                scroll="adaptive",
            ),
            alignment=ft.alignment.center,
            padding=ft.padding.only(top = 15, bottom=15),
        )
    

    @property
    def measurements(self, item_name: str):
        for measurement in self.measurement_list:
            if measurement.label == item_name:
                return measurement
        return None


    def clear_body(self, e=None):
        for measurement in self.measurement_list:
            measurement.clear_body()
    
    def set_default(self, e=None):
        for measurement in self.measurement_list:
            measurement.set_default()

    def format_text(self, e=None):
        format_text = ''
        print(self.measurement_list) # TODO
        for measurement in self.measurement_list:
            text = measurement.format_text().strip()
            if text != '':
                format_text = format_text + text + '\n'
        
        print(format_text) # TODO

        # return format_text

    def get_values(self, e=None): # 集合所有的measurement values, 若有同名後者會覆寫前者
        values = dict()
        for measurement in self.measurement_list:
            values.update(measurement.get_values())
        return values

    def db_save(self, e=None):
        pass

    def db_load(self, e=None):
        pass


########################## Basic
# 客製化IOP按鈕
iop = Measurement_Text('IOP', default=dict(iop_mode = 'Pneumo'))
iop.add_before_build(
    {
        'iop_mode': ft.Dropdown(
            width=100,
            height=40,
            content_padding = 10,
            dense=True,
            expand=True,
            label="Mode",
            # hint_text="",
            options=[
                ft.dropdown.Option("Pneumo"),
                ft.dropdown.Option("GAT"),
                ft.dropdown.Option("Tonopen"),
            ],
        )
    }   
)

form_basic = Form(
    label="Basic",
    measurement_list=[
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        iop,
        Measurement_Text('Cornea', multiline=True),
        Measurement_Text('Lens'),
        Measurement_Text('Fundus', multiline=True),
        Measurement_Text('CDR'),
    ]
)
########################## Plasty
form_plasty = Form(
    label = "Plasty",
    measurement_list = [
        Measurement_Text('MRD'),
        Measurement_Text('LF'),
        Measurement_Text('Exo', ['OD', 'PD', 'OS']),
        Measurement_Text('EOM'),
        Measurement_Check(
            label = 'CAS', 
            item_list = ['Retrobulbar pain', 'Motion pain', 'Redness eyelid', 'Redness conjunctiva', 'Swelling caruncle', 'Swelling eyelids', 'Swelling conjunctiva'], 
            width_list = 150,
        ),
        Measurement_Check(
            label = 'Muscle Involvement',
            item_list = ['SR', 'MR', 'IR', 'LR', 'SO', 'IO', 'LE'],
            width_list = 70
        )
    ],
)
########################## DED
form_dryeye = Form(
    label="DryEye",
    measurement_list=[
        Measurement_Check('Symptom', ['photophobia','pain'], [130,70], compact=True),
        Measurement_Check('History', ['Smoking','Hyperlipidemia'], [100,130], compact=True),
        Measurement_Text('OSDI', '_'),
        Measurement_Text('SPEED', '_'),
        Measurement_Text('Shirmer'),
        Measurement_Text('TBUT'),
        Measurement_Text('NEI'),
        Measurement_Check('Anterior displacement MCJ', ['OD','OS'], [70,70], compact=True),
        Measurement_Text('Mei_EXP'),
        Measurement_Text('Mei_NUM')
    ]
)
########################## IVI
form_ivi = Form(
    label="IVI",
    measurement_list=[
        Measurement_Text('VA'),
        iop,
        Measurement_Text('Lens'),
        Measurement_Text('CMT'),
        Measurement_Check('IRF', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('SRF', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('SHRM', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('Atrophy', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('Gliosis', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('New hemorrhage', ['OD','OS'], [70,70], compact=True),
        Measurement_Text('Fundus', multiline=True),
    ]
)
########################## MERGE

_form_list = [form_basic, form_plasty, form_dryeye, form_ivi]


def forms():
    return _form_list