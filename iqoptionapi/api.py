import time,random
import json
import logging
import threading
import requests
import ssl
import atexit
from collections import deque
from iqoptionapi.http.login import Login
from iqoptionapi.http.loginv2 import Loginv2
from iqoptionapi.http.logout import Logout
from iqoptionapi.http.login2fa import Login2FA
from iqoptionapi.http.send_sms import SMS_Sender
from iqoptionapi.http.verify import Verify
from iqoptionapi.http.getprofile import Getprofile
from iqoptionapi.http.auth import Auth
from iqoptionapi.http.token import Token
from iqoptionapi.http.appinit import Appinit
from iqoptionapi.http.billing import Billing
from iqoptionapi.http.buyback import Buyback

from iqoptionapi.http.events import Events
from iqoptionapi.ws.client import WebsocketClient

from iqoptionapi.ws.chanels.ssid import Ssid
from iqoptionapi.ws.chanels.setactives import SetActives
from iqoptionapi.ws.chanels.buy_place_order_temp import Buy_place_order_temp
from iqoptionapi.ws.chanels.heartbeat import Heartbeat


from iqoptionapi.ws.objects.timesync import TimeSync
from iqoptionapi.ws.objects.profile import Profile
from iqoptionapi.ws.objects.candles import Candles
from iqoptionapi.ws.objects.listinfodata import ListInfoData
from iqoptionapi.ws.objects.betinfo import Game_betinfo_data
import iqoptionapi.global_value as global_value
from collections import defaultdict

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))


requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member


class API(object):  # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-public-methods
    socket_option_opened = {}
    socket_option_closed = {}
    timesync = TimeSync()
    profile = Profile()
    candles = {}
    listinfodata = ListInfoData()
    # for digital
    position_changed = None
    instrument_quites_generated_data = nested_dict(2, dict)
    instrument_quites_generated_timestamp = nested_dict(2, dict)
    leaderboard_deals_client = None
    #position_changed_data = nested_dict(2, dict)
    # microserviceName_binary_options_name_option=nested_dict(2,dict)
    order_async = nested_dict(2, dict)
    order_binary = {}
    game_betinfo = Game_betinfo_data()
    instruments = None
    financial_information = None
    buy_order_id = None
    buy_forex_id = None
    positions_forex= None
    fechadas_forex = None
    pendentes_forex = None
    cancel_order_forex = None
    traders_mood = {}  # get hight(put) %
    order_data = None
    positions = None
    position = None
    deferred_orders = None
    position_history_v2 = None
    available_leverages = None
    order_canceled = None
    close_position_data = None


    subscribe_commission_changed_data = nested_dict(2, dict)
    real_time_candles = nested_dict(3, dict)
    real_time_candles_maxdict_table = nested_dict(2, dict)
    candle_generated_check = nested_dict(2, dict)


    sold_options_respond = None
    tpsl_changed_respond = None
    auto_margin_call_changed_respond = None
    top_assets_updated_data = {}
    get_options_v2_data = None
    # --for binary option multi buy
    buy_multi_result = None


    result = None
    training_balance_reset_request = None
    balances_raw = None
    user_profile_client = None
    leaderboard_userinfo_deals_client = None
    users_availability = None

    orders_history = []
    #novas funções dos alertas
    alerta = None
    alertas = None
    alertas_tocados = []
    #nova função que puxa todos os realtimes
    all_realtime_candles = {}
    #novas funções do forex
    buy_forex_id = None
    positions_forex= None
    fechadas_forex = None
    pendentes_forex = None
    cancel_order_forex = None
    leverage_forex = None
    #nova função compra digital
    orders = {}
    #nova função captura payouts
    payout_digitais = {}
    assets_digital = None
    payout_binarias = {}
    underliyng_list = None


    def __init__(self, username, password, proxies=None):

        self.host = "iqoption.com"
        self.url_auth2 = f"https://auth.{self.host}/api/v2/verify/2fa"
        self.https_url = f"https://{self.host}/api".format(host=self.host)
        self.wss_url = f"wss://{self.host}/echo/websocket".format(host=self.host)
        self.url_events = f"https://event.{self.host}/api/v1/events"
        self.url_login = f"https://auth.{self.host}/api/v2/login"
        self.url_logout = f"https://auth.{self.host}/api/v1.0/logout"
        
        self.websocket_client = None
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.username = username
        self.password = password
        self.token_login2fa = None
        self.token_sms = None
        self.proxies = proxies


        self.__active_account_type = None
        self.mutex = threading.Lock()
        self.request_id = 0

    def prepare_http_url(self, resource):
        return "/".join((self.https_url, resource.url))

    def send_http_request(self, resource, method, data=None, params=None, headers=None):  # pylint: disable=too-many-arguments

        logger = logging.getLogger(__name__)
        url = self.prepare_http_url(resource)

        logger.debug(url)

        response = self.session.request(method=method,
                                        url=url,
                                        data=data,
                                        params=params,
                                        headers=headers,
                                        proxies=self.proxies)
        logger.debug(response)
        logger.debug(response.text)
        logger.debug(response.headers)
        logger.debug(response.cookies)

        response.raise_for_status()
        return response

    def send_http_request_v2(self, url, method, data=None, params=None, headers=None):  # pylint: disable=too-many-arguments

        logger = logging.getLogger(__name__)

        logger.debug(method + ": " + url + " headers: " + str(self.session.headers) +
                     " cookies:  " + str(self.session.cookies.get_dict()))

        response = self.session.request(method=method,
                                        url=url,
                                        data=data,
                                        params=params,
                                        headers=headers,
                                        proxies=self.proxies)
        logger.debug(response)
        logger.debug(response.text)
        logger.debug(response.headers)
        logger.debug(response.cookies)

        # response.raise_for_status()
        return response

    @property
    def websocket(self):
        return self.websocket_client.wss

    def send_websocket_request(self, name, msg, request_id="", no_force_send=True):

        logger = logging.getLogger(__name__)

        self.mutex.acquire()
        self.request_id += 1
        request = self.request_id if request_id == "" else request_id
        self.mutex.release()

        data = json.dumps(dict(name=name, request_id=str(request), msg=msg))

        while (global_value.ssl_Mutual_exclusion or global_value.ssl_Mutual_exclusion_write) and no_force_send:
            pass
        global_value.ssl_Mutual_exclusion_write = True
        self.websocket.send(data)
        logger.debug(data)
        global_value.ssl_Mutual_exclusion_write = False

        return str(request)

    @property
    def logout(self):
        return Logout(self)

    @property
    def login(self):
        return Login(self)

    @property
    def login_2fa(self):
        return Login2FA(self)

    @property
    def send_sms_code_OLD(self):
        return SMS_Sender(self)

    @property
    def verify_2fa(self):
        return Verify(self)

    @property
    def loginv2(self):
        return Loginv2(self)

    @property
    def auth(self):
        return Auth(self)

    @property
    def appinit(self):
        return Appinit(self)

    @property
    def token(self):
        return Token(self)

    @property
    def events(self):
        return Events(self)

    @property
    def billing(self):
        return Billing(self)

    @property
    def buyback(self):
        return Buyback(self)
