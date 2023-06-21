import flet as ft
import datetime
from typing import Any, Union, List, Tuple
import psycopg2
from psycopg2.sql import SQL, Identifier, Placeholder, Literal
from psycopg2.extras import RealDictCursor
import logging
import inspect
import os
import time

import plotly.express as px

# CONST and ATTRIBUTES
TEST_MODE = bool(os.getenv('SDES_TEST', False))
FORMAT_MODE = 0
# DATE_MODE = 1
HOST = '10.53.70.143'
if TEST_MODE:
    HOST = 'localhost'
PORT = '5431'
DBNAME = 'vgh_oph_2'
USER = 'postgres'
PASSWORD ='qazxcdews'
FONT_SIZE_FACTOR = 0.6
INTERVAL_FOR_NEW_DB_ROW = datetime.timedelta(hours=5) # 距離上筆記錄的創造時間大於5小時前就算新紀錄 
# DOCTOR_ID

# COLUMN NAMES
COLUMN_ID = 'id'
COLUMN_PATIENT_HISNO = 'patient_hisno'
COLUMN_PATIENT_NAME = 'patient_name'
COLUMN_PATIENT_BIRTHDAY = 'patient_birthday'
COLUMN_PATIENT_AGE = 'patient_age'
COLUMN_DOC = 'doctor_id'
COLUMN_TIME_CREATED = 'created_at'
COLUMN_TIME_UPDATED = 'updated_at'

class PatientData():
    def __init__(self, hisno, name=None, birthday=None, age=None) -> None:
        self.data_dict = {
            COLUMN_PATIENT_HISNO: hisno,
            COLUMN_PATIENT_NAME: name,
            COLUMN_PATIENT_BIRTHDAY: birthday,
            COLUMN_PATIENT_AGE: age
        }
        self.hisno = hisno
        self.name = name
        self.birthday = birthday
        self.age = age
        self.db_row_id = {} # key: form_name; value: db_row_id
        self.db_loaded_dict = {}
    
    def __eq__(self, __value: object) -> bool: # 定義比較相等的方法
        if not isinstance(__value, PatientData):
            return False
        return self.hisno == __value.hisno

#客製化基本設定: 檔案+console
logger = logging.getLogger("SDES_form")
logger.setLevel(logging.DEBUG) #這是logger的level
BASIC_FORMAT = '[%(asctime)s %(levelname)-8s] %(message)s'
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(BASIC_FORMAT, datefmt=DATE_FORMAT)
if TEST_MODE:
    ##設定console handler的設定
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG) ##可以獨立設定console handler的level，如果不設就會預設使用logger的level
    ch.setFormatter(formatter)
    logger.addHandler(ch)
##設定file handler的設定
log_filename = "SDES_log.txt"
fh = logging.FileHandler(log_filename) #預設mode='a'，持續寫入
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
##將handler裝上
logger.addHandler(fh)

def db_close(): # 如果不釋出不知道會造成甚麼效應?
    cursor.close()
    db_conn.close()

def db_connect():
    global db_conn
    global cursor
    try:
        # 偵測database
        query_db_exists = f'''
        SELECT EXISTS( 
            SELECT datname FROM pg_catalog.pg_database WHERE datname = '{DBNAME}'
        );'''
        query_db_create = f'''
        CREATE DATABASE {DBNAME};
        '''
        
        t_conn = psycopg2.connect(host=HOST, dbname='postgres', user=USER, password=PASSWORD, port = PORT)
        t_cursor = t_conn.cursor(cursor_factory = RealDictCursor)
        t_cursor.execute(query_db_exists)
        t_conn.commit() # 
        exists_db = t_cursor.fetchone()['exists']
        if exists_db == False:
            t_conn.autocommit = True
            t_cursor.execute(query_db_create)
            logger.info(f"{inspect.stack()[0][3]}||[{DBNAME}] Database builded")
            t_conn.close()
        else:
            logger.info(f"{inspect.stack()[0][3]}||[{DBNAME}] Database exists")
        db_conn = psycopg2.connect(host=HOST, dbname=DBNAME, user=USER, password=PASSWORD, port = PORT)
        cursor = db_conn.cursor(cursor_factory = RealDictCursor)
        logger.info(f"{inspect.stack()[0][3]}||[{DBNAME}] Connect database successfully!")
        # except Exception as error:
        #     t_conn.rollback()
        #     logger.error(f"{inspect.stack()[0][3]}||Error in building database: {error}")
        #     return False
    except Exception as e:
        logger.error(f"{inspect.stack()[0][3]}||Encounter exception: {e}")


#### FORMAT REGION ####
## form內黏合measurement的輸出格式
def format_merge(format_list: list, **kwargs):
    format_text = ''
    if FORMAT_MODE == -1: # 無任何日期
        for item in format_list:
            format_text = format_text + f"{item}\n"
    elif FORMAT_MODE == 0: # 區塊模式
        today = datetime.datetime.today().strftime("%Y%m%d")
        format_text = f"--{kwargs.get('form_name')}:{today}--\n"
        for item in format_list:
            format_text = format_text + f"{item}\n"
    elif FORMAT_MODE == 1: # 每行西元紀年
        today = datetime.datetime.today().strftime("%Y%m%d")
        for item in format_list:
            format_text = format_text + f"{today} {item}\n"
    elif FORMAT_MODE == 2: # 每行民國紀年
        today = str(datetime.datetime.today().year-1911) + datetime.datetime.today().strftime("%m%d")
        for item in format_list:
            format_text = format_text + f"{today} {item}\n"
    elif FORMAT_MODE == 3: # 每行西元紀年(2位數)
        today = str(datetime.datetime.today().year-2000) + datetime.datetime.today().strftime("%m%d")
        for item in format_list:
            format_text = format_text + f"{today} {item}\n"
    
    return format_text
    
## measurement的輸出格式

# Format Template
# def format_(measurement):
#     format_text = ''
#     ... = measurement.body['...'].value.strip()
#     ... = measurement.body['...'].value.strip()
#     format_text = ......

#     format_text = f"{measurement.label}:" + format_text
#     return format_text

def format_no_output(measurement):
    '''
    No format output
    '''
    return ''


def format_text_tradition(measurement):
    '''
    Ex: Cornea:clear OD, clear OS, ...
    '''
    format_text = ''
    other_format_text = ''
    for item_name in measurement.item_list:
        if item_name == 'OD' or item_name == 'OS':
            if measurement.body[item_name].value.strip() != '':
                format_text = format_text + f"{measurement.body[item_name].value} {item_name}, "
        else:
            if measurement.body[item_name].value.strip() != '':
                other_format_text = other_format_text + f"{measurement.body[item_name].value} {item_name}, "
    format_text = format_text + other_format_text
    
    format_text = f"{measurement.label}:" + format_text.rstrip(', ')
    return format_text


def format_text_slash(measurement):
    '''
    Ex: TBUT: 5/5
    '''
    format_text = ''
    for item_name in measurement.item_list:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/')
    return format_text


def format_text_slash_mm(measurement):
    '''
    Ex: Schirmer 1:5/5mm
    '''
    format_text = ''
    for item_name in measurement.item_list:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/') + 'mm'
    return format_text


def format_text_slash_um(measurement):
    '''
    Ex: CCT: 5/5um
    '''
    format_text = ''
    for item_name in measurement.item_list:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/') + 'um'
    return format_text


