import flet as ft
import datetime
from typing import Union, List, Tuple
import psycopg2
from psycopg2.sql import SQL, Identifier, Placeholder, Literal
from psycopg2.extras import RealDictCursor
import logging
import inspect
import os
import time

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
    for item_name in measurement.body:
        if item_name == 'OD' or item_name == 'OS':
            if measurement.body[item_name].value.strip() != '':
                format_text = format_text + f"{measurement.body[item_name].value} {item_name}, "
        else:
            if measurement.body[item_name].value.strip() != '':
                other_format_text = other_format_text + f"{measurement.body[item_name].value} {item_name}, "
    format_text = format_text + other_format_text
    
    format_text = f"{measurement.label}:" + format_text.rstrip(', ')
    return format_text


def format_text_2score(measurement):
    '''
    Ex: TBUT: 5/5
    '''
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/')
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


def format_checkbox(measurement):
    '''
    Ex: IRF:OD,OS
    '''
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value == True:
            format_text = format_text + f"{item_name},"

    format_text = f"{measurement.label}:" + format_text.rstrip(',')
    return format_text


def format_checkbox_tristate(measurement):
    '''
    Ex: History:DM(+),CHF(-)
    '''
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value == True:
            format_text = format_text + f"{item_name}(+),"
        elif measurement.body[item_name].value == None:
            format_text = format_text + f"{item_name}(-),"
        else:
            pass

    format_text = f"{measurement.label}:" + format_text.rstrip(',')
    return format_text


def format_shirmer1(measurement):
    '''
    Ex: Shirmer 1:5/5mm
    '''
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/') + 'mm'
    return format_text


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
#### FORMAT REGION ####


