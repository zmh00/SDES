import flet as ft
import datetime
from typing import Union, List
import psycopg2
from psycopg2.sql import SQL, Identifier, Placeholder, Literal
from psycopg2.extras import RealDictCursor
import logging

# CONST and ATTRIBUTES
TEST_MODE = False
DATE_MODE = 1
HOST = '10.53.70.143'
if TEST_MODE:
    HOST = 'localhost'
PORT = '5431'
DBNAME = 'vgh_oph'
USER = 'postgres'
PASSWORD ='qazxcdews'
FONT_SIZE_FACTOR = 0.8
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
        logger.info(f"Connect [{DBNAME}] database successfully!")
    except Exception as e:
        logger.error(f"Encounter exception: {e}")


def format_today(mode):
    if mode == 1: # 西元紀年
        today = datetime.datetime.today().strftime("%Y%m%d")
    elif mode == 2: # 民國紀年
        today = str(datetime.datetime.today().year-1911) + datetime.datetime.today().strftime("%m%d") 
    elif mode == 3: # 西元紀年，兩位數
        today = str(datetime.datetime.today().year-2000) + datetime.datetime.today().strftime("%m%d")
    return today


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

    def __repr__(self) -> str:
        return f"{self.label}||{super().__repr__()}"

    def build(self): # 初始化UI
        pass # 需要客製化: 因為元件設計差異大，Method overriding after inheritence

    
    def add_before_build(self, data_row: dict): # 增加元素要透過這函數:影響item_list和body內容
        for keys in data_row:
            self.item_list.append(keys)
            self.body[keys] = data_row[keys]
    

    def add_after_build(self, data_row: dict):
        for keys in data_row:
            self.item_list.append(keys)
            self.body[keys] = data_row[keys]
            self.row.controls.append(self.body[keys])
        self.update()


    def data_set_value(self, values_dict):
        for item in self.item_list:
            if str(item).strip() == '': # 如果item是空字串
                key = f"{self.label}".replace(' ','_')
            else:
                key = f"{self.label}_{item}".replace(' ','_')  # 把空格處理掉 => 減少後續辨識錯誤
            self.body[item].value = values_dict[key]
        self.update()
    
    def data_clear(self, e=None): # 清除
        pass

    def data_return_default(self, e=None): # 恢復預設值
        pass
    
    def data_opdformat(self, e=None): # 帶入門診病例的格式
        pass
    
    @property
    def db_column_names(self):
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
        column_names = self.db_column_names
        values = {}
        for i, item in enumerate(self.item_list):
            value = self.body[item].value
            if type(value) == str:
                value = value.strip() # 前後空格去除
            values[column_names[i]] = value
        return values

#### FORMAT REGION ####
def format_no_output(measurement:Measurement):
    return ''


def format_textfield(measurement:Measurement):
    format_text = ''
    other_format_text = ''
    for i in measurement.body:
        if i == 'OD' or i == 'OS':
            if measurement.body[i].value.strip() != '':
                format_text = format_text + f"{measurement.body[i].value} {i}, "
        else:
            if measurement.body[i].value.strip() != '':
                other_format_text = other_format_text + f"{measurement.body[i].value} {i}, "
    format_text = format_text + other_format_text
    
    if len(format_text) == 0:
        return ''
    else:
        today = format_today(DATE_MODE)
        format_text = f"{today} {measurement.label}:{format_text.rstrip(', ')}"
    return format_text


def format_checkbox(measurement:Measurement):
    format_text = ''
    for item_name in measurement.body:
        if measurement.body[item_name].value != False:
            format_text = format_text + f"{item_name}, "
    
    if len(format_text) == 0:
        return ''
    else:
        today = format_today(DATE_MODE)
        format_text = f"{today} {measurement.label}:{format_text.rstrip(', ')}"
    return format_text


def format_iop(measurement:Measurement):
    format_text = ''
    if measurement.body['OD'].value.strip() != '' and measurement.body['OS'].value.strip() != '':
        return ''
    else:
        iop_od = measurement.body['OD'].value.strip()
        iop_os = measurement.body['OS'].value.strip()
        iop_mode = measurement.body['mode'].value
        format_text = f"({iop_mode}) {iop_od}/{iop_os}mmHg"
        today = format_today(DATE_MODE)    
        format_text = f"{today} {measurement.label}:{format_text}"
        return format_text


def format_exo(measurement:Measurement):
    exo_od=''
    exo_os=''
    exo_pd=''
    if measurement.body['OD'].value.strip() != '':
        exo_od = measurement.body['OD'].value.strip()
    if measurement.body['OS'].value.strip() != '':
        exo_os = measurement.body['OS'].value.strip()
    if measurement.body['PD'].value.strip() != '':
        exo_pd = measurement.body['PD'].value.strip()
    if exo_od == '' and exo_os == '' and exo_pd == '':
        return ''
    else:
        today = format_today(DATE_MODE)    
        format_text = f"{today} {measurement.label}:{exo_od}>--{exo_pd}--<{exo_os}"
        return format_text