def format_text_parentheses(measurement):
    '''
    Ex: K(OD):(H).../(V)...
    '''
    format_text_list = []
    for item_name in measurement.item_list:
        t = measurement.body[item_name].value.strip()
        t = t if t != '' else '?'
        format_text_list.append(f'({item_name}){t}')

    format_text = f"{measurement.label}:" + '/'.join(format_text_list)
    return format_text


# def format_checkbox(measurement): # 先暫時不使用
#     '''
#     Ex: IRF:OD,OS
#     '''
#     format_text = ''
#     for item_name in measurement.body:
#         if measurement.body[item_name].value == True:
#             format_text = format_text + f"{item_name},"

#     format_text = f"{measurement.label}:" + format_text.rstrip(',')
#     return format_text


def format_checkbox_tristate(measurement):
    '''
    Ex: History:DM(+),CHF(-)
    '''
    format_text = ''
    if measurement.tristate == True: # 三種狀態
        for item_name in measurement.item_list:
            if measurement.body[item_name].value == True:
                format_text = format_text + f"{item_name}(+),"
            elif measurement.body[item_name].value == None:
                format_text = format_text + f"{item_name}(-),"
            else: # tristate下沒勾選的會跳過
                pass 
    else: # 二種狀態
        for item_name in measurement.item_list:
            if measurement.body[item_name].value == True:
                format_text = format_text + f"{item_name}(+),"
            else:
                format_text = format_text + f"{item_name}(-),"

    format_text = f"{measurement.label}:" + format_text.rstrip(',')
    return format_text


## 以下為客製欄位
def format_iop(measurement):
    '''
    Ex: IOP:(Pneumo)10/10mmHg
    '''
    format_text = ''
    iop_od = measurement.body['OD'].value.strip()
    iop_od = iop_od if iop_od != '' else 'x'
    iop_os = measurement.body['OS'].value.strip()
    iop_os = iop_os if iop_os != '' else 'x'

    iop_mode = measurement.body['mode'].value
    if iop_mode =='' or iop_mode == None:
        format_text = f"{iop_od}/{iop_os}mmHg"
    else:
        format_text = f"({iop_mode}){iop_od}/{iop_os}mmHg"

    format_text = f"{measurement.label}:" + format_text
    return format_text


def format_exo(measurement):
    '''
    Ex: EXO:12>--65--<12
    '''
    exo_od=''
    exo_os=''
    exo_pd=''
    if measurement.body['OD'].value.strip() != '':
        exo_od = measurement.body['OD'].value.strip()
    if measurement.body['OS'].value.strip() != '':
        exo_os = measurement.body['OS'].value.strip()
    if measurement.body['PD'].value.strip() != '':
        exo_pd = measurement.body['PD'].value.strip()
    else:
        format_text = f"{measurement.label}:{exo_od}>--{exo_pd}--<{exo_os}"
        return format_text
    
def format_goct(measurement):
    '''
    Ex: GOCT:RNFL:80/80um, GCIPL:65/65um
    '''
    rnfl_od='err'
    rnfl_os='err'
    gcipl_od='err'
    gcipl_os='err'
    if measurement.body['RNFL_OD'].value.strip() != '':
        rnfl_od = measurement.body['OD'].value.strip()
    if measurement.body['RNFL_OS'].value.strip() != '':
        rnfl_os = measurement.body['OS'].value.strip()
    if measurement.body['GCIPL_OD'].value.strip() != '':
        gcipl_od = measurement.body['OD'].value.strip()
    if measurement.body['GCIPL_OS'].value.strip() != '':
        gcipl_os = measurement.body['OS'].value.strip()  
    
    format_text = f"{measurement.label}:RNFL:{rnfl_od}/{rnfl_os}um, GCIPL:{gcipl_od}/{gcipl_os}um"
    return format_text
#### FORMAT REGION ####


class Measurement(ft.UserControl):
    def head_on_click(self, e=None):
        '''
        head元件點擊後觸發:全有全無快捷
        '''
        if self.control_type == ft.TextField: # textfield型態 => return to defaulr
            self.data_return_default()
        elif self.control_type == ft.Checkbox:
            if self.tristate == True:
                head_click_state = [False, True, None]
            else:
                head_click_state = [False, True]
            index = self.head_click_state_index + 1
            if index >= len(head_click_state):
                index = 0
            self.head_click_state_index = index
            for item in self.item_list:
                if type(self.body[item]) == ft.Checkbox: # 要是checkbox才調整值
                    self.body[item].value = head_click_state[index]

        elif self.control_type == ft.Dropdown:
            pass

        self.row.update()
    

    def head_on_enter(self, e=None):
        '''
        head元件進入後觸發:顏色變藍
        '''
        e.control.style.color = ft.colors.BLUE
        e.control.update()

    def head_on_exit(self, e=None):
        '''
        head元件離開後觸發:顏色還原
        '''
        e.control.style.color = None
        e.control.update()

    def __init__(self, label: str, control_type: ft.Control, item_list: List[str], format_func, format_region, default): # 接受參數用
        super().__init__()
        self.label = label # 辨識必須: 後續加入form內的measurement都需要label
        self.control_type = control_type # 未使用考慮可以移除
        
        # 新版self.head => 加上點擊快捷效果
        self.head_click_state_index = 0 # 標註head的點擊狀態:起始是False(checkbox為空)
        self.head = ft.Text(
            text_align='center',
            spans=[
                ft.TextSpan(
                    self.label, # 替換成label
                    style=ft.TextStyle(
                        size=25 * FONT_SIZE_FACTOR, 
                        weight=ft.FontWeight.W_600, 
                        color=ft.colors.BLACK,
                    ),
                    on_enter=self.head_on_enter,
                    on_exit=self.head_on_exit,
                    on_click=self.head_on_click,
                )
            ],
            tooltip=""
        )


        ## 舊版self.head
        # self.head = ft.Text(
        #     self.label, 
        #     text_align='center', 
        #     # style=ft.TextThemeStyle.TITLE_MEDIUM,
        #     size=25 * FONT_SIZE_FACTOR, 
        #     weight=ft.FontWeight.W_600, 
        #     color=ft.colors.BLACK,
        # ) 
        
        self.body = {} # 一個measurement下各個item欄位control會被放入body(dict)內部，最後build時會被逐一加入self.row內輸出
        if type(item_list) is not list: # 輸入一個item轉換成list型態
            self.item_list = [str(item_list)]
        else:
            self.item_list = item_list
        
        self.ignore_exist_item_list = [] # 跳脫data_exist檢查的項目，此功能要透過add_control加入的元件才能設定
        
        self.format_func = format_func
        self.format_region = format_region
        self.default = default # {item_keys: default_value}


    def __repr__(self) -> str:
        return f"{self.label}||{super().__repr__()}"


    def build(self): # 初始化UI
        pass # 需要客製化: 因為元件設計差異大，Method overriding after inheritence

    
    def add_control(self, item_name, control, ignore_exist = False):
        '''
        在啟動(build)之前增加flet元素
        此函數影響item_list和body內容
        ignore_exist 可讓此項目不影響data_exist判斷 => 較不重要的項目
        '''
        self.item_list.append(item_name)
        self.body[item_name] = control
        if ignore_exist:
            self.ignore_exist_item_list.append(item_name)

    
    def data_clear(self): 
        '''
        顯示欄位清除
        '''
        for item_name in self.body:
            if type(self.body[item_name]) == ft.Checkbox:
                self.body[item_name].value = False
            elif type(self.body[item_name]) == ft.TextField:
                self.body[item_name].value = ''
            elif type(self.body[item_name]) == ft.Dropdown:
                self.body[item_name].value = None
            else:
                print("1213121")
            self.update()


    def data_return_default(self):
        '''
        顯示欄位恢復預設值
        '''
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用
    

    def data_exist(self):
        '''
        回傳一個Measurement內是否全部為空值，用在opdformat的傳入篩選
        - textfield內容strip後若為空字串則為空值
        - checkbox內容若為False(空白框框)則為空值 => tristate的原因(True、None當作有輸入)
        '''
        exist = False
        for i, item in enumerate(self.item_list):
            # 特殊欄位跳過
            if item in self.ignore_exist_item_list:
                continue
            
            value = self.body[item].value
            control_type = type(self.body[item])

            if type(value) == str: # text型態空值
                if value.strip() != '':
                    exist = True
            elif control_type == ft.Checkbox:
                if (value != False): # 為了checkbox型態的tristate
                    exist = True
            elif control_type == ft.Dropdown:
                if (value != None): # FIXME 需要測試
                    exist = True
            else:
                logger.error(f"data_exist內部遇到未定義型態||type:{type(value)}||value:{value}")

        return exist


    def data_load_db(self, values_dict):
        '''
        將資料庫取得的values_dict(keys為資料庫形式:db_column_names)傳入顯示欄位
        tristate checkbox會被轉譯(self.tristate_db_to_data)
        '''
        # tristate資料需要轉化
        tristate_db_to_data ={
            True: True,
            False: None,
            None: False,
        }

        # 透過self.db_column_names方便程式碼閱讀但效率變差
        column_names = self.db_column_names()

        for i, item in enumerate(self.item_list):
            control_type = type(self.body[item])
            if control_type == ft.Checkbox and self.tristate == True: # tristate資料需要轉換
                self.body[item].value = tristate_db_to_data[values_dict[column_names[i]]] # 資料庫獲取資料會在此轉換型態
            else:
                self.body[item].value = values_dict[column_names[i]]
        self.update()
    

    def db_column_names(self) -> list:
        '''
        將label+item名稱轉成資料庫column_names
        '''
        column_names = []
        for item in self.item_list:
            if str(item).strip() == '': # 如果item是空字串
                key = f"{self.label}".replace(' ','_')
            else:
                key = f"{self.label}_{item}".replace(' ','_')  # 把空格處理掉 => 減少後續辨識錯誤
            column_names.append(key)
        return column_names


    def db_values_dict(self):  #將內部資料輸出: dict( {self.label}_{item_name} : value )
        '''
        將measurement內部值搭配column_names形成values_dict
        過程不會捨棄空值 => 統一到Form處理
        '''
        tristate_data_to_db ={
            True: True,
            None: False,
            False: None,
        }

        column_names = self.db_column_names()
        values = {}
        for i, item in enumerate(self.item_list):
            value = self.body[item].value
            control_type = type(self.body[item])

            if type(value) == str: # 為何不用self.control_type 是因為control如果有新增其他type control會有問題 要用更細的type(self.body[item])判斷
                value = value.strip() # 字串類型前後空格去除
            elif control_type == ft.Checkbox and self.tristate == True: # 處理tristate
                value = tristate_data_to_db[value] # 資料轉換
            elif control_type == ft.Checkbox and self.tristate == False: # 處理普通checkbox
                pass
            elif type(value) == None: # dropbox預設可能會是None
                pass 
            else:
                pass
            values[column_names[i]] = value
        return values


    def data_opdformat(self): 
        '''
        帶入門診病例的格式
        目前設計確認有無資料放在form內部，所以會傳入data_opdformat都是已有使用者輸入資料的
        '''
        # 客製化格式
        format_text = self.format_func(self)
        
        # 分類到指定的region('s','o','p')，format_text為list type
        return self.format_region, format_text