class Measurement(ft.UserControl):
    tristate_data_to_db ={
        True: True,
        None: False,
        False: None,
    }
    
    tristate_db_to_data ={
        True: True,
        False: None,
        None: False,
    }

    def __init__(self, label: str, control_type: ft.Control, item_list: List[str], format_func, format_region, default): # 接受參數用
        super().__init__()
        self.label = label # 辨識必須: 後續加入form內的measurement都需要label
        self.control_type = control_type # 未使用考慮可以移除
        self.head = ft.Text(
            self.label, 
            text_align='center', 
            # style=ft.TextThemeStyle.TITLE_MEDIUM,
            size=25 * FONT_SIZE_FACTOR, 
            weight=ft.FontWeight.W_600, 
            color=ft.colors.BLACK
        ) 
        self.body = {} # 不同型態measurement客製化
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
        if self.control_type == ft.Checkbox: # checkbox data_clear
            for item_name in self.body:
                self.body[item_name].value = False
            self.update()
        elif self.control_type == ft.TextField: # textfield data_clear
            for item_name in self.body:
                self.body[item_name].value = ''
            self.update()
        # else: #其他可能?


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
                if (value != None): # 為了checkbox型態的tristate
                    exist = True
            else:
                logger.error(f"data_exist內部遇到未定義型態||type:{type(value)}||value:{value}")

        return exist


    def data_load_db(self, values_dict):
        '''
        將資料庫取得的values_dict(keys為資料庫形式:db_column_names)傳入顯示欄位
        tristate checkbox會被轉譯(self.tristate_db_to_data)
        '''
        # 透過self.db_column_names方便程式碼閱讀但效率變差
        column_names = self.db_column_names()

        for i, item in enumerate(self.item_list):
            if type(self.body[item]) == ft.Checkbox:
                self.body[item].value = self.tristate_db_to_data[values_dict[column_names[i]]] # 資料庫獲取資料會在此轉換型態
            else:
                self.body[item].value = values_dict[column_names[i]]
        self.update()
    

    def db_column_names(self):
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
        column_names = self.db_column_names()
        values = {}
        for i, item in enumerate(self.item_list):
            value = self.body[item].value
            control_type = type(self.body[item])

            if type(value) == str: # 為何不用self.control_type 是因為control如果有新增其他type control會有問題 要用更細的type(self.body[item])判斷
                value = value.strip() # 字串類型前後空格去除
            elif control_type == ft.Checkbox and self.tristate == True: # 處理tristate
                value = self.tristate_data_to_db[value] # 資料轉換
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


    def build(self):
        # self.head = ft.Text(self.label, text_align='center', style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.W_400, color=ft.colors.BLACK)
        style_textfield = dict(
            dense=True, 
            height=40*FONT_SIZE_FACTOR+5, 
            cursor_height=20*FONT_SIZE_FACTOR, 
            content_padding = 10*FONT_SIZE_FACTOR, 
            expand=True
        )
        if len(self.item_list) == 1:
            self.body[self.item_list[0]] = ft.TextField(autofocus=True, **style_textfield)
        else:
            for i, item_name in enumerate(self.item_list):
                if self.body.get(item_name, None) != None: # 表示body已有control
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
    
         
class Measurement_Check(Measurement):
    def __init__(self, label: str, item_list: list, width_list: Union[List[int], int] = None, format_region = 'o', format_func = format_checkbox_tristate, default: dict = None, compact = False, tristate = True):
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
        # self.head = ft.Text(self.label, text_align='center', style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.W_400, color=ft.colors.BLACK)
        for i, item_name in enumerate(self.item_list):
            self.body[item_name] = ft.Checkbox(label=item_name, value=False, width=self.checkbox_width[i], height=25, tristate=self.tristate) # height = 25 讓呈現更緊
        
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
            return ft.Row(controls=[self.head, self.row], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            return ft.Column(controls=[self.head, self.row]) # 讓head換行後接著checkboxes
    

class Form(ft.Tab): #目的是擴增Tab的功能
    def __init__(self, label, measurement_list: List[Measurement]):
        super().__init__()
        self.label = label # 資料儲存
        self.measurement_list = measurement_list # 資料儲存
        
        self.display = ft.Container(
            content= ft.Text(value='已擷取......資料', color=ft.colors.WHITE, weight=ft.FontWeight.BOLD, visible=False),
            alignment=ft.alignment.center,
            bgcolor = ft.colors.BLUE,
            margin= ft.margin.only(top=5, bottom=0),
            visible= True,
        )
        self.text = self.label # 呈現用途
        self.content = ft.Column(
            controls=[
                self.display, 
                ft.Container( # 呈現用途
                    content=ft.Column(
                        controls=self.measurement_list,
                        scroll="adaptive",
                    ),
                    # alignment=ft.alignment.center,
                    expand=True,
                    padding=ft.padding.only(top=0, bottom=15),
                )
            ]
        )
        

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
                for column_name in measurement.db_column_names():
                    if measurement.control_type == ft.TextField: # FIXME 元件可以新增control，所以細節元件的type不一定等於measurement type
                        other_columns = other_columns + f' "{column_name}" text,'
                    elif measurement.control_type == ft.Checkbox:
                        other_columns = other_columns + f' "{column_name}" boolean,'
            
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
                    for column_name in measurement.db_column_names():
                        if column_name in diff:
                            if measurement.control_type == ft.TextField:
                                add_columns = add_columns + f' ADD COLUMN "{column_name}" text,'
                            elif measurement.control_type == ft.Checkbox:
                                add_columns = add_columns + f' ADD COLUMN "{column_name}" boolean,'
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
    ),
    ignore_exist=True
)

