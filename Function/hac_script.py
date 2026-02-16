# # Function/hac_script.py
# import pandas as pd
# import requests
# import re
# import json
#
#
# def get_base_url(env: str) -> str:
#     if env == "Dev":
#         return "https://ecomtest01.hkmpcl.com.hk/hac"
#     else:
#         return "https://www-nowaf.hkmpcl.com.hk/hac"
#
#
# def prepare_session(base_url: str, username: str, password: str):
#     """
#     Login + 取得 scripting CSRF。
#     成功: 回傳 (session, csrf_execute, None)
#     失敗: 回傳 (None, None, error_message)
#     """
#     session = requests.Session()
#     try:
#         # 1) 取得 login 頁面的 CSRF
#         login_page = session.get(f"{base_url}/")
#         csrf_login_match = re.search(
#             r'meta name="_csrf" content="([^"]+)"', login_page.text
#         )
#         if not csrf_login_match:
#             return None, None, "Login failed: cannot find CSRF token on login page."
#
#         csrf_login = csrf_login_match.group(1)
#
#         # 2) 帶帳密登入
#         login_data = {
#             "j_username": username,
#             "j_password": password,
#             "_csrf": csrf_login,
#         }
#         resp_login = session.post(f"{base_url}/j_spring_security_check", data=login_data)
#
#         # 登入失敗：還在 login 頁面
#         if "j_spring_security_check" in resp_login.text and "Username" in resp_login.text:
#             return None, None, "Login failed: wrong username or password (still on login page)."
#
#         # 3) 開 scripting console 拿執行用 CSRF
#         scripting_page = session.get(f"{base_url}/console/scripting/")
#         if "j_spring_security_check" in scripting_page.text:
#             return None, None, "Login failed: redirected back to login when opening scripting console."
#
#         csrf_execute_match = re.search(
#             r'meta name="_csrf" content="([^"]+)"', scripting_page.text
#         )
#         if not csrf_execute_match:
#             return None, None, "Cannot find CSRF token on scripting console page."
#
#         csrf_execute = csrf_execute_match.group(1)
#
#         return session, csrf_execute, None
#     except Exception as e:
#         return None, None, f"Login/CSRF failed: {e}"
#
#
# def execute_script(session, base_url: str, csrf_execute: str, script_text: str):
#     """
#     執行 Groovy script。
#     回傳 (ok: bool, message: str)
#     """
#     data = {
#         "commit": "true",
#         "scriptType": "groovy",
#         "script": script_text,
#     }
#     headers = {"X-CSRF-TOKEN": csrf_execute}
#
#     try:
#         resp = session.post(
#             f"{base_url}/console/scripting/execute",
#             data=data,
#             headers=headers,
#         )
#
#         # 如果被踢回 login 頁
#         if "j_spring_security_check" in resp.text and "<form" in resp.text:
#             return False, "Execute failed: got login page HTML (session expired or not logged in)."
#
#         # 嘗試當 JSON 解析
#         try:
#             data_json = resp.json()
#             return True, json.dumps(data_json, indent=2, ensure_ascii=False)
#         except ValueError:
#             # 不是 JSON，就視為錯誤文字
#             return False, resp.text
#     except Exception as e:
#         return False, str(e)
#
#
# # =============== PPP Excel / Script ===============
#
# def read_ppp_excel(path: str) -> pd.DataFrame:
#     """讀 PPP personal price Excel，含表頭。"""
#     return pd.read_excel(path, engine="openpyxl", header=0)
#
#
# def build_ppp_script_from_row(row: pd.Series) -> str:
#     """由一列 PPP Excel 資料生成 Groovy script。"""
#     customer_pk = row["customer pkey"]
#     customer_type = row["customer type"]
#     interval = row["interval"]
#     sku_code = row["sku code"]
#     price_val = row["price"]
#     start_time = row["start time"]
#     end_time = row["end time"]
#     usermax = row["usermax"]
#     street = row["street"]
#     sub_cat2 = row["sub cat 2"]
#     last_purchased_price = row["last purchased price"]
#     cost_bearer = row["cost bearer"]
#     delete_offer = row["delete offer"]
#     is_recommended = row["is recommended"]
#     seq = row["seq"]
#
#     def nz(v, default=""):
#         return default if (pd.isna(v) or v == "") else v
#
#     customer_type = nz(customer_type, "active_cus")
#     interval = nz(interval, 60000)
#     sku_code = nz(sku_code, "")
#     price_val = nz(price_val, 0)
#     start_time = nz(start_time, "2025-12-16 10:00:00")
#     end_time = nz(end_time, "2025-12-31 00:00:00")
#     usermax = nz(usermax, 5)
#     street = nz(street, "supermarket")
#     sub_cat2 = nz(sub_cat2, "AA111100")
#     last_purchased_price = nz(last_purchased_price, 0)
#     cost_bearer = nz(cost_bearer, "HKTV")
#     delete_offer = nz(delete_offer, 1)
#     is_recommended = nz(is_recommended, 0)
#     seq = nz(seq, 1)
#
#     start_time_str = str(start_time)
#     end_time_str = str(end_time)
#
#     return f"""
# import hk.com.hktv.facades.personalPrice.data.HktvPersonalPriceSettingData;
# import hk.com.hktv.facades.personalPrice.data.HktvPersonalPriceProductOfferData;
# String customerPk = "{customer_pk}";
# HktvPersonalPriceSettingData hktvPersonalPriceSettingData = new HktvPersonalPriceSettingData();
# HktvPersonalPriceProductOfferData personalPriceProductOfferData = new HktvPersonalPriceProductOfferData();
# hktvPersonalPriceSettingData.setCustomerType("{customer_type}");
# hktvPersonalPriceSettingData.setInterval({interval});
# personalPriceProductOfferData.setSkuCode("{sku_code}");
# personalPriceProductOfferData.setPrice({price_val});
# personalPriceProductOfferData.setStartTime("{start_time_str}.0");
# personalPriceProductOfferData.setEndTime("{end_time_str}.0");
# personalPriceProductOfferData.setUserMax({usermax});
# personalPriceProductOfferData.setStreet("{street}");
# personalPriceProductOfferData.setSubCat2("{sub_cat2}");
# personalPriceProductOfferData.setLastPurchasedPrice({last_purchased_price});
# personalPriceProductOfferData.setCostBearer("{cost_bearer}");
# personalPriceProductOfferData.setDeleteOffer({delete_offer});
# personalPriceProductOfferData.setLastExpiryTime("{end_time_str}.0");
# personalPriceProductOfferData.setIsRecommended({is_recommended});
# personalPriceProductOfferData.setSeq({seq});
# hktvPersonalPriceService.savePersonalPriceSetting(hktvPersonalPriceSettingData, customerPk, 3196800);
# hktvPersonalPriceService.savePersonalPrice(personalPriceProductOfferData, customerPk);
# """
#
#
# def run_excel_ppp(env: str, username: str, password: str, excel_path: str) -> str:
#     """PPP Excel 批次"""
#     try:
#         df = read_ppp_excel(excel_path)
#     except Exception as e:
#         return f"Failed to read PPP Excel: {e}"
#
#     if df.empty:
#         return "PPP Excel has no data."
#
#     row_count = len(df)
#     base_url = get_base_url(env)
#     session, csrf_execute, err = prepare_session(base_url, username, password)
#     if err:
#         return err
#
#     lines = [f"[PPP] Total rows: {row_count}"]
#
#     for i in range(row_count):
#         row = df.iloc[i]
#         script_text = build_ppp_script_from_row(row)
#         ok, resp = execute_script(session, base_url, csrf_execute, script_text)
#         status = "Success" if ok else "Failed"
#         lines.append(
#             f"Row {i+1}: customerPk={row['customer pkey']}, "
#             f"sku={row['sku code']}, price={row['price']} -> {status}"
#         )
#
#     return "\n".join(lines)
#
#
# # =============== AAA Excel / Script（示範） ===============
#
# def read_aaa_excel(path: str) -> pd.DataFrame:
#     """
#     讀 AAA Excel，含表頭。
#     這裡先假設欄位也有 'sku code', 'price'，之後可以依實際 AAA 檔改。
#     """
#     return pd.read_excel(path, engine="openpyxl", header=0)
#
#
# def build_aaa_script_from_row(row: pd.Series) -> str:
#     """由 AAA Excel 一列資料生成 Groovy script（示範，之後可換成正式腳本）。"""
#     sku_code = row.get("sku code", "")
#     price_val = row.get("price", 0)
#
#     def nz(v, default=""):
#         return default if (pd.isna(v) or v == "") else v
#
#     sku_code = nz(sku_code, "")
#     price_val = nz(price_val, 0)
#
#     return f"""
# // AAA Excel script example
# println("AAA Excel row, sku={sku_code}, price={price_val}");
# """
#
#
# def run_excel_aaa(env: str, username: str, password: str, excel_path: str) -> str:
#     """AAA Excel 批次"""
#     try:
#         df = read_aaa_excel(excel_path)
#     except Exception as e:
#         return f"Failed to read AAA Excel: {e}"
#
#     if df.empty:
#         return "AAA Excel has no data."
#
#     row_count = len(df)
#     base_url = get_base_url(env)
#     session, csrf_execute, err = prepare_session(base_url, username, password)
#     if err:
#         return err
#
#     lines = [f"[AAA] Total rows: {row_count}"]
#
#     for i in range(row_count):
#         row = df.iloc[i]
#         script_text = build_aaa_script_from_row(row)
#         ok, resp = execute_script(session, base_url, csrf_execute, script_text)
#         status = "Success" if ok else "Failed"
#         lines.append(
#             f"Row {i+1}: sku={row.get('sku code', '')}, price={row.get('price', '')} -> {status}"
#         )
#
#     return "\n".join(lines)
#
#
# # =============== Single script ===============
#
# def run_single(env: str, username: str, password: str, script_text: str) -> str:
#     """給 UI 用的單一 script 執行入口，回傳顯示字串。"""
#     base_url = get_base_url(env)
#     session, csrf_execute, err = prepare_session(base_url, username, password)
#     if err:
#         return err
#
#     ok, resp = execute_script(session, base_url, csrf_execute, script_text)
#     status = "Success" if ok else "Failed"
#     return f"[Single] {status}\n{resp}"
#
#
# # =============== Impex import ===============
#
# def run_impex(env: str, username: str, password: str, impex_text: str) -> str:
#     """
#     Impex Import (console/impex/import, Import content tab)。
#     回傳可顯示在 UI 的字串。
#     """
#     base_url = get_base_url(env)
#     session = requests.Session()
#     try:
#         # 1) login page + CSRF
#         login_page = session.get(f"{base_url}/")
#         csrf_login_match = re.search(
#             r'meta name="_csrf" content="([^"]+)"',
#             login_page.text,
#         )
#         if not csrf_login_match:
#             return "Login failed: cannot find CSRF token on login page."
#
#         csrf_login = csrf_login_match.group(1)
#
#         # 2) login
#         login_data = {
#             "j_username": username,
#             "j_password": password,
#             "_csrf": csrf_login,
#         }
#         resp_login = session.post(f"{base_url}/j_spring_security_check", data=login_data)
#
#         if "j_spring_security_check" in resp_login.text and "Username" in resp_login.text:
#             return "Login failed: wrong username/password or extra security."
#
#         # 3) Impex page CSRF
#         impex_page = session.get(f"{base_url}/console/impex/import/")
#         csrf_exec_match = re.search(
#             r'meta name="_csrf" content="([^"]+)"',
#             impex_page.text,
#         )
#         if not csrf_exec_match:
#             return "Impex page: cannot find CSRF token."
#
#         csrf_execute = csrf_exec_match.group(1)
#
#         # 4) POST impex
#         data = {
#             "scriptContent": impex_text,
#             "validationEnum": "IMPORT_STRICT",
#             "maxThreads": "12",
#             "encoding": "UTF-8",
#             "_legacyMode": "on",
#             "_enableCodeExecution": "on",
#             "_distributedMode": "on",
#             "_sldEnabled": "on",
#         }
#         headers = {"X-CSRF-TOKEN": csrf_execute}
#
#         resp = session.post(
#             f"{base_url}/console/impex/import",
#             data=data,
#             headers=headers,
#         )
#
#         # 5) parse result span
#         m = re.search(
#             r'<span id="impexResult"[^>]*data-result="([^"]*)"',
#             resp.text,
#         )
#         if m:
#             result_msg = m.group(1)
#             return f"[Impex] {result_msg}"
#         else:
#             if "Import finished successfully" in resp.text:
#                 return "[Impex] Import finished successfully (span not found, matched by text)."
#             return f"[Impex] Import result span not found. HTTP {resp.status_code}"
#     except Exception as e:
#         return f"[Impex] Error: {e}"



