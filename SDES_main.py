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


def setWindowLeftMiddle(page: Page):
    import ctypes
    user32 = ctypes.windll.user32
    width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    page.window_top = (height - page.height)/2
    page.window_left = 0
    page.update()


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
    
    # def save(e):
    #     # TODO 存入資料庫
    #     notify("已存入資料庫")


    # def save_opd(e):
    #     # 把測量值的文字組出來
    #     # TODO 重寫
    #     final_text = ''
    #     for i in ctrl_basic:
    #         text = i.format_text()
    #         if text != '':
    #             if final_text == '':
    #                 final_text = text
    #             else:
    #                 final_text = final_text + '\r\n' + text
    #     print(f"final_text: {final_text}")
    #     text = set_O(final_text)
    #     notify(text=text)
    #     save(e)

    def page_resize(e):
        print("New page size:", page.window_width, page.window_height)

    # def reset(e):
    #     tabs.selected_index = 0
    #     page.update()

    # def on_keyboard(e: ft.KeyboardEvent): # 支援組合鍵快捷
    #     if e.alt and e.key == 'D':
    #         reset_basic(e)
    #     elif e.alt and e.key == 'S':
    #         save(e)
    #     elif e.alt and e.key == 'A':
    #         save_opd(e)
    #     elif e.alt and e.key == 'F':
    #         pass
    
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
    # page.on_keyboard_event = on_keyboard    
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
    AllForm = SDES_form.forms
    tabs = ft.Tabs(
        selected_index = 2,
        animation_duration = 250,
        tabs = AllForm.form_list,
        expand = False,
        height = 420,
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
            ft.FilledTonalButton("帶回門診", icon=ft.icons.ARROW_BACK, expand=True, on_click=AllForm.data_format()),
            ft.OutlinedButton("儲存",icon=ft.icons.ARROW_CIRCLE_DOWN_ROUNDED, expand=True, on_click=AllForm.db_save()),
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
                on_click = AllForm.data_clear()
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