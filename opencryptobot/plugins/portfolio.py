import pickle
import os
import prettytable as pt
import opencryptobot.emoji as emo
import opencryptobot.utils as utl

from telegram import ParseMode
from opencryptobot.ratelimit import RateLimit
from opencryptobot.api.apicache import APICache
from opencryptobot.api.coingecko import CoinGecko
from opencryptobot.plugin import OpenCryptoPlugin, Category, Keyword


class Portfolio(OpenCryptoPlugin):
    # Initialize data
    _data_path = "data.pickle"
    portfolios = {}
    def __init__(self, telegram_bot):
        super().__init__(telegram_bot)
        self._data_path = "data.pickle"
        if not os.path.isfile(self._data_path):
            self.portfolios = {}
        else:
            with open(self._data_path, 'rb') as f:
                self.portfolios = pickle.load(f)
        
    def get_cmds(self):
        return ["port", "portfolio"]

    @OpenCryptoPlugin.save_data
    @OpenCryptoPlugin.send_typing
    def get_action(self, bot, update, args):
        # TODO: Do this in every plugin
        keywords = utl.get_kw(args)
        arg_list = utl.del_kw(args)

        vs_cur = "usd"

        func = str()
        if len(arg_list) >= 1:
            func = arg_list[0]

        if RateLimit.limit_reached(update):
            return

        cg = CoinGecko()
        msg = str()

        #message.from_user.id
        #message.from_user.first_name
        #message.from_user.last_name
        #message.from_user.username
        
        if func.upper() == "ADD":            
            user_id = update.message.from_user.id
            #if len(self.portfolios[user_id]) > 20:
            #    update.message.reply_text('Usage: Too many open fakka!')

            if len(arg_list) != 2:
                update.message.reply_text('Usage: add <symbol_id>')
                return
            try:
                response = APICache.get_cg_coins_list()
            except Exception as e:
                return self.handle_error(e, update)

            coin_id = str()
            coin_name = str()

            for entry in response:
                if entry["id"].upper() == arg_list[1].upper():
                    coin_id = entry["id"]
                    coin_name = entry["name"]
                    break

            if not coin_id:
                update.message.reply_text('Parameter <symbol> is no valid id! Check out https://api.coingecko.com/api/v3/coins/list')
                return
            
            try:
                result = cg.get_simple_price(coin_id, vs_cur)
            except Exception as e:
                return self.handle_error(e, update)

            price = 0.0
            for currency in result:
                price = float(result[currency][vs_cur])

            if user_id not in self.portfolios:
                self.portfolios[user_id] = {}
            self.portfolios[user_id][coin_id] = price
            with open(self._data_path, 'wb') as f:
                pickle.dump(self.portfolios, f, pickle.HIGHEST_PROTOCOL)
            msg = f"`{coin_id} ({coin_name}) at {price}$`\n"
            msg += "Portfolio updated successfully!"

        elif func.upper() == "REMOVE":      
            user_id = update.message.from_user.id
            if len(arg_list) != 2:
                update.message.reply_text('Usage: remove <symbol_id>')
                return
            try:
                response = APICache.get_cg_coins_list()
            except Exception as e:
                return self.handle_error(e, update)

            coin_id = str()
            coin_name = str()

            for entry in response:
                if entry["id"].upper() == arg_list[1].upper():
                    coin_id = entry["id"]
                    coin_name = entry["name"]
                    break
            
            if not coin_id:
                update.message.reply_text('Parameter <symbol> is no valid id! Check out https://api.coingecko.com/api/v3/coins/list')
                return
            
            if user_id not in self.portfolios:
                self.portfolios[user_id] = {}
            del self.portfolios[user_id][coin_id]
            with open(self._data_path, 'wb') as f:
                pickle.dump(self.portfolios, f, pickle.HIGHEST_PROTOCOL)
            msg = f"`{coin_id} ({coin_name})`\n"
            msg += "Portfolio updated successfully!"

        elif func.upper() == "TOP":          
            
            table = pt.PrettyTable(['User', 'Profit'])
            table.align['User'] = 'l'
            table.align['Profit'] = 'r'    
            
            for users in self.portfolios:
                try:
                    result = cg.get_simple_price(','.join(self.portfolios[users].keys()), vs_cur)
                except Exception as e:
                    return self.handle_error(e, update)
                profit = 0.0
                for currency in result:
                    price = self.portfolios[users][currency]
                    last = float(result[currency][vs_cur])
                    profit += (last / price * 100) - 100
                table.add_row([users, f'{profit:.2f}%'])

            msg = f"Top moon\n"
            #table.sortby = "Profit [%]"
            #table.reversesort = True
            update.message.reply_text(f'<pre>{msg}{table}</pre>', parse_mode=ParseMode.HTML, quote=False)
            return

        else:
            user_id = update.message.from_user.id

            if len(arg_list) == 3:
                user_id = arg_list[2]

            if user_id not in self.portfolios:
                update.message.reply_text('Your portfolio is empty! Use add <symbol>')
                return
           
            try:
                result = cg.get_simple_price(','.join(self.portfolios[user_id].keys()), vs_cur)
            except Exception as e:
                return self.handle_error(e, update)
            
            table = pt.PrettyTable(['Symbol', 'Price', 'Last', 'Profit'])
            table.align['Symbol'] = 'l'
            table.align['Price'] = 'r'
            table.align['Last'] = 'r'
            table.align['Profit'] = 'r'

            data = None
            msg = f"Portfolio: {update.message.from_user.first_name} ({user_id})\n"
            for currency in result:
                price = self.portfolios[user_id][currency]
                last = float(result[currency][vs_cur])
                profit = (last / price * 100) - 100
                try:
                    data = CoinGecko().get_coin_by_id(currency)
                except Exception as e:
                    data["symbol"] = currency
                symbol = data["symbol"].upper()
                table.add_row([symbol, f'{price:.3f}', f'{last:.3f}', f'{profit:.2f}%'])
            
            update.message.reply_text(f'<pre>{msg}{table}</pre>', parse_mode=ParseMode.HTML, quote=False)
            return

        if keywords.get(Keyword.INLINE):
            return msg

        self.send_msg(msg, update, keywords)

    def get_usage(self):
        return f"`" \
               f"/{self.get_cmds()[0]} add <symbol_id>\n\n" \
               f"/{self.get_cmds()[0]} remove <symbol_id>\n\n" \
               f"/{self.get_cmds()[0]} top" \
               f"`"

    def get_description(self):
        return "Portfolio"

    def get_category(self):
        return Category.PRICE

    def inline_mode(self):
        return True