from trading_bot_v4 import TradingBotV4
from capital_api import CapitalComAPI
from gui.aggression_control import AggressionControlGUI

# Bot + API vorbereiten
api = CapitalComAPI(API_KEY, ACCOUNT_ID, PASSWORD, use_demo=True)
bot = TradingBotV4(api, capital=1000, position_size=0.5)

# GUI starten
gui = AggressionControlGUI()
gui.attach_bot(bot)
bot.attach_gui(gui)