class Measurement_Text(Measurement):
    def __init__(self, label: str, item_list: list = None, multiline = False, format_region = 'o', format_func = format_text_tradition, default: dict = None):
        super().__init__(label, ft.TextField, item_list, format_region=format_region, format_func=format_func, default=default)
        self.multiline = multiline
        if item_list is None:
            self.item_list = ['OD', 'OS'] # 預設是雙眼的資料
        
    # specific to textbox
    def set_multiline(self):
        for item in self.body:
            self.body[item].multiline = True
            self.body[item].height = None
        # self.row.update() # 建立時就指定應該不用update


    def build(self): # flet元件要建立時會呼叫build()
        # self.head 在Measurement中定義
        
        # UI呈現載體
        self.row = ft.Row(
            # expand=True, 
            controls=[
                self.head,  
            ]
        )

        # 填充body元件 + 存入self.row
        style_textfield = dict(
            dense=True, 
            height=40*FONT_SIZE_FACTOR+5, 
            cursor_height=20*FONT_SIZE_FACTOR, 
            content_padding = 10*FONT_SIZE_FACTOR, 
            expand=True
        )

        for i, item_name in enumerate(self.item_list):
            if self.body.get(item_name, None) != None: # 表示body內已有此item => 例如提前置入的control(ex:iop)　或　經過第一次build後再次呼叫build時(每次元件建立時都會呼叫一次)
                self.row.controls.append(self.body[item_name]) # 直接加入 row # TODO是不是應該row有元素就不要重置
                continue
            if len(self.item_list) == 1:
                self.body[item_name] = ft.TextField(autofocus=True, **style_textfield)
            else:
                if i == 0:
                    self.body[item_name] = ft.TextField(label=item_name, autofocus=True, **style_textfield)
                else:
                    self.body[item_name] = ft.TextField(label=item_name, **style_textfield)
                    
            self.row.controls.append(self.body[item_name]) # 確保顯示的順序和建立時一致
        
        # set_multiline if True
        if self.multiline == True:
            self.set_multiline()

        # 使用預設值初始化
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]    
        
        # 設定head tooltip
        if self.default != None: 
            self.head.tooltip = "填入預設值"

        return self.row
    
         
