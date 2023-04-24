import flet as ft
import datetime
from typing import Union, List, Tuple
import psycopg2
from psycopg2.sql import SQL, Identifier, Placeholder, Literal
from psycopg2.extras import RealDictCursor
import logging
import inspect

# CONST and ATTRIBUTES
TEST_MODE = False
FORMAT_MODE = 1
# DATE_MODE = 1
HOST = '10.53.70.143'
if TEST_MODE:
    HOST = 'localhost'
PORT = '5431'
DBNAME = 'vgh_oph'
USER = 'postgres'
PASSWORD ='qazxcdews'
FONT_SIZE_FACTOR = 0.6
# DOCTOR_ID

# COLUMN NAMES
COLUMN_PATIENT_HISNO = 'patient_hisno'
COLUMN_PATIENT_NAME = 'patient_name'
COLUMN_DOC = 'doctor_id'
COLUMN_TIME_CREATED = 'created_at'
COLUMN_TIME_UPDATED = 'updated_at'

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
        db_conn = psycopg2.connect(host=HOST, dbname=DBNAME, user=USER, password=PASSWORD, port = PORT)
        cursor = db_conn.cursor(cursor_factory = RealDictCursor)
        logger.info(f"{inspect.stack()[0][3]}||Connect [{DBNAME}] database successfully!")
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
    return ''


def format_text_tradition(measurement):
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
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value.strip() == '':
            format_text = format_text + f"?/"
        else:
            format_text = format_text + f"{measurement.body[item_name].value.strip()}/"
    
    format_text = f"{measurement.label}:" + format_text.rstrip('/')
    return format_text


def format_checkbox(measurement):
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value != False:
            format_text = format_text + f"{item_name},"

    format_text = f"{measurement.label}:" + format_text.rstrip(',')
    return format_text


def format_k(measurement):
    format_text = ''
    k_h = measurement.body['H'].value.strip()
    k_h = k_h if k_h != '' else 'error'
    k_v = measurement.body['V'].value.strip()
    k_v = k_v if k_v != '' else 'error'
    format_text = f"(H){k_h}/(V){k_v}"

    format_text = f"{measurement.label}:" + format_text
    return format_text


def format_iop(measurement):
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
    def __init__(self, label: str, control_type: ft.Control, item_list: List[str]): # 接受參數用
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
        
        self.ignore_exist_item_list = [] # 跳脫data_exist檢查的項目

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


    def data_set_value(self, values_dict):
        for item in self.item_list:
            if str(item).strip() == '': # 如果item是空字串
                key = f"{self.label}".replace(' ','_')
            else:
                key = f"{self.label}_{item}".replace(' ','_')  # 把空格處理掉 => 減少後續辨識錯誤
            self.body[item].value = values_dict[key]
        self.update()
    
    def data_clear(self): # 清除
        pass

    def data_return_default(self): # 恢復預設值
        pass
    
    @property
    def data_exist(self):
        '''
        回傳Measurement是否皆為空值
        '''
        exist = False
        for i, item in enumerate(self.item_list):
            # 特殊欄位跳過
            if item in self.ignore_exist_item_list:
                continue
            
            value = self.body[item].value
            if type(value) == str: # text型態空值
                if value.strip() != '':
                    exist = True
            elif type(value) == bool: # checkbox型態空值
                if value != False:
                    exist = True
            else:
                logger.error(f"data_exist內部遇到未定義型態||type:{type(value)}||value:{value}")

        return exist

    def data_opdformat(self, format_func, format_region): 
        '''
        帶入門診病例的格式
        目前設計確認有無資料放在form內部，所以會傳入data_opdformat都是有使用者輸入資料的
        '''
        # 客製化格式
        format_text = format_func(self)
        
        # 分類到指定的region('s','o','p')，format_text為list type
        return format_region, format_text
    

    @property
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


    @property
    def db_values_dict(self):  #將內部資料輸出: dict( {self.label}_{item_name} : value )
        '''
        將measurement內部值搭配column_names形成values_dict，只有去除頭尾空格，沒有捨棄空值
        '''
        column_names = self.db_column_names
        values = {}
        for i, item in enumerate(self.item_list):
            value = self.body[item].value
            if type(value) == str:
                value = value.strip() # 前後空格去除
            values[column_names[i]] = value
        return values