form_basic = Form(
    label="Basic",
    measurement_list=[
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        Measurement_Text('K(OD)', ['H','V'], format_func=format_text_parentheses),
        Measurement_Text('K(OS)', ['H','V'], format_func=format_text_parentheses),
        iop,
        Measurement_Text('Cornea', multiline=True),
        Measurement_Text('AC'),
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
    measurement_list=[
        Measurement_Check('Symptom', ['dry eye', 'dry mouth', 'pain','photophobia','tearing','discharge'], compact=True, format_region='s'),
        Measurement_Text('Other Symptoms', '', format_region='s', multiline=True),
        Measurement_Check('Affected QoL', ['driving', 'reading', 'work', 'outdoor', 'depressed']),
        Measurement_Text('3C_hrs', ''),
        Measurement_Text('SPEED', ''),
        Measurement_Text('OSDI', ''),
        Measurement_Text('History', '', format_region='s', multiline=True),
        Measurement_Check('PHx', ['DM', 'Hyperlipidemia', 'Sjogren','GVHD', 'AlloPBSCT', 'Seborrheic','Smoking', 'CATA', 'Refractive', 'IPL'], compact=True, format_region='s'),
        Measurement_Text('Shirmer 1', format_func=format_shirmer1),
        Measurement_Text('TBUT', format_func=format_text_2score),
        Measurement_Text('NEI'),
        Measurement_Check('MCJ_displacement', ['OD','OS'], compact=True),
        Measurement_Text('Telangiectasia'),
        Measurement_Check('MG plugging', ['OD','OS'], compact=True),
        Measurement_Text('Meibum', multiline=True),
        Measurement_Text('Mei_EXP'),
        Measurement_Text('LLT', format_func=format_text_2score),
        Measurement_Text('Blinking'),
        Measurement_Text('MG atrophy(OD)',['upper','lower'], format_func=format_text_parentheses),
        Measurement_Text('MG atrophy(OS)',['upper','lower'], format_func=format_text_parentheses),
        Measurement_Text('Lipidview', multiline=True),
        Measurement_Check('Lab abnormal', ['SSA/B', 'ANA', 'RF', 'dsDNA', 'ESR'], compact=True),
        Measurement_Text('Impression','', format_func=format_no_output, format_region='p'),
        Measurement_Check('Treatment', ['NPAT', 'Restasis', 'Autoserum', 'Diquas', 'IPL', 'Punctal plug'], compact=True),
    ]
)

form_ipl = Form(
    label="IPL",
    measurement_list=[
        Measurement_Text('IPL NO', '', format_region='p'),
        Measurement_Check('Post-IPL', [''], compact=True),
        Measurement_Text('Massage(OD)', ['upper','lower'], format_region='p'),
        Measurement_Text('Massage(OS)', ['upper','lower'], format_region='p'),
        Measurement_Check('Improved Symptoms', ['dry eye', 'dry mouth', 'pain','photophobia','tearing','discharge'], compact=True),
        Measurement_Text('Other Symptoms', '', multiline=True),
        Measurement_Check('Improved QoL', ['driving', 'reading', 'work', 'outdoor', 'depressed']),
        Measurement_Text('SPEED', ''),
        Measurement_Text('OSDI', ''),
        Measurement_Text('Shirmer 1', format_func=format_shirmer1),
        Measurement_Text('TBUT', format_func=format_text_2score),
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
    ),
    ignore_exist=True
)

form_ivi = Form(
    label="IVI",
    measurement_list=[
        Measurement_Text('VA'),
        Measurement_Text('REF'),
        Measurement_Text('K', ['H','V'], format_func=format_text_parentheses),
        iop,
        Measurement_Text('Lens'),
        Measurement_Text('CMT'),
        Measurement_Text('Fundus+OCT',[''], multiline=True),
        Measurement_Check('IRF', ['OD','OS'], compact=True),
        Measurement_Check('SRF', ['OD','OS'], compact=True),
        Measurement_Check('SHRM', ['OD','OS'], compact=True),
        Measurement_Check('Atrophy', ['OD','OS'], compact=True),
        Measurement_Check('Gliosis', ['OD','OS'], compact=True),
        Measurement_Check('Schsis', ['OD','OS'], compact=True),
        Measurement_Check('New hemorrhage', ['OD','OS'], compact=True),
        Measurement_Text('OCT findings', multiline=True),
        Measurement_Check('Impression', ['AMD','PCV', 'RAP', 'mCNV', 'CRVO', 'BRVO', 'DME', 'VH', 'CME', 'PDR', 'NVG', 'IGS', 'CSCR'], compact=True),
        Measurement_Text('Other Impression', multiline=True),
        Measurement_Check('Treatment', ['Eyelea','Lucentis', 'Avastin', 'Ozurdex', 'Beovu', 'Faricimab'], compact=True),
    ]
)

########################## MERGE
db_conn = None
cursor = None

form_list_tuples = (form_dryeye, form_ipl, form_basic, form_ivi, form_plasty) # 不應該被變更的所有form_list
forms = Forms(form_list_tuples) # 初始化註冊所有forms

if __name__ == '__main__': # load這個library來建立DB
    db_connect()
    forms.db_migrate()