class Measurement_Check(Measurement):
    def __init__(self, label: str, item_list: list, width_list: Union[List[int], int] = None, format_region = 'o', format_func = format_checkbox_tristate, default: dict = None, compact = False, tristate = False):
        if type(item_list) != list:
            raise Exception("Wrong input in Measurement_Check item_list")
        super().__init__(label, ft.Checkbox, item_list, format_region=format_region, format_func=format_func, default=default)
        self.compact = compact
        self.tristate = tristate
        # width setting
        if width_list == None: # 自動依據字串長度產生寬度
            tmp = []
            for item in item_list:
                tmp.append(int(60 + (len(item)-1) * 6))
            self.checkbox_width = tmp
        elif type(width_list) == list: # 指定寬度list
            if len(width_list) != len(item_list):
                raise Exception("Not match between width_list and item_list")
            self.checkbox_width = width_list
        elif type(width_list) == int: # 指定單一寬度
            self.checkbox_width = [width_list] * len(item_list)
        else:
            raise Exception("Something wrong with width_list")
        
    
    def build(self):
        # self.head 在Measurement中定義
        
        # UI呈現載體
        self.row = ft.Row(
            controls=[],
            spacing=1,
            run_spacing=1,
            wrap=True,
        )

        # 填充body元件 + 存入self.row
        for i, item_name in enumerate(self.item_list):
            if self.body.get(item_name, None) != None: # 表示body內已有此item => 例如提前置入的control(ex:iop)　或　經過第一次build後再次呼叫build時(每次元件建立時都會呼叫一次)
                self.row.controls.append(self.body[item_name]) # 直接加入 row
                continue
            self.body[item_name] = ft.Checkbox(
                label=item_name,
                value=False,
                width=self.checkbox_width[i],
                height=25, # height = 25 讓呈現更緊 
                tristate=self.tristate
            )

            self.row.controls.append(self.body[item_name]) # 確保顯示的順序和建立時一致

        # 使用預設值初始化
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]

        # 設定head tooltip
        if self.tristate == True:
            self.head.tooltip = "全是/全否/全取消"
        else:
            self.head.tooltip = "全選/全取消"

        # 決定輸出緊密程度
        if self.compact:
            return ft.Row(controls=[self.head, self.row], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            return ft.Column(controls=[self.head, self.row]) # 讓head換行後接著checkboxes
    

class Measurement_Dropdown(Measurement):
    def __init__(self, label: str, item_dict: dict, format_func = format_text_parentheses, format_region = 'o', default = None):
        self.item_dict = item_dict # 包含item_list和選項內容
        item_list = list(item_dict.keys()) # 擷取其中的keys作為item list
        super().__init__(label, ft.Dropdown, item_list, format_region=format_region, format_func=format_func, default=default)

    def build(self):
        
        # UI呈現的載體
        self.row = ft.Row( 
            controls=[
                self.head,  
            ],
        )

        # 填充body元件 + 存入self.row
        for item_name in self.item_list:
            if self.body.get(item_name, None) != None: # 表示body內已有此item => 例如提前置入的control(ex:iop)　或　經過第一次build後再次呼叫build時(每次元件建立時都會呼叫一次)
                self.row.controls.append(self.body[item_name]) # 直接加入 row
                continue
            
            max_length = 0
            option_list = []
            for option_value in self.item_dict[item_name]:
                option_list.append(ft.dropdown.Option(option_value))
                max_length = max(max_length, len(option_value))
            
            self.body[item_name] = ft.Dropdown(
                label=item_name,
                options=option_list,
                # width=max_length*8+40,
                dense=True,
                height=40*FONT_SIZE_FACTOR+5,
                content_padding=6,
                text_size=15,
                expand=True
            )

            self.row.controls.append(self.body[item_name])
        
        return self.row
        

class Form(ft.Tab): 
    '''
    擴增Tab的功能
    '''
    def __init__(self, label, control_list: List[Measurement]):
        '''
        control_list: 表單內所有control(呈現單元+資料單元)
        measurement_list: 表單內資料單元
        '''
        super().__init__()
        self.label = label # 資料儲存label
        self.control_list = control_list # contorl list: 內涵單純呈現的項目+資料儲存(measurement)
        self.measurement_list = self.set_measurement_list(control_list=control_list) # 資料儲存(measurement)欄位
        
        self.display = ft.Container(
            content= ft.Text(value='已擷取......資料', color=ft.colors.WHITE, weight=ft.FontWeight.BOLD, visible=False),
            alignment=ft.alignment.center,
            bgcolor = ft.colors.BLUE,
            margin= ft.margin.only(top=5, bottom=0),
            visible= True,
        )

        # 呈現單元: text, content為flet.Tab下固有屬性
        self.text = self.label # tab標籤名 
        self.content = ft.Column( # tab內容
            controls=[
                self.display, 
                ft.Container( # 呈現用途
                    content=ft.Column(
                        controls=self.control_list,
                        scroll="adaptive",
                    ),
                    # alignment=ft.alignment.center,
                    expand=True,
                    padding=ft.padding.only(top=0, bottom=15),
                )
            ]
        )

    def set_measurement_list(self, control_list):
        '''
        將control_list排除呈現單元剩下資料單元
        '''
        measurement_list = []
        for control in control_list:
            if isinstance(control, Measurement):
                measurement_list.append(control)
            elif isinstance(control, (ft.Row, ft.Column)): # 如果是Row或Column打包的資料項 => 要往下去找 #FIXME 目前先限制只能一層Row/Column
                measurement_list.extend(control.controls)
        return measurement_list        


    def set_display(self, text=None):
        '''
        顯示form內的顯示欄位，若沒text就隱藏display
        '''
        if text == None: 
            self.display.content.visible = False
        else:
            self.display.content.value = text
            self.display.content.visible = True
        self.display.update()


    def set_doctor_id(self, doctor_id):
        self.doctor_id = doctor_id


    # def measurements(self, item_name: str): # 沒用
    #     for measurement in self.measurement_list:
    #         if measurement.label == item_name:
    #             return measurement
    #     return None


    def data_load_db(self, values_dict):
        '''
        將資料庫資料讀取後設定到顯示欄位
        '''
        for measurement in self.measurement_list:
            measurement.data_load_db(values_dict)


    def data_clear(self):
        for measurement in self.measurement_list:
            measurement.data_clear()
        self.set_display() # 清除display


    def data_return_default(self):
        for measurement in self.measurement_list:
            measurement.data_return_default()


    def data_exist(self):
        for measurement in self.measurement_list:
            if measurement.data_exist():
                return True
        return False


    def data_opdformat(self):
        '''
        form階層的格式化輸出，主要添加換行和時間模式，並排除沒有資料的欄位
        '''
        format_dict = {
            's':[],
            'o':[],
            'p':[]
        }
        for measurement in self.measurement_list:
            if measurement.data_exist(): # 確認有無資料決定是否納入
                region, text = measurement.data_opdformat()
                format_dict[region].append(text)

        format_form = {}
        for region in format_dict:
            if len(format_dict[region]) !=0:
                format_form[region] = format_merge(format_dict[region], form_name = self.label)

        # testing
        if TEST_MODE:
            print(f"format_form: {format_form}")

        return format_form

    
    def db_column_names(self):
        '''
        集合所有的measurement column_names(經過轉換適合db使用)，不論有無空值
        '''
        column_names = []
        for measurement in self.measurement_list:
            column_names.extend(measurement.db_column_names())
        return column_names


    def db_values_dict(self):
        '''
        集合所有的measurement values_dict 
        - 若有同名後者會覆寫前者
        '''
        values = {}
        for measurement in self.measurement_list:
            values.update(measurement.db_values_dict())
        return values


    def db_values_exist(self, values_dict): 
        '''
        判斷是不是全空值
        當成空值條件:
        - textfield: ''是空值
        - checkbox: 轉換後的None是空值(True、False會被留下)
        '''
        # ignore_list_final = []
        for measurement in self.measurement_list:
            for item in measurement.item_list:
                if item not in measurement.ignore_exist_item_list:
                    # 先取得資料庫的column_names對應
                    if str(item).strip() == '': # 如果item是空字串
                        db_key = f"{measurement.label}".replace(' ','_')
                    else:
                        db_key = f"{measurement.label}_{item}".replace(' ','_')  # 把空格處理掉 => 減少後續辨識錯誤
                    # 判斷是否為空值
                    if type(values_dict[db_key])==str:
                        if values_dict[db_key]!='':
                            return True
                    elif (values_dict[db_key]==True) or (values_dict[db_key]==False):
                        return True
        return False


    def db_migrate(self) -> bool: 
        '''
        偵測目前有沒有這個table沒有就建立，如果有column差異就新增?
        #### 需要注意引號與大小寫table name and column name => 目前設計是case sensitive
        # TODO 目前未考慮型態變更
        '''
        
        # 偵測table
        detect_query = f'''SELECT EXISTS (
            SELECT FROM pg_tables
            WHERE tablename  = '{self.label}')'''
        try:
            cursor.execute(detect_query)
            exists = cursor.fetchone()['exists']
        except Exception as error:
            db_conn.rollback()
            logger.error(f"{inspect.stack()[0][3]}||Table[{self.label}] Error in detect table existence: {error}")
            return False

        if exists == False: #Table不存在
            logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] NOT exists! Building...")
            # 組合需要的欄位
            other_columns = ''
            for measurement in self.measurement_list:
                for i, column_name in enumerate(measurement.db_column_names()): # 因為db_column_names()序列和item_list順序一樣 => 可以直接用index檢視
                    print(i, column_name)
                    if type(measurement.body[measurement.item_list[i]]) == ft.Checkbox: # 因為元件可以新增control，所以採用細節元件的type 非measurement.control_type
                        other_columns = other_columns + f' "{column_name}" boolean,'
                    else: # measurement.control_type == ft.TextField or measurement.control_type == ft.Dropdown: 
                        other_columns = other_columns + f' "{column_name}" text,'
            
            # 創建table
            query = f'''CREATE TABLE IF NOT EXISTS "{self.label}" (
                "{COLUMN_ID}" serial PRIMARY KEY,
                "{COLUMN_TIME_CREATED}" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                "{COLUMN_TIME_UPDATED}" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                "{COLUMN_DOC}" varchar(8),
                "{COLUMN_PATIENT_HISNO}" varchar(15) NOT NULL,
                "{COLUMN_PATIENT_NAME}" varchar(20),
                "{COLUMN_PATIENT_BIRTHDAY}" varchar(20),
                "{COLUMN_PATIENT_AGE}" varchar(8),
                {other_columns.rstrip(',')})'''
            try:
                cursor.execute(query)
                db_conn.commit()
            except Exception as error:
                logger.error(f"{inspect.stack()[0][3]}||Table[{self.label}] Error in transaction(CREATE TABLE) and rollback: {error}")
                db_conn.rollback()
                return False
        
        else: #Table已存在
            logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] Exists!")
            # 只需要取得一筆就能透過cursor.description取得column names
            query = f''' SELECT * FROM "{self.label}" LIMIT 1 ''' 
            cursor.execute(query)
            # 舊column_names集合
            old_column_names = set()
            for c in cursor.description:
                old_column_names.add(c.name)
            # 新column_names集合
            new_column_names = set(self.db_column_names())
            diff = new_column_names - old_column_names
            if len(diff) ==0:
                logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] NO NEED FOR ADDING COLUMN!")
            else:
                logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] ADDING COLUMN[{len(diff)}]:{diff}")
                # 將集合差值的column names搭配data type形成query => "{column_name}"使用雙引號: case-sensitive 
                add_columns = ''
                for measurement in self.measurement_list:
                    for i, column_name in enumerate(measurement.db_column_names()):
                        if column_name in diff:
                            if type(measurement.body[measurement.item_list[i]]) == ft.Checkbox:
                                add_columns = add_columns + f' ADD COLUMN "{column_name}" boolean,'
                            else: # measurement.control_type == ft.TextField or measurement.control_type == ft.Dropdown:
                                add_columns = add_columns + f' ADD COLUMN "{column_name}" text,'
                            
                # 新增Column欄位
                query = f''' ALTER TABLE "{self.label}" {add_columns.rstrip(',')}'''
                try:
                    cursor.execute(query)
                    db_conn.commit()
                except Exception as error:
                    logger.error(f"{inspect.stack()[0][3]}||Table[{self.label}] Error in transaction(ALTER TABLE) and rollback: {error}")
                    db_conn.rollback()
                    return False
        # TODO 型態如果有變化要更改
        return True
        

    def db_save(self, patient_data:PatientData):
        values_dict = self.db_values_dict()

        if (patient_data.db_row_id.get(self.label, None) == None) and (self.db_values_exist(values_dict) == False): 
        # 如果沒有資料輸入(空白text or unchecked checkbox or 需要被ignore的欄位)就不送資料庫
        # 前提是insertion，如果是需要update，要考慮空值洗掉資料的需求
            return None

        # 加入病人醫師基本資訊
        values_dict.update(
            {
                COLUMN_DOC: self.doctor_id,
                COLUMN_PATIENT_HISNO: patient_data.hisno,
                COLUMN_PATIENT_NAME: patient_data.name,
                COLUMN_PATIENT_BIRTHDAY: patient_data.birthday,
                COLUMN_PATIENT_AGE: patient_data.age
            }
        )

        # psycopg parameterized SQL 因為防範SQL injection不支持欄位名稱有'%','(',')' => 改用自製query
        
        # 自製query
        if patient_data.db_row_id.get(self.label, None) == None:
            fields = ""
            values = ""
            for column in values_dict:
                # if (values_dict[column] != None) and (values_dict[column] != ''): ### values_dict在db_values_exist應該檢查過是否有值，未來可移除None
                fields = fields + f'"{column}", '
                if type(values_dict[column]) == str:
                    values = values + f"'{values_dict[column]}', "
                elif values_dict[column] == None:
                    values = values + f"NULL, "
                else:
                    values = values + f"{values_dict[column]}, "
            query = f'''INSERT INTO "{self.label}" ({fields.rstrip(', ')}) VALUES ({values.rstrip(', ')}) RETURNING {COLUMN_ID};'''
        else:
            query_parameters = ''
            for column in values_dict:
                if type(values_dict[column]) == str:
                    query_parameters = query_parameters + f'''"{column}"='{values_dict[column]}', '''
                elif values_dict[column] == None:
                    query_parameters = query_parameters + f'''"{column}"=NULL, '''
                else:
                    query_parameters = query_parameters + f'''"{column}"={values_dict[column]}, '''
            
            query_parameters = query_parameters + f'''"{COLUMN_TIME_UPDATED}"=NOW() '''
            query = f'''UPDATE "{self.label}" SET {query_parameters} WHERE "{COLUMN_ID}"={patient_data.db_row_id.get(self.label, None)};'''

        try:
            # cursor.execute(query, values_dict) #因為前面定義過有標籤的placeholder，可以傳入dictionary => 不能使用因為自製query
            if patient_data.db_row_id.get(self.label, None) == None:
                t1 = time.perf_counter()
                cursor.execute(query)
                res = cursor.fetchone()
                patient_data.db_row_id[self.label] = res[COLUMN_ID] # 存入後取得該row_id可以繼續update
                db_conn.commit()
                t2 = time.perf_counter()
                logger.debug(f'{inspect.stack()[0][3]}||Form[{self.label}]||Patient[{patient_data.hisno}]||Finish INSERT in {(t2-t1)*1000}ms')
            else:
                t1 = time.perf_counter()
                cursor.execute(query)
                db_conn.commit()
                t2 = time.perf_counter()
                logger.debug(f'{inspect.stack()[0][3]}||Form[{self.label}]||Patient[{patient_data.hisno}]||Finish UPDATE in {(t2-t1)*1000}ms')

            return True
        except Exception as e:
            logger.error(f"{inspect.stack()[0][3]}||Form[{self.label}]||Patient[{patient_data.hisno}]||Encounter exception: {e}")
            db_conn.rollback()
            return False

    
    def db_load(self, patient_data:PatientData):
        # 抓取符合醫師+病人的最新一筆資料
        query = SQL("SELECT * FROM {table} WHERE {doc}={doctor_id} AND {hisno}={patient_hisno} ORDER BY id DESC NULLS LAST LIMIT 1").format(
            table = Identifier(self.label),
            doc = Identifier(COLUMN_DOC),
            doctor_id = Literal(self.doctor_id),
            hisno = Identifier(COLUMN_PATIENT_HISNO),
            patient_hisno = Literal(patient_data.hisno),
        )

        try:
            t1 = time.perf_counter()
            cursor.execute(query)
            row = cursor.fetchone()
            t2 = time.perf_counter()
            logger.debug(f'{inspect.stack()[0][3]}||Form[{self.label}]||Patient[{patient_data.hisno}]||Loading query finished in {(t2-t1)*1000}ms')
            if row is None: # 沒有資料就回傳None
                self.set_display(text="無資料可擷取")
                return None
            row = dict(row)
            self.data_load_db(row) # 設定measurement資料
            self.set_display(text=f"已擷取資料日期:{row[COLUMN_TIME_UPDATED].strftime('%Y-%m-%d %H:%M')}") # 顯示display:資料擷取日期
            
            if row[COLUMN_TIME_CREATED] >= (datetime.datetime.today() - INTERVAL_FOR_NEW_DB_ROW).astimezone(tz=None): # 在指定時效內此row可以作為update用途
                patient_data.db_row_id[self.label] = row[COLUMN_ID] # 存下 row_id in order to update that row

            # 只留下目前表單會有的欄位
            db_columns = self.db_column_names()
            tmp_dict = {key: row[key] for key in db_columns}
            patient_data.db_loaded_dict[self.label] = tmp_dict # 將資料庫讀取出來的資料去掉和使用者輸入無關資料，方便後續做比較

            return True
        except Exception as e:
            logger.error(f"{inspect.stack()[0][3]}||Form[{self.label}]||Patient[{patient_data.hisno}]||Encounter exception: {e}")
            return False