import pandas as pd
import requests
import re
import json


def get_base_url(env: str) -> str:
    if env == "Dev":
        return "https://ecomtest01.hkmpcl.com.hk/hac"
    else:
        return "https://www01.hkmpcl.com.hk/hac/"


def prepare_hac_session(base_url: str, username: str, password: str, target_page: str = None):
    """
    Unified login + get target page CSRF (scripting/impex/other).
    Returns: (session, csrf_token, None) or (None, None, error_msg)
    """
    session = requests.Session()
    try:
        # 1) Get login CSRF
        login_page = session.get(f"{base_url}/")
        csrf_login_match = re.search(r'meta name="_csrf" content="([^"]+)"', login_page.text)
        if not csrf_login_match:
            return None, None, "Login failed: cannot find CSRF token on login page."

        csrf_login = csrf_login_match.group(1)

        # 2) Login POST
        login_data = {
            "j_username": username,
            "j_password": password,
            "_csrf": csrf_login,
        }
        resp_login = session.post(f"{base_url}/j_spring_security_check", data=login_data)

        if "j_spring_security_check" in resp_login.text and "Username" in resp_login.text:
            return None, None, "Login failed: wrong username or password."

        # 3) Get target page + CSRF (if specified)
        if target_page:
            target_resp = session.get(f"{base_url}/{target_page}")
            if "j_spring_security_check" in target_resp.text:
                return None, None, f"Login failed: redirected to login on {target_page}."

            csrf_match = re.search(r'meta name="_csrf" content="([^"]+)"', target_resp.text)
            if not csrf_match:
                return None, None, f"Cannot find CSRF token on {target_page} page."

            return session, csrf_match.group(1), None

        return session, None, None  # No target page needed
    except Exception as e:
        return None, None, f"Login/session failed: {e}"