class Measurement_Text(Measurement):
    def __init__(self, label: str, item_list: list = None, multiline = False, format_region = 'o', format_func = format_text_tradition, default: dict = None):
        super().__init__(label, ft.TextField, item_list)
        self.multiline = multiline
        self.format_func = format_func
        self.format_region = format_region
        self.default = default # {item_keys: default_value}
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
    

    def data_clear(self):
        for item_name in self.body:
            self.body[item_name].value = ''
        self.update()


    def data_return_default(self):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用
        
    
    def data_opdformat(self):
        return super().data_opdformat(format_func=self.format_func, format_region=self.format_region)
         


class Measurement_Check(Measurement):
    def __init__(self, label: str, item_list: list, width_list: Union[List[int], int] = None, format_region = 'o', format_func = format_checkbox, default: dict = None, compact = False):
        if type(item_list) != list:
            raise Exception("Wrong input in Measurement_Check item_list")
        super().__init__(label, ft.Checkbox, item_list)
        self.default = default # {item_keys: default_value}
        self.format_func = format_func
        self.format_region = format_region
        self.compact = compact
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
            self.body[item_name] = ft.Checkbox(label=item_name, value=False, width=self.checkbox_width[i], height=25) # height = 25 讓呈現更緊
        
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
    

    def data_clear(self):
        for item_name in self.body:
            self.body[item_name].value = False
        self.update()


    def data_return_default(self):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用


    def data_opdformat(self):
        return super().data_opdformat(format_func=self.format_func, format_region=self.format_region)


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
        if text == None: # 若沒有顯示文字就隱藏display
            self.display.content.visible = False
        else:
            self.display.content.value = text
            self.display.content.visible = True
        self.display.update()

    def set_doctor_id(self, doctor_id, *args):
        self.doctor_id = doctor_id

    def set_patient_data(self, patient_hisno, patient_name, *args):
        self.patient_hisno = patient_hisno
        self.patient_name = patient_name


    @property
    def measurements(self, item_name: str):
        for measurement in self.measurement_list:
            if measurement.label == item_name:
                return measurement
        return None


    def check_form_values_exist(self, values_dict: dict) -> bool:
        '''
        判斷傳入values_dict是否有值，針對不同類型的資料有不同判斷方式
        '''
        for key in values_dict:
            value =  values_dict[key]
            if type(value) == str and value.strip() != '':
                return True
            elif type(value) == bool and value != False:
                return True
        return False


    def data_set_value(self, values_dict):
        for measurement in self.measurement_list:
            measurement.data_set_value(values_dict)


    def data_clear(self):
        for measurement in self.measurement_list:
            measurement.data_clear()
        self.set_display() # 清除display


    def data_return_default(self):
        for measurement in self.measurement_list:
            measurement.data_return_default()


    def data_exist(self):
        for measurement in self.measurement_list:
            if measurement.data_exist:
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
            if measurement.data_exist: # 確認有無資料決定是否納入
                region, text = measurement.data_opdformat()
                format_dict[region].append(text)

        format_form = {}
        for region in format_dict:
            if len(format_dict[region]) !=0:
                format_form[region] = format_merge(format_dict[region], form_name = self.label)

        return format_form

    @property
    def db_column_names(self): # 集合所有的measurement column_names
        column_names = []
        for measurement in self.measurement_list:
            column_names.extend(measurement.db_column_names)
        return column_names

    @property
    def db_values_dict(self): # 集合所有的measurement values, 若有同名後者會覆寫前者
        values = {}
        for measurement in self.measurement_list:
            values.update(measurement.db_values_dict)
        return values

    def db_migrate(self) -> bool: 
        '''
        偵測目前有沒有這個table沒有就建立，如果有column差異就新增?
        #### 需要注意引號與大小寫table name and column name => 目前設計是case sensitive
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
                for column_name in measurement.db_column_names:
                    if measurement.control_type == ft.TextField:
                        other_columns = other_columns + f' "{column_name}" text,'
                    elif measurement.control_type == ft.Checkbox:
                        other_columns = other_columns + f' "{column_name}" boolean,'
            
            # 創建table
            query = f'''CREATE TABLE IF NOT EXISTS "{self.label}" (
                id serial PRIMARY KEY,
                "{COLUMN_TIME_CREATED}" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                "{COLUMN_TIME_UPDATED}" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                "{COLUMN_DOC}" varchar(8),
                "{COLUMN_PATIENT_HISNO}" varchar(15) NOT NULL,
                "{COLUMN_PATIENT_NAME}" varchar(20),
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
            new_column_names = set(self.db_column_names)
            diff = new_column_names - old_column_names
            if len(diff) ==0:
                logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] NO NEED FOR ADDING COLUMN!")
            else:
                logger.info(f"{inspect.stack()[0][3]}||Table[{self.label}] ADDING COLUMN[{len(diff)}]:{diff}")
                # 將集合差值的column names搭配data type形成query => "{column_name}"使用雙引號: case-sensitive 
                add_columns = ''
                for measurement in self.measurement_list:
                    for column_name in measurement.db_column_names:
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
        return True
        

    def db_save(self, patient_hisno, *args, **kwargs):
        patient_name = kwargs.get('patient_name', None)
        values_dict = self.db_values_dict
        
        # 如果沒有資料輸入(空白text or unchecked checkbox)就不送資料庫
        # TODO 確認有沒有資料的方式是否改成透過measurement.data_exist?
        if self.check_form_values_exist(values_dict) == False:
            return None
        
        # 有種可能是有名字一樣的measurement => column_names會多於values_dict
        column_names = self.db_column_names
        if len(column_names) != len(values_dict):
            raise Exception(f"Table[{self.label}] Different length of column_names and values_dict")
        
        # 將醫師資料+病人資料存入
        column_names = [COLUMN_DOC, COLUMN_PATIENT_HISNO, COLUMN_PATIENT_NAME] + column_names
        values_dict.update(
            {
                COLUMN_DOC: self.doctor_id,
                COLUMN_PATIENT_HISNO: patient_hisno,
                COLUMN_PATIENT_NAME: patient_name,
            }
        )

        # psycopg parameterized SQL 因為防範SQL injection不支持欄位名稱有'%','(',')'
        # try:
        #     # 建立query
        #     query = SQL("insert into {table} ({fields}) values ({values})").format(
        #         table = Identifier(self.label),
        #         fields = SQL(', ').join(map(Identifier, column_names)),
        #         values = SQL(', ').join(map(Placeholder, column_names))
        #     )
        # except Exception as e:
        #     print(e)
        
        # 自製query
        fields = ""
        values = ""
        for column in column_names:
            if (values_dict[column] != None) and (values_dict[column] != ''): # None 和 空字串不能直接放入SQL內
                fields = fields + f'"{column}", '
                if type(values_dict[column]) == str:
                    values = values + f"'{values_dict[column]}', "
                else:
                    values = values + f"{values_dict[column]}, "
        query = f'''INSERT INTO "{self.label}" ({fields.rstrip(', ')}) VALUES ({values.rstrip(', ')})'''

        try:
            #cursor.execute(query, values_dict) #因為前面定義過有標籤的placeholder，可以傳入dictionary
            cursor.execute(query)
            db_conn.commit()
            # logger.debug(f'{inspect.stack()[0][3]}||Form[{self.label}]||Finish saving commit')
            return True
        except Exception as e:
            logger.error(f"{inspect.stack()[0][3]}||Form[{self.label}]||Encounter exception: {e}")
            db_conn.rollback()
            return False

    
    def db_load(self, patient_hisno, **kwargs):
        # 抓取符合醫師+病人的最新一筆資料
        query = SQL("SELECT * FROM {table} WHERE {doc}={doctor_id} AND {hisno}={patient_hisno} ORDER BY id DESC NULLS LAST LIMIT 1").format(
            table = Identifier(self.label),
            doc = Identifier(COLUMN_DOC),
            doctor_id = Literal(self.doctor_id),
            hisno = Identifier(COLUMN_PATIENT_HISNO),
            patient_hisno = Literal(patient_hisno),
        )

        try:
            cursor.execute(query)
            row = cursor.fetchone()
            # logger.debug(f'Table[{self.label}]|Patient[{patient_hisno}] Loading query finished')
            if row is None: # 沒有資料就回傳None
                self.set_display(text="無資料可擷取")
                return None
            self.data_set_value(dict(row)) # 設定measurement資料
            self.set_display(text=f"已擷取資料日期:{row[COLUMN_TIME_UPDATED].strftime('%Y-%m-%d %H:%M')}") # 顯示display:資料擷取日期
            return True
        except Exception as e:
            logger.error(f"{inspect.stack()[0][3]}||Table[{self.label}]||Encounter exception: {e}")
            return False