class Forms(): #集合Form(Tab)，包裝存、取、清除功能
    def __init__(self, form_list: Tuple[Form]) -> None:
        self.form_list_original = form_list # 儲存所有forms(不應變動)
        self.form_list_selected = list(form_list) # 會因為選擇fomrs而變動
        self.doctor_id = None
    

    def set_form_list_selected(self, form_names: List[str]):
        tmp_list = []
        for form in self.form_list_original:
            if form.label in form_names:
                tmp_list.append(form)
        self.form_list_selected = tmp_list


    # def data_set_value(self, values_dict):
    #     pass

    # def data_return_default(self, e=None):
    #     pass


    def db_values_dict(self, tab_index = None):
        '''
        取得目前各表單的資料dict，可幫助比較是否有資料異動
        '''
        return_dict = {}
        if tab_index == None: # 判斷全部forms
            for form in self.form_list_selected:
                return_dict[form.label] = form.db_values_dict()
        else:
            return_dict[self.form_list_selected[tab_index].label] = self.form_list_selected[tab_index].db_values_dict()
        return return_dict


    def set_doctor_id(self, doctor_id):
        self.doctor_id = doctor_id
        for form in self.form_list_selected:
            form.set_doctor_id(doctor_id=doctor_id)


    def data_opdformat_one(self): # 單一form格式化輸出
        pass

    def data_opdformat(self): # 全部forms格式化輸出
        format_final = {
            's':'',
            'o':'',
            'p':''
        }
        for form in self.form_list_selected:
            format_form = form.data_opdformat() # This is dict
            for region in format_form:
                format_final[region] = format_final[region] + format_form[region]

        return format_final


    def data_clear(self, tab_index = None): # 全部/單一form清除
        if tab_index == None: # 全部
            for form in self.form_list_selected:
                form.data_clear()
        else:
            self.form_list_selected[tab_index].data_clear()


    def data_exist(self, tab_index = None):
        if tab_index == None: # 判斷全部forms
            for form in self.form_list_selected:
                if form.data_exist():
                    return True
            return False
        else:
            return self.form_list_selected[tab_index].data_exist()


    def db_migrate(self): # 全部forms migrate
        res_string = ''
        for form in self.form_list_original:
            res = form.db_migrate()
            res_string = res_string + f"{form.label}:{res}\n"
        return res_string

    # 按下存檔按鈕時會抓取病人資料
    def db_save(self, patient_data:PatientData, tab_index = None): # 儲存form:整合儲存單一與全部
        error_list = []
        empty_list = []
        if tab_index == None: # 全部
            for form in self.form_list_selected:
                res = form.db_save(patient_data)
                if res == None:
                    logger.info(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_data.hisno}||Skip saving")
                    empty_list.append(form.label)
                    form.data_clear() # 存完清除
                elif res == False:
                    logger.error(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_data.hisno}||Fail saving")
                    error_list.append(form.label)
                else:
                    logger.debug(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_data.hisno}||Finish saving")
                    form.data_clear() # 存完清除
        else: # 單一
            res = self.form_list_selected[tab_index].db_save(patient_data)
            if res == None:
                logger.info(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_data.hisno}||Skip saving")
                empty_list.append(form.label)
                self.form_list_selected[tab_index].data_clear() # 存完清除
            elif res == False:
                logger.error(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_data.hisno}||Fail saving")
                error_list.append(self.form_list_selected[tab_index].label)
            else:
                logger.debug(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_data.hisno}||Finish saving")
                self.form_list_selected[tab_index].data_clear() # 存完清除
        
        return error_list, empty_list # 回傳給GUI做notify


    def db_load(self, patient_data:PatientData, tab_index = None): # 讀取form:整合讀取單一與全部
        error_list = []
        empty_list = []
        if tab_index == None: # 全部
            for form in self.form_list_selected:
                res = form.db_load(patient_data)
                if res == None:
                    logger.info(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_data.hisno}||Empty record")
                    empty_list.append(form.label) 
                elif res == False:
                    logger.error(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_data.hisno}||Fail loading")
                    error_list.append(form.label)
                else:
                    logger.debug(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_data.hisno}||Finish loading")
        else: # 單一
            res = self.form_list_selected[tab_index].db_load(patient_data)
            if res == None:
                logger.info(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_data.hisno}||Empty record")
                empty_list.append(form.label) 
            elif res == False:
                logger.error(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_data.hisno}||Fail loading")
                error_list.append(self.form_list_selected[tab_index].label)
            else:
                logger.debug(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_data.hisno}||Finish loading")
            
        return error_list, empty_list # 回傳給GUI做notify


    # def db_load_all(self, patient_hisno, *args, **kwargs): # 全部forms 讀取 => 暫時不用
    #     for form in self.form_list_selected:
    #         res = form.db_load(patient_hisno, *args, **kwargs)
    #         if res == None:
    #             logger.info(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Empty record")
    #         elif res == False:
    #             logger.error(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Fail loading")
    #         else:
    #             logger.debug(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Finish loading")