def execute_script(session, base_url: str, csrf_execute: str, script_text: str):
    """
    Execute Groovy script.
    Returns: (ok: bool, message: str)
    """
    data = {
        "commit": "true",
        "scriptType": "groovy",
        "script": script_text,
    }
    headers = {"X-CSRF-TOKEN": csrf_execute}

    try:
        resp = session.post(
            f"{base_url}/console/scripting/execute",
            data=data,
            headers=headers,
        )

        if "j_spring_security_check" in resp.text and "<form" in resp.text:
            return False, "Execute failed: got login page (session expired)."

        try:
            data_json = resp.json()
            return True, json.dumps(data_json, indent=2, ensure_ascii=False)
        except ValueError:
            return False, resp.text
    except Exception as e:
        return False, str(e)


# =============== PPP Excel / Script ===============

def read_ppp_excel(path: str) -> pd.DataFrame:
    """讀 PPP personal price Excel，含表頭。"""
    return pd.read_excel(path, engine="openpyxl", header=0)


def build_ppp_script_from_row(row: pd.Series) -> str:
    """由一列 PPP Excel 資料生成 Groovy script。"""
    customer_pk = row["customer pkey"]
    customer_type = row["customer type"]
    interval = row["interval"]
    sku_code = row["sku code"]
    price_val = row["price"]
    start_time = row["start time"]
    end_time = row["end time"]
    usermax = row["usermax"]
    street = row["street"]
    sub_cat2 = row["sub cat 2"]
    last_purchased_price = row["last purchased price"]
    cost_bearer = row["cost bearer"]
    delete_offer = row["delete offer"]
    is_recommended = row["is recommended"]
    seq = row["seq"]

    def nz(v, default=""):
        return default if (pd.isna(v) or v == "") else v

    customer_type = nz(customer_type, "active_cus")
    interval = nz(interval, 60000)
    sku_code = nz(sku_code, "")
    price_val = nz(price_val, 0)
    start_time = nz(start_time, "2025-12-16 10:00:00")
    end_time = nz(end_time, "2025-12-31 00:00:00")
    usermax = nz(usermax, 5)
    street = nz(street, "supermarket")
    sub_cat2 = nz(sub_cat2, "AA111100")
    last_purchased_price = nz(last_purchased_price, 0)
    cost_bearer = nz(cost_bearer, "HKTV")
    delete_offer = nz(delete_offer, 1)
    is_recommended = nz(is_recommended, 0)
    seq = nz(seq, 1)

    start_time_str = str(start_time)
    end_time_str = str(end_time)

    return f"""
import hk.com.hktv.facades.personalPrice.data.HktvPersonalPriceSettingData;
import hk.com.hktv.facades.personalPrice.data.HktvPersonalPriceProductOfferData;
String customerPk = "{customer_pk}";
HktvPersonalPriceSettingData hktvPersonalPriceSettingData = new HktvPersonalPriceSettingData();
HktvPersonalPriceProductOfferData personalPriceProductOfferData = new HktvPersonalPriceProductOfferData();
hktvPersonalPriceSettingData.setCustomerType("{customer_type}");
hktvPersonalPriceSettingData.setInterval({interval});
personalPriceProductOfferData.setSkuCode("{sku_code}");
personalPriceProductOfferData.setPrice({price_val});
personalPriceProductOfferData.setStartTime("{start_time_str}.0");
personalPriceProductOfferData.setEndTime("{end_time_str}.0");
personalPriceProductOfferData.setUserMax({usermax});
personalPriceProductOfferData.setStreet("{street}");
personalPriceProductOfferData.setSubCat2("{sub_cat2}");
personalPriceProductOfferData.setLastPurchasedPrice({last_purchased_price});
personalPriceProductOfferData.setCostBearer("{cost_bearer}");
personalPriceProductOfferData.setDeleteOffer({delete_offer});
personalPriceProductOfferData.setLastExpiryTime("{end_time_str}.0");
personalPriceProductOfferData.setIsRecommended({is_recommended});
personalPriceProductOfferData.setSeq({seq});
hktvPersonalPriceService.savePersonalPriceSetting(hktvPersonalPriceSettingData, customerPk, 3196800);
hktvPersonalPriceService.savePersonalPrice(personalPriceProductOfferData, customerPk);
"""


