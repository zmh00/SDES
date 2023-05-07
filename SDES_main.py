from typing import Any, List, Optional, Union
import flet as ft
from flet import Page
import datetime
import time
# import subprocess
import uiautomation as auto
# forms listed in SDES_form
import SDES_form
import updater
import atexit

# packing command
# flet pack .\SDES_main.py --name SDES --icon .\icon.png 

# OPD system process name
PROCESS_NAME = 'vghtpe.dcr.win.exe'

# Settings of updater
OWNER = 'zmh00'
REPO = 'SDES'
VERSION_TAG = 'v1.4.4'
TARGET_FILE = 'SDES'
ALERT_TITLE = 'SDES Updater'


PatientDataClass = SDES_form.PatientData
patient_previous_data = PatientDataClass(hisno=None)
patient_now_data = PatientDataClass(hisno=None)


def patient_data_from_opd(patient_hisno: ft.TextButton, patient_name: ft.Text, patient_hisno_manual: ft.TextField, toggle_func, load_func, dlg_overwrite): 
    global patient_now_data, patient_previous_data
    state = -1
    with auto.UIAutomationInitializerInThread():
        while(1):
            try:
                window_soap = auto.WindowControl(searchDepth=1, AutomationId="frmSoap")
                if window_soap.Exists():
                    t = window_soap.Name.split()
                    
                    patient_now_data = PatientDataClass(hisno=t[0], name=t[1], birthday=t[4][1:-1], age=t[3][:2])
                    # {
                    #     SDES_form.COLUMN_PATIENT_HISNO: t[0],
                    #     SDES_form.COLUMN_PATIENT_NAME: t[1],
                    #     SDES_form.COLUMN_PATIENT_BIRTHDAY: t[4][1:-1],
                    #     SDES_form.COLUMN_PATIENT_AGE: t[3][:2],
                    #     # 'id': t[6], 
                    #     # 'charge': t[5],
                    # }

                    if patient_now_data != patient_previous_data: # 找到新病人

                        # 更新資料顯示 => 影響後續函數獲取病人資訊 patient_data
                        patient_hisno.content.value = patient_now_data.hisno
                        patient_name.value = patient_now_data.name
                        if patient_hisno.visible == False:
                            toggle_func() # 切換顯示函數
                            patient_hisno_manual.value = '' # 清空manual的資料
                        else:
                            patient_hisno.update()
                            patient_name.update()

                        if dlg_overwrite.open == False: # 若目前有未存警告就暫停load新資料 # FIXME
                            # 讀取資料新病人資料 => 若有未儲存資料跳警告處理
                            load_func()  # 讀取此病人單一或全部表單
                            
                            print(f"patient_data_from_opd::patient_previous_data = {patient_previous_data.hisno}; patient_now_data = {patient_now_data.hisno}") # FIXME

                            # # 寫入舊病人資料 => 會在load_db內處理好
                            # patient_previous_data = patient_now_data

                    else:
                        if state != 1: # 找過一樣的data
                            state = 1
                            auto.Logger.WriteLine(f"Same Patient Data:{patient_now_data.hisno}||{patient_now_data.name}", auto.ConsoleColor.Yellow)
                else:
                    if state != 0: # 找不到window frmSoap
                        state = 0
                        auto.Logger.WriteLine(f"No window frmSoap", auto.ConsoleColor.Red)
                        time.sleep(0.2)
            except Exception as e:
                auto.Logger.WriteLine(f"Something wrong:{e}", auto.ConsoleColor.Red)
                time.sleep(0.2)


def set_S(text_input, location, replace):
    return set_text('s', text_input, location, replace)

def set_O(text_input, location, replace):
    return set_text('o', text_input, location, replace)

def set_P(text_input, location, replace):
    return set_text('p', text_input, location, replace)

