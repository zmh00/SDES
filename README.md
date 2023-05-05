# SDES (Structured Data Entry System)
- Introduction: a SDES build with python backend, postgresql database, and flutter(flet) GUI
- Environment: 
  - Windows 7 above
  - Python 3.8.10
- Features:
  - 對接醫院門診系統，自動擷取病人資訊與結構化資訊帶入
  - 對接資料庫系統，輸入資料結構化存入深化後續研究價值
  - 提升使用者體驗降低使用門檻(快捷鍵支援、減少操作步驟)
  - 自更新架構讓診間電腦同步
---
# TODO
- [ ]  增加form內部的divider?
- [ ]  目前migrate功能不會偵測型態變更
- [ ]  欄位編輯 ⇒ 手動新增欄位
---
- Prerequisite python package: 
  ```sh
  pip install psycopg2, flet, uiautomation
  ``` 
- Build up postgresql server