def run_excel_ppp(env: str, username: str, password: str, excel_path: str) -> str:
    """PPP Excel 批次"""
    try:
        df = read_ppp_excel(excel_path)
    except Exception as e:
        return f"Failed to read PPP Excel: {e}"

    if df.empty:
        return "PPP Excel has no data."

    row_count = len(df)
    base_url = get_base_url(env)
    session, csrf_execute, err = prepare_hac_session(base_url, username, password, "console/scripting/")
    if err:
        return err

    lines = [f"[PPP] Total rows: {row_count}"]

    for i in range(row_count):
        row = df.iloc[i]
        script_text = build_ppp_script_from_row(row)
        ok, resp = execute_script(session, base_url, csrf_execute, script_text)
        status = "Success" if ok else "Failed"
        lines.append(
            f"Row {i+1}: customerPk={row['customer pkey']}, "
            f"sku={row['sku code']}, price={row['price']} -> {status}"
        )

    return "\n".join(lines)


# =============== AAA Excel / Script（示範） ===============

def read_aaa_excel(path: str) -> pd.DataFrame:
    """讀 AAA Excel，含表頭。"""
    return pd.read_excel(path, engine="openpyxl", header=0)


def build_aaa_script_from_row(row: pd.Series) -> str:
    """由 AAA Excel 一列資料生成 Groovy script（示範）。"""
    sku_code = row.get("sku code", "")
    price_val = row.get("price", 0)

    def nz(v, default=""):
        return default if (pd.isna(v) or v == "") else v

    sku_code = nz(sku_code, "")
    price_val = nz(price_val, 0)

    return f"""
// AAA Excel script example
println("AAA Excel row, sku={sku_code}, price={price_val}");
"""