########################## Basic
# 客製化IOP按鈕
iop = Measurement_Text('IOP', format_func=format_iop)
iop.add_control(
    item_name='mode',
    control=ft.Dropdown(
        width=100,
        height=29,
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
    ),
    ignore_exist=True
)

form_basic = Form(
    label="Basic",
    control_list=[
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        Measurement_Text('K(OD)', ['H','V'], format_func=format_text_parentheses),
        Measurement_Text('K(OS)', ['H','V'], format_func=format_text_parentheses),
        Measurement_Text('CCT', format_func=format_text_slash_um),
        iop,
        Measurement_Text('Cornea', multiline=True),
        Measurement_Text('AC'),
        Measurement_Text('Lens'),
        Measurement_Text('Fundus', multiline=True),
        Measurement_Text('CDR'),
        Measurement_Text('M_OCT'),
        Measurement_Text('G_OCT', ['RNFL_OD','RNFL_OS','GCIPL_OD', 'GCIPL_OS'], format_func=format_goct),
        Measurement_Text('others', multiline=True),
        Measurement_Text('Impression', format_region='p', multiline=True),
    ]
)

########################## Plasty
form_plasty = Form(
    label = "Plasty",
    control_list = [
        Measurement_Text('MRD'),
        Measurement_Text('LF'),
        Measurement_Text('Exo', ['OD', 'PD', 'OS'], format_func=format_exo),
        Measurement_Text('EOM'),
        Measurement_Check(
            label = 'CAS', 
            item_list = ['Retrobulbar pain', 'Motion pain', 'Redness eyelid', 'Redness conjunctiva', 'Swelling caruncle', 'Swelling eyelids', 'Swelling conjunctiva'], 
        ),
        Measurement_Check(
            label = 'Muscle Involvement',
            item_list = ['SR', 'MR', 'IR', 'LR', 'SO', 'IO', 'LE']
        )
    ],
)

