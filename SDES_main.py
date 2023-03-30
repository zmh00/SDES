import flet as ft
from flet import Page
import datetime
# import bot_gui
import time
import subprocess
import uiautomation as auto
from typing import Union
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


def get_patient_data(patient_hisno: ft.TextButton, patient_name: ft.Text):
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
                        patient_hisno.update()
                        patient_name.update()
                        old_p_dict = p_dict
                    else:
                        if state != 1:
                            state = 1
                            auto.Logger.WriteLine(f"Same Patient Data", auto.ConsoleColor.Yellow)
                else:
                    if state != 0:
                        state = 0
                        auto.Logger.WriteLine(f"No window frmSoap", auto.ConsoleColor.Red)
                        time.sleep(0.2)
            except:
                auto.Logger.WriteLine(f"Something wrong", auto.ConsoleColor.Red)
                time.sleep(0.2)

# FIXME
# def search_window(window, retry=5, topmost=False):  
#     '''
#     找尋傳入的window物件重覆retry次, 找到後會將其取得focus和可以選擇是否topmost, 若找不到會常識判斷其process有沒有responding
#     retry<0: 無限等待 => 等待OPD系統開啟用
#     '''
#     # TODO 可以加上判斷物件是否IsEnabled => 這樣可以防止雖然找得到視窗或物件但其實無法對其操作
#     _retry = retry
#     try:
#         while retry != 0:
#             if window.Exists():
#                 auto.Logger.WriteLine(
#                     f"Window found: {window.GetSearchPropertiesStr()}", auto.ConsoleColor.Yellow)
#                 window.SetActive()  # 這有甚麼用??
#                 window.SetTopmost(True)
#                 if topmost is False:
#                     window.SetTopmost(False)
#                 window.SetFocus()
#                 return window
#             else:
#                 if process_responding():
#                     auto.Logger.WriteLine(f"Window not found: {window.GetSearchPropertiesStr()}", auto.ConsoleColor.Red)
#                     retry = retry-1
#                 else:
#                     auto.Logger.WriteLine(f"Process not responding", auto.ConsoleColor.Red)
#                 time.sleep(1)
#         auto.Logger.WriteLine(f"Window not found(after {_retry} times): {window.GetSearchPropertiesStr()}", auto.ConsoleColor.Red)
#         captureimage()
#         return None
#     except Exception as err:
#         auto.Logger.WriteLine(f"Something wrong unexpected: {window.GetSearchPropertiesStr()}", auto.ConsoleColor.Red)
#         print(err) # TODO remove in the future
#         captureimage()
#         return search_window(window, retry=retry) # 目前使用遞迴處理 => 會無窮迴圈後續要考慮新方式 # TODO


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


def setWindowRightMiddle(page: Page):
    import ctypes
    user32 = ctypes.windll.user32
    width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    page.window_top = (height - page.height)/2
    page.window_left = width - page.window_width
    page.update()


def main(page: Page):
    #################################################### functions
    def toggle_patient_data(e):
        patient_hisno.visible = not patient_hisno.visible
        patient_name.visible = not patient_name.visible
        patient_row_manual.visible = not patient_row_manual.visible
        patient_column.update()
        
    
    def notify(text: str):
        page.snack_bar.content = ft.Text(text)
        page.snack_bar.open = True
        page.update()
        time.sleep(0.7)
    
    def save(e):
        # TODO 存入資料庫
        notify("已存入資料庫")


    def save_opd(e):
        # 把測量值的文字組出來
        # TODO 重寫
        final_text = ''
        for i in ctrl_basic:
            text = i.format_text()
            if text != '':
                if final_text == '':
                    final_text = text
                else:
                    final_text = final_text + '\r\n' + text
        print(f"final_text: {final_text}")
        text = set_O(final_text)
        notify(text=text)
        save(e)


    def page_resize(e):
        print("New page size:", page.window_width, page.window_height)
        cas.update()
        page.update()


    def reset(e):
        tabs.selected_index = 0
        page.update()


    def on_keyboard(e: ft.KeyboardEvent): # 支援組合鍵快捷
        if e.alt and e.key == 'D':
            reset_basic(e)
        elif e.alt and e.key == 'S':
            save(e)
        elif e.alt and e.key == 'A':
            save_opd(e)
        elif e.alt and e.key == 'F':
            pass
    
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
    page.scroll = "adaptive"
    page.on_keyboard_event = on_keyboard    
    # page.theme_mode = 'dark'
    
    # 預設snackbar => 底部欄位通知
    page.snack_bar = ft.SnackBar(
        content=ft.Text("系統通知"),
    )

    page.on_resize = page_resize
    setWindowRightMiddle(page=page)
    page.update()

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
        content= ft.Text("擷取病歷號", style=ft.TextThemeStyle.DISPLAY_MEDIUM, text_align='center'),
        style=ft.ButtonStyle(
            padding=0
        ),
        tooltip = "點擊編輯病歷號",
        on_click=toggle_patient_data,
        visible=True
        # disabled=True,
        # on_hover=
    )
    patient_name = ft.Text("擷取病人姓名", style=ft.TextThemeStyle.DISPLAY_MEDIUM, text_align='center', visible=True)
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
    tabs = ft.Tabs(
        selected_index=2,
        animation_duration=250,
        tabs=SDES_form.forms(),
        expand=False,
        height=420,
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

    ########################## submit
    submit = ft.Row(
        controls=[
            ft.FilledTonalButton("帶回門診", icon=ft.icons.ARROW_BACK, expand=True, on_click=save_opd),
            ft.OutlinedButton("儲存",icon=ft.icons.ARROW_CIRCLE_DOWN_ROUNDED, expand=True, on_click=save),
            ft.OutlinedButton(
                "清除表格",
                style=ft.ButtonStyle(
                    color={
                        ft.MaterialState.DEFAULT: ft.colors.RED,
                    },
                ),
                icon=ft.icons.DELETE_FOREVER_OUTLINED, 
                icon_color='red', 
                expand=True,
                on_click = reset
            ),
            ft.OutlinedButton("測試",icon=ft.icons.ARROW_CIRCLE_DOWN_ROUNDED, expand=True, on_click=None),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )
    #################################################### Final
    page.add(
         patient_column,
         tabview,
         submit,
    )
    #################################################### Other functions
    get_patient_data(patient_hisno, patient_name) # 這些函數似乎會被開一個thread執行，所以不會阻塞

ft.app(target=main)