def run_excel_aaa(env: str, username: str, password: str, excel_path: str) -> str:
    """AAA Excel 批次"""
    try:
        df = read_aaa_excel(excel_path)
    except Exception as e:
        return f"Failed to read AAA Excel: {e}"

    if df.empty:
        return "AAA Excel has no data."

    row_count = len(df)
    base_url = get_base_url(env)
    session, csrf_execute, err = prepare_hac_session(base_url, username, password, "console/scripting/")
    if err:
        return err

    lines = [f"[AAA] Total rows: {row_count}"]

    for i in range(row_count):
        row = df.iloc[i]
        script_text = build_aaa_script_from_row(row)
        ok, resp = execute_script(session, base_url, csrf_execute, script_text)
        status = "Success" if ok else "Failed"
        lines.append(
            f"Row {i+1}: sku={row.get('sku code', '')}, price={row.get('price', '')} -> {status}"
        )

    return "\n".join(lines)


# =============== Single script ===============

def run_single(env: str, username: str, password: str, script_text: str) -> str:
    """給 UI 用的單一 script 執行入口。"""
    base_url = get_base_url(env)
    session, csrf_execute, err = prepare_hac_session(base_url, username, password, "console/scripting/")
    if err:
        return err

    ok, resp = execute_script(session, base_url, csrf_execute, script_text)
    status = "Success" if ok else "Failed"
    return f"[Single] {status}\n{resp}"