########################## DED
form_dryeye = Form(
    label="DryEye",
    control_list=[
        Measurement_Check('Symptom', ['dry eye', 'dry mouth', 'pain','photophobia','tearing','discharge'], compact=True, format_region='s', tristate=True),
        Measurement_Text('Other Symptoms', '', format_region='s', multiline=True),
        Measurement_Check('Affected QoL', ['driving', 'reading', 'work', 'outdoor', 'depressed'], tristate=True),
        Measurement_Text('3C_hrs', ''),
        Measurement_Text('SPEED', ''),
        Measurement_Text('OSDI', ''),
        Measurement_Text('History', '', format_region='s', multiline=True),
        Measurement_Check('PHx', ['DM', 'Hyperlipidemia', 'Sjogren','GVHD', 'AlloPBSCT', 'Seborrheic','Smoking', 'CATA', 'Refractive', 'IPL', 'Cosmetics'], compact=True, format_region='s', tristate=True),
        Measurement_Text('Schirmer 1 test', format_func=format_text_slash_mm),
        Measurement_Text('TBUT', format_func=format_text_slash),
        Measurement_Text('NEI'),
        Measurement_Check('Conjunctivochalasis', ['OD','OS'], compact=True),
        Measurement_Check('MCJ_displacement', ['OD','OS'], compact=True),
        Measurement_Text('Telangiectasia'),
        Measurement_Check('MG plugging', ['OD','OS'], compact=True),
        Measurement_Text('Meibum', multiline=True),
        Measurement_Text('Mei_EXP'),
        Measurement_Text('LLT', format_func=format_text_slash),
        Measurement_Text('Blinking'),
        Measurement_Text('MG atrophy(OD)',['upper','lower'], format_func=format_text_parentheses),
        Measurement_Text('MG atrophy(OS)',['upper','lower'], format_func=format_text_parentheses),
        Measurement_Text('Lipiview', multiline=True),
        Measurement_Check('Lab abnormal', ['SSA/B', 'ANA', 'RF', 'dsDNA', 'ESR'], compact=True, tristate=True),
        Measurement_Text('Impression','', format_func=format_no_output, format_region='p'),
        Measurement_Check('Treatment', ['NPAT', 'Restasis', 'Autoserum', 'Diquas', 'IPL', 'Punctal plug'], compact=True),
    ]
)

form_ipl = Form(
    label="IPL",
    control_list=[
        Measurement_Text('IPL NO', '', format_region='p'),
        Measurement_Check('Post-IPL', [''], compact=True),
        Measurement_Text('Massage(OD)', ['upper','lower'], format_region='p'),
        Measurement_Text('Massage(OS)', ['upper','lower'], format_region='p'),
        Measurement_Check('Improved Symptoms', ['dry eye', 'dry mouth', 'pain','photophobia','tearing','discharge'], compact=True, tristate=True),
        Measurement_Text('Other Symptoms', '', multiline=True),
        Measurement_Check('Improved QoL', ['driving', 'reading', 'work', 'outdoor', 'depressed'], tristate=True),
        Measurement_Text('SPEED', ''),
        Measurement_Text('OSDI', ''),
        Measurement_Text('Schirmer 1', format_func=format_text_slash_mm),
        Measurement_Text('TBUT', format_func=format_text_slash),
        Measurement_Text('NEI'),
        Measurement_Check('MCJ_displacement', ['OD','OS'], compact=True),
        Measurement_Text('Telangiectasia'),
        Measurement_Check('MG plugging', ['OD','OS'], compact=True),
        Measurement_Text('Meibum', multiline=True),
        Measurement_Text('Mei_EXP'),
    ]
)

########################## IVI
iop = Measurement_Text('IOP', format_func=format_iop)
iop.add_control(
    item_name='mode',
    control=ft.Dropdown(
        width=100,
        height=29,
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
    ),
    ignore_exist=True
)

form_ivi = Form(
    label="IVI",
    control_list=[
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        Measurement_Text('K', ['OD','OS'], format_func=format_text_parentheses),
        iop,
        Measurement_Text('Lens'),
        Measurement_Text('CMT'),
        Measurement_Text('Fundus+OCT',[''], multiline=True),
        Measurement_Check('IRF', ['OD','OS'], compact=True),
        Measurement_Check('SRF', ['OD','OS'], compact=True),
        Measurement_Check('PED', ['OD','OS'], compact=True),
        Measurement_Check('SHRM', ['OD','OS'], compact=True),
        Measurement_Check('Atrophy', ['OD','OS'], compact=True),
        Measurement_Check('Gliosis', ['OD','OS'], compact=True),
        Measurement_Check('Schisis', ['OD','OS'], compact=True),
        Measurement_Check('New hemorrhage', ['OD','OS'], compact=True),
        ft.Divider(height=0, thickness=3),
        Measurement_Check('Impression_OD', ['AMD','PCV', 'RAP', 'mCNV', 'CRVO', 'BRVO', 'DME', 'VH', 'CME', 'PDR', 'NVG', 'IGS', 'CSCR'], compact=True),
        Measurement_Check('Treatment_OD', ['Eylea','Lucentis', 'Avastin', 'Ozurdex', 'Beovu', 'Faricimab', 'Gas'], compact=True),
        ft.Divider(height=0, thickness=3),
        Measurement_Check('Impression_OS', ['AMD','PCV', 'RAP', 'mCNV', 'CRVO', 'BRVO', 'DME', 'VH', 'CME', 'PDR', 'NVG', 'IGS', 'CSCR'], compact=True),
        Measurement_Check('Treatment_OS', ['Eylea','Lucentis', 'Avastin', 'Ozurdex', 'Beovu', 'Faricimab', 'Gas'], compact=True),
        Measurement_Text('Other Impression', multiline=True),
    ]
)

