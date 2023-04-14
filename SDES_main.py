import flet as ft
from flet import Page
import datetime
import time
import subprocess
import uiautomation as auto
# forms listed in SDES_form
import SDES_form

PROCESS_NAME = 'vghtpe.dcr.win.exe'

def process_exists(process_name=PROCESS_NAME):
    '''
    Check if a program (based on its name) is running
    Return yes/no exists window and its PID
    '''
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
    # use buildin check_output right away
    output = subprocess.check_output(call).decode(
        'big5')  # 在中文的console中使用需要解析編碼為big5
    output = output.strip().split('\r\n')
    if len(output) == 1:  # 代表只有錯誤訊息
        return False, 0
    else:
        # check in last line for process name
        last_line_list = output[-1].lower().split()
    return last_line_list[0].startswith(process_name.lower()), last_line_list[1]


def process_responding(name=PROCESS_NAME):
    """Check if a program (based on its name) is responding"""
    cmd = 'tasklist /FI "IMAGENAME eq %s" /FI "STATUS eq running"' % name
    status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    status = str(status).lower() # case insensitive
    return name in status


def process_responding_PID(pid):
    """Check if a program (based on its PID) is responding"""
    cmd = 'tasklist /FI "PID eq %d" /FI "STATUS eq running"' % pid
    status = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout.read()
    status = str(status).lower()
    return str(pid) in status


def captureimage(control = None, postfix = ''):
    auto.Logger.WriteLine('CAPTUREIMAGE INITIATION', auto.ConsoleColor.Yellow)
    if control is None:
        c = auto.GetRootControl()
    else:
        c = control
    if postfix == '':
        path = f"{datetime.datetime.today().strftime('%Y%m%d_%H%M%S')}.png"
    else:
        path = f"{datetime.datetime.today().strftime('%Y%m%d_%H%M%S')}_{postfix}.png"
    c.CaptureToImage(path)


def patient_data_autoset(patient_hisno: ft.TextButton, patient_name: ft.Text, toggle_func): # TODO refactor the parameters and structure
    old_p_dict = None
    state = -1
    with auto.UIAutomationInitializerInThread():
        while(1):
            try:
                window_soap = auto.WindowControl(searchDepth=1, AutomationId="frmSoap")
                if window_soap.Exists():
                    l = window_soap.Name.split()
                    p_dict = {
                        'hisno': l[0],
                        'name': l[1],
                        'id': l[6], 
                        'charge': l[5],
                        'birthday': l[4][1:-1],
                        'age': l[3][:2]
                    }
                    if p_dict != old_p_dict:
                        patient_hisno.content.value = p_dict['hisno']
                        patient_name.value = p_dict['name']
                        old_p_dict = p_dict
                        if patient_hisno.visible == False:
                            toggle_func() # 切換函數，需要研究如何呼叫較適合
                        else:
                            patient_hisno.update()
                            patient_name.update()
                    else:
                        if state != 1: # 找過一樣的data
                            state = 1
                            auto.Logger.WriteLine(f"Same Patient Data", auto.ConsoleColor.Yellow)
                else:
                    if state != 0: # 找不到window frmSoap
                        state = 0
                        auto.Logger.WriteLine(f"No window frmSoap", auto.ConsoleColor.Red)
                        time.sleep(0.2)
            except:
                auto.Logger.WriteLine(f"Something wrong", auto.ConsoleColor.Red)
                time.sleep(0.2)


def set_O(text_input, location=0, replace=0):
    return set_text('o', text_input, location, replace)