class Forms(): #集合Form(Tab)，包裝存、取、清除功能
    def __init__(self, form_list: Tuple[Form]) -> None:
        self.form_list_original = form_list # 儲存所有forms(不應變動)
        self.form_list_selected = list(form_list) # 會因為選擇fomrs而變動
        self.doctor_id = None
        self.patient_hisno = None
        self.patient_name = None
    

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


    def set_doctor_id(self, doctor_id, *args):
        self.doctor_id = doctor_id
        for form in self.form_list_selected:
            form.set_doctor_id(doctor_id=doctor_id)


    def set_patient_data(self, patient_hisno, patient_name, *args):
        self.patient_hisno = patient_hisno
        self.patient_name = patient_name
        for form in self.form_list_selected:
            form.set_patient_data(patient_hisno=patient_hisno, patient_name=patient_name)


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


    def data_exist(self):
        for form in self.form_list_selected:
            if form.data_exist():
                return True
        return False


    def db_migrate(self): # 全部forms migrate
        res_string = ''
        for form in self.form_list_original:
            res = form.db_migrate()
            res_string = res_string + f"{form.label}:{res}\n"
        return res_string

    # 按下存檔按鈕時會抓取病人資料
    def db_save(self, patient_hisno, tab_index = None, **kwargs): # 儲存form:整合儲存單一與全部
        error_list = []
        if tab_index == None: # 全部
            for form in self.form_list_selected:
                res = form.db_save(patient_hisno, **kwargs)
                if res == None:
                    logger.info(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_hisno}||Skip saving")
                    form.data_clear() # 存完清除
                elif res == False:
                    logger.error(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_hisno}||Fail saving")
                    error_list.append(form.label)
                else:
                    logger.debug(f"{inspect.stack()[0][3]}||Forms[{form.label}]||{self.doctor_id}||{patient_hisno}||Finish saving")
                    form.data_clear() # 存完清除
        else: # 單一
            res = self.form_list_selected[tab_index].db_save(patient_hisno, **kwargs)
            if res == None:
                logger.info(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_hisno}||Skip saving")
                self.form_list_selected[tab_index].data_clear() # 存完清除
            elif res == False:
                logger.error(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_hisno}||Fail saving")
                error_list.append(self.form_list_selected[tab_index].label)
            else:
                logger.debug(f"{inspect.stack()[0][3]}||Forms[{self.form_list_selected[tab_index].label}]||{self.doctor_id}||{patient_hisno}||Finish saving")
                self.form_list_selected[tab_index].data_clear() # 存完清除
        
        return error_list


    def db_load(self, patient_hisno, tab_index = None, **kwargs): # 讀取form:整合讀取單一與全部
        error_list = []
        # TODO load之前應該要判斷 Forms exist，如果存在要返回警告，選擇強制清除就繼續
        if tab_index == None: # 全部
            for form in self.form_list_selected:
                res = form.db_load(patient_hisno, **kwargs)
                if res == None:
                    logger.info(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Empty record")
                elif res == False:
                    logger.error(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Fail loading")
                    error_list.append(form.label)
                else:
                    logger.debug(f"{inspect.stack()[0][3]}||{form.label}||{self.doctor_id}||{patient_hisno}||Finish loading")
        else: # 單一
            res = self.form_list_selected[tab_index].db_load(patient_hisno, **kwargs)
            if res == None:
                logger.info(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_hisno}||Empty record")
            elif res == False:
                logger.error(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_hisno}||Fail loading")
                error_list.append(self.form_list_selected[tab_index].label)
            else:
                logger.debug(f"{inspect.stack()[0][3]}||{self.form_list_selected[tab_index].label}||{self.doctor_id}||{patient_hisno}||Finish loading")
            
        return error_list # 回傳給GUI做notify


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
        Measurement_Text('K(OD)', ['H','V'], format_func=format_k),
        Measurement_Text('K(OS)', ['H','V'], format_func=format_k),
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
        Measurement_Text('Other Symptoms', '', format_region='s'),
        Measurement_Text('History', '', format_region='s'),
        Measurement_Check('PHx', ['DM', 'Hyperlipidemia', 'Sjogren', 'Seborrheic','Smoking', 'CATA', 'Refractive', 'IPL'], compact=True, format_region='s'),
        Measurement_Text('Shirmer 1', format_func=format_text_2score),
        Measurement_Text('TBUT', format_func=format_text_2score),
        Measurement_Text('NEI', format_func=format_text_2score),
        Measurement_Check('MCJ_displacement', ['OD','OS'], compact=True),
        Measurement_Text('Telangiectasia'),
        Measurement_Check('MG plugging', ['OD','OS'], compact=True),
        Measurement_Text('Meibum', multiline=True),
        Measurement_Text('Mei_EXP', format_func=format_text_2score),
        Measurement_Text('Question', ['OSDI', 'SPEED']),
        Measurement_Text('LLT', format_func=format_text_2score),
        Measurement_Text('Lipidview', multiline=True),
        Measurement_Check('Lab abnormal', ['SSA/B', 'ANA', 'ESR','RF', 'dsDNA'], compact=True),
        Measurement_Text('Impression','', format_func=format_no_output, format_region='p'),
        Measurement_Check('Treatment', ['NPAT', 'Restasis', 'Autoserum', 'Diquas', 'IPL', 'Punctal plug'], compact=True),
    ]
)

form_ipl = Form(
    label="IPL",
    measurement_list=[
        Measurement_Text('IPL NO', '', format_region='p'),
        Measurement_Text('Massage(OD)', ['upper','lower'], format_region='p'),
        Measurement_Text('Massage(OS)', ['upper','lower'], format_region='p')
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
        iop,
        Measurement_Text('Lens'),
        Measurement_Text('CMT'),
        Measurement_Check('IRF', ['OD','OS'], compact=True),
        Measurement_Check('SRF', ['OD','OS'], compact=True),
        Measurement_Check('SHRM', ['OD','OS'], compact=True),
        Measurement_Check('Atrophy', ['OD','OS'], compact=True),
        Measurement_Check('Gliosis', ['OD','OS'], compact=True),
        Measurement_Check('New hemorrhage', ['OD','OS'], compact=True),
        Measurement_Text('Fundus', multiline=True),
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
