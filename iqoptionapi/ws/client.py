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


# client.py
"""Module for IQ option websocket."""

import json
import logging
import websocket
import iqoptionapi.constants as OP_code
import iqoptionapi.global_value as global_value
from threading import Thread
import time


class WebsocketClient:
    """Class for working with IQ Option WebSocket."""

    def __init__(self, api):
        """
        :param api: The instance of :class:`IQOptionAPI <iqoptionapi.api.IQOptionAPI>`.
        """
        self.api = api
        self.logger = logging.getLogger(__name__)
        self.wss = None
        self.should_run = True  # Flag to control the WebSocket thread

    def connect(self):
        """Establish a WebSocket connection."""
        self.logger.info("Initializing WebSocket connection.")
        self.wss = websocket.WebSocketApp(
            self.api.wss_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )

        # Run WebSocket in a separate thread
        thread = Thread(target=self._run_forever, daemon=True)
        thread.start()

    def _run_forever(self):
        """Run the WebSocket connection in a loop."""
        while self.should_run:
            try:
                self.wss.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                self.logger.error(f"WebSocket connection failed: {e}")
                time.sleep(5)  # Wait before attempting to reconnect
            else:
                self.logger.info("WebSocket disconnected. Attempting to reconnect...")
                time.sleep(5)  # Reconnection delay

    def stop(self):
        """Stop the WebSocket connection."""
        self.should_run = False
        if self.wss:
            self.wss.close()

    def on_message(self, wss, message):
        """Process WebSocket messages."""
        global_value.ssl_Mutual_exclusion = True
        self.logger.debug(f"Received message: {message}")
        try:
            message = json.loads(message)
            # Call all necessary handlers here
            # Example: technical_indicators(self.api, message)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
        finally:
            global_value.ssl_Mutual_exclusion = False

    def on_error(self, wss, error):
        """Handle WebSocket errors."""
        self.logger.error(f"WebSocket error: {error}")
        global_value.websocket_error_reason = str(error)
        global_value.check_websocket_if_error = True

    def on_close(self, wss, close_status_code, close_msg):
        """Handle WebSocket close events."""
        self.logger.info(f"WebSocket closed. Code: {close_status_code}, Message: {close_msg}")
        global_value.check_websocket_if_connect = 0

    def on_open(self, wss):
        """Handle WebSocket open events."""
        self.logger.info("WebSocket connection established.")
        global_value.check_websocket_if_connect = 1