def set_text(panel, text_input, location=0, replace=0) -> str:
    # panel = 's','o','p'
    # location=0 從頭寫入 | location=1 從尾寫入
    # replace=0 append | replace=1 取代原本的內容
    # 現在預設插入的訊息會換行
    # 門診系統解析換行是'\r\n'，如果只有\n會被忽視但仍可以被記錄 => 可以放入隱藏字元，不知道網頁版怎麼顯示?
    parameters = {
        's': ['PanelSubject', 'txtSoapSubject'],
        'o': ['PanelObject', 'txtSoapObject'],
        'p': ['PanelPlan', 'txtSoapPlan'],
    }
    panel = str(panel).lower()
    if panel not in parameters.keys():
        auto.Logger.WriteLine("Wrong panel in input_text",auto.ConsoleColor.Red)
        return False

    with auto.UIAutomationInitializerInThread():
        window_soap = auto.WindowControl(searchDepth=1, AutomationId="frmSoap")
        # window_soap = search_window(window_soap)
        if not window_soap.Exists():
            auto.Logger.WriteLine("No window frmSoap", auto.ConsoleColor.Red)
            return "未找到SOAP視窗"
        else:
            edit_control = window_soap.PaneControl(searchDepth=1, AutomationId=parameters[panel][0]).EditControl(searchDepth=1, AutomationId=parameters[panel][1])
            if edit_control.Exists():
                text_original = edit_control.GetValuePattern().Value
                print(f"original text: {text_original}")
                if replace == 1:
                    text = text_input
                else:
                    if location == 0:  # 從文本頭部增加訊息
                        text = text_input+'\r\n'+text_original
                    elif location == 1:  # 從文本尾部增加訊息
                        text = text_original+'\r\n'+text_input
                try:
                    edit_control.GetValuePattern().SetValue(text)  # SetValue完成後游標會停在最前面的位置
                    # edit_control.SendKeys(text) # SendKeys完成後游標停在輸入完成的位置，輸入過程加上延遲有打字感，能直接使用換行(\n會自動變成\r\n)
                    auto.Logger.WriteLine(f"Input finished!", auto.ConsoleColor.Yellow)
                    return "成功帶入門診系統"
                except:
                    auto.Logger.WriteLine(f"Input failed!", auto.ConsoleColor.Red)
                    return "帶入門診系統失敗"
            else:
                auto.Logger.WriteLine(f"No edit control", auto.ConsoleColor.Red)
                return "No edit control"


        