form_uveitis = Form(
    label="Uveitis",
    control_list=[
        Measurement_Text('Symptoms',[''], format_region='s', multiline=True),
        
        Measurement_Text('History', [''], format_region='s', multiline=True),
        ft.Divider(height=0, thickness=3),
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        Measurement_Text('IOP', format_func=format_iop),
        Measurement_Dropdown('KP_SIZE', {
            'OD':['fine','small','medium','large'],
            'OS':['fine','small','medium','large'],
        }),
        Measurement_Text('KP_NUM'),
        Measurement_Dropdown('AC cells', {
            'OD':['0','0.5+','1+','2+','3+','4+'],
            'OS':['0','0.5+','1+','2+','3+','4+'],
        }),
        Measurement_Dropdown('AC flare', {
            'OD':['0','0.5+','1+','2+','3+','4+'],
            'OS':['0','0.5+','1+','2+','3+','4+'],
        }),
        Measurement_Check('Anterior segment(OD)', ['hypopyon','PAS', 'PS'], compact=True),
        Measurement_Check('Anterior segment(OS)', ['hypopyon','PAS', 'PS'], compact=True),
        Measurement_Check('Iris(OD)', ['atrophy(diffuse)','atrophy(sector)', 'nodule(margin)', 'nodule(stroma)'], compact=True),
        Measurement_Check('Iris(OS)', ['atrophy(diffuse)','atrophy(sector)', 'nodule(margin)', 'nodule(stroma)'], compact=True),
        ft.Divider(height=0, thickness=3),
        Measurement_Dropdown('Vitreous cells', {
            'OD':['0','0.5+','1+','2+','3+','4+'],
            'OS':['0','0.5+','1+','2+','3+','4+'],
        }),
        Measurement_Dropdown('Vitreous haze', {
            'OD':['0','1','2','3','4'],
            'OS':['0','1','2','3','4'],
        }),
        Measurement_Dropdown('Scleritis', {
            'OD':['anterior', 'posterior', 'diffuse', 'nodular', 'necrotizing'],
            'OS':['anterior', 'posterior', 'diffuse', 'nodular', 'necrotizing'],
        }),
        ft.Divider(height=0, thickness=3),
        Measurement_Check('Ind(OD)', ['Snow bank','Snow ball', 'vasculitis', 'retinitis', 'chorioretinitis', 'hemorrhage'], compact=True),
        Measurement_Check('Ind(OS)', ['Snow bank','Snow ball', 'vasculitis', 'retinitis', 'chorioretinitis', 'hemorrhage'], compact=True),
        Measurement_Text('CMT'),
        Measurement_Text('Ind/OCT', [''], multiline=True),
        Measurement_Text('FAG/ICG', [''], multiline=True),
        ft.Divider(height=0, thickness=3),
        Measurement_Dropdown('Diagnosis', {
            'Laterality':['Unilateral','Bilateral','Alt. unilateral'],
            'Location':['Anterior','Posterior','Intermediate','Pan'],
            'Granulomatous':['G.', 'Non-G']
        }, format_region='p'),
        Measurement_Check('Diagnosis with', ['Glaucoma','Retinal vasculitis'], format_region='p', compact=True),
        Measurement_Text('Note', [''], format_region='p', multiline=True),
        Measurement_Text('Follow period', [''], format_region='p', multiline=True),

    ]
)


# FIXME   '''Testing'''
def plot_IVI(e=None):
    import plotly.graph_objects as go

    # Manually input the data as Python lists
    dates = ['2020-11-25', '2020-12-09', '2020-12-25', '2021-02-23', '2021-05-26', '2021-11-25']
    va_od = [0.05,0.05,0.2,0.5,0.7,0.8]
    va_os = [1.0,0.9,1.0,0.8,0.9,0.8]
    cmt_od = [642,730,650,462,370,361]
    cmt_os = [280, 267,270,265,262, 265]

    # Create a line plot with two y-axes
    fig = go.Figure()

    # Add the line plot for measurementA
    fig.add_trace(
        go.Line(
            x=dates, 
            y=va_od, 
            name='VA_OD', 
            # line=dict(color='blue')
        )
    )

    fig.add_trace(
        go.Line(
            x=dates, 
            y=va_os, 
            name='VA_OS', 
            # line=dict(color='blue')
        )
    )

    # Add the line plot for measurementB
    fig.add_trace(
        go.Line(
            x=dates,
            y=cmt_od,
            name='CMT_OD',
            # line=dict(color='red'),
            yaxis='y2'
        )
    )

    # Add the line plot for measurementB
    fig.add_trace(
        go.Line(
            x=dates,
            y=cmt_os,
            name='CMT_OS',
            # line=dict(color='red'),
            yaxis='y2'
        )
    )

    # Set the title and axis labels
    fig.update_layout(
        # title='Measurement A and B over Time',
        xaxis=dict(
            title='Date',
            tickmode='linear',
            dtick='M1',  # Adjust the spacing between ticks here (M1 indicates monthly spacing)
            tickformat='%Y-%m-%d'),  # Custom tick label format (abbreviated month and year)
        yaxis=dict(title='VA', color='blue'),
        yaxis2=dict(title='CMT', color='red', overlaying='y', side='right'),
        hovermode='x unified',
        xaxis_hoverformat='%Y-%m-%d',
    )

    fig.update_xaxes(showspikes=True, showline=False, spikedash='dash', showticklabels = True)


    # Add vertical lines and annotations
    vertical_lines = ['2020-11-25', '2021-01-02']
    annotations = ['IVIO OD', 'IVIE OD']

    for i in range(len(vertical_lines)):
        fig.add_shape(
            type='line',
            x0=vertical_lines[i],
            x1=vertical_lines[i],
            y0=0,
            y1=1,
            xref='x',
            yref='paper',
            line=dict(color='black', dash='dash'),
            name=f'Event {i+1}',
            # hovertemplate=f'<b>Event {i+1}</b><br>Date: {vertical_lines[i]}'
        )
        fig.add_trace(go.Scatter(x=[vertical_lines[i], vertical_lines[i]], y=[0, 1], mode='lines',
                                line=dict(color='black', dash='dash'),
                                name=annotations[i],
                                hovertemplate=f'Date: {vertical_lines[i]}',showlegend=False))

        fig.add_annotation(x=vertical_lines[i], y=1.1, xref='x', yref='paper',
                        text=annotations[i], showarrow=False)

    # Show the plot
    fig.show()
    

# FIXME 
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
            bgcolor=ft.colors.RED,
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
                    border=ft.InputBorder.UNDERLINE,
                    filled=True,
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
                    expand=True,
                    border=ft.InputBorder.UNDERLINE,
                    filled=True,
                )
            
            self.body.append(text)

        self.body.append(button_remove)
        
        return ft.Row(controls=self.body)

# FIXME 
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
                "id": 2,
                'hisno': '0000',
                "日期": "20210102",
                "處置": "IVIE",
                "側別": "OD",
                "Note": "less SRF"
            },
            {
                "id": 1,
                'hisno': '0000',
                "日期": "20201125",
                "處置": "IVIO",
                "側別": "OD",
                "Note": ""
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
    #     self.body_rows.insert(
    #         0,
    #         Data_row(
    #             self.column_names,
    #             {
    #                 # TODO 只尋找self.body_input內除了button的元件 => 考慮新增self.body_input的body
    #             }
    #         )
    #     )
    #     # 清除輸入框
    #     pass

    # def datatable_remove(self, e=None): 
    #     pass


def date_on_focus(e=None):
    e.control.value = ''
    e.control.update()


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


form_test = Form(
    label="IVI_treatment",
    control_list=[
        ft.ElevatedButton("IVI歷程圖", on_click=plot_IVI),
        # Measurement_Text('VA'),
        # Measurement_Text('REF'),
        d
    ]
)

# FIXME   '''Testing'''

########################## MERGE
db_conn = None
cursor = None

form_list_tuples = (form_dryeye, form_ipl, form_basic, form_plasty, form_uveitis, form_ivi) # 不應該被變更的所有form_list
forms = Forms(form_list_tuples) # 初始化註冊所有forms

if __name__ == '__main__': # load這個library來建立DB
    db_connect()
    forms.db_migrate()