# ------------------------------------------------------------------------

    @property
    def getprofile(self):
        return Getprofile(self)
# for active code ...


    @property
    def ssid(self):
        return Ssid(self)
# --------------------------------------------------------------------------------


    def set_user_settings(self, balanceId, request_id=""):
        # Main name:"unsubscribeMessage"/"subscribeMessage"/"sendMessage"(only for portfolio.get-positions")
        # name:"portfolio.order-changed"/"portfolio.get-positions"/"portfolio.position-changed"
        # instrument_type="cfd"/"forex"/"crypto"/"digital-option"/"turbo-option"/"binary-option"

        msg = {"name": "set-user-settings",
               "version": "1.0",
               "body": {
                   "name": "traderoom_gl_common",
                   "version": 3,
                   "config": {
                       "balanceId": balanceId

                   } } }
        self.send_websocket_request(
            name="sendMessage", msg=msg, request_id=str(request_id))

    def subscribe_position_changed(self, name, instrument_type, request_id):
        # instrument_type="multi-option","crypto","forex","cfd"
        # name="position-changed","trading-fx-option.position-changed",digital-options.position-changed
        msg = {"name": name,
               "version": "1.0",
               "params": {
                   "routingFilters": {"instrument_type": str(instrument_type)}
               } }
        self.send_websocket_request(
            name="subscribeMessage", msg=msg, request_id=str(request_id))

    def setOptions(self, request_id, sendResults):
        msg = {"sendResults": sendResults}
        self.send_websocket_request(
            name="setOptions", msg=msg, request_id=str(request_id))



    @property
    def setactives(self):
        return SetActives(self)


# ____BUY_for__Forex__&&__stock(cfd)__&&__ctrpto_____
    @property
    def buy_order(self):
        return Buy_place_order_temp(self)

    @property
    def heartbeat(self):
        return Heartbeat(self)