def main(page: Page):
    #################################################### functions
    def test_db():
        SDES_form.db_connect()
        if SDES_form.db_conn == None:
            notify("資料庫連線失敗")
        else:
            notify("資料庫連線成功")

    def setWindowLeftMiddle():
        import ctypes
        user32 = ctypes.windll.user32
        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

        page.window_top = (height - page.height)/2
        page.window_left = 0
        page.update()

    def setWindowRightMiddle():
        import ctypes
        user32 = ctypes.windll.user32
        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

        page.window_top = (height - page.height)/2
        page.window_left = width - page.window_width
        page.update()

    def toggle_patient_data(e=None):
        patient_hisno.visible = not patient_hisno.visible
        patient_name.visible = not patient_name.visible
        patient_row_manual.visible = not patient_row_manual.visible
        patient_column.update()
        
    def notify(text: str, delay = 0.2):
        page.snack_bar.content = ft.Text(text)
        page.snack_bar.open = True
        page.update()
        time.sleep(delay)


    def setting_set_doctorid(e=None):
        AllForm.set_doctor_id(doctor_id_viewdoctorid.value)
        custom_title.value = f"病歷結構化輸入系統 [DOC:{doctor_id_viewdoctorid.value}]"
        doctor_id_viewall.value = doctor_id_viewdoctorid.value
        view_pop()
        test_db()

    
    def setting_set_all(e=None):
        AllForm.set_doctor_id(doctor_id_viewall.value)
        custom_title.value = f"病歷結構化輸入系統 [DOC:{doctor_id_viewall.value}]"
        SDES_form.DATE_MODE = date_mode.value
        SDES_form.HOST = host.value
        SDES_form.PORT = port.value
        SDES_form.DBNAME = dbname.value
        SDES_form.USER = user.value
        SDES_form.PASSWORD = psw.value
        # SDES_form.FONT_SIZE_FACTOR = int(font_size_slider.value) / 100
        view_pop()
        test_db()


    # TODO 需要重構
    doctor_id_viewdoctorid = ft.TextField(label="Doctor ID", hint_text="Please enter short code of doctor ID(EX:4123)", dense=True, height=45, on_submit=setting_set_doctorid)
    doctor_id_viewall = ft.TextField(label="Doctor ID", hint_text="Please enter short code of doctor ID(EX:4123)", dense=True, height=45, on_submit=setting_set_all)
    date_mode = ft.Dropdown(
        options=[
            ft.dropdown.Option(key=1, text='西元紀年'),
            ft.dropdown.Option(key=2, text='民國紀年'),
            ft.dropdown.Option(key=3, text='西元紀年(2位數)'),
        ],
        dense=True, height=45, content_padding = 10, value=1
    )
    host = ft.TextField(label="HOST IP", value=SDES_form.HOST, dense=True, height=45)
    port = ft.TextField(label="PORT", value=SDES_form.PORT, dense=True, height=45)
    dbname = ft.TextField(label="DB NAME", value=SDES_form.DBNAME, dense=True, height=45)
    user = ft.TextField(label="USER NAME", value=SDES_form.USER, dense=True, height=45)
    psw = ft.TextField(label="PASSWORD", value=SDES_form.PASSWORD ,password=True, dense=True, height=45)
    # TODO 無法透過更新數值調整元件大小 => 需要重繪
    # font_size_slider = ft.Slider(min=20, max=100, divisions=4, label="{value}%", value=(SDES_form.FONT_SIZE_FACTOR*100), expand=True)
    # font_size_row = ft.Row(
    #     controls=[
    #         ft.Text("Font Size:"),
    #         font_size_slider,
    #     ],
    # )
    

    def setting_show_doctorid(e=None):
        view_setting_doctorid = ft.View(
            route = "/setting",
            appbar=ft.AppBar( 
                title=ft.Row([
                        ft.WindowDragArea(ft.Container(ft.Text("系統設定", size=15, weight=ft.FontWeight.BOLD), alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                        ft.IconButton(ft.icons.CLOSE, on_click=lambda _: page.window_close(), icon_size = 25, tooltip = 'Close')
                    ]),
                center_title=False,
                bgcolor=ft.colors.SURFACE_VARIANT,
                # toolbar_height=30  # 目前無法改變回上一頁按鍵大小
            ),
            controls=[
                ft.Column(
                    controls=[
                        doctor_id_viewdoctorid,
                        ft.Row(
                            controls=[ft.ElevatedButton("設定", on_click=setting_set_doctorid, expand=True)]
                        ), 
                    ], 
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                authorship,
            ],
        )

        page.views.append(view_setting_doctorid)
        page.update()


    def setting_show_all(e=None):
        view_setting = ft.View(
            route = "/setting",
            appbar=ft.AppBar( 
                title=ft.Row([
                        ft.WindowDragArea(ft.Container(ft.Text("系統設定", size=15, weight=ft.FontWeight.BOLD), alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                        ft.IconButton(ft.icons.CLOSE, on_click=lambda _: page.window_close(), icon_size = 25, tooltip = 'Close')
                    ]),
                center_title=False,
                bgcolor=ft.colors.SURFACE_VARIANT,
                # toolbar_height=30  # 目前無法改變回上一頁按鍵大小
            ),
            controls=[
                ft.Column(
                    controls=[
                        doctor_id_viewall, date_mode, host, port, dbname, user, psw, 
                        # font_size_row,
                        ft.Row(
                            controls=[ft.ElevatedButton("設定", on_click=setting_set_all, expand=True)]
                        ),
                    ], 
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                authorship
            ],
        )

        page.views.append(view_setting)
        page.update()
    

    def on_keyboard(e: ft.KeyboardEvent): # 支援組合鍵快捷
        if e.alt and e.key == 'Q':
            save_opd_db(e)
        elif e.alt and e.key == 'A':
            AllForm.data_clear()
        elif e.alt and e.key == 'W':
            save_db(e)
        elif e.alt and e.key == 'S':
            load_db_one(e)
    
    # def route_change(route):
    #     page.views.clear()
    #     page.views.append(
    #         ft.View(
    #             "/",
    #             [
    #                 ft.AppBar(title=ft.Text("Flet app"), bgcolor=ft.colors.SURFACE_VARIANT),
    #                 ft.ElevatedButton("Visit Store", on_click=lambda _: page.go("/store")),
    #             ],
    #         )
    #     )
    #     if page.route == "/store":
    #         page.views.append(
    #             ft.View(
    #                 "/store",
    #                 [
    #                     ft.AppBar(title=ft.Text("Store"), bgcolor=ft.colors.SURFACE_VARIANT),
    #                     ft.ElevatedButton("Go Home", on_click=lambda _: page.go("/")),
    #                 ],
    #             )
    #         )
    #     page.update()

    def view_pop(e=None):
        page.views.pop()
        page.update()

    #################################################### Window settings
    # page.show_semantics_debugger = True # for testing
    page.title = "Structured Data Entry System"
    page.window_width = 450
    page.window_height = 700
    page.window_resizable = True  # window is not resizable
    # page.window_always_on_top = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.spacing = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    # page.window_title_bar_hidden = True
    page.scroll = ft.ScrollMode.AUTO
    page.on_keyboard_event = on_keyboard    
    page.theme_mode = 'LIGHT'
    
    # Appbar => 頂部工作列
    page.window_title_bar_hidden = True
    page.window_title_bar_buttons_hidden = True
    custom_title = ft.Text("病歷結構化輸入系統 [尚未輸入醫師ID]", size=15, weight=ft.FontWeight.BOLD)
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.DOUBLE_ARROW),
        leading_width=20,
        title=ft.Row([
                ft.WindowDragArea(ft.Container(custom_title, alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                ft.IconButton(ft.icons.SETTINGS, on_click= setting_show_all, icon_size = 20, tooltip = 'Setting'),
                ft.IconButton(ft.icons.CLOSE, on_click=lambda _: page.window_close(), icon_size = 20, tooltip = 'Close')
            ]),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        toolbar_height=30,
    )
    
    # Snackbar => 底部欄位通知
    page.snack_bar = ft.SnackBar(
        content=ft.Text("系統通知"),
    )
    setWindowRightMiddle()

    # page.on_route_change = route_change
    page.on_view_pop = view_pop # 點擊改變view後自動產生的回上一頁按鈕
    # page.go(page.route)

    #################################################### Contents
    ########################## patient infomation
    patient_hisno_manual = ft.TextField(
        label="病歷號", 
        hint_text="請手動輸入病歷號",
        border=ft.InputBorder.UNDERLINE,
        filled=True,
        width=300,
    )
    patient_row_manual = ft.Row(
        controls=[
            patient_hisno_manual, 
            ft.IconButton(
                icon=ft.icons.SETTINGS_BACKUP_RESTORE,
                tooltip='回到自動擷取模式',
                on_click=toggle_patient_data,
            )
        ], 
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
        visible=False,
    )
    patient_hisno = ft.TextButton(
        content= ft.Text("擷取病歷號", style=ft.TextThemeStyle.HEADLINE_MEDIUM, text_align='center'),
        style=ft.ButtonStyle(
            padding=0
        ),
        tooltip = "點擊編輯病歷號",
        on_click=toggle_patient_data,
        visible=True
        # disabled=True,
        # on_hover=
    )
    patient_name = ft.Text("擷取病人姓名", style=ft.TextThemeStyle.HEADLINE_MEDIUM, text_align='center', visible=True)
    patient_column = ft.Column(
        controls=[
            patient_row_manual, 
            patient_hisno,
            patient_name
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    ########################## tab merge
    AllForm = SDES_form.forms
    tabs = ft.Tabs(
        selected_index = 0, # index從0開始
        animation_duration = 250,
        tabs = AllForm.form_list,
        expand = False,
        height = 435,
    )
    tabview = ft.Column( # 加上裝飾divider的tabs
        controls=[
            ft.Divider(height=0, thickness=3),
            tabs,
            ft.Divider(height=0, thickness=3),
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.START
    )
    
    ########################## submit functions

    def patient_data_check() -> dict:
        return_dict = {
            'patient_hisno': None,
            'patient_name': None,
        }
        if patient_hisno.visible == False: # 手動輸入病人資訊
            _patient_hisno = str(patient_hisno_manual.value).strip()
            if _patient_hisno =='':
                notify("無法取得病人病歷號")
                return False
            else:
                return_dict['patient_hisno'] = _patient_hisno
        else: # 病人資訊自動模式
            _patient_hisno = patient_hisno.content.value
            _patient_name = patient_name.value
            if _patient_hisno == '擷取病歷號':
                notify("無法取得病人病歷號")
                return False
            else:
                return_dict['patient_hisno'] = _patient_hisno
                return_dict['patient_name'] = _patient_name
        return return_dict

    def load_db_one(e):
        patient = patient_data_check()
        if patient != False:
            res = AllForm.db_load_one(patient_hisno=patient['patient_hisno'], tab_index=tabs.selected_index)
            if res ==  None:
                notify("資料庫為空")
            elif res == False:
                notify("讀取資料失敗")
            elif res == True:
                notify("讀取資料成功")
                # notify成功讀取 => 已經有display通知?

    
    def save_db(e):
        patient = patient_data_check()
        if patient != False:
            try:
                AllForm.db_save(**patient) # 傳入{'patient_hisno':..., 'patient_name':...,}
                notify("完成資料寫入資料庫")
                AllForm.data_clear()
            except Exception as e:
                notify("資料寫入資料庫失敗")


    def save_opd_db(e):
        patient = patient_data_check()
        if patient != False:
            try:
                AllForm.db_save(**patient) # 傳入{'patient_hisno':..., 'patient_name':...,}
                notify("完成資料寫入資料庫")
            except Exception as e:
                notify("資料寫入資料庫失敗")

            text = AllForm.data_opdformat()
            try:
                set_O(text)
                notify("完成資料寫入門診系統")
                AllForm.data_clear()
            except Exception as e:
                notify("資料寫入門診系統失敗")


    ########################## submit
    submit = ft.Column([
        ft.Row(
            controls=[
                ft.FilledTonalButton(
                    text = "帶回門診(Q)",
                    height = 30, 
                    icon=ft.icons.ARROW_BACK, 
                    expand=True, 
                    on_click = save_opd_db
                ),
                ft.OutlinedButton(
                    text = "儲存資料庫(W)",
                    height = 30,
                    icon=ft.icons.ARROW_CIRCLE_DOWN_ROUNDED,
                    expand=True,
                    on_click = save_db
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        ft.Row(
            controls=[
                ft.OutlinedButton(
                    text = "清除全表格(A)",
                    height = 30,
                    style=ft.ButtonStyle(
                        color={
                            ft.MaterialState.DEFAULT: ft.colors.RED,
                        },
                    ),
                    icon=ft.icons.DELETE_FOREVER_OUTLINED,  
                    icon_color='red', 
                    expand=True,
                    on_click = AllForm.data_clear
                ),
                ft.OutlinedButton(
                    text = "讀取資料庫(S)",
                    height = 30,
                    icon=ft.icons.ARROW_CIRCLE_UP_ROUNDED,
                    expand=True,
                    on_click = load_db_one
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    ])
    authorship = ft.Row(
        controls = [ft.Text("ZMH © 2023", style=ft.TextThemeStyle.BODY_SMALL, weight=ft.FontWeight.BOLD)],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    #################################################### Final
    page.add(
         patient_column,
         tabview,
         submit,
    )
    setting_show_doctorid()
    #################################################### Other functions
    patient_data_autoset(patient_hisno, patient_name, toggle_func=toggle_patient_data) # 這些函數似乎會被開一個thread執行，所以不會阻塞
    
ft.app(target=main)
SDES_form.db_close()
print(f"DB closing..")