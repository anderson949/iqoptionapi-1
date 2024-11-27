from iqoptionapi.api import API
import iqoptionapi.constants as OP_code
import iqoptionapi.country_id as Country
import threading
import time
import json
import logging
import operator
import iqoptionapi.global_value as global_value
from collections import defaultdict
from collections import deque
from iqoptionapi.expiration import get_expiration_time, get_remaning_time
from iqoptionapi.version_control import api_version
from datetime import datetime, timedelta
from random import randint
import queue

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))


class IQ_Option:
    __version__ = api_version

    def __init__(self, email, password, active_account_type="PRACTICE"):
        self.size = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800,
                     3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]
        self.email = email
        self.password = password
        self.suspend = 0.5
        self.thread = None
        self.subscribe_candle = []
        self.subscribe_candle_all_size = []
        self.subscribe_mood = []
        self.subscribe_indicators = []
        # for digit
        self.get_digital_spot_profit_after_sale_data = nested_dict(2, int)
        self.get_realtime_strike_list_temp_data = {}
        self.get_realtime_strike_list_temp_expiration = 0
        self.SESSION_HEADER = {
            "User-Agent": r"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36"}
        self.SESSION_COOKIE = {}
        self.count = 0
        self.q = queue.Queue(maxsize=4)


    def get_server_timestamp(self):
        return self.api.timesync.server_timestamp

    def re_subscribe_stream(self):
        try:
            for ac in self.subscribe_candle:
                sp = ac.split(",")
                self.start_candles_one_stream(sp[0], sp[1])
        except:
            pass
        # -----------------
        try:
            for ac in self.subscribe_candle_all_size:
                self.start_candles_all_size_stream(ac)
        except:
            pass
        # -------------reconnect subscribe_mood
        try:
            for ac in self.subscribe_mood:
                self.start_mood_stream(ac)
        except:
            pass

    def set_session(self, header, cookie):
        self.SESSION_HEADER = header
        self.SESSION_COOKIE = cookie

    def connect_2fa(self, sms_code):
        return self.connect(sms_code=sms_code)

    def check_connect(self):

        if not global_value.check_websocket_if_connect:
            return False
        else:
            return True
        # wait for timestamp getting

    def get_all_ACTIVES_OPCODE(self):
        return OP_code.ACTIVES

    def update_ACTIVES_OPCODE(self):
        # update from binary option
        self.get_ALL_Binary_ACTIVES_OPCODE()
        # crypto /dorex/cfd
        self.instruments_input_all_in_ACTIVES()
        dicc = {}
        for lis in sorted(OP_code.ACTIVES.items(), key=operator.itemgetter(1)):
            dicc[lis[0]] = lis[1]
        OP_code.ACTIVES = dicc

    def get_name_by_activeId(self, activeId):
        info = self.get_financial_information(activeId)
        try:
            return info["msg"]["data"]["active"]["name"]
        except:
            return None

    def get_financial_information(self, activeId):
        self.api.financial_information = None
        data = {"name":"get-financial-information", "version":"1.0", "body":{
                "query":"query GetAssetProfileInfo($activeId:ActiveID!, $locale: LocaleName){\n active(id: $activeId) {\n id\n name(source: TradeRoom, locale: $locale)\n ticker\n media {\n siteBackground\n }\n charts {\n dtd {\n change\n }\n m1 {\n change\n }\n y1 {\n change\n }\n ytd {\n change\n }\n }\n index_fininfo: fininfo {\n ... on Index {\n description(locale: $locale)\n }\n }\n fininfo {\n ... on Pair {\n type\n description(locale: $locale)\n currency {\n name(locale: $locale)\n }\n base {\n name(locale: $locale)\n ... on Stock {\n company {\n country {\n nameShort\n }\n gics {\n sector\n industry\n }\n site\n domain\n }\n keyStat {\n marketCap\n peRatioHigh\n }\n }\n ... on CryptoCurrency {\n site\n domain\n coinsInCirculation\n maxCoinsQuantity\n volume24h\n marketCap\n }\n }\n }\n }\n }\n }",
                "operationName": "GetAssetProfileInfo", "variables":{"activeId":activeId} }}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.financial_information == None:
            pass
        return self.api.financial_information

    def get_leader_board(self, country, from_position, to_position, near_traders_count, user_country_id=0, near_traders_country_count=0, top_country_count=0, top_count=0, top_type=2):
        self.api.leaderboard_deals_client = None
        country_id = Country.ID[country]
        data = {"name":"request-leaderboard-deals-client", "version":"1.0",
                "body":{"country_id":country_id,
                        "user_country_id":user_country_id,
                        "from_position":from_position,
                        "to_position":to_position,
                        "near_traders_country_count":near_traders_country_count,
                        "near_traders_count":near_traders_count,
                        "top_country_count":top_country_count,
                        "top_count":top_count,
                        "top_type":top_type}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.leaderboard_deals_client == None:
            pass
        return self.api.leaderboard_deals_client

    def get_instruments(self, type):
        # type="crypto"/"forex"/"cfd"
        time.sleep(self.suspend)
        self.api.instruments = None
        while self.api.instruments == None:
            try:
                data = {"name":"get-instruments", "version":"4.0", "body":{"type":type}}
                name = "sendMessage"
                self.api.send_websocket_request(name, data)
                start = time.time()
                while self.api.instruments == None and time.time() - start < 10:
                    pass
            except:
                logging.error('**error** api.get_instruments need reconnect')
                self.connect()
        return self.api.instruments

    def instruments_input_to_ACTIVES(self, type):
        instruments = self.get_instruments(type)
        for ins in instruments["instruments"]:
            OP_code.ACTIVES[ins["id"]] = ins["active_id"]

    def instruments_input_all_in_ACTIVES(self):
        self.instruments_input_to_ACTIVES("crypto")
        self.instruments_input_to_ACTIVES("forex")
        self.instruments_input_to_ACTIVES("cfd")

    def get_ALL_Binary_ACTIVES_OPCODE(self):
        init_info = self.get_all_init()
        for dirr in (["binary", "turbo"]):
            for i in init_info["result"][dirr]["actives"]:
                OP_code.ACTIVES[(init_info["result"][dirr]["actives"][i]["name"]).split(".")[1]] = int(i)

    def get_profile_ansyc(self):
        while self.api.profile.msg == None:
            pass
        return self.api.profile.msg

    def get_currency(self):
        balances_raw = self.get_balances()
        for balance in balances_raw["msg"]:
            if balance["id"] == global_value.balance_id:
                return balance["currency"]

    def get_balance_id(self):
        return global_value.balance_id

    def get_balance(self):
        balances_raw = self.get_balances()
        for balance in balances_raw["msg"]:
            if balance["id"] == global_value.balance_id:
                return balance["amount"]

    def get_balances(self):
        self.api.balances_raw = None
        '''
        data = {"name": "internal-billing.get-balances",
        "version": "1.0",
        "body": {
            "types_ids": [1, 4,2],
            "tournaments_statuses_ids": [ 3,2]}}
        '''
        data = {"name": "internal-billing.get-balances", "version": "1.0",}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.balances_raw == None:
            pass
        return self.api.balances_raw

    def get_balance_mode(self):
        # self.api.profile.balance_type=None
        profile = self.get_profile_ansyc()
        for balance in profile.get("balances"):
            if balance["id"] == global_value.balance_id:
                if balance["type"] == 1:
                    return "REAL"
                elif balance["type"] == 4:
                    return "PRACTICE"
                elif balance["type"] == 2:
                    return "TOURNAMENT"

    def reset_practice_balance(self):
        self.api.training_balance_reset_request = None
        name="sendMessage"
        data={"name": "reset-training-balance","version": "2.0"}
        self.api.send_websocket_request(name, data)
        while self.api.training_balance_reset_request == None:
            pass
        return self.api.training_balance_reset_request
    
    def position_change_all(self, Main_Name, user_balance_id):
        instrument_type = ["cfd", "forex", "crypto", "digital-option", "turbo-option", "binary-option"]
        for ins in instrument_type:
            data = {"name": "portfolio.position-changed", "version": "3.0", "params":
                    {"routingFilters": {"instrument_type": str(ins),"user_balance_id": user_balance_id}}}
            name = Main_Name
            self.api.send_websocket_request(name, data)

    def order_changed_all(self, Main_Name):
        instrument_type = ["cfd", "forex", "crypto", "digital-option", "turbo-option", "binary-option"]
        for ins in instrument_type:
            data = {"name": "portfolio.order-changed", "version": "2.0",
                   "params": {"routingFilters": {"instrument_type": str(ins)}}}
            name = Main_Name
            self.api.send_websocket_request(name, data)

    def change_balance(self, Balance_MODE):
        def set_id(b_id):
            if global_value.balance_id != None:
                self.position_change_all(
                    "unsubscribeMessage", global_value.balance_id)
            global_value.balance_id = b_id
            self.position_change_all("subscribeMessage", b_id)
        real_id = None
        practice_id = None
        tournament_id = None
        for balance in self.get_profile_ansyc()["balances"]:
            if balance["type"] == 1:
                real_id = balance["id"]
            if balance["type"] == 4:
                practice_id = balance["id"]
            if balance["type"] == 2:
                tournament_id = balance["id"]
        if Balance_MODE == "REAL":
            set_id(real_id)
        elif Balance_MODE == "PRACTICE":
            set_id(practice_id)
        elif Balance_MODE == "TOURNAMENT":
            set_id(tournament_id)
        else:
            logging.error("ERROR doesn't have this mode")
            exit(1)

    def get_candles(self, ACTIVES, interval, count, endtime):
        if ACTIVES not in OP_code.ACTIVES:
            print('Asset {} not found in constants'.format(ACTIVES))
            return None
        request_id = ''
        while True:
            try:
                active_id = OP_code.ACTIVES[ACTIVES]
                data = {"name":"get-candles",
                        "version":"2.0",
                        "body":{"active_id":int(active_id),
                                "split_normalization": True,
                                "size":interval,#time size sample:if interval set 1 mean get time 0~1 candle 
                                "to":int(endtime),   #int(self.api.timesync.server_timestamp),
                                "count":count,#get how many candle
                                "":active_id } }
                name = "sendMessage"
                request_id = self.api.send_websocket_request(name, data)
                start_time = time.time()
                while self.check_connect and request_id not in self.api.candles:
                    if time.time() - start_time > 10:  # Tempo limite de 10 segundos
                        #raise TimeoutError('Erro API, Tempo limite aguardando candles')
                        self.connect()
                        break 
                    time.sleep(0.1)
                if request_id in self.api.candles:
                    break
            except:
                logging.error('**error** get_candles need reconnect')
                self.connect()
        return self.api.candles.pop(request_id).candles_data

    def subscribe_top_assets_updated(self, instrument_type):
        data = {"name": "top-assets-updated",
                "params": {"routingFilters": {"instrument_type": str(instrument_type)}},"version": "3.0"}
        name = "subscribeMessage"
        self.api.send_websocket_request(name, data)

    def unsubscribe_top_assets_updated(self, instrument_type):
        data = {"name": "top-assets-updated", "version": "3.0",
                "params": {"routingFilters": {"instrument_type": str(instrument_type)}}}
        name = "unsubscribeMessage"
        self.api.send_websocket_request(name, data)

    def get_top_assets_updated(self, instrument_type):
        if instrument_type in self.api.top_assets_updated_data:
            return self.api.top_assets_updated_data[instrument_type]
        else:
            return None

    def subscribe_commission_changed(self, instrument_type):
        data = {"name": "commission-changed", "version": "1.0",
                "params": {"routingFilters": {"instrument_type": str(instrument_type)}}}
        name = "subscribeMessage"
        self.api.send_websocket_request(name, data)

    def unsubscribe_commission_changed(self, instrument_type):
        data = {"name": "commission-changed", "version": "1.0",
                "params": {"routingFilters": {"instrument_type": str(instrument_type)}}}
        name = "unsubscribeMessage"
        self.api.send_websocket_request(name, data)

    def get_commission_change(self, instrument_type):
        return self.api.subscribe_commission_changed_data[instrument_type]

    def start_mood_stream(self, ACTIVES, instrument="turbo-option"):
        if ACTIVES in self.subscribe_mood == False:
            self.subscribe_mood.append(ACTIVES)

        while True:
            active = OP_code.ACTIVES[ACTIVES]
            data = {
                "name": "traders-mood-changed",
                "params":
                    {"routingFilters": {
                                "instrument": instrument,
                                "asset_id": active
                            }}}
            name = "subscribeMessage"
            self.api.send_websocket_request(name, data)
            try:
                self.api.traders_mood[OP_code.ACTIVES[ACTIVES]]
                break
            except:
                time.sleep(5)

    def stop_mood_stream(self, ACTIVES, instrument="turbo-option"):
        if ACTIVES in self.subscribe_mood == True:
            del self.subscribe_mood[ACTIVES]
            active = OP_code.ACTIVES[ACTIVES]
            data = {"name": "traders-mood-changed","params":
                    {"routingFilters": {"instrument": instrument,"asset_id": active}}}
            name = "unsubscribeMessage"
            self.api.send_websocket_request(name, data)

    def get_traders_mood(self, ACTIVES):
        # return highter %
        return self.api.traders_mood[OP_code.ACTIVES[ACTIVES]]

    def get_all_traders_mood(self):
        # return highter %
        return self.api.traders_mood

    def check_binary_order(self, order_id):
        while order_id not in self.api.order_binary:
            pass
        your_order = self.api.order_binary[order_id]
        del self.api.order_binary[order_id]
        return your_order

    def check_win_v4(self, id_number):
        while True:
            time.sleep(0.05)
            try:
                if self.api.socket_option_closed[id_number] != None:
                    break
            except:
                pass
        x = self.api.socket_option_closed[id_number]
        return x['msg']['win'], (0 if x['msg']['win'] == 'equal' else float(x['msg']['sum']) * -1 if x['msg']['win'] == 'loose' else float(x['msg']['win_amount']) - float(x['msg']['sum']))

    def check_win_v3(self, id_number):
        try:
            if self.get_async_order(id_number)["option-closed"] !={}:
                 return True, self.get_async_order(id_number)["option-closed"]["msg"]["profit_amount"]-self.get_async_order(id_number)["option-closed"]["msg"]["amount"]
            else:
                return False, None
        except:
            pass

    def get_optioninfo_v2(self, limit):
        self.api.get_options_v2_data = None
        data = {"name":"get-options",
                "body":{"limit":limit, 
                        "instrument_type":"binary,turbo",
                        "user_balance_id":int(global_value.balance_id)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.get_options_v2_data == None:
            pass
        return self.api.get_options_v2_data

    def get_remaning(self, duration):
        for remaning in get_remaning_time(self.api.timesync.server_timestamp):
            if remaning[0] == duration:
                return remaning[1]
        logging.error('get_remaning(self,duration) ERROR duration')
        return "ERROR duration"

    def sell_option(self, options_ids):
        self.api.sold_options_respond = None
        data = {"name":"sell-options","version":"3.0", "body":{"options_ids":(options_ids)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.sold_options_respond == None:
            pass
        return self.api.sold_options_respond

    def get_digital_spot_profit_after_sale(self, position_id):
        def get_instrument_id_to_bid(data, instrument_id):
            for row in data["msg"]["quotes"]:
                if row["symbols"][0] == instrument_id:
                    return row["price"]["bid"]
            return None
        while self.get_async_order(position_id)["position-changed"] == {}:
            pass
        # ___________________/*position*/_________________
        position = self.get_async_order(position_id)["position-changed"]["msg"]
        # doEURUSD201911040628PT1MPSPT
        # z mean check if call or not
        if position["instrument_id"].find("MPSPT"):
            z = False
        elif position["instrument_id"].find("MCSPT"):
            z = True
        else:
            logging.error(
                'get_digital_spot_profit_after_sale position error' + str(position["instrument_id"]))

        ACTIVES = position['raw_event']['instrument_underlying']
        amount = max(position['raw_event']["buy_amount"],
                     position['raw_event']["sell_amount"])
        start_duration = position["instrument_id"].find("PT") + 2
        end_duration = start_duration + \
            position["instrument_id"][start_duration:].find("M")

        duration = int(position["instrument_id"][start_duration:end_duration])
        z2 = False
        getAbsCount = position['raw_event']["count"]
        instrumentStrikeValue = position['raw_event']["instrument_strike_value"] / 1000000.0
        spotLowerInstrumentStrike = position['raw_event']["extra_data"]["lower_instrument_strike"] / 1000000.0
        spotUpperInstrumentStrike = position['raw_event']["extra_data"]["upper_instrument_strike"] / 1000000.0
        aVar = position['raw_event']["extra_data"]["lower_instrument_id"]
        aVar2 = position['raw_event']["extra_data"]["upper_instrument_id"]
        getRate = position['raw_event']["currency_rate"]
        # ___________________/*position*/_________________
        instrument_quites_generated_data = self.get_instrument_quites_generated_data(
            ACTIVES, duration)
        f_tmp = get_instrument_id_to_bid(
            instrument_quites_generated_data, aVar)
        # f is bidprice of lower_instrument_id ,f2 is bidprice of upper_instrument_id
        if f_tmp != None:
            self.get_digital_spot_profit_after_sale_data[position_id]["f"] = f_tmp
            f = f_tmp
        else:
            f = self.get_digital_spot_profit_after_sale_data[position_id]["f"]
        f2_tmp = get_instrument_id_to_bid(
            instrument_quites_generated_data, aVar2)
        if f2_tmp != None:
            self.get_digital_spot_profit_after_sale_data[position_id]["f2"] = f2_tmp
            f2 = f2_tmp
        else:
            f2 = self.get_digital_spot_profit_after_sale_data[position_id]["f2"]
        if (spotLowerInstrumentStrike != instrumentStrikeValue) and f != None and f2 != None:
            if (spotLowerInstrumentStrike > instrumentStrikeValue or instrumentStrikeValue > spotUpperInstrumentStrike):
                if z:
                    instrumentStrikeValue = (spotUpperInstrumentStrike - instrumentStrikeValue) / abs(
                        spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                    f = abs(f2 - f)
                else:
                    instrumentStrikeValue = (instrumentStrikeValue - spotUpperInstrumentStrike) / abs(
                        spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                    f = abs(f2 - f)
            elif z:
                f += ((instrumentStrikeValue - spotLowerInstrumentStrike) /
                      (spotUpperInstrumentStrike - spotLowerInstrumentStrike)) * (f2 - f)
            else:
                instrumentStrikeValue = (spotUpperInstrumentStrike - instrumentStrikeValue) / (
                    spotUpperInstrumentStrike - spotLowerInstrumentStrike)
                f -= f2
            f = f2 + (instrumentStrikeValue * f)
        if z2:
            pass
        if f != None:
            # price=f/getRate
            price = (f / getRate)
            # getAbsCount Reference
            return price * getAbsCount - amount
        else:
            return None

    def close_digital_option(self, position_id):
        self.api.result = None
        while self.get_async_order(position_id)["position-changed"] == {}:
            pass
        position_changed = self.get_async_order(position_id)["position-changed"]["msg"]
        position_id = position_changed["external_id"]
        data = {"name": "digital-options.close-position", "version": "1.0",
                "body": {"position_id": int(position_id)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.result == None:
            pass
        return self.api.result

    def check_win_digital_v2(self, buy_order_id):
        while True:
            order_data = self.get_async_order(buy_order_id)
            if order_data['closed']== True:
                break
            time.sleep(0.01)
        order_data = order_data['msg']
        if order_data != None:
            if order_data["status"] == "closed":
                return True, order_data["pnl_realized"]
            else:
                return False, None
        else:
            return False, None

    def buy_order(self,instrument_type, instrument_id, side, amount, leverage,
                  type, limit_price=None, stop_price=None, stop_lose_kind=None,
                  stop_lose_value=None, take_profit_kind=None, take_profit_value=None,
                  use_trail_stop=False, auto_margin_call=False, use_token_for_commission=False):
        self.api.buy_order_id = None
        self.api.buy_order(
                    instrument_type=instrument_type, instrument_id=instrument_id,
                    side=side, amount=amount, leverage=leverage,
                    type=type, limit_price=limit_price, stop_price=stop_price,
                    stop_lose_value=stop_lose_value, stop_lose_kind=stop_lose_kind,
                    take_profit_value=take_profit_value, take_profit_kind=take_profit_kind,
                    use_trail_stop=use_trail_stop, auto_margin_call=auto_margin_call,
                    use_token_for_commission=use_token_for_commission)
        while self.api.buy_order_id == None:
            pass
        check, data = self.get_order(self.api.buy_order_id)
        while data["status"] == "pending_new":
            check, data = self.get_order(self.api.buy_order_id)
            time.sleep(1)
        if check:
            if data["status"] != "rejected":
                return True, self.api.buy_order_id
            else:
                return False, data["reject_status"]
        else:
            return False, None

    def leverage_forex(self, par):
        self.api.leverage_forex = None
        self.api.get_leverage_forex()
        while self.api.leverage_forex == None:
            time.sleep(0.3)
            pass
        leverage =  self.api.leverage_forex
        try:
            for i in leverage["msg"]['items']:
                if par in i['name']:
                    leverage = i['max_leverages']['0']
            return leverage
        except:
            return None

    def buy_forex_order(self, par,direcao,valor_entrada,preco_entrada,win,lose):
        self.api.buy_forex_id = None
        leverage = self.leverage_forex(par)
        par = OP_code.ACTIVES[par]
        self.api.buy_order_forex(leverage,par,direcao,valor_entrada,preco_entrada,win,lose)
        while self.api.buy_forex_id == None:
            time.sleep(0.3)
            pass
        if self.api.buy_forex_id["status"] == 2000:
            return True, self.api.buy_forex_id["msg"]["id"]
        else:
            return False, self.api.buy_forex_id["msg"]

    def cancel_forex_order(self, id):
        self.api.cancel_order_forex = None
        self.api.Cancel_order_forex(id)
        while self.api.cancel_order_forex == None:
            time.sleep(0.3)
            pass
        if self.api.cancel_order_forex["status"] == 2000:
            return True, self.api.cancel_order_forex["msg"]
        else:
            return False, self.api.cancel_order_forex["msg"]
             
    def get_positions_all(self):
        self.api.positions_forex= None
        data = {"name": "portfolio.get-positions",
                "version": "4.0",
                "body": {"offset": 0, "limit": 100,
                "user_balance_id": int(global_value.balance_id),
                "instrument_types":["marginal-forex",
                                    "marginal-cfd",
                                    "marginal-crypto",
                                    "forex",
                                    "fx-option",
                                    "binary-option",
                                    "turbo-option",
                                    "digital-option"]}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.positions_forex== None:
            time.sleep(0.5)
            pass
        if self.api.positions_forex["status"] == 2000:
            return True, self.api.positions_forex["msg"]
        else:
            return False, self.api.positions_forex["msg"]

    def change_auto_margin_call(self, ID_Name, ID, auto_margin_call):
        self.api.auto_margin_call_changed_respond = None
        data = {"name":"change-auto-margin-call", "version":"2.0",
            "body":{ID_Name: ID, "auto_margin_call": bool(auto_margin_call)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.auto_margin_call_changed_respond == None:
            pass
        if self.api.auto_margin_call_changed_respond["status"] == 2000:
            return True, self.api.auto_margin_call_changed_respond
        else:
            return False, self.api.auto_margin_call_changed_respond

    def change_order(self, ID_Name, order_id, stop_lose_kind, stop_lose_value,
                     take_profit_kind, take_profit_value, use_trail_stop, auto_margin_call):
        check = True
        if ID_Name == "position_id":
            check, order_data = self.get_order(order_id)
            position_id = order_data["position_id"]
            ID = position_id
        elif ID_Name == "order_id":
            ID = order_id
        else:
            logging.error('change_order input error ID_Name')
        if check:
            self.api.tpsl_changed_respond = None
            data = {"name":"change-tpsl","version":"2.0",
                "body":{ID_Name: ID, 
                        "stop_lose_kind": stop_lose_kind,
                        "stop_lose_value": stop_lose_value,
                        "take_profit_kind": take_profit_kind,
                        "take_profit_value": take_profit_value,
                        "use_trail_stop": use_trail_stop,
                        "extra":{"stop_lose_kind":stop_lose_kind, 
                                 "take_profit_kind":take_profit_kind}}}
            name = "sendMessage"
            self.api.send_websocket_request(name, data)
            self.change_auto_margin_call(
                ID_Name=ID_Name, ID=ID, auto_margin_call=auto_margin_call)
            while self.api.tpsl_changed_respond == None:
                pass
            if self.api.tpsl_changed_respond["status"] == 2000:
                return True, self.api.tpsl_changed_respond["msg"]
            else:
                return False, self.api.tpsl_changed_respond
        else:
            logging.error('change_order fail to get position_id')
            return False, None

    def get_async_order(self, buy_order_id):
        # name': 'position-changed', 'microserviceName': "portfolio"/"digital-options"
        return self.api.order_async[buy_order_id]

    def get_order(self, buy_order_id):
        self.api.order_data = None
        data = {"name":"get-order", "body":{"order_id":int(buy_order_id)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.order_data == None:
            pass
        if self.api.order_data["status"] == 2000:
            return True, self.api.order_data["msg"]
        else:
            return False, None

    def get_pending(self, instrument_type):
        self.api.deferred_orders = None
        data = {"name":"get-deferred-orders",
                "version":"1.0",
                "body":{"user_balance_id":int(global_value.balance_id),
                        "instrument_type":instrument_type}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.deferred_orders == None:
            pass
        if self.api.deferred_orders["status"] == 2000:
            return True, self.api.deferred_orders["msg"]
        else:
            return False, None

    def get_positions(self, instrument_type):
        self.api.positions = None
        if instrument_type=="digital-option":
            name="digital-options.get-positions"
        elif instrument_type=="fx-option":
            name="trading-fx-option.get-positions"
        else:
            name="get-positions"
        data = {"name":name,"body":{"instrument_type":instrument_type,
                                    "user_balance_id":int(global_value.balance_id)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.positions == None:
            time.sleep(0.1)
            pass
        if self.api.positions["status"] == 2000:
            return True, self.api.positions["msg"]
        else:
            return False, None

    def get_position(self, buy_order_id):
        self.api.position = None
        check, order_data = self.get_order(buy_order_id)
        position_id = order_data["position_id"]
        data = {"name":"get-position","body":{"position_id":position_id,}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.position == None:
            pass
        if self.api.position["status"] == 2000:
            return True, self.api.position["msg"]
        else:
            return False, None

    def get_digital_position(self, order_id):
        self.api.position = None
        while self.get_async_order(order_id)["position-changed"] == {}:
            pass
        position_id = self.get_async_order(
            order_id)["position-changed"]["msg"]["external_id"]
        data = {"name":"digital-options.get-position", "body":{"position_id":position_id}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.position == None:
            pass
        return self.api.position

    def get_position_history_v2(self, instrument_type, limit, offset, start, end):
        # instrument_type=crypto forex fx-option multi-option cfd digital-option turbo-option
        self.api.position_history_v2 = None
        data = {"name":"portfolio.get-history-positions", "version": "2.0",
                "body":{"instrument_types":[instrument_type],
                        "limit":limit,
                        "offset":offset,
                        "start":start,
                        "end":end,
                        "user_balance_id":int(global_value.balance_id)}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.position_history_v2 == None:
            pass
        if self.api.position_history_v2["status"] == 2000:
            return True, self.api.position_history_v2["msg"]
        else:
            return False, None

    def get_available_leverages(self, instrument_type, actives=""):
        self.api.available_leverages = None
        if actives == "":
            actives = ""
        else:
            actives =  OP_code.ACTIVES[actives]
        data = {"name":"get-available-leverages", "version":"2.0",
                "body":{"instrument_type":instrument_type,"actives":[actives]}}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.available_leverages == None:
            pass
        if self.api.available_leverages["status"] == 2000:
            return True, self.api.available_leverages["msg"]
        else:
            return False, None

    def cancel_order(self, buy_order_id):
        self.api.order_canceled = None
        data = { "name":"cancel-order","version":"1.0", "body":{"order_id":buy_order_id }}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.order_canceled == None:
            pass
        if self.api.order_canceled["status"] == 2000:
            return True
        else:
            return False

    def close_position(self, position_id):
        check, data = self.get_order(position_id)
        if data["position_id"] != None:
            position_id = data["position_id"]
            self.api.close_position_data = None
            data = {"name":"close-position", "version":"1.0","body":{"position_id":position_id}}
            name = "sendMessage"
            self.api.send_websocket_request(name, data)
            while self.api.close_position_data == None:
                pass
            if self.api.close_position_data["status"] == 2000:
                return True
            else:
                return False
        else:
            return False

    def get_option_open_by_other_pc(self):
        return self.api.socket_option_opened

    def del_option_open_by_other_pc(self, id):
        del self.api.socket_option_opened[id]

    def opcode_to_name(self, opcode):
        return list(OP_code.ACTIVES.keys())[list(OP_code.ACTIVES.values()).index(opcode)]

    def get_user_profile_client(self, user_id):
        self.api.user_profile_client = None
        data = {"name":"get-user-profile-client", "body":{"user_id":int(user_id)}, "version":"1.0"}
        name = "sendMessage"
        self.api.send_websocket_request(name, data)
        while self.api.user_profile_client == None:
            pass
        return self.api.user_profile_client

    def request_leaderboard_userinfo_deals_client(self, user_id, country_id):
        self.api.leaderboard_userinfo_deals_client = None
        while True:
            try:
                if self.api.leaderboard_userinfo_deals_client["isSuccessful"] == True:
                    break
            except:
                pass
            data = {"name": "request-leaderboard-userinfo-deals-client","version":"1.0",
                    "body": {"country_ids":[country_id],"requested_user_id": int(user_id)}}
            name = "sendMessage"
            self.api.send_websocket_request(name, data)
            time.sleep(0.2)
        return self.api.leaderboard_userinfo_deals_client

    def get_users_availability(self, user_id):
        self.api.users_availability = None
        while self.api.users_availability == None:
            data = {"name":"get-users-availability", "body":{"user_ids":[user_id]}, "version":"1.0"}
            name = "sendMessage"
            self.api.send_websocket_request(name, data)
            time.sleep(0.2)
        return self.api.users_availability

    def logout(self):
        self.api.logout()

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
    # Nova função de compra das digitais

    def get_instrument(self, active, exp, dir, expiration):
        if dir == 'call':
            dir = 'C'
        else:
            dir = 'P'
        date_formated = str(datetime.utcfromtimestamp(exp).strftime("%Y%m%d%H%M"))
        instrument_id = "do" + str(active) + "A" + \
                date_formated[:8] + "D" + date_formated[8:] + \
                "00T" + str(expiration) + "M" + dir + "SPT"
        return str(instrument_id)

    def connect(self, sms_code=None):
        try:
            self.api.close()
        except:
            pass
        self.api = API(self.email, self.password)
        check = None
        # 2FA--
        if sms_code is not None:
            self.api.setTokenSMS(self.resp_sms)
            status, reason = self.api.connect2fa(sms_code)
            if not status:
                return status, reason
        # 2FA--
        self.api.set_session(headers=self.SESSION_HEADER, cookies=self.SESSION_COOKIE)
        check, reason = self.api.connect()
        if check == True:
            self.re_subscribe_stream()
            while global_value.balance_id == None:
                pass
            self.position_change_all("subscribeMessage", global_value.balance_id)
            self.order_changed_all("subscribeMessage")
            self.api.setOptions(1, True)
            return True, None
        else:
            if json.loads(reason)['code'] == 'verify':
                response = self.api.send_sms_code(json.loads(reason)['method'],json.loads(reason)['token'])
                if response.json()['code'] != 'success':
                    return False, response.json()['message']
                # token_sms
                self.resp_sms = response
                return False, "2FA"
            return False, reason

########### fUNÇÕES DE COMPRA BINARIAS E DIGITAL ###########
    def buy(self,valor, ativo, direction, expiration):
        expiration = int(expiration)
        self.q.put(1)
        asset_id = OP_code.ACTIVES[ativo]
        name = "sendMessage"
        exp, idx = get_expiration_time(
            int(self.api.timesync.server_timestamp), expiration)
        if idx < 5:
            option = 3  # "turbo"
        else:
            option = 1  # "binary"
        data ={"name": "binary-options.open-option",
                "version": "2.0",
                "body":{"user_balance_id": int(global_value.balance_id),
                        "active_id": asset_id,
                        "option_type_id": option,
                        "direction": direction.lower(),
                        "expired": int(exp),
                        "price": valor,
                        "refund_value": 0,
                        "profit_percent": 0,}}
        print(data)
        req_id = int(randint(0, 1000000))
        self.api.send_websocket_request(name, data, str(req_id))
        time.sleep(1)
        self.q.get()
        start = time.time()
        while True:
            time.sleep(0.1)
            if time.time() - start <= 5:
                try:
                    message = self.api.orders[str(req_id)]
                    break
                except Exception as err:
                    # print(err)
                    pass
            else:
                return False, None
        try:
            return True, message['id']
        except:
            return False, message['message']

    def buy_digital_spot_v2(self, valor, ativo, direcao, timeframe):
        timeframe = int(timeframe)
        asset_id = OP_code.ACTIVES[ativo]
        timestamp = int(time.time())
        if timeframe == 1:
            exp, _ = get_expiration_time(timestamp, timeframe)
        else:
            now_date = datetime.fromtimestamp(
                timestamp) + timedelta(minutes=1, seconds=30)
            
            while True:
                if now_date.minute % timeframe == 0 and time.mktime(now_date.timetuple()) - timestamp > 30:
                    break
                now_date = now_date + timedelta(minutes=1)
            exp = time.mktime(now_date.timetuple())
        instrument_id = self.get_instrument(asset_id, exp, direcao, timeframe)
        #print(f'instrument_id = {instrument_id}')
        #print(f'exp = {exp}')
        name = "sendMessage"
        data = {"name": "digital-options.place-digital-option", "version": "3.0",
                "body":{"user_balance_id": int(global_value.balance_id),
                        "instrument_id": instrument_id,
                        "amount": str(valor),
                        "instrument_index": 0,
                        "asset_id": int(asset_id),}}
        # print(data)
        req_id = str(randint(0, 100000))
        self.api.send_websocket_request(name, data, req_id)
        start = time.time()
        while True:
            time.sleep(0.1)
            if time.time() - start <= 5:
                try:
                    message =self.api.orders[str(req_id)]
                    break
                except Exception as err:
                    # print(err)
                    pass
            else:
                return False, None
        try:
            return True, message['id']
        except:
            return False, message['message']

    def captura_positions(self):
        return self.api.orders_history
        
############ FUNÇÕES QUE PUXA PREÇO ATUAL #############
    def start_candles_stream_v2(self,ativo,size):
        asset_id = OP_code.ACTIVES[ativo]
        name = "subscribeMessage"
        data = {"name": "candle-generated", "params":
                 {"routingFilters": {"active_id": str(asset_id),"size": int(size)}}}
        self.api.send_websocket_request(name, data)

    def get_all_realtime(self):
        #primeiro você precisa dar um subscrible no par que deseja
        #usando a função start_candles_stream_v2(ativo,size)
        return self.api.all_realtime_candles

############ FUNÇÕES DE ALERTA ############
    def start_subscribe_alerts(self):
        name = "subscribeMessage"
        data = {"name": "alert-triggered"}
        self.api.send_websocket_request(name, data)

    def criar_alerta(self, active, instrument_type, value):
        self.api.alerta = None
        asset_id = OP_code.ACTIVES[active]
        name = "sendMessage"
        data = {"name": "create-alert", "version":"1.0",
                "body":{"asset_id":int(asset_id),
                        "instrument_type":instrument_type,
                        "type":"price",
                        "value":value,
                        "activations":1}}
        self.api.send_websocket_request(name, data)
        while self.api.alerta == None:
            time.sleep(0.01)
            pass   
        return self.api.alerta
    
    def get_alerta(self):
        self.api.alertas = None
        name = "sendMessage"
        data = {"name":"get-alerts", "version":"1.0", "body":{"asset_id":0,"type":""}}
        self.api.send_websocket_request(name, data)
        while self.api.alertas == None:
            time.sleep(0.01)
            pass            
        if self.api.alertas != []:
            for i in self.api.alertas:
                i['par'] = list(OP_code.ACTIVES.keys())[list(OP_code.ACTIVES.values()).index(i['asset_id'])]
        return self.api.alertas
    
    def delete_alerta(self,id):
        self.api.alerta = None
        name = "sendMessage"
        data = {"name": "delete-alert","version":"1.0", "body":{"id":id}}
        self.api.send_websocket_request(name, data)   
        while self.api.alerta == None:
            time.sleep(0.01)
            pass            
        return self.api.alerta
    
    def alertas_realtime(self):
        return self.api.alertas_tocados

########### FUNÇÕES QUE CAPTURA PARES E PAYOUTS ###########
    def get_all_open_time(self):
        """
        Retorna informações de tempo aberto para todos os pares disponíveis (binárias, digitais e outros),
        utilizando a estrutura e chamadas da nova API.
        """
        # Inicializa o armazenamento de pares abertos
        self.OPEN_TIME = nested_dict(3, dict)
    
        # Threads para diferentes tipos de mercado
        binary = threading.Thread(target=self.__get_binary_open)
        digital = threading.Thread(target=self.__get_digital_open)
        other = threading.Thread(target=self.__get_other_open)
    
        # Inicia as threads
        binary.start()
        digital.start()
        other.start()
    
        # Aguarda as threads concluírem
        binary.join()
        digital.join()
        other.join()
    
        return self.OPEN_TIME
    
    # Novas implementações para as funções específicas
    def __get_binary_open(self):
        """
        Atualiza os pares binários disponíveis na estrutura OPEN_TIME.
        """
        self.api.payout_binarias = None
        request = {"name": "get-initialization-data", "version": "4.0", "body": {}}
        self.api.send_websocket_request(name="sendMessage", msg=request)
    
        # Aguarda a resposta
        start = time.time()
        while self.api.payout_binarias is None:
            time.sleep(0.1)
            if time.time() - start > 10:  # Timeout após 10 segundos
                return
    
        # Processa os dados recebidos
        binary_data = self.api.payout_binarias
        if binary_data:
            for option_type in ["binary", "turbo"]:
                if option_type in binary_data:
                    for active_id, active_data in binary_data[option_type]["actives"].items():
                        if active_data["enabled"]:
                            name = str(active_data["name"]).split(".")[1]
                            self.OPEN_TIME[option_type][name] = {
                                "open": not active_data["is_suspended"],
                                "payout": 100 - int(active_data["option"]["profit"]["commission"]),
                            }
    
    def __get_digital_open(self):
        """
        Atualiza os pares digitais disponíveis na estrutura OPEN_TIME.
        """
        self.api.underliyng_list = None
        request = {
            "name": "digital-option-instruments.get-underlying-list",
            "version": "2.0",
            "body": {"filter_suspended": True},
        }
        self.api.send_websocket_request(name="sendMessage", msg=request)
    
        # Aguarda a resposta
        start = time.time()
        while self.api.underliyng_list is None:
            time.sleep(0.1)
            if time.time() - start > 10:  # Timeout após 10 segundos
                return
    
        # Processa os dados recebidos
        digital_data = self.api.underliyng_list.get("underlying", [])
        for digital in digital_data:
            name = digital["underlying"]
            is_open = any(
                schedule["open"] < time.time() < schedule["close"]
                for schedule in digital.get("schedule", [])
            )
            self.OPEN_TIME["digital"][name] = {"open": is_open}
    
    def __get_other_open(self):
        """
        Atualiza outros pares disponíveis na estrutura OPEN_TIME.
        """
        # Exemplo genérico para futuros mercados ou categorias específicas.
        self.api.other_markets = None
        request = {
            "name": "get-other-markets",
            "version": "1.0",
            "body": {},  # Adicione parâmetros relevantes
        }
        self.api.send_websocket_request(name="sendMessage", msg=request)
    
        # Aguarda a resposta
        start = time.time()
        while self.api.other_markets is None:
            time.sleep(0.1)
            if time.time() - start > 10:  # Timeout após 10 segundos
                return
    
        # Processa os dados recebidos
        other_data = self.api.other_markets.get("markets", [])
        for market in other_data:
            name = market["name"]
            self.OPEN_TIME["other"][name] = {"open": market.get("is_open", False)}

    def captura_binarias(self):
        self.api.payout_binarias = None
        binarias = {"name": "get-initialization-data", "version": "4.0", "body": {}}
        self.api.send_websocket_request(name="sendMessage", msg = binarias)
        start = time.time()
        while self.api.payout_binarias== None:
            time.sleep(0.1)
            if time.time() - start > 10:
                return None
        binary_data = self.api.payout_binarias
        lista = {}
        lista['binary'] = {}
        lista['turbo'] = {}
        binary_list = ["binary", "turbo"]
        if binary_data:
            for option in binary_list:
                if option in binary_data:
                    for actives_id in binary_data[option]["actives"]:
                        active = binary_data[option]["actives"][actives_id]
                        name = str(active["name"]).split(".")[1]
                        lista[option][name] = {}
                        if active["enabled"] == True:
                            if active["is_suspended"] == True:
                                lista[option][name]["open"] = False
                                lista[option][name]["payout"] = 0
                            else:
                                lista[option][name]["open"] = True
                                lista[option][name]["payout"] = 100 - int(active["option"]["profit"]["commission"])
                        else:
                            lista[option][name]["open"] = False
                            lista[option][name]["payout"] = 0
                        # update actives opcode       
                        OP_code.ACTIVES[name] = int(actives_id)    
        return lista

    def captura_digital(self):
        self.api.underliyng_list = None
        digital  = {"name": "digital-option-instruments.get-underlying-list", 
                    "version": "2.0", "body": {"filter_suspended": True}}
        self.api.send_websocket_request(name="sendMessage", msg =digital) 
        start = time.time()
        while self.api.underliyng_list == None:
            time.sleep(0.1)
            if time.time() - start > 10:
                return None
        digital_data = self.api.underliyng_list["underlying"]
        lista = {}
        lista['digital']={}
        for digital in digital_data:
            name = digital["underlying"]
            lista['digital'][name] = {}
            schedule = digital["schedule"]
            lista['digital'][name]['open'] = False
            for schedule_time in schedule:
                start = schedule_time["open"]
                end = schedule_time["close"]
                if start < time.time() < end:
                    lista['digital'][name]['open'] = True
            # update digital actives opcode
            active_id_valor = digital['active_id']
            OP_code.ACTIVES[name] = active_id_valor
        return lista

    def payout_digital_old(self, par):
        asset_id = OP_code.ACTIVES[par]
        t = time.time()
        try:
            if t - int(self.api.payout_digitais[asset_id]['hora']) <= 300:
                #print('retornando pay já puxado anteriormente')
                return self.api.payout_digitais[asset_id]['pay']
        except:
            pass
        self.api.payout_digitais[asset_id] = None
        data = {"name": "price-splitter.client-price-generated", "version": "1.0", "params":
                {"routingFilters":{"instrument_type":"digital-option", "asset_id": str(asset_id)}}}
        self.api.send_websocket_request(name = "subscribeMessage", msg = data)
        start = time.time()
        while self.api.payout_digitais[asset_id] is None:
            if int(time.time() - start) > 10:
                #print('AVISO! Não consegui puxar o payout da digital, sua internet pode estar lenta demais.\n')
                name = "unsubscribeMessage"
                data = {"name": "price-splitter.client-price-generated", "version": "1.0", "params":
                        {"routingFilters": {"instrument_type": "digital-option", "asset_id": int(asset_id)}}}
                self.api.send_websocket_request(name, msg=data)
                return 0  
        name = "unsubscribeMessage"
        data = {"name": "price-splitter.client-price-generated", "version": "1.0","params":
                {"routingFilters": {"instrument_type": "digital-option","asset_id": int(asset_id)}}}
        self.api.send_websocket_request(name, msg=data)
        return self.api.payout_digitais[asset_id]['pay']
    
    def payout_digital(self):
        lista = self.captura_digital()
        self.api.assets_digital= None
        name = "sendMessage"
        data = {"name": "get-top-assets","version": "3.0",
                "body": {"instrument_type": "digital-option","region_id": -1}}
        self.api.send_websocket_request(name, data)
        t = time.time()
        while self.api.assets_digital == None:
            if time.time() - t >= 10:
                return None
            time.sleep(0.5)
            pass
        pays = {}
        for i in self.api.assets_digital:
            try:
                par = list(OP_code.ACTIVES.keys())[list(OP_code.ACTIVES.values()).index(i['active_id'])]
                if lista['digital'][par]['open']:
                    try:
                        payout =  int(i['spot_profit'])
                    except: payout = 0
                    pays[par]= payout
                else:
                    pays[par]= 0
            except: pass
        return pays

########## FUNÇÕES OPERAÇÃO EM FOREX ##############
    def leverage_marginal_forex(self, par):
        self.api.leverage_forex = None
        name = "sendMessage"
        data = {"name": "marginal-forex-instruments.get-underlying-list", "version": "1.0", "body": {}}
        self.api.send_websocket_request(name, data)
        while self.api.leverage_forex == None:
            time.sleep(0.3)
            pass
        leverage =  self.api.leverage_forex
        try:
            for i in leverage["msg"]['items']:
                if par in i['name']:
                    leverage = i['max_leverages']['0']
            return leverage
        except:
            return None

    def buy_marginal_forex(self, par,direcao,valor_entrada,preco_entrada,win,lose):
        self.api.buy_forex_id = None
        leverage = self.leverage_marginal_forex(par)
        par = OP_code.ACTIVES[par]
        name = "sendMessage"
        data = {"name": "marginal-forex.place-stop-order",
                "version": "1.0",
                "body":{"side": str(direcao),
                        "user_balance_id": int(global_value.balance_id),
                        "count": str(valor_entrada),
                        "instrument_id": "mf."+str(par),
                        "instrument_active_id": int(par),
                        "leverage": str(leverage),
                        "stop_price": str(preco_entrada),
                        "take_profit": {
                        "type": "price",
                        "value": str(win)}, "stop_loss": {"type": "price","value": str(lose)}}}
        self.api.send_websocket_request(name, data)
        self.api.buy_order_forex(leverage,par,direcao,valor_entrada,preco_entrada,win,lose)

        while self.api.buy_forex_id == None:
            time.sleep(0.3)
            pass
        if self.api.buy_forex_id["status"] == 2000:
            return True, self.api.buy_forex_id["msg"]["id"]
        else:
            return False, self.api.buy_forex_id["msg"]

    def buy_forex(self, par,direcao,valor_entrada,multiplicador= None,preco_entrada= None,preco_profit= None,preco_lose= None):
        if direcao =='call':
            direcao = 'buy'
        if direcao =='put':
            direcao = 'sell'   
        if preco_entrada == None:
            tipo = 'market'
        else: tipo = 'limit'
        if preco_lose == None:
            auto_margin = True
        else: auto_margin = False
        if multiplicador == None:
            st, msg = self.get_available_leverages("forex",par)
            if st == True:
                multiplicador = msg['leverages'][-1]['regulated_default']
            else: multiplicador = 100
        name = "sendMessage"
        data = {"name": "place-order-temp", "version": "4.0",
                "body":{"user_balance_id": int(global_value.balance_id),
                        "client_platform_id": 9,
                        "instrument_type": "forex",
                        "instrument_id": str(par),
                        "side": str(direcao),
                        "type": str(tipo), #"market"/"limit"/"stop"
                        "amount": float(valor_entrada),
                        "leverage": int(multiplicador),
                        "limit_price": preco_entrada, #funciona somente se type="limit"
                        "stop_price": 0, #funciona somente se type="stop"
                        "auto_margin_call": bool(auto_margin), #true se não estiver usando stop definido
                        "use_trail_stop": "false",
                        "take_profit_value": preco_profit,
                        "take_profit_kind": "price",
                        "stop_lose_value": preco_lose,
                        "stop_lose_kind": "price"}}
        self.api.send_websocket_request(name, data)
        while self.api.buy_order_id == None:
            pass
        check, data = self.get_order(self.api.buy_order_id)
        while data["status"] == "pending_new":
            check, data = self.get_order(self.api.buy_order_id)
            time.sleep(1)
        if check:
            if data["status"] != "rejected":
                return True, self.api.buy_order_id
            else:
                return False, data["reject_status"]
        else:
            return False, None

    def cancel_marginal_forex(self, id):
        self.api.cancel_order_forex = None
        name = "sendMessage"
        data = {"name":"marginal-forex.cancel-pending-order", "version":"1.0", "body":{"order_id":id}}
        self.apisend_websocket_request(name, data)
        while self.api.cancel_order_forex == None:
            time.sleep(0.3)
            pass
        if self.api.cancel_order_forex["status"] == 2000:
            return True, self.api.cancel_order_forex["msg"]
        else:
            return False, self.api.cancel_order_forex["msg"]
             
    def get_fechadas_marginal_forex(self):
        self.api.fechadas_forex= None
        user_id = self.api.profile.msg['user_id']
        name = "sendMessage"
        data = {"name": "portfolio.get-history-positions", "version": "2.0",
                "body":{"user_id": user_id,
                        "user_balance_id": int(global_value.balance_id),
                        "instrument_types": [
                        "marginal-forex"],"offset": 0,"limit": 30}}
        self.api.send_websocket_request(name, data)
        while self.api.fechadas_forex == None:
            time.sleep(0.5)
            pass
        if self.api.fechadas_forex["status"] == 2000:
            return True, self.api.fechadas_forex["msg"]
        else:
            return False, self.api.fechadas_forex["msg"]
    
    def get_positions_marginal_forex(self):
        self.api.positions_forex= None
        name = "sendMessage"
        data = {"name": "portfolio.get-positions", "version": "4.0",
                "body": {"offset": 0, "limit": 100, "user_balance_id": int(global_value.balance_id),
                "instrument_types": ["marginal-forex", "marginal-cfd", "marginal-crypto"]}}
        self.api.send_websocket_request(name, data)
        while self.api.positions_forex== None:
            time.sleep(0.5)
            pass
        if self.api.positions_forex["status"] == 2000:
            return True, self.api.positions_forex["msg"]
        else:
            return False, self.api.positions_forex["msg"]

    def get_pendentes_forex(self):
        self.api.pendentes_forex= None
        name = "sendMessage"
        data = {"name": "portfolio.get-orders", "version": "2.0", 
                "body": { "user_balance_id": int(global_value.balance_id), "kind": "deferred"}}
        self.api.send_websocket_request(name, data)
        while self.api.pendentes_forex== None:
            time.sleep(0.5)
            pass
        if self.api.pendentes_forex["status"] == 2000:
            return True, self.api.pendentes_forex["msg"]
        else:
            return False, self.api.pendentes_forex["msg"]
