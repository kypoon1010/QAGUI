import logging
import requests

# API URL 和 Gateway 名稱
PaymentGatewayDevURL = "https://hktvpayment-prm-dev.hkmpcl.com.hk/hktv_prm/s2s/payment/updatePaymentStrategySettings"
PaymentGatewayStagingURL = "https://hktvpayment-prm-staging.hkmpcl.com.hk/hktv_prm/s2s/payment/updatePaymentStrategySettings"

MPGSGateway = "mpgs"
CybersourceGateway = "cybersource"
PaydollarGateway = "paydollar"
ALL_GATEWAYS = [MPGSGateway, CybersourceGateway, PaydollarGateway]


def toggle_gateway(context, gateway, active: bool):
    link = PaymentGatewayDevURL if context['selected_domain'] == "Dev" else PaymentGatewayStagingURL
    action = "Open" if active else "Close"
    payload = {'gateway': gateway, 'active': str(active).lower()}
    try:
        res = requests.post(url=link, params=payload)
        res.raise_for_status()
        res_data = res.json()
        status = res_data['apiStatusInfo']['statusCode']
        result = f"{gateway.capitalize()} {action}: {status}"
        return result
    except Exception as e:
        logging.error(f"Error during {gateway} {action}: {e}")
        return f"Error during {gateway} {action}: {e}"


def set_gateway_status(context, enable_gateways):
    results = []
    for gw in ALL_GATEWAYS:
        active = gw in enable_gateways
        results.append(toggle_gateway(context, gw, active))
    return "\n".join(filter(None, results))


def MPGS_Gateway_Only(context):
    return set_gateway_status(context, [MPGSGateway])


def Cybersource_Gateway_Only(context):
    return set_gateway_status(context, [CybersourceGateway])


def Paydollar_Gateway_Only(context):
    return set_gateway_status(context, [PaydollarGateway])


def All_Gateway_Open(context):
    return set_gateway_status(context, ALL_GATEWAYS)