#### FORMAT REGION ####

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


    def build(self):
        # self.head = ft.Text(self.label, text_align='center', style=ft.TextThemeStyle.TITLE_LARGE, weight=ft.FontWeight.W_400, color=ft.colors.BLACK)
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
    

    def data_clear(self, e=None):
        for item_name in self.body:
            self.body[item_name].value = ''
        self.update()


    def data_return_default(self, e=None):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用
        
    
    def data_opdformat(self, e=None):
        if self.format_func == None:
            format_text = format_textfield(self)
        else:
            format_text = self.format_func(self) # EXO、IOP需要客製化
        return format_text


class Measurement_Check(Measurement):
    def __init__(self, label: str, item_list: list, width_list: Union[List[int], int] = 70, format_func = None, default: dict = None, compact = False):
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
    

    def data_clear(self, e=None):
        for item_name in self.body:
            self.body[item_name].value = False
        self.update()


    def data_return_default(self, e=None):
        if self.default != None:
            for keys in self.default:
                self.body[keys].value = self.default[keys]
            self.update() # 因為有update，只能在元件已經建立加入page後使用


    def data_opdformat(self, e=None):
        if self.format_func == None:
            format_text = format_checkbox(self)
        else:
            format_text = self.format_func(self)
        return format_text


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


    def data_exist(self, values_dict: dict) -> bool:
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

    def data_clear(self, e=None):
        for measurement in self.measurement_list:
            measurement.data_clear()
        self.set_display() # 清除display
    
    def data_return_default(self, e=None):
        for measurement in self.measurement_list:
            measurement.data_return_default()

    def data_opdformat(self, e=None):
        format_text = ''
        for measurement in self.measurement_list:
            text = measurement.data_opdformat()
            if text != '':
                format_text = format_text + text + '\n'
        return format_text

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

    def db_migrate(self) -> bool: # 偵測目前有沒有這個table沒有就建立，如果有column差異就新增?
        #### 需要注意引號與大小寫table name and column name => 目前設計是case sensitive
        
        # 偵測table
        detect_query = f'''SELECT EXISTS (
            SELECT FROM pg_tables
            WHERE tablename  = '{self.label}')'''
        try:
            cursor.execute(detect_query)
            exists = cursor.fetchone()['exists']
        except Exception as error:
            db_conn.rollback()
            logger.error(f"Table[{self.label}] Error in detect table existence: {error}")
            return False

        if exists == False: #Table不存在
            logger.info(f"Table[{self.label}] NOT exists! Building...")
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
                logger.error(f"Table[{self.label}] Error in transaction(CREATE TABLE) and rollback: {error}")
                db_conn.rollback()
                return False
        
        else: #Table已存在
            logger.info(f"Table[{self.label}] Exists!")
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
                logger.info(f"Table[{self.label}] NO NEED FOR ADDING COLUMN!")
            else:
                logger.info(f"Table[{self.label}] ADDING COLUMN[{len(diff)}]:{diff}")
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
                    logger.error(f"Table[{self.label}] Error in transaction(ALTER TABLE) and rollback: {error}")
                    db_conn.rollback()
                    return False
        return True
        

    def db_save(self, patient_hisno, *args, **kwargs):
        patient_name = kwargs.get('patient_name', None)
        values_dict = self.db_values_dict

        # 如果沒有資料輸入(空白text or unchecked checkbox)就不送資料庫
        if self.data_exist(values_dict) == False:
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

        # 建立query
        query = SQL("insert into {table} ({fields}) values ({values})").format(
            table = Identifier(self.label),
            fields = SQL(', ').join(map(Identifier, column_names)),
            values = SQL(', ').join(map(Placeholder, column_names))
        )

        try:
            cursor.execute(query, values_dict) #因為前面定義過有標籤的placeholder，可以傳入dictionary
            db_conn.commit()
            logger.info(f'Table[{self.label}] Saving query finished')
            return True
        except Exception as e:
            logger.error(f"Table[{self.label}] Encounter exception: {e}")
            db_conn.rollback()
            return False

    
    def db_load(self, patient_hisno, *args, **kwargs):
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
            logger.info(f'Table[{self.label}]|Patient[{patient_hisno}] Loading query finished')
            if row is None: # 沒有資料就回傳None
                return None
            self.data_set_value(dict(row)) # 設定measurement資料
            self.set_display(text=f"已擷取資料日期:{row[COLUMN_TIME_UPDATED].strftime('%Y-%m-%d %H:%M')}") # 顯示display:資料擷取日期
            return True
        except Exception as e:
            logger.error(f"Table[{self.label}] Encounter exception: {e}")
            return False


