import json
import logging
import requests
from datetime import datetime

# Fixed DEV / STAGING endpoints
MALL_DEV = "https://ecomtest01.hkmpcl.com.hk/"
MALL_STAGING = "https://www01.hkmpcl.com.hk/"

PAYMENT_GATEWAY_DEV = "https://hktv-odm-dev.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"
PAYMENT_GATEWAY_STAGING = "https://hktv-odm-staging.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"

DEV = "Dev"
STAGING = "Staging"

API_MAP = {
    DEV: {
        "user_search": MALL_DEV + "hktvwebservices/v1/hktv/s2s/customer/get_user_list_by_search_text",
        "order": MALL_DEV + "hktvwebservices/v1/hktv/get_order_with_batches",
        "token": MALL_DEV + "hktvwebservices/oauth/token",
        "batch": MALL_DEV + "hktvwebservices/v1/hktv/s2s/customerReceivedBatch/create",
        "status": MALL_DEV + "hktvwebservices/v1/hktv/s2s/consignment/splitAndUpdateConsignmentStatus",
        "pg": PAYMENT_GATEWAY_DEV,
    },
    STAGING: {
        "user_search": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/customer/get_user_list_by_search_text",
        "order": MALL_STAGING + "hktvwebservices/v1/hktv/get_order_with_batches",
        "token": MALL_STAGING + "hktvwebservices/oauth/token",
        "batch": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/customerReceivedBatch/create",
        "status": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/consignment/splitAndUpdateConsignmentStatus",
        "pg": PAYMENT_GATEWAY_STAGING,
    },
}


from datetime import datetime, timedelta

def get_today_formatted():
    # 昨天的同一時間，ISO-8601 + 時區，例如 2026-01-28T10:00:00+08:00
    dt = datetime.now().astimezone() - timedelta(days=1)
    return dt.replace(microsecond=0).isoformat()

def extract_store_code(sku_id: str):
    return sku_id.split('_', 1)[0]


def get_user_token(env: str, uid: str, pw: str):
    if not uid or not pw:
        raise Exception("[Failed] No uid or pw")

    url = API_MAP[env]["token"]

    headers = {
        "Authorization": "Basic aGt0dl9tYWxsX2lvczojRSlpZytnMVR2Iw==",
    }

    files = {
        "grant_type": (None, "password"),
        "username": (None, uid),
        "password": (None, pw),
    }
    try:
        response = requests.post(url=url, headers=headers, files=files, timeout=30)
        response.raise_for_status()
        data = response.json()
        token = data['access_token']
        logging.info("Token acquired: %s", token)
        return token
    except Exception as e:
        logging.error("Failed to get token: %s", e)
        raise


def api_order_get_order_id_with_batches(env: str, uid: str, pw: str, order: str):
    bearer_token = get_user_token(env, uid, pw)

    if not uid or not order:
        raise ValueError("Missing user_id or order_id")

    url = API_MAP[env]["order"]

    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"bearer {bearer_token}"},
            params={"user_id": uid, "lang": "zh", "order_id": order},
        )
        resp.raise_for_status()
        result = resp.json()

        sub_order_numbers = [
            cons.get("subOrderNumber")
            for batch in result.get("deliveryBatches", [])
            for entry in batch.get("entries", [])
            for cons in entry.get("consignmentEntries", [])
            if cons.get("subOrderNumber")
        ]

        return sub_order_numbers

    except requests.RequestException as e:
        raise RuntimeError(f"Request failed: {e}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON response")