# =============== Impex import ===============

def run_impex(env: str, username: str, password: str, impex_text: str) -> str:
    """
    Impex Import (console/impex/import).
    """
    base_url = get_base_url(env)
    session, csrf_execute, err = prepare_hac_session(base_url, username, password, "console/impex/import/")
    if err:
        return err

    data = {
        "scriptContent": impex_text,
        "validationEnum": "IMPORT_STRICT",
        "maxThreads": "12",
        "encoding": "UTF-8",
        "_legacyMode": "on",
        "_enableCodeExecution": "on",
        "_distributedMode": "on",
        "_sldEnabled": "on",
    }
    headers = {"X-CSRF-TOKEN": csrf_execute}

    try:
        resp = session.post(f"{base_url}/console/impex/import", data=data, headers=headers)

        if "j_spring_security_check" in resp.text and "<form" in resp.text:
            return "[Impex] Session expired: got login page."

        m = re.search(r'<span id="impexResult"[^>]*data-result="([^"]*)"', resp.text)
        if m:
            return f"[Impex] {m.group(1)}"
        if "Import finished successfully" in resp.text:
            return "[Impex] Import finished successfully (span not found, matched by text)."
        return f"[Impex] Result span not found. HTTP {resp.status_code}"
    except Exception as e:
        return f"[Impex] Error: {e}"
