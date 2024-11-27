"""Module for IQ option websocket."""

import json
import logging
import websocket
import iqoptionapi.constants as OP_code
import iqoptionapi.global_value as global_value
from threading import Thread
from iqoptionapi.ws.received.technical_indicators import technical_indicators
from iqoptionapi.ws.received.time_sync import time_sync
from iqoptionapi.ws.received.heartbeat import heartbeat
from iqoptionapi.ws.received.balances import balances
from iqoptionapi.ws.received.profile import profile
from iqoptionapi.ws.received.balance_changed import balance_changed
from iqoptionapi.ws.received.candles import candles
from iqoptionapi.ws.received.buy_complete import buy_complete
from iqoptionapi.ws.received.option import option
from iqoptionapi.ws.received.position_history import position_history
from iqoptionapi.ws.received.list_info_data import list_info_data
from iqoptionapi.ws.received.candle_generated import candle_generated_realtime
from iqoptionapi.ws.received.candle_generated_v2 import candle_generated_v2
from iqoptionapi.ws.received.commission_changed import commission_changed
from iqoptionapi.ws.received.socket_option_opened import socket_option_opened
from iqoptionapi.ws.received.api_option_init_all_result import api_option_init_all_result
from iqoptionapi.ws.received.initialization_data import initialization_data
from iqoptionapi.ws.received.underlying_list import underlying_list
from iqoptionapi.ws.received.instruments import instruments
from iqoptionapi.ws.received.financial_information import financial_information
from iqoptionapi.ws.received.position_changed import position_changed
from iqoptionapi.ws.received.option_opened import option_opened
from iqoptionapi.ws.received.option_closed import option_closed
from iqoptionapi.ws.received.top_assets_updated import top_assets_updated
from iqoptionapi.ws.received.strike_list import strike_list
from iqoptionapi.ws.received.api_game_betinfo_result import api_game_betinfo_result
from iqoptionapi.ws.received.traders_mood_changed import traders_mood_changed
from iqoptionapi.ws.received.order import order
from iqoptionapi.ws.received.position import position
from iqoptionapi.ws.received.positions import positions
from iqoptionapi.ws.received.order_placed_temp import order_placed_temp
from iqoptionapi.ws.received.deferred_orders import deferred_orders
from iqoptionapi.ws.received.history_positions import history_positions
from iqoptionapi.ws.received.available_leverages import available_leverages
from iqoptionapi.ws.received.order_canceled import order_canceled
from iqoptionapi.ws.received.position_closed import position_closed
from iqoptionapi.ws.received.overnight_fee import overnight_fee
from iqoptionapi.ws.received.api_game_getoptions_result import api_game_getoptions_result
from iqoptionapi.ws.received.sold_options import sold_options
from iqoptionapi.ws.received.tpsl_changed import tpsl_changed
from iqoptionapi.ws.received.auto_margin_call_changed import auto_margin_call_changed
from iqoptionapi.ws.received.digital_option_placed import digital_option_placed
from iqoptionapi.ws.received.result import result
from iqoptionapi.ws.received.instrument_quotes_generated import instrument_quotes_generated
from iqoptionapi.ws.received.training_balance_reset import training_balance_reset
from iqoptionapi.ws.received.socket_option_closed import socket_option_closed
from iqoptionapi.ws.received.live_deal_binary_option_placed import live_deal_binary_option_placed
from iqoptionapi.ws.received.live_deal_digital_option import live_deal_digital_option
from iqoptionapi.ws.received.leaderboard_deals_client import leaderboard_deals_client
from iqoptionapi.ws.received.live_deal import live_deal
from iqoptionapi.ws.received.user_profile_client import user_profile_client
from iqoptionapi.ws.received.leaderboard_userinfo_deals_client import leaderboard_userinfo_deals_client
from iqoptionapi.ws.received.client_price_generated import client_price_generated
from iqoptionapi.ws.received.users_availability import users_availability


