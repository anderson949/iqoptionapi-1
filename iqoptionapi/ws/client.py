# client.py
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
        self.wss = None
        self.thread = None
        self.is_running = False

        # Inicializa global_value com valores padrão
        if not hasattr(global_value, 'check_websocket_if_connect'):
            global_value.check_websocket_if_connect = 0

    def start(self):
        """Inicia a conexão WebSocket se não estiver em execução."""
        logger = logging.getLogger(__name__)

        if not self.is_running:
            if self.api and hasattr(self.api, 'wss_url') and self.api.wss_url:
                self.wss = websocket.WebSocketApp(
                    self.api.wss_url,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=self.on_open
                )
                logger.info(f"WebSocket URL: {self.api.wss_url}")
                self.thread = Thread(target=self.run_forever)
                self.thread.daemon = True
                self.thread.start()
                self.is_running = True
                logger.info("WebSocket iniciado com sucesso.")
            else:
                logger.error("API ou URL do WebSocket não estão configurados corretamente.")
                self.wss = None
        else:
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

    def run_forever(self):
        """Executa o WebSocket em uma thread separada."""
        logger = logging.getLogger(__name__)
        try:
            if self.wss:
                self.wss.run_forever()
            else:
                logger.error("WebSocket não foi inicializado corretamente.")
        except Exception as e:
            logger.error(f"Erro no WebSocket durante execução: {e}")
        finally:
            self.is_running = False

    @staticmethod
    def on_message(_, message):
        """Processa as mensagens recebidas do WebSocket."""
        logger = logging.getLogger(__name__)
        logger.debug(f"Mensagem recebida: {message}")

    @staticmethod
    def on_error(_, error):
        """Lida com erros do WebSocket."""
        logger = logging.getLogger(__name__)
        logger.error(f"Erro no WebSocket: {error}")
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
        logger.warning(f"Conexão WebSocket fechada. Status: {close_status_code}, Mensagem: {close_msg}")
        global_value.check_websocket_if_connect = 0
