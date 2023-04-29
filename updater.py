import requests
import webbrowser
import ctypes # for notification dialog in windows, consider tkinter in cross-platform design

ALERT_TITLE = 'Warning'


def alert(windowtitle, windowcontent):
    '''Alert window displayed in Windows
    - windowtitle: title of the window
    - windowcontent: content of the window
    '''
    WS_EX_TOPMOST = 0x40000
    ctypes.windll.user32.MessageBoxExW(None, windowcontent, windowtitle, WS_EX_TOPMOST)


def updater_github(owner, repo, target_file: str, version_tag: str, mode):
    '''Update notification through comparison tag difference on Github release
    - owner: name of the owner of the repository
    - repo: name of the repository 
    - target_file: name for search in assets
    - version_tag: pass in the local version for comparison
    - mode: 'browser'|'direct'. browser means open the browser link and download by the user in order to avoid antiviral alarm; direct means download by requests directly.
    '''
    # latest_url: github release API(https://api.github.com/repos/{owner}/{repo}/releases/latest)
    latest_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    
    # TODO 將requests函式庫改成Python原生庫並獨立釋出
    try:
        res = requests.get(url=latest_url)
        if res.status_code == requests.codes.ok:
            res_json = res.json()
            latest_version_tag = res_json['tag_name']
            latest_assets = res_json['assets']
        else:
            alert(ALERT_TITLE, f"請求失敗，HTTP代碼：{res.status_code}")
            return False

        for asset in latest_assets:
            if target_file in asset['name']:
                browser_download_url = asset['browser_download_url']
                target_full_name = asset['name']
                break
        
        if version_tag < latest_version_tag: # check whether the local program is the latest with string comparison in python
            print("Not the latest vesion!")

            # open browser
            if mode == 'browser':
                # display a message box
                alert(ALERT_TITLE, "有新版的程式會透過瀏覽器下載")

                print("Browser downloading...")
                webbrowser.open(browser_download_url, new=2)

            # download by requests
            elif mode == 'direct':
                # display a message box
                alert(ALERT_TITLE, "有新版的程式直接下載於同一文件夾內(需等待片刻)")

                print("Direct downloading...")
                res = requests.get(browser_download_url)
                if res.status_code == requests.codes.ok:
                    filename, extension = target_full_name.split('.') # split the filename 
                    filename = f'{filename}({latest_version_tag}).{extension}' # reset the file name and add version tag
                    with open(filename, 'wb') as f:
                        f.write(res.content)
                    
                    # display a message box
                    alert(ALERT_TITLE, "已下載完成(於同一文件夾內)")

                else:
                    alert(ALERT_TITLE, f"請求失敗，HTTP代碼：{res.status_code}")
            return False
        else:
            print("Already the latest version!")
            return True
    except Exception as e:
        alert(ALERT_TITLE, f"Something wrong:{e}")
        return False