def set_text(panel, text_input:str, location, replace) -> str:
    '''
    panel = 's','o','p'
    location=0 從頭寫入 | location=1 從尾寫入
    replace=0 append | replace=1 取代原本的內容
    現在預設插入的訊息會換行
    門診系統解析換行是'\r\n'，如果只有\n會被忽視但仍可以被記錄 => 可以放入隱藏字元，不知道網頁版怎麼顯示?
    '''
    parameters = {
        's': ['PanelSubject', 'txtSoapSubject'],
        'o': ['PanelObject', 'txtSoapObject'],
        'p': ['PanelPlan', 'txtSoapPlan'],
    }
    panel = str(panel).lower()
    if panel not in parameters.keys():
        auto.Logger.WriteLine("Wrong panel in input_text",auto.ConsoleColor.Red)
        return False
    
    text_input = text_input.replace('\n','\r\n') # 原本換行符號進入門診系統需要更改

    with auto.UIAutomationInitializerInThread():
        window_soap = auto.WindowControl(searchDepth=1, AutomationId="frmSoap")
        if not window_soap.Exists():
            auto.Logger.WriteLine("No window frmSoap", auto.ConsoleColor.Red)
            raise Exception("未找到SOAP視窗")
        else:
            edit_control = window_soap.PaneControl(searchDepth=1, AutomationId=parameters[panel][0]).EditControl(searchDepth=1, AutomationId=parameters[panel][1])
            if edit_control.Exists():
                text_original = edit_control.GetValuePattern().Value
                
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
                    raise Exception("帶入門診系統失敗")
            else:
                auto.Logger.WriteLine(f"No edit control", auto.ConsoleColor.Red)
                raise Exception("No edit control")


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
        '''
        Switch between automatic and manual patient data retrieval
        '''
        patient_hisno.visible = not patient_hisno.visible
        patient_name.visible = not patient_name.visible
        patient_row_manual.visible = not patient_row_manual.visible
        patient_column.update()
        
    def notify(text: str, delay = 0.2):
        '''
        Notify message with snack_bar at bottom
        '''
        page.snack_bar.content = ft.Text(text)
        page.snack_bar.open = True
        page.update()
        time.sleep(delay)

    def setting_form_submit(e=None):
        '''
        The on_click event of apply settings button in setting_form
        Set the doctorid and forms selection. Used for initial login.
        '''
        # 設定doctor id
        if setting_form_doctorid.value.strip() != '':
            SDES_form.forms.set_doctor_id(setting_form_doctorid.value)
            custom_title.value = f"[DOC:{setting_form_doctorid.value}]"
            setting_connection_doctorid.value = setting_form_doctorid.value
        
        # 將被選到的forms加入
        forms_selected = []
        for control in setting_form_checkbox.controls:
            if control.value == True:
                forms_selected.append(control.label)
        SDES_form.forms.set_form_list_selected(forms_selected)
        tabs.tabs = SDES_form.forms.form_list_selected
        
        # 設定日期形式
        SDES_form.FORMAT_MODE = int(setting_form_formatmode.value)

        view_pop()
        test_db()

    def setting_connection_submit(e=None):
        '''
        The on_click event of apply settings button in setting_connection
        Set the connection parameters
        '''
        # 設定doctor id
        if setting_connection_doctorid.value.strip() != '':
            SDES_form.forms.set_doctor_id(setting_connection_doctorid.value)
            custom_title.value = f"[DOC:{setting_connection_doctorid.value}]"
            setting_form_doctorid.value = setting_connection_doctorid.value
        
        # 設定連線參數
        SDES_form.HOST = setting_connection_host.value
        SDES_form.PORT = setting_connection_port.value
        SDES_form.DBNAME = setting_connection_dbname.value
        SDES_form.USER = setting_connection_user.value
        SDES_form.PASSWORD = setting_connection_psw.value
        # SDES_form.FONT_SIZE_FACTOR = int(font_size_slider.value) / 100

        view_pop()
        test_db()

    def setting_form_checkall(e=None):
        '''
        勾選或取消所有forms時會一次設定其他checkbox
        '''
        if setting_form_allbox.value == True:
            for control in setting_form_checkbox.controls:
                control.value = True
            setting_form_checkbox.update()
        else:
            for control in setting_form_checkbox.controls:
                control.value = False
            setting_form_checkbox.update()

    def setting_form_uncheckall(e=None):
        '''
        有任一checkbox uncheck要uncheck activate all
        '''
        if setting_form_allbox.value == True and e.control.value == False:
            setting_form_allbox.value = False
            setting_form_allbox.update()

    def setting_connection_db_migrate(e=None):
        '''
        The on_click event of migration database button in setting_connection
        '''
        SDES_form.db_connect()
        res_string = SDES_form.forms.db_migrate()
        page.dialog = dlg_migration
        dlg_migration.content.value = res_string
        dlg_migration.open = True
        page.update()

    def on_change_patient_hisno_manual(e=None):
        pass
        # SDES_form.forms.reset_db_row_id()
        # SDES_form.forms.data_clear() # UX不好
    
    def on_submit_patient_hisno_manual(e=None):
        load_db()

    
    def dlg_overwrite_show(e=None):
        page.dialog = dlg_overwrite
        text = f"病歷號: {patient_previous_data.hisno}\n"
        name = patient_previous_data.data_dict.get(SDES_form.COLUMN_PATIENT_NAME, None)
        if name != None and name != '':
            text = text + f"姓名: {name}\n"
        
        dlg_overwrite.content.value = f"如何處理上位病人修改未儲存資料?\n{text}"
        dlg_overwrite.open = True
        page.update()


    def dlg_overwrite_hide(e=None):
        dlg_overwrite.open = False
        page.update()


    def dlg_overwrite_ignore(e=None):
        dlg_overwrite_hide()
        SDES_form.forms.data_clear() # 把資料清掉
        load_db() # 前面load_db因為non-blocking先return等這邊決定完繼續


    def dlg_overwrite_save(e=None):
        dlg_overwrite_hide()
        save_db(patient=patient_previous_data) # 儲存+清空表單
        load_db() # 前面load_db因為non-blocking先return等這邊決定完繼續load


    # dialog overwrite
    dlg_overwrite = ft.AlertDialog(
        title=ft.Text("資料未儲存"),
        content=ft.Text(),
        modal=False,
        actions=[
            ft.TextButton("寫入資料庫", on_click=dlg_overwrite_save),
            ft.TextButton("捨棄資料", on_click=dlg_overwrite_ignore),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    # dialog migration
    dlg_migration = ft.AlertDialog(
        title=ft.Text("Migration response"),
        content=ft.Text(),
        on_dismiss=lambda e: print("Dialog dismissed!")
    )

    # 系統設定
    setting_form_allbox = ft.Checkbox(label="Activate ALL Forms", value=False, height=25, width=200, on_change=setting_form_checkall)
    setting_form_checkbox = ft.Row(
        controls=[ft.Checkbox(label=form.label, value=False, height=25, width=200, on_change=setting_form_uncheckall) for form in SDES_form.forms.form_list_original],
        wrap=True
    )
    setting_form_doctorid = ft.TextField(label="Doctor ID", hint_text="Please enter short code of doctor ID(EX:4123)", dense=True, height=45, on_submit=setting_form_submit, autofocus=True)
    setting_form_formatmode = ft.Dropdown(
        options=[
            ft.dropdown.Option(key=-1, text='無任何日期'),
            ft.dropdown.Option(key=0, text='區塊模式'),
            ft.dropdown.Option(key=1, text='西元紀年'),
            ft.dropdown.Option(key=2, text='民國紀年'),
            ft.dropdown.Option(key=3, text='西元紀年(2位數)'),
        ],
        dense=True, height=45, content_padding = 10, value=0
    )
    
    setting_connection_doctorid = ft.TextField(label="Doctor ID", hint_text="Please enter short code of doctor ID(EX:4123)", dense=True, height=45, on_submit=setting_connection_submit, autofocus=True)
    setting_connection_host = ft.TextField(label="HOST IP", value=SDES_form.HOST, dense=True, height=45)
    setting_connection_port = ft.TextField(label="PORT", value=SDES_form.PORT, dense=True, height=45)
    setting_connection_dbname = ft.TextField(label="DB NAME", value=SDES_form.DBNAME, dense=True, height=45)
    setting_connection_user = ft.TextField(label="USER NAME", value=SDES_form.USER, dense=True, height=45)
    setting_connection_psw = ft.TextField(label="PASSWORD", value=SDES_form.PASSWORD ,password=True, dense=True, height=45)
    
    setting_connection_savebutton = ft.Switch(label="Save ALL forms", value=True, expand=True)
    setting_connection_loadbutton = ft.Switch(label="Load ALL forms", value=True, expand=True)

    authorship = ft.Row(
        controls = [ft.Text("ZMH © 2023", style=ft.TextThemeStyle.BODY_SMALL, weight=ft.FontWeight.BOLD)],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # TODO 無法透過更新數值調整元件大小 => 需要重繪
    # font_size_slider = ft.Slider(min=20, max=100, divisions=4, label="{value}%", value=(SDES_form.FONT_SIZE_FACTOR*100), expand=True)
    # font_size_row = ft.Row(
    #     controls=[
    #         ft.Text("Font Size:"),
    #         font_size_slider,
    #     ],
    # )

    def setting_form_show(e=None):
        '''
        Show Settings: doctorid + forms selection
        '''
        setting_form_allbox.on_change = setting_form_checkall
        for control in setting_form_checkbox.controls:
            control.on_change = setting_form_uncheckall
            
        view_setting_form = ft.View(
            route = "/setting_initial",
            appbar=ft.AppBar( 
                title=ft.Row([
                        ft.WindowDragArea(ft.Container(ft.Text("Settings", size=15, weight=ft.FontWeight.BOLD), alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                        ft.IconButton(ft.icons.CLOSE, on_click=lambda _: page.window_close(), icon_size = 25, tooltip = 'Close')
                    ]),
                center_title=False,
                bgcolor=ft.colors.SURFACE_VARIANT,
                # toolbar_height=30  # 目前無法改變回上一頁按鍵大小
            ),
            controls=[
                ft.Column(
                    controls=[
                        setting_form_doctorid,
                        setting_form_formatmode,
                        setting_form_allbox,
                        setting_form_checkbox,
                        ft.Row(
                            controls=[ft.ElevatedButton("Apply Settings", on_click=setting_form_submit, expand=True)]
                        ), 
                    ], 
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                authorship,
            ],
        )
        page.views.append(view_setting_form)
        page.update()


    def setting_connection_show(e=None):
        '''
        Show Settings: connection + button event + migration
        '''
        view_setting_connection = ft.View(
            route = "/setting_connection",
            appbar=ft.AppBar( 
                title=ft.Row([
                        ft.WindowDragArea(ft.Container(ft.Text("Settings: Connection", size=15, weight=ft.FontWeight.BOLD), alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                        ft.IconButton(ft.icons.CLOSE, on_click=lambda _: page.window_close(), icon_size = 25, tooltip = 'Close')
                    ]),
                center_title=False,
                bgcolor=ft.colors.SURFACE_VARIANT,
                # toolbar_height=30  # 目前無法改變回上一頁按鍵大小
            ),
            controls=[
                ft.Column(
                    controls=[
                        setting_connection_doctorid, setting_connection_host, setting_connection_port, setting_connection_dbname, setting_connection_user, setting_connection_psw,
                        ft.Row(
                            controls=[setting_connection_loadbutton, setting_connection_savebutton]
                        ),
                        # font_size_row,
                        ft.Row(
                            controls=[ft.ElevatedButton("Apply Settings", on_click=setting_connection_submit, expand=True)]
                        ),
                        ft.Row(
                            controls=[ft.ElevatedButton("Migrate Database", on_click=setting_connection_db_migrate, expand=True)]
                        ),
                    ], 
                    expand=True,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                authorship
            ],
        )
        page.views.append(view_setting_connection)
        page.update()
    

    def on_keyboard(e: ft.KeyboardEvent): # 支援組合鍵快捷
        if e.alt and e.key == 'Q':
            save_opd_db(e)
        elif e.alt and e.key == 'A':
            SDES_form.forms.data_clear()
        elif e.alt and e.key == 'W':
            save_db(e)
        elif e.alt and e.key == 'S':
            load_db(e)
    
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
    page.title = "結構化輸入系統"
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
    custom_title = ft.Text("[未輸入醫師ID]", size=15, weight=ft.FontWeight.BOLD)
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.DOUBLE_ARROW),
        leading_width=10,
        title=ft.Row([
                ft.WindowDragArea(ft.Container(custom_title, alignment=ft.alignment.center_left, padding=ft.padding.only(bottom=3)), expand=True),
                ft.IconButton(ft.icons.TEXT_SNIPPET_OUTLINED, on_click= setting_form_show, icon_size = 20, tooltip = 'Forms'),
                ft.IconButton(ft.icons.SETTINGS, on_click= setting_connection_show, icon_size = 20, tooltip = 'Connection'),
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
        # on_change=on_change_patient_hisno_manual,
        on_submit=on_submit_patient_hisno_manual,
        # on_blur=on_change_patient_hisno_manual,
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
    
    patient_column = ft.Column( # Comprise all the patient information
        controls=[
            patient_row_manual, 
            patient_hisno,
            patient_name
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    ########################## tab merge
    tabs = ft.Tabs(
        selected_index = 0, # index從0開始
        animation_duration = 250,
        tabs = SDES_form.forms.form_list_selected,
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
        '''
        病患資料的再確認
        - 確認是否有資料(手動或自動)
        - 如果是手動輸入資料要放到 patient_now_dict
        '''
        global patient_now_data

        if patient_hisno.visible == False: # 手動模式
            _hisno = str(patient_hisno_manual.value).strip()
            if _hisno =='':
                notify("未輸入病人病歷號")
                return False
            else:
                if _hisno == patient_previous_data.hisno: # 舊的這樣才能保留前面的db_row_id等讀取過的資訊
                    patient_now_data = patient_previous_data
                else:  # 新的就可以隨意
                    patient_now_data = PatientDataClass(hisno=_hisno)

        else: # 自動模式 => 資料應該要在patient_data_from_opd設定好了
            _hisno = patient_hisno.content.value
            if _hisno == '擷取病歷號':
                notify("無法取得病人病歷號")
                return False
            elif _hisno != patient_now_data.hisno: # 目前自動擷取欄位和patient_now_dict內資料不同 => 如果出現需要debug
                SDES_form.logger.error("!!!!!!病人資訊異常!!!!!!") # FIXME
        
        return True


    def load_db(e=None):
        global patient_previous_data
        check = patient_data_check()
        if check != False:
            if setting_connection_loadbutton.value == False: # 讀取單一Form
                tab_index = tabs.selected_index
            else:
                tab_index = None
            
            if (patient_now_data != patient_previous_data) and SDES_form.forms.data_exist(tab_index=tab_index): # 有新病人+未儲存資料 => 跳警告
                if SDES_form.forms.db_values_dict(tab_index=tab_index) != patient_previous_data.db_loaded_dict: # 未儲存資料和該使用者上筆資料不同才跳警告 =>這邊會遇到取單一和取全部的問題
                    dlg_overwrite_show() # 選擇存資料或拋棄資料
                    return # 如果不return程序會繼續 => flet是non-blocking設計
            # else: # FIXME測試用
            #     print(f"load_db_else::patient_now_data:{patient_now_data.hisno}\npatient_previous_data:{patient_previous_data.hisno}\ndata_exist{SDES_form.forms.data_exist(tab_index=tab_index)}")
            
            SDES_form.forms.data_clear() # 不論load一或多個都應該清掉全部

            error_list, empty_list = SDES_form.forms.db_load(patient_data=patient_now_data, tab_index=tab_index) # 讀取db
            patient_previous_data = patient_now_data 
            
            if len(error_list) !=0: # 有失敗優先顯示
                notify(f"讀取資料失敗: {error_list}", delay=1.5)
            elif len(empty_list) !=0:
                notify(f"無資料可讀取: {empty_list}", delay=1.0)
            else:
                notify("讀取資料成功")
        

    
    def save_db(e=None, patient: PatientDataClass = None):
        '''
        存到資料庫 => 存完內含清除表單功能
        '''
        global patient_previous_data
        check = patient_data_check()
        if check != False: # 有patient資料
            if setting_connection_savebutton.value == False: # 存單一Form
                tab_index = tabs.selected_index
            else:
                tab_index = None
            try:
                if patient == None: # 如果沒有傳入patient參數預設使用patient_now_data
                    # if (patient_now_data != patient_previous_data) and SDES_form.forms.data_exist(tab_index=tab_index): # 為了解決如果讀取上一個病人資訊然後直接按寫入，應該要能insert一筆新的
                    #     SDES_form.forms.reset_db_row_id()
                    patient = patient_now_data

                error_list, empty_list = SDES_form.forms.db_save(patient_data=patient, tab_index=tab_index) # 儲存form 
                patient_previous_data = patient 
                if len(error_list) !=0:
                    notify(f"資料寫入資料庫失敗:{error_list}", delay=1.5)
                elif len(empty_list) !=0:
                    notify(f"無資料可寫入: {empty_list}", delay=1.0)
                else:
                    notify("資料寫入資料庫成功", delay=1.0)
            except Exception as e:
                SDES_form.logger.error(e)
                notify("資料寫入資料庫異常", delay=1.5)


    def save_opd_db(e=None):
        check = patient_data_check()
        if check != False:
            # save to opd
            format_dict = SDES_form.forms.data_opdformat()
            try:
                for region in format_dict:
                    if format_dict[region] != '':
                        set_text(panel=region, text_input=format_dict[region], location=0, replace=0)
                notify("完成資料寫入門診系統")
            except Exception as e:
                SDES_form.logger.error(e)
                notify("資料寫入門診系統失敗", delay=1.5)

        # 存入資料庫      
        save_db(patient = patient_now_data)


    def clear_forms(e=None):
        '''
        清除表格內容且重設(SDES_form.forms.reset_db_row_id()) => 讓新紀錄可以insertion
        '''
        global patient_now_data
        try:
            SDES_form.forms.data_clear()
            patient_now_data.db_row_id = {} # 讓資料可以變成insert? # FIXME
            notify("已清除所有表格內容且同一病人會創建新紀錄")
        except Exception as e:
            notify("清除表格異常", delay=1.5)


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
                    on_click = clear_forms
                ),
                ft.OutlinedButton(
                    text = "讀取資料庫(S)",
                    height = 30,
                    icon=ft.icons.ARROW_CIRCLE_UP_ROUNDED,
                    expand=True,
                    on_click = load_db
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    ])
    
    #################################################### Final
    page.add(
         patient_column,
         tabview,
         submit,
    )
    setting_form_show()
    #################################################### Other functions
    patient_data_from_opd(patient_hisno, patient_name, patient_hisno_manual, toggle_func=toggle_patient_data, load_func=load_db, dlg_overwrite=dlg_overwrite) # 這些函數會被開一個thread執行，所以不會阻塞


def close_db():
    if SDES_form.db_conn != None:
        SDES_form.db_close()
        SDES_form.logger.debug("DB closing..")
    SDES_form.logger.info("Program Terminated")


# 註冊當程式關閉前關閉DB連線
atexit.register(close_db)

# 確認是否為最新的版本
updater.ALERT_TITLE = ALERT_TITLE
is_latest = updater.updater_github(OWNER, REPO, TARGET_FILE, VERSION_TAG, mode='browser')
if is_latest==True:
    ft.app(target=main)