class Forms(): #集合Form(Tab)，包裝存、取、清除功能
    def __init__(self, form_list: List[Form]) -> None:
        self.form_list = form_list
        self.doctor_id = None
        self.patient_hisno = None
        self.patient_name = None
    
    # def data_set_value(self, values_dict):
    #     pass

    # def data_return_default(self, e=None):
    #     pass


    def set_doctor_id(self, doctor_id, *args):
        self.doctor_id = doctor_id
        for form in self.form_list:
            form.set_doctor_id(doctor_id=doctor_id)


    def set_patient_data(self, patient_hisno, patient_name, *args):
        self.patient_hisno = patient_hisno
        self.patient_name = patient_name
        for form in self.form_list:
            form.set_patient_data(patient_hisno=patient_hisno, patient_name=patient_name)


    def data_opdformat(self, e=None):
        form_text = ''
        for form in self.form_list:
            form_text = form_text + form.data_opdformat()
        return form_text


    def data_clear(self, e=None): # 全部forms 清除
        for form in self.form_list:
            form.data_clear()


    def db_migrate(self): # 全部forms migrate
        for form in self.form_list:
            form.db_migrate()
    

    # 按下存檔按鈕時會抓取病人資料
    def db_save(self, patient_hisno, *args, **kwargs): # 全部forms 儲存
        for form in self.form_list:
            res = form.db_save(patient_hisno, *args, **kwargs)
            if res == None:
                form.data_clear() # TODO 這行有甚麼用?
                logger.info(f"{form.label}||{self.doctor_id}||{patient_hisno}||Skip writing to database")
            elif res == False:
                logger.error(f"{form.label}||{self.doctor_id}||{patient_hisno}||Fail writing to database")
            else:
                logger.info(f"{form.label}||{self.doctor_id}||{patient_hisno}||Finish writing to database")


    def db_load_one(self, patient_hisno, tab_index, *args, **kwargs): # 讀取特定form
        res = self.form_list[tab_index].db_load(patient_hisno, *args, **kwargs)
        if res == None:
            logger.info(f"{self.form_list[tab_index].label}||{self.doctor_id}||{patient_hisno}||Empty record")
        elif res == False:
            logger.error(f"{self.form_list[tab_index].label}||{self.doctor_id}||{patient_hisno}||Fail reading from database")
        else:
            logger.info(f"{self.form_list[tab_index].label}||{self.doctor_id}||{patient_hisno}||Finish reading from database")
        
        return res # 回傳給GUI做notify

    def db_load_all(self, patient_hisno, *args, **kwargs): # 全部forms 讀取 => 暫時不用
        for form in self.form_list:
            res = form.db_load(patient_hisno, *args, **kwargs)
            if res == None:
                logger.info(f"{form.label}||{self.doctor_id}||{patient_hisno}||Empty record")
            elif res == False:
                logger.error(f"{form.label}||{self.doctor_id}||{patient_hisno}||Fail reading from database")
            else:
                logger.info(f"{form.label}||{self.doctor_id}||{patient_hisno}||Finish reading from database")

########################## Basic
# 客製化IOP按鈕
iop = Measurement_Text('IOP', format_func=format_iop)
iop.add_before_build(
    {
        'mode': ft.Dropdown(
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
        Measurement_Text('K(OD)', ['H','V']),
        Measurement_Text('K(OS)', ['H','V']),
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
        Measurement_Text('Exo', ['OD', 'PD', 'OS'], format_func=format_exo),
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
        Measurement_Text('OSDI',''),
        Measurement_Text('SPEED',''),
        Measurement_Text('Shirmer'),
        Measurement_Text('TBUT'),
        Measurement_Text('NEI'),
        Measurement_Check('Anterior displacement MCJ', ['OD','OS'], [70,70], compact=True),
        Measurement_Text('Mei_EXP'),
        Measurement_Text('Mei_NUM')
    ]
)

########################## IVI
iop = Measurement_Text('IOP', format_func=format_iop)
iop.add_before_build(
    {
        'mode': ft.Dropdown(
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

########################## TEST
form_test2 = Form(
    label="Test",
    measurement_list=[
        iop,
        Measurement_Text('test1'),
        Measurement_Text('test2'),
        Measurement_Check('IRF', ['OD','OS'], [70,70], compact=True),
        Measurement_Check('cmt', ['OD','OS'], [70,70], compact=True),
    ]
)
########################## MERGE
db_conn = None
cursor = None

if TEST_MODE:
    forms = Forms([form_dryeye, form_ivi, form_plasty])
else:
    forms = Forms([form_dryeye, form_ivi, form_plasty]) # 註冊使用的form

if __name__ == '__main__': # load這個library來建立DB
    db_connect()
    forms.db_migrate()

# finally:
#     # 斷開資料庫的連線
#     db_conn.close()

# TESTING
# f= init('4123','123456789','sss')
# f.form_list[0].db_migrate()