# -------------------------------------------------------

    def set_session(self, cookies, headers):
        """Method to set session cookies."""

        self.session.headers.update(headers)

        self.session.cookies.clear_session_cookies()
        requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)

    def start_websocket(self):
        global_value.check_websocket_if_connect = None
        global_value.check_websocket_if_error = False
        global_value.websocket_error_reason = None

        self.websocket_client = WebsocketClient(self)

        self.websocket_thread = threading.Thread(target=self.websocket.run_forever, kwargs={'sslopt': {
                                                 "check_hostname": False, "cert_reqs": ssl.CERT_NONE, "ca_certs": "cacert.pem"}})  # for fix pyinstall error: cafile, capath and cadata cannot be all omitted
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        while True:
            try:
                if global_value.check_websocket_if_error:
                    return False, global_value.websocket_error_reason

                if global_value.check_websocket_if_connect == 0:
                    return False, "Websocket connection closed."
                    
                elif global_value.check_websocket_if_connect == 1:

                    return True, None
            except Exception as err:
                pass

            pass

    # @tokensms.setter
    def setTokenSMS(self, response):
        token_sms = response.json()['token']
        self.token_sms = token_sms

    # @token2fa.setter
    def setToken2FA(self, response):
        token_2fa = response.json()['token']
        self.token_login2fa = token_2fa

    def get_ssid(self):
        response = None
        try:
            if self.token_login2fa is None:
                response = self.login(
                    self.username, self.password)  # pylint: disable=not-callable
            else:
                response = self.login_2fa(
                    self.username, self.password, self.token_login2fa)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(e)
            return e
        return response

    def send_ssid(self):
        self.profile.msg = None
        self.ssid(global_value.SSID)  # pylint: disable=not-callable
        while self.profile.msg == None:
            pass
        if self.profile.msg == False:
            return False
        else:
            return True

    def connect(self):

        global_value.ssl_Mutual_exclusion = False
        global_value.ssl_Mutual_exclusion_write = False
        """Method for connection to IQ Option API."""
        try:
            self.close()
        except:
            pass
        check_websocket, websocket_reason = self.start_websocket()

        if check_websocket == False:
            return check_websocket, websocket_reason

        # doing temp ssid reconnect for speed up
        if global_value.SSID != None:

            check_ssid = self.send_ssid()

            if check_ssid == False:
                # ssdi time out need reget,if sent error ssid,the weksocket will close by iqoption server
                response = self.get_ssid()
                try:
                    global_value.SSID = response.cookies["ssid"]
                except:
                    return False, response.text
                atexit.register(self.logout)
                self.start_websocket()
                self.send_ssid()

        # the ssid is None need get ssid
        else:
            response = self.get_ssid()
            try:
                global_value.SSID = response.cookies["ssid"]
            except:
                self.close()
                return False, response.text
            atexit.register(self.logout)
            self.send_ssid()

        # set ssis cookie
        requests.utils.add_dict_to_cookiejar(
            self.session.cookies, {"ssid": global_value.SSID})

        self.timesync.server_timestamp = None
        while True:
            try:
                if self.timesync.server_timestamp != None:
                    break
            except:
                pass
        return True, None

    def connect2fa(self, sms_code):
        response = self.verify_2fa(sms_code, self.token_sms)

        if response.json()['code'] != 'success':
            return False, response.json()['message']

        # token_2fa
        self.setToken2FA(response)
        if self.token_login2fa is None:
            return False, None
        return True, None

    def close(self):
        self.websocket.close()
        self.websocket_thread.join()

    def websocket_alive(self):
        return self.websocket_thread.is_alive()

    
    #############################################################################################
    # funções novas adicionadas, Lucas Feix:
    # alteração automatica dos pares no constants
    # função do payout digital melhorada
    # função de criar, excluir e puxar todos os alertas
    # função de puxar preços atuais melhorada
    # criada função de operar forex marginal
    # melhorada função de operar forex normal
    # opção de conectar com autenticação de 2 fatores
    # opção de conectar em conta torneio
    # atualizada função getcandles para receber pares simultâneos

    def _post(self, data=None, headers=None):
        return self.send_http_request_v2(method="POST", url=self.url_auth2,data=json.dumps(data), headers=headers)

    def send_sms_code(self,metodo, token_reason):

        data = {"method": str(metodo),
                "token": token_reason}

        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Referer': f'https://{self.host}/en/login',
            'Sec-Fetch-Mode': 'cors',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
            }

        return self._post(data=data, headers=headers)
    
    def addcandles(self, request_id, candles_data):
        self.candles[request_id] = Candles(candles_data)

    