def api_order_split_and_update_consignment_status(env: str, consignment_code: str, status: str):
    url = API_MAP[env]["status"]

    data = {
        'consignmentCode': consignment_code,
        'status': status
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        res_json = response.json()
        logging.info("Full response: %s", res_json)

        if res_json.get("status", {}).get("code") != "success":
            raise RuntimeError(f"API call unsuccessful. Status: {res_json.get('status')}")

        if "data" not in res_json or "status" not in res_json["data"]:
            raise ValueError("Response missing required 'data' or 'status' fields.")

        updated_status = res_json["data"]["status"]
        logging.info("Updated status: %s", updated_status)

        return updated_status

    except requests.RequestException as e:
        logging.error("Request failed: %s", e)
        raise


def api_order_create_customer_received_batch(env: str, code: str, consignment_codes):
    """
    code: order id (sub_order)
    consignment_codes: str or list[str]
    """
    if isinstance(consignment_codes, str):
        consignment_codes = [consignment_codes]
    elif consignment_codes is None:
        consignment_codes = []

    if not consignment_codes:
        raise ValueError("No consignment codes provided to create customer received batch")

    customer_received_time = get_today_formatted()
    url = API_MAP[env]["batch"]

    payload = {
        "code": code,
        "customerReceivedTime": customer_received_time,
        "consignments": consignment_codes,
        "referenceFiles": [
            {
                "imageData": "https://dyn-img-dev.hkmpcl.com.hk/mkgb/common/wzu/emw/ZAbvdmkaqK20240521165451.png",
                "imageSeq": 1,
                "imageCategory": "CUST_SIGN"
            }
        ]
    }

    logging.info("CustomerReceivedBatch start: code=%s, consignments=%s", code, consignment_codes)

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        res_data = response.json()

        status = res_data.get('status', {})
        status_code = status.get('code')
        message = status.get('message', '')

        if status_code == 'fail':
            if "Consignment has customer received batch already" in message:
                logging.info("CustomerReceivedBatch exists: code=%s", code)
                return res_data

            if "Unable to create network file" in message:
                logging.warning("CustomerReceivedBatch network error, retry once: code=%s", code)
                response_retry = requests.post(url, json=payload)
                response_retry.raise_for_status()
                res_data_retry = response_retry.json()

                retry_status = res_data_retry.get('status', {})
                retry_status_code = retry_status.get('code')
                retry_message = retry_status.get('message', '')

                if retry_status_code == 'fail' and \
                        "Consignment has customer received batch already" in retry_message:
                    logging.info("CustomerReceivedBatch exists after retry: code=%s", code)
                    return res_data_retry

                raise RuntimeError(f"Retry API failed: {retry_message}")

            raise RuntimeError(f"API returned failure: {message}")

        logging.info("CustomerReceivedBatch success: code=%s", code)
        return res_data

    except requests.RequestException as e:
        logging.error("CustomerReceivedBatch request error: code=%s, err=%s", code, e)
        raise


def api_user_get_user_info(env: str, tel: str):
    url = API_MAP[env]["user_search"]

    params = {"searchText": tel}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        res_data = response.json()

        status_code = res_data.get('status', {}).get('code')
        if status_code != 'success':
            raise RuntimeError(f"API returned failure: {res_data.get('status', {}).get('message', 'Unknown error')}")

        customers = res_data.get('data', [])
        if not customers:
            raise RuntimeError(f"No customers found for searchText: {tel}")

        customer_info = customers[0]
        return {
            "pk": customer_info.get("pk"),
            "uid": customer_info.get("uid"),
            "name": customer_info.get("name"),
            "email": customer_info.get("email"),
            "membershipLevel": customer_info.get("membershipLevel")
        }

    except requests.RequestException as e:
        logging.error("Customer search request failed: %s", e)
        raise RuntimeError(f"Customer search API failed: {e}")


def api_order_get_consignment_and_waybill(env: str, order_id: str):
    url = API_MAP[env]["pg"]

    consignments = []
    waybills = []

    page = 1
    while True:
        payload = {
            "orderId": [order_id],
            "sortDirection": "DESC",
            "pn": page,
            "ps": 20
        }

        try:
            response = requests.post(url=url, json=payload)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data or not isinstance(data['data'], list):
                break

            page_items = data['data']
            if not page_items:
                break

            for item in page_items:
                consignment_code = item.get('consignmentCode')
                waybill_number = item.get('waybillNumber')

                if consignment_code:
                    consignments.append(consignment_code)
                if waybill_number:
                    waybills.append(waybill_number)

            if len(page_items) < 20:
                break

            page += 1

        except Exception as e:
            logging.error(
                "Failed to get consignments/waybills for order_id=%s, page=%s: %s",
                order_id, page, e
            )
            raise

    def unique(seq):
        seen = set()
        result = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                result.append(x)
        return result

    consignments = unique(consignments)
    waybills = unique(waybills)

    def normalize(values):
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        return values

    return {
        "consignmentCode": normalize(consignments),
        "waybillNumber": normalize(waybills),
    }


def api_Function_Order_RECEIVED_BY_CUSTOMER(
    env: str,
    order: str,
    store_code: str = None,
    sku: str = None,
    uid: str = None,
    tel: str = None,
    pw: str = None,
    status: str = 'RECEIVED_BY_CUSTOMER'
):
    if order is None:
        raise Exception('[Failed] No order provided')

    # Determine sub_order_numbers
    if store_code:
        sub_order_numbers = order + "-" + store_code
    elif sku:
        store_code = extract_store_code(sku)
        sub_order_numbers = order + "-" + store_code
    elif uid and pw:
        sub_order_numbers = api_order_get_order_id_with_batches(env, uid, pw, order)
    elif tel and pw:
        user = api_user_get_user_info(env, tel)
        uid = user["uid"]
        sub_order_numbers = api_order_get_order_id_with_batches(env, uid, pw, order)
    else:
        raise Exception('[Failed] No enough info for complete order')

    logging.info('sub_order_numbers (raw): %s', sub_order_numbers)

    if isinstance(sub_order_numbers, str):
        sub_order_numbers = [sub_order_numbers]

    seen = set()
    unique_sub_orders = []
    for so in sub_order_numbers:
        if so not in seen:
            seen.add(so)
            unique_sub_orders.append(so)
    sub_order_numbers = unique_sub_orders

    logging.info('sub_order_numbers (unique): %s', sub_order_numbers)

    if not sub_order_numbers:
        logging.warning("No sub_order_numbers found, skipping processing")
        raise Exception('[Failed] Cannot Update order - No sub_order_numbers')

    for sub_order in sub_order_numbers:
        logging.info("Processing sub_order: %s", sub_order)

        result = api_order_get_consignment_and_waybill(env, sub_order)
        consignmentCode = result["consignmentCode"]
        logging.info('consignmentCode: %s', consignmentCode)

        if isinstance(consignmentCode, list):
            consignment_codes = consignmentCode
        elif isinstance(consignmentCode, str):
            consignment_codes = [consignmentCode]
        else:
            consignment_codes = []

        if not consignment_codes:
            raise Exception('[Failed] Cannot Update order - No consignment_codes')

        api_order_create_customer_received_batch(env, sub_order, consignment_codes)

        for code in consignment_codes:
            api_order_split_and_update_consignment_status(env, code, status)




# import json
# import logging
# import requests
# from datetime import datetime
#
# # Fixed DEV / STAGING endpoints
# MALL_DEV = "https://ecomtest01.hkmpcl.com.hk/"
# MALL_STAGING = "https://www01.hkmpcl.com.hk/"
#
# PAYMENT_GATEWAY_DEV = "https://hktv-odm-dev.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"
# PAYMENT_GATEWAY_STAGING = "https://hktv-odm-staging.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"
#
# DEV = "Dev"
# STAGING = "Staging"
#
# API_MAP = {
#     DEV: {
#         "user_search": MALL_DEV + "hktvwebservices/v1/hktv/s2s/customer/get_user_list_by_search_text",
#         "order": MALL_DEV + "hktvwebservices/v1/hktv/get_order_with_batches",
#         "token": MALL_DEV + "hktvwebservices/oauth/token",
#         "batch": MALL_DEV + "hktvwebservices/v1/hktv/s2s/customerReceivedBatch/create",
#         "status": MALL_DEV + "hktvwebservices/v1/hktv/s2s/consignment/splitAndUpdateConsignmentStatus",
#         "pg": PAYMENT_GATEWAY_DEV,
#     },
#     STAGING: {
#         "user_search": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/customer/get_user_list_by_search_text",
#         "order": MALL_STAGING + "hktvwebservices/v1/hktv/get_order_with_batches",
#         "token": MALL_STAGING + "hktvwebservices/oauth/token",
#         "batch": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/customerReceivedBatch/create",
#         "status": MALL_STAGING + "hktvwebservices/v1/hktv/s2s/consignment/splitAndUpdateConsignmentStatus",
#         "pg": PAYMENT_GATEWAY_STAGING,
#     },
# }
#
#
# def get_today_formatted():
#     return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#
#
# def extract_store_code(sku_id: str):
#     return sku_id.split('_', 1)[0]
#
#
# def get_user_token(env: str, uid: str, pw: str):
#     if not uid or not pw:
#         raise Exception("[Failed] No uid or pw")
#
#     url = API_MAP[env]["token"]
#
#     headers = {
#         "Authorization": "Basic aGt0dl9tYWxsX2lvczojRSlpZytnMVR2Iw==",
#     }
#
#     files = {
#         "grant_type": (None, "password"),
#         "username": (None, uid),
#         "password": (None, pw),
#     }
#     try:
#         response = requests.post(url=url, headers=headers, files=files, timeout=30)
#         response.raise_for_status()
#         data = response.json()
#         token = data['access_token']
#         logging.info("Token acquired: %s", token)
#         return token
#     except Exception as e:
#         logging.error("Failed to get token: %s", e)
#         raise
#
#
# def api_order_get_order_id_with_batches(env: str, uid: str, pw: str, order: str):
#     bearer_token = get_user_token(env, uid, pw)
#
#     if not uid or not order:
#         raise ValueError("Missing user_id or order_id")
#
#     url = API_MAP[env]["order"]
#
#     try:
#         resp = requests.get(
#             url,
#             headers={"Authorization": f"bearer {bearer_token}"},
#             params={"user_id": uid, "lang": "zh", "order_id": order},
#         )
#         resp.raise_for_status()
#         result = resp.json()
#
#         sub_order_numbers = [
#             cons.get("subOrderNumber")
#             for batch in result.get("deliveryBatches", [])
#             for entry in batch.get("entries", [])
#             for cons in entry.get("consignmentEntries", [])
#             if cons.get("subOrderNumber")
#         ]
#
#         return sub_order_numbers
#
#     except requests.RequestException as e:
#         raise RuntimeError(f"Request failed: {e}")
#     except json.JSONDecodeError:
#         raise ValueError("Invalid JSON response")
#
#
# def api_order_split_and_update_consignment_status(env: str, consignment_code: str, status: str):
#     url = API_MAP[env]["status"]
#
#     data = {
#         'consignmentCode': consignment_code,
#         'status': status
#     }
#     try:
#         response = requests.post(url, data=data)
#         response.raise_for_status()
#         res_json = response.json()
#         logging.info("Full response: %s", res_json)
#
#         if res_json.get("status", {}).get("code") != "success":
#             raise RuntimeError(f"API call unsuccessful. Status: {res_json.get('status')}")
#
#         if "data" not in res_json or "status" not in res_json["data"]:
#             raise ValueError("Response missing required 'data' or 'status' fields.")
#
#         updated_status = res_json["data"]["status"]
#         logging.info("Updated status: %s", updated_status)
#
#         return updated_status
#
#     except requests.RequestException as e:
#         logging.error("Request failed: %s", e)
#         raise
#
#
# def api_order_create_customer_received_batch(env: str, code: str, consignment_codes):
#     """
#     code: order id (sub_order)
#     consignment_codes: str or list[str]
#     """
#     if isinstance(consignment_codes, str):
#         consignment_codes = [consignment_codes]
#     elif consignment_codes is None:
#         consignment_codes = []
#
#     if not consignment_codes:
#         raise ValueError("No consignment codes provided to create customer received batch")
#
#     customer_received_time = get_today_formatted()
#     url = API_MAP[env]["batch"]
#
#     payload = {
#         "code": code,
#         "customerReceivedTime": customer_received_time,
#         "consignments": consignment_codes,
#         "referenceFiles": [
#             {
#                 "imageData": "https://dyn-img-dev.hkmpcl.com.hk/mkgb/common/wzu/emw/ZAbvdmkaqK20240521165451.png",
#                 "imageSeq": 1,
#                 "imageCategory": "CUST_SIGN"
#             }
#         ]
#     }
#
#     logging.info("CustomerReceivedBatch start: code=%s, consignments=%s", code, consignment_codes)
#
#     try:
#         response = requests.post(url, json=payload)
#         response.raise_for_status()
#         res_data = response.json()
#
#         status = res_data.get('status', {})
#         status_code = status.get('code')
#         message = status.get('message', '')
#
#         if status_code == 'fail':
#             if "Consignment has customer received batch already" in message:
#                 logging.info("CustomerReceivedBatch exists: code=%s", code)
#                 return res_data
#
#             if "Unable to create network file" in message:
#                 logging.warning("CustomerReceivedBatch network error, retry once: code=%s", code)
#                 response_retry = requests.post(url, json=payload)
#                 response_retry.raise_for_status()
#                 res_data_retry = response_retry.json()
#
#                 retry_status = res_data_retry.get('status', {})
#                 retry_status_code = retry_status.get('code')
#                 retry_message = retry_status.get('message', '')
#
#                 if retry_status_code == 'fail' and \
#                         "Consignment has customer received batch already" in retry_message:
#                     logging.info("CustomerReceivedBatch exists after retry: code=%s", code)
#                     return res_data_retry
#
#                 raise RuntimeError(f"Retry API failed: {retry_message}")
#
#             raise RuntimeError(f"API returned failure: {message}")
#
#         logging.info("CustomerReceivedBatch success: code=%s", code)
#         return res_data
#
#     except requests.RequestException as e:
#         logging.error("CustomerReceivedBatch request error: code=%s, err=%s", code, e)
#         raise
#
#
# def api_user_get_user_info(env: str, tel: str):
#     url = API_MAP[env]["user_search"]
#
#     params = {"searchText": tel}
#
#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         res_data = response.json()
#
#         status_code = res_data.get('status', {}).get('code')
#         if status_code != 'success':
#             raise RuntimeError(f"API returned failure: {res_data.get('status', {}).get('message', 'Unknown error')}")
#
#         customers = res_data.get('data', [])
#         if not customers:
#             raise RuntimeError(f"No customers found for searchText: {tel}")
#
#         customer_info = customers[0]
#         return {
#             "pk": customer_info.get("pk"),
#             "uid": customer_info.get("uid"),
#             "name": customer_info.get("name"),
#             "email": customer_info.get("email"),
#             "membershipLevel": customer_info.get("membershipLevel")
#         }
#
#     except requests.RequestException as e:
#         logging.error("Customer search request failed: %s", e)
#         raise RuntimeError(f"Customer search API failed: {e}")
#
#
# def api_order_get_consignment_and_waybill(env: str, order_id: str):
#     url = API_MAP[env]["pg"]
#
#     consignments = []
#     waybills = []
#
#     page = 1
#     while True:
#         payload = {
#             "orderId": [order_id],
#             "sortDirection": "DESC",
#             "pn": page,
#             "ps": 20
#         }
#
#         try:
#             response = requests.post(url=url, json=payload)
#             response.raise_for_status()
#             data = response.json()
#
#             if 'data' not in data or not isinstance(data['data'], list):
#                 break
#
#             page_items = data['data']
#             if not page_items:
#                 break
#
#             for item in page_items:
#                 consignment_code = item.get('consignmentCode')
#                 waybill_number = item.get('waybillNumber')
#
#                 if consignment_code:
#                     consignments.append(consignment_code)
#                 if waybill_number:
#                     waybills.append(waybill_number)
#
#             if len(page_items) < 20:
#                 break
#
#             page += 1
#
#         except Exception as e:
#             logging.error(
#                 "Failed to get consignments/waybills for order_id=%s, page=%s: %s",
#                 order_id, page, e
#             )
#             raise
#
#     def unique(seq):
#         seen = set()
#         result = []
#         for x in seq:
#             if x not in seen:
#                 seen.add(x)
#                 result.append(x)
#         return result
#
#     consignments = unique(consignments)
#     waybills = unique(waybills)
#
#     def normalize(values):
#         if not values:
#             return None
#         if len(values) == 1:
#             return values[0]
#         return values
#
#     return {
#         "consignmentCode": normalize(consignments),
#         "waybillNumber": normalize(waybills),
#     }
#
#
# def api_Function_Order_RECEIVED_BY_CUSTOMER(
#     env: str,
#     order: str,
#     store_code: str = None,
#     sku: str = None,
#     uid: str = None,
#     tel: str = None,
#     pw: str = None,
#     status: str = 'RECEIVED_BY_CUSTOMER'
# ):
#     if order is None:
#         raise Exception('[Failed] No order provided')
#
#     # Determine sub_order_numbers
#     if store_code:
#         sub_order_numbers = order + "-" + store_code
#     elif sku:
#         store_code = extract_store_code(sku)
#         sub_order_numbers = order + "-" + store_code
#     elif uid and pw:
#         sub_order_numbers = api_order_get_order_id_with_batches(env, uid, pw, order)
#     elif tel and pw:
#         user = api_user_get_user_info(env, tel)
#         uid = user["uid"]
#         sub_order_numbers = api_order_get_order_id_with_batches(env, uid, pw, order)
#     else:
#         raise Exception('[Failed] No enough info for complete order')
#
#     logging.info('sub_order_numbers (raw): %s', sub_order_numbers)
#
#     if isinstance(sub_order_numbers, str):
#         sub_order_numbers = [sub_order_numbers]
#
#     seen = set()
#     unique_sub_orders = []
#     for so in sub_order_numbers:
#         if so not in seen:
#             seen.add(so)
#             unique_sub_orders.append(so)
#     sub_order_numbers = unique_sub_orders
#
#     logging.info('sub_order_numbers (unique): %s', sub_order_numbers)
#
#     if not sub_order_numbers:
#         logging.warning("No sub_order_numbers found, skipping processing")
#         raise Exception('[Failed] Cannot Update order - No sub_order_numbers')
#
#     for sub_order in sub_order_numbers:
#         logging.info("Processing sub_order: %s", sub_order)
#
#         result = api_order_get_consignment_and_waybill(env, sub_order)
#         consignmentCode = result["consignmentCode"]
#         logging.info('consignmentCode: %s', consignmentCode)
#
#         if isinstance(consignmentCode, list):
#             consignment_codes = consignmentCode
#         elif isinstance(consignmentCode, str):
#             consignment_codes = [consignmentCode]
#         else:
#             consignment_codes = []
#
#         if not consignment_codes:
#             raise Exception('[Failed] Cannot Update order - No consignment_codes')
#
#         api_order_create_customer_received_batch(env, sub_order, consignment_codes)
#
#         for code in consignment_codes:
#             api_order_split_and_update_consignment_status(env, code, status)
#
#






















# import json
# import logging
#
# import requests
#
#
# def api_Function_Order_RECEIVED_BY_CUSTOMER(context, order=None, store_code=None, sku=None, uid=None, tel=None, pw=None,
#                                             status='RECEIVED_BY_CUSTOMER'):
#     order = order or context.get('order_number')
#     if order is None:
#         raise Exception('[Failed] No order provided')
#
#     uid = uid or context.get('uid')
#     tel = tel or context.get('tel')
#     pw = pw or context.get('pw')
#     store_code = store_code or context.get('store_code')
#     sku = sku or context.get('sku')
#
#     # Determine sub_order_numbers based on available info
#     if store_code:
#         sub_order_numbers = order + "-" + store_code
#     elif sku:
#         store_code = extract_store_code(context, context['sku'])
#         sub_order_numbers = order + "-" + store_code
#     elif uid and pw:
#         sub_order_numbers = api_order_get_order_id_with_batches(context, uid, pw, order)
#     elif tel and pw:
#         uid = api_user_get_user_info(context, tel)['uid']
#         sub_order_numbers = api_order_get_order_id_with_batches(context, uid, pw, order)
#     else:
#         raise Exception('[Failed] No enough info for complete order')
#
#     print(f'sub_order_numbers (raw): {sub_order_numbers}')
#
#     # normalize to list
#     if isinstance(sub_order_numbers, str):
#         sub_order_numbers = [sub_order_numbers]
#
#     # remove duplicate sub_orders, keep order
#     seen = set()
#     unique_sub_orders = []
#     for so in sub_order_numbers:
#         if so not in seen:
#             seen.add(so)
#             unique_sub_orders.append(so)
#     sub_order_numbers = unique_sub_orders
#
#     print(f'sub_order_numbers (unique): {sub_order_numbers}')
#
#     if not sub_order_numbers:
#         print("No sub_order_numbers found, skipping processing")
#         raise Exception('[Failed] Cannot Update order - No sub_order_numbers')
#
#     for sub_order in sub_order_numbers:
#         print(f"Processing sub_order: {sub_order}")
#
#         # 1) get all consignmentCode for this sub_order
#         result = api_order_get_consignment_and_waybill(context, sub_order)
#         consignmentCode = result["consignmentCode"]  # str | list | None
#         print(f'consignmentCode: {consignmentCode}')
#
#         # normalize to list for later use
#         if isinstance(consignmentCode, list):
#             consignment_codes = consignmentCode
#         elif isinstance(consignmentCode, str):
#             consignment_codes = [consignmentCode]
#         else:
#             consignment_codes = []
#
#         if not consignment_codes:
#             raise Exception('[Failed] Cannot Update order - No consignment_codes')
#
#         # 2) one batch call per sub_order
#         api_order_create_customer_received_batch(context, sub_order, consignment_codes)
#
#         # 3) update each consignment
#         for code in consignment_codes:
#             api_order_split_and_update_consignment_status(context, code, status)
#
#
# def extract_store_code(context, sku_id: str):
#     context['store_code'] = sku_id.split('_', 1)[0]
#     return context['store_code']
#
# def get_user_token(context, uid=None, pw=None):
#     context['token'] = None
#     uid = uid or context["uid"]
#     pw = pw or context["pw"]
#
#     if not uid or not pw:
#         raise Exception("[Failed] No uid or pw")
#
#     url = value_based_env_return(context, Api_Get_Token_Dev, Api_Get_Token_Staging)
#
#     headers = {
#         "Authorization": "Basic aGt0dl9tYWxsX2lvczojRSlpZytnMVR2Iw==",  # base64(client_id:client_secret)
#     }
#
#     files = {
#         "grant_type": (None, "password"),
#         "username": (None, context["uid"]),
#         "password": (None, context["pw"]),
#     }
#     try:
#         # Body goes in files= to force multipart; do NOT use params= for body fields
#         response = requests.post(url=url, headers=headers, files=files, timeout=30)  # multipart form-data [4]
#         response.raise_for_status()
#         data = response.json()
#         context['token'] = data['access_token']
#         logging.info(f"Token acquired: {context['token']}")
#         with allure.step("getUserToken"):
#             pass
#     except Exception as e:
#         logging.error(f"Failed to get token: {e}")
#         handle_failure_with_screenshot(context, f"Failed to get token: {e}")
#
#     return context['token']
#
# def api_order_get_order_id_with_batches(context, uid, pw, order):
#     bearer_token = get_user_token(context, uid, pw)
#
#     if not uid or not order:
#         raise ValueError("Missing user_id or order_id")
#
#     url = value_based_env_return(context, Api_Get_Order_With_Batches_Dev, Api_Get_Order_With_Batches_Staging)
#
#     try:
#         resp = requests.get(
#             url,
#             headers={"Authorization": f"bearer {bearer_token}"},
#             params={"user_id": uid, "lang": "zh", "order_id": order},
#         )
#         resp.raise_for_status()
#         result = resp.json()
#
#         sub_order_numbers = [
#             cons.get("subOrderNumber")
#             for batch in result.get("deliveryBatches", [])
#             for entry in batch.get("entries", [])
#             for cons in entry.get("consignmentEntries", [])
#             if cons.get("subOrderNumber")
#         ]
#
#         return sub_order_numbers
#
#     except requests.RequestException as e:
#         raise RuntimeError(f"Request failed: {e}")
#     except json.JSONDecodeError:
#         raise ValueError("Invalid JSON response")
#
# def api_order_split_and_update_consignment_status(context, consignment_code, status):
#     url = value_based_env_return(context, Api_Update_Consignment_Status_Dev, Api_Update_Consignment_Status_Staging)
#
#     data = {
#         'consignmentCode': consignment_code,
#         'status': status
#     }
#     try:
#         response = requests.post(url, data=data)
#         response.raise_for_status()
#         res_json = response.json()
#         print("Full response:", res_json)
#
#         # Validate success status
#         if res_json.get("status", {}).get("code") != "success":
#             raise RuntimeError(f"API call unsuccessful. Status: {res_json.get('status')}")
#
#         # Validate presence of "data" and "status" field inside "data"
#         if "data" not in res_json or "status" not in res_json["data"]:
#             raise ValueError("Response missing required 'data' or 'status' fields.")
#
#         updated_status = res_json["data"]["status"]
#         print(f"Updated status: {updated_status}")
#
#         return updated_status
#
#     except requests.RequestException as e:
#         print(f"Request failed: {e}")
#         raise
#
# def api_order_create_customer_received_batch(context, code, consignment_codes):
#     """
#     code: order id (sub_order)
#     consignment_codes: str or list[str]
#     """
#     # normalize to list
#     if isinstance(consignment_codes, str):
#         consignment_codes = [consignment_codes]
#     elif consignment_codes is None:
#         consignment_codes = []
#
#     if not consignment_codes:
#         raise ValueError("No consignment codes provided to create customer received batch")
#
#     customer_received_time = get_today_formatted()
#     url = value_based_env_return(context, Api_Create_Customer_Received_Batch_Dev,
#                                  Api_Create_Customer_Received_Batch_Staging)
#
#     payload = {
#         "code": code,
#         "customerReceivedTime": customer_received_time,
#         "consignments": consignment_codes,
#         "referenceFiles": [
#             {
#                 "imageData": "https://dyn-img-dev.hkmpcl.com.hk/mkgb/common/wzu/emw/ZAbvdmkaqK20240521165451.png",
#                 "imageSeq": 1,
#                 "imageCategory": "CUST_SIGN"
#             }
#         ]
#     }
#
#     logging.info("CustomerReceivedBatch start: code=%s, consignments=%s", code, consignment_codes)
#
#     try:
#         response = requests.post(url, json=payload)
#         response.raise_for_status()
#         res_data = response.json()
#
#         status = res_data.get('status', {})
#         status_code = status.get('code')
#         message = status.get('message', '')
#
#         if status_code == 'fail':
#             # already created → accept and exit
#             if "Consignment has customer received batch already" in message:
#                 logging.info("CustomerReceivedBatch exists: code=%s", code)
#                 return res_data
#
#             # network file issue → retry once
#             if "Unable to create network file" in message:
#                 logging.warning("CustomerReceivedBatch network error, retry once: code=%s", code)
#                 response_retry = requests.post(url, json=payload)
#                 response_retry.raise_for_status()
#                 res_data_retry = response_retry.json()
#
#                 retry_status = res_data_retry.get('status', {})
#                 retry_status_code = retry_status.get('code')
#                 retry_message = retry_status.get('message', '')
#
#                 if retry_status_code == 'fail' and \
#                         "Consignment has customer received batch already" in retry_message:
#                     logging.info("CustomerReceivedBatch exists after retry: code=%s", code)
#                     return res_data_retry
#
#                 raise RuntimeError(f"Retry API failed: {retry_message}")
#
#             # other fail
#             raise RuntimeError(f"API returned failure: {message}")
#
#         logging.info("CustomerReceivedBatch success: code=%s", code)
#         return res_data
#
#     except requests.RequestException as e:
#         logging.error("CustomerReceivedBatch request error: code=%s, err=%s", code, e)
#         raise
#
# def api_user_get_user_info(context, tel):
#     url = value_based_env_return(context, Api_Get_User_List_By_Search_Text_Dev,
#                                  Api_Get_User_List_By_Search_Text_Staging)
#
#     params = {"searchText": tel}
#
#     try:
#         response = requests.get(url, params=params)
#         response.raise_for_status()
#         res_data = response.json()
#
#         status_code = res_data.get('status', {}).get('code')
#         if status_code != 'success':
#             raise RuntimeError(f"API returned failure: {res_data.get('status', {}).get('message', 'Unknown error')}")
#
#         customers = res_data.get('data', [])
#         if not customers:
#             raise RuntimeError(f"No customers found for searchText: {search_text}")
#
#         # Return first customer with required fields
#         customer_info = customers[0]
#         return {
#             "pk": customer_info.get("pk"),
#             "uid": customer_info.get("uid"),
#             "name": customer_info.get("name"),
#             "email": customer_info.get("email"),
#             "membershipLevel": customer_info.get("membershipLevel")
#         }
#
#     except requests.RequestException as e:
#         print(f"Customer search request failed: {e}")
#         raise RuntimeError(f"Customer search API failed: {e}")
#
# def api_order_get_consignment_and_waybill(context, order_id):
#     url = value_based_env_return(context, Api_Get_Consignments_Code_Dev, Api_Get_Consignments_Code_Staging)
#
#     consignments = []
#     waybills = []
#
#     page = 1
#     while True:
#         payload = {
#             "orderId": [order_id],
#             "sortDirection": "DESC",
#             "pn": page,
#             "ps": 20
#         }
#
#         try:
#             response = requests.post(url=url, json=payload)
#             response.raise_for_status()
#             data = response.json()
#
#             if 'data' not in data or not isinstance(data['data'], list):
#                 break
#
#             page_items = data['data']
#             if not page_items:
#                 break
#
#             for item in page_items:
#                 consignment_code = item.get('consignmentCode')
#                 waybill_number = item.get('waybillNumber')
#
#                 if consignment_code:
#                     consignments.append(consignment_code)
#                 if waybill_number:
#                     waybills.append(waybill_number)
#
#             if len(page_items) < 20:
#                 break
#
#             page += 1
#
#         except Exception as e:
#             logging.error(f"Failed to get consignments/waybills for order_id={order_id}, page={page}: {e}")
#             print(f"Error: {e}")
#             raise
#
#     # de-duplicate, keep order
#     def unique(seq):
#         seen = set()
#         result = []
#         for x in seq:
#             if x not in seen:
#                 seen.add(x)
#                 result.append(x)
#         return result
#
#     consignments = unique(consignments)
#     waybills = unique(waybills)
#
#     def normalize(values):
#         if not values:
#             return None
#         if len(values) == 1:
#             return values[0]  # single → str
#         return values  # multiple → list[str]
#
#     return {
#         "consignmentCode": normalize(consignments),
#         "waybillNumber": normalize(waybills),
#     }
#






































# # import json
# # from datetime import datetime, timedelta
# #
# # import requests
# #
# MallDevDomain = "https://ecomtest01.hkmpcl.com.hk/"
# MallStagingDomain = "https://www01.hkmpcl.com.hk/"
#
# PaymentGatewayDevURL = "https://hktv-odm-dev.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"
# PaymentGatewayStagingURL = "https://hktv-odm-staging.hkmpcl.com.hk/hktv-odm/s2s/mms/order/search-consignments-and-osg-orders"
#
# # Relative APIs
# CustomerReceivedBatchAPI = "hktvwebservices/v1/hktv/s2s/customerReceivedBatch/create"
# UpdateConsignmentStatusAPI = "hktvwebservices/v1/hktv/s2s/consignment/splitAndUpdateConsignmentStatus"
# GetUserListBySearchTextAPI = "hktvwebservices/v1/hktv/s2s/customer/get_user_list_by_search_text"
# GetOrderWithBatchesAPI = "hktvwebservices/v1/hktv/get_order_with_batches"
# OauthTokenAPI = "hktvwebservices/oauth/token"
#
# DEV = "Dev"
# STAGING = "Staging"
#
# API_MAP = {
#     DEV: {
#         "user_search": MallDevDomain + GetUserListBySearchTextAPI,
#         "order": MallDevDomain + GetOrderWithBatchesAPI,
#         "token": MallDevDomain + OauthTokenAPI,
#         "batch": MallDevDomain + CustomerReceivedBatchAPI,
#         "status": MallDevDomain + UpdateConsignmentStatusAPI,
#         "pg": PaymentGatewayDevURL,
#     },
#     STAGING: {
#         "user_search": MallStagingDomain + GetUserListBySearchTextAPI,
#         "order": MallStagingDomain + GetOrderWithBatchesAPI,
#         "token": MallStagingDomain + OauthTokenAPI,
#         "batch": MallStagingDomain + CustomerReceivedBatchAPI,
#         "status": MallStagingDomain + UpdateConsignmentStatusAPI,
#         "pg": PaymentGatewayStagingURL,
#     },
# }
#
# #
# # def _require_env(env):
# #     if env not in API_MAP:
# #         raise ValueError("Please select an environment (Dev or Staging).")
# #
# #
# # def _api_request(method, url, **kwargs):
# #     try:
# #         resp = requests.request(method, url, **kwargs)
# #         resp.raise_for_status()
# #         return resp.json(), None
# #     except requests.exceptions.RequestException as e:
# #         return None, f"Request failed: {e}"
# #     except json.JSONDecodeError:
# #         return None, "Invalid JSON response"
# #
# #
# # def get_user_list_by_search_text(env, tel):
# #     if not tel:
# #         return None, "Please enter tel."
# #
# #     _require_env(env)
# #     url = API_MAP[env]["user_search"]
# #     result, err = _api_request("GET", url, params={"searchText": tel})
# #     if err:
# #         return None, err
# #
# #     if result.get("status", {}).get("code") == "success" and result.get("data"):
# #         return result["data"][0].get("uid"), "Success"
# #     return None, "No user found or API error"
# #
# #
# # def get_oauth_token(env, username, password):
# #     if not username or not password:
# #         return None, "Please enter both username and password."
# #
# #     _require_env(env)
# #     url = API_MAP[env]["token"]
# #     headers = {"Authorization": "Basic aGt0dl9tYWxsX2lvczojRSlpZytnMVR2Iw=="}
# #     data = {"grant_type": "password", "username": username, "password": password}
# #
# #     result, err = _api_request("POST", url, headers=headers, data=data)
# #     if err:
# #         return None, err
# #
# #     token = result.get("access_token")
# #     if token:
# #         return token, "Success"
# #     return None, "Token request failed"
# #
# #
# # def get_order_with_batches(env, user_id, order_id, bearer_token):
# #     if not user_id or not order_id:
# #         return None, "Please enter both user_id and order_id."
# #
# #     _require_env(env)
# #     url = API_MAP[env]["order"]
# #     headers = {"Authorization": f"bearer {bearer_token}"}
# #     params = {"user_id": user_id, "lang": "zh", "order_id": order_id}
# #
# #     result, err = _api_request("GET", url, headers=headers, params=params)
# #     if err:
# #         return None, err
# #
# #     status_block = result.get("status")
# #     code = status_block.get("code") if isinstance(status_block, dict) else None
# #
# #     if code == "success" or status_block is None:
# #         return result, "Success"
# #     return None, f"No order found or API error (status={code})"
# #
# #
# # def get_consignment_code(env, order_number, store_code):
# #     if not order_number or not store_code:
# #         return None, None, "Please enter both Order number and Store Code."
# #
# #     _require_env(env)
# #     url = API_MAP[env]["pg"]
# #     order_id = f"{order_number}-{store_code}"
# #
# #     payload = {
# #         "orderId": [order_id],
# #         "sortDirection": "DESC",
# #         "pn": 1,
# #         "ps": 20,
# #     }
# #     headers = {"Content-Type": "application/json"}
# #
# #     result, err = _api_request("POST", url, json=payload, headers=headers)
# #     if err:
# #         return None, None, err
# #
# #     if (
# #             result.get("status", {}).get("code", "").lower() == "success"
# #             and result.get("data")
# #     ):
# #         first = result["data"][0]
# #         return first["consignmentCode"], first["status"], "Success"
# #     return None, None, "No consignment code found."
# #
# #
# # def get_yesterday_formatted():
# #     y = datetime.now() - timedelta(days=1)
# #     return f"{y.year}-{y.month:02d}-{y.day:02d}T00:00:00+08:00"
# #
# #
# # def create_customer_received_batch(env, code, consignment_code):
# #     _require_env(env)
# #     if not consignment_code:
# #         raise RuntimeError("Consignment code is required.")
# #
# #     url = API_MAP[env]["batch"]
# #     payload = {
# #         "code": code,
# #         "customerReceivedTime": get_yesterday_formatted(),
# #         "consignments": [consignment_code],
# #         "referenceFiles": [
# #             {
# #                 "imageData": "https://dyn-img-dev.hkmpcl.com.hk/mkgb/common/wzu/emw/ZAbvdmkaqK20240521165451.png",
# #                 "imageSeq": 1,
# #                 "imageCategory": "CUST_SIGN",
# #             }
# #         ],
# #     }
# #
# #     for attempt in range(2):
# #         result, err = _api_request("POST", url, json=payload)
# #         if err:
# #             if attempt == 1:
# #                 raise RuntimeError(err)
# #             continue
# #
# #         status = result.get("status", {})
# #         code = status.get("code", "").lower()
# #         msg = status.get("message", "")
# #
# #         if code == "success" or "customer received batch already" in msg:
# #             return result
# #         if attempt == 0:
# #             continue
# #         raise RuntimeError(f"API returned failure: {status}")
# #
# #     raise RuntimeError("Failed to create customer received batch after retries.")
# #
# #
# # def split_and_update_consignment_status(env, consignment_code, status):
# #     _require_env(env)
# #     url = API_MAP[env]["status"]
# #     data = {"consignmentCode": consignment_code, "status": status}
# #
# #     result, err = _api_request("POST", url, data=data)
# #     if err:
# #         raise RuntimeError(err)
# #
# #     if result.get("status", {}).get("code") != "success":
# #         raise RuntimeError(f"API call unsuccessful. Status: {result.get('status')}")
# #
# #     try:
# #         return result["data"]["status"]
# #     except (KeyError, TypeError):
# #         raise ValueError("Response missing required 'data.status' field.")
