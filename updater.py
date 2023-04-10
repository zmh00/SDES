import requests
import os

# 輸入GitHub用戶名和存儲庫名稱
username = "zmh00"
repository = "SDES"
target_name = "SDES_main.exe"

# 發送GET請求獲取最新的發布版本
url = f"https://api.github.com/repos/{username}/{repository}/releases/latest"
response = requests.get(url)

# 確認請求成功
if response.status_code == requests.codes.ok:
    target_url = ''
    assets = response.json()['assets']
    for asset in assets:
        if asset['name'] == target_name:
            target_url = asset['browser_download_url']
            break
    
    # 發送GET請求獲取檔案內容
    response = requests.get(target_url)

    # 確認請求成功
    if response.status_code == requests.codes.ok:
        # 將內容寫入檔案中
        with open(target_name, "wb") as f:
            f.write(response.content)
        print(f"已將檔案下載至 {target_name}。")
    else:
        # 請求失敗時輸出錯誤訊息
        print(f"請求失敗，HTTP代碼：{response.status_code}")
else:
    # 請求失敗時輸出錯誤訊息
    print(f"請求失敗，HTTP代碼：{response.status_code}")

os.system("pause")