class WebsocketClient:
    """Classe para lidar com a comunicação via WebSocket do IQ Option."""

    def __init__(self, api):
        self.api = api
        self.wss = None  # Inicializa o atributo como None
        self.thread = None
        self.is_running = False  # Flag para controlar o estado do WebSocket

        # Inicializa o global_value com valores padrão, se necessário
        if not hasattr(global_value, 'check_websocket_if_connect'):
            global_value.check_websocket_if_connect = 0

    def start(self):
        """Inicia a conexão WebSocket se não estiver em execução."""
        if not self.is_running:
            if self.api and self.api.wss_url:  # Verifique se a API e URL estão configurados
                self.wss = websocket.WebSocketApp(
                    self.api.wss_url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open
                )
                self.thread = Thread(target=self.run_forever)
                self.thread.daemon = True
                self.thread.start()
                self.is_running = True
                logger = logging.getLogger(__name__)
                logger.info("WebSocket iniciado com sucesso.")
            else:
                logger = logging.getLogger(__name__)
                logger.error("API ou URL do WebSocket não estão configurados corretamente.")
        else:
            logger = logging.getLogger(__name__)
            logger.warning("WebSocket já está em execução. Ignorando nova inicialização.")

    def stop(self):
        """Para a conexão WebSocket se estiver em execução."""
        if self.is_running:
            self.wss.close()
            self.thread.join()
            self.is_running = False
            logger = logging.getLogger(__name__)
            logger.info("WebSocket fechado com sucesso.")
        else:
            logger = logging.getLogger(__name__)
            logger.warning("WebSocket não está em execução. Ignorando o fechamento.")

    def restart(self):
        """Reinicia a conexão WebSocket."""
        self.stop()
        self.start()

    def run_forever(self):
        """Executa o WebSocket em uma thread separada."""
        try:
            if self.wss:  # Verifique se self.wss não é None antes de chamar run_forever
                self.wss.run_forever()
            else:
                logger = logging.getLogger(__name__)
                logger.error("WebSocket não foi inicializado corretamente.")
        except websocket.WebSocketException as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erro no WebSocket: {e}")
        finally:
            self.is_running = False

    def dict_queue_add(self, dict, maxdict, key1, key2, key3, value):
        """Adiciona um valor a um dicionário aninhado com limite de tamanho."""
        if key3 in dict[key1][key2]:
            dict[key1][key2][key3] = value
        else:
            while True:
                try:
                    dic_size = len(dict[key1][key2])
                except:
                    dic_size = 0
                if dic_size < maxdict:
                    dict[key1][key2][key3] = value
                    break
                else:
                    del dict[key1][key2][sorted(dict[key1][key2].keys())[0]]

    def api_dict_clean(self, obj):
        """Limpa o dicionário se ele exceder o tamanho máximo."""
        if len(obj) > 5000:
            for k in obj.keys():
                del obj[k]
                break

    def on_message(self, _, message):
        """Processa as mensagens recebidas do WebSocket."""
        global_value.ssl_Mutual_exclusion = True
        logger = logging.getLogger(__name__)
        logger.debug(message)
        
        message = json.loads(message)

        # Processa as mensagens usando os manipuladores
        technical_indicators(self.api, message, self.api_dict_clean)
        time_sync(self.api, message)
        heartbeat(self.api, message)
        balances(self.api, message)
        profile(self.api, message)
        # Continue com todos os outros manipuladores...
        
        global_value.ssl_Mutual_exclusion = False

    @staticmethod
    def on_error(_, error):
        """Lida com erros do WebSocket."""
        logger = logging.getLogger(__name__)
        logger.error(f"Erro no WebSocket: {error}")
        global_value.websocket_error_reason = str(error)
        global_value.check_websocket_if_error = True

    @staticmethod
    def on_open(_):
        """Lida com a abertura da conexão WebSocket."""
        logger = logging.getLogger(__name__)
        logger.info("Conexão WebSocket aberta.")
        global_value.check_websocket_if_connect = 1

    @staticmethod
    def on_close(_, close_status_code, close_msg):
        """Lida com o fechamento da conexão WebSocket."""
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Conexão WebSocket fechada. Status: {close_status_code}, Mensagem: {close_msg}"
        )
        global_value.check_websocket_if_connect = 0
