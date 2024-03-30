import yfinance
import matplotlib.pyplot as plt
from pymongo import MongoClient
import cProfile
import pstats
import bisect




class Strategy():
    def buying_strategy(self, iterated_price_list):
        raise NotImplementedError
    def selling_strategy(self, iterated_price_list, purchased_prices,type):
        raise NotImplementedError

class RollingMeanStrategy(Strategy):
    def __init__(self, buy_percent_parameter=1.03, short_percent_paramter=.97,
                 time_series_length_parameter=10, sell_high_parameter=1.30, sell_low_parameter=.97):
        self.buy_percent_parameter = buy_percent_parameter
        self.short_percent_paramter = short_percent_paramter
        self.time_series_length_parameter = time_series_length_parameter
        self.sell_high_parameter = sell_high_parameter
        self.sell_low_parameter = sell_low_parameter


    def buying_strategy(self, iterated_price_list):
        price = iterated_price_list[-1]


        if len(iterated_price_list) < self.time_series_length_parameter:
            return "Nah"
        
        else:
            rolling_mean = sum(iterated_price_list[(len(iterated_price_list)-self.time_series_length_parameter):]) / self.time_series_length_parameter
            if price > (self.buy_percent_parameter * rolling_mean):
                return "Buy"
            elif price < (self.short_percent_paramter * rolling_mean):
                return "Short"
            else:
                return "Nah"


    def selling_strategy(self, iterated_price_list, purchased_prices,type):
        purchased_prices.sort()
        sorted_purchases = purchased_prices
        current_price = iterated_price_list[-1]

        buy_unloads_front = []
        buy_unloads_back = []
        short_unloads_front = []
        short_unloads_back = []

        if type == "Buy":
            for item in sorted_purchases:
                if (current_price / item) > self.sell_high_parameter:
                    buy_unloads_front.append(item)
                else:
                    break
            for item in sorted_purchases[::-1]:
                if (current_price / item) < self.sell_low_parameter:
                    buy_unloads_back.append(item)
                else:
                    break
            return {"Buy_Unloads_Front" : buy_unloads_front, "Buy_Unloads_Back" : buy_unloads_back}
        
        elif type == "Short":
            for item in sorted_purchases:
                if (item / current_price) < .5:
                    short_unloads_front.append(item)
                else:
                    break
            for item in sorted_purchases[::-1]:
                if (item / current_price) > 1.5:
                    short_unloads_back.append(item)
                else:
                    break
            return {"Short_Unloads_Front" : short_unloads_front, "Short_Unloads_Back" : short_unloads_back}
       
class BuyAndHoldStrategy(Strategy):
    def buying_strategy(self, iterated_price_list):
        return "Buy"
    def selling_strategy(self, iterated_price_list, purchased_prices,type):
        if type == "Buy":
            return {"Buy_Unloads_Front" : [], "Buy_Unloads_Back" : []}
        if type == "Short":
            return {"Short_Unloads_Front" : [], "Short_Unloads_Back" : []}

class Graphing:
    def plot_portfolio_values_with_stats(self, portfolio_values_dicts, stats1, stats2, final_metrics1, final_metrics2):
        fig = plt.figure(figsize=(14, 8))
        ax1 = fig.add_subplot(121)
        for label, values in portfolio_values_dicts.items():
            ax1.plot(values, label=label)
        ax1.set_title('Portfolio Value Over Time')
        ax1.set_xlabel('Time Steps')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True)
        ax1.patch.set_edgecolor('black')
        ax1.patch.set_linewidth(2)

        ax2 = fig.add_subplot(222)
        ax2.axis('off')
        ax2.set_title('Buy and Hold Strategy Stats')
        stats_text1 = self.create_stats_text(stats1) + "\n\nFinal Metrics:\n" + self.create_metrics_text(final_metrics1)
        ax2.text(0.5, 0.5, stats_text1, va='center', ha='center', fontsize=10)
        ax2.patch.set_edgecolor('black') 
        ax2.patch.set_linewidth(2)

        ax3 = fig.add_subplot(224)
        ax3.axis('off')
        ax3.set_title('Active Strategy Stats')
        stats_text2 = self.create_stats_text(stats2) + "\n\nFinal Metrics:\n" + self.create_metrics_text(final_metrics2)
        ax3.text(0.5, 0.5, stats_text2, va='center', ha='center', fontsize=10)
        ax3.grid = True
        ax3.patch.set_edgecolor('black')
        ax3.patch.set_linewidth(2)

        plt.tight_layout()
        plt.show()

    def create_metrics_text(self, metrics):
        metrics_text = f"Total Funds: ${metrics['total_funds']:.2f}\n"
        metrics_text += f"Buy Holdings Value: ${metrics['buy_holdings_value']:.2f}\n"
        metrics_text += f"Short Holdings Value: ${metrics['short_holdings_value']:.2f}"
        return metrics_text

    def format_stats(self, stats):
        formatted_stats = {}
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                formatted_stats[key] = '${:,.2f}'.format(value)
            else:
                formatted_stats[key] = value
        return formatted_stats

    def create_stats_text(self, stats):
        formatted_stats = ""
        for trade_type, trade_stats in stats.items():
            formatted_stats += f"{trade_type}:\n"
            formatted_stats += '\n'.join(f"  {key.replace('_', ' ').title()}: {value}"
                                         for key, value in trade_stats.items())
            formatted_stats += '\n\n'
        return formatted_stats.strip()
    
    def plot_portfolio_values_with_stats(self, portfolio_values_dicts, stats1, stats2, final_metrics1, final_metrics2, use_first_strategy=True):
        if use_first_strategy:
            portfolio_values = portfolio_values_dicts['Buy and Hold']
            stats = stats1
            final_metrics = final_metrics1
            strategy_name = 'Buy and Hold'
        else:
            portfolio_values = portfolio_values_dicts['Rolling Mean Strategy']
            stats = stats2
            final_metrics = final_metrics2
            strategy_name = 'Rolling Mean Strategy'

        fig = plt.figure(figsize=(14, 8))

        ax1 = fig.add_subplot(121)
        ax1.plot(portfolio_values, label=strategy_name)
        ax1.set_title('Portfolio Value Over Time')
        ax1.set_xlabel('Time Steps')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True)
        ax1.patch.set_edgecolor('black')
        ax1.patch.set_linewidth(2)

        ax2 = fig.add_subplot(122)
        ax2.axis('off')
        ax2.set_title(f'{strategy_name} Stats')
        stats_text = self.create_stats_text(stats) + "\n\nFinal Metrics:\n" + self.create_metrics_text(final_metrics)
        ax2.text(0.5, 0.5, stats_text, va='center', ha='center', fontsize=10)
        ax2.patch.set_edgecolor('black')
        ax2.patch.set_linewidth(2)

        plt.tight_layout()
        plt.show()

class TradeAnalysis:
    def __init__(self, mongo_trades):
        self.mongo_trades = mongo_trades
        self.trade_log = self.fetch_trade_log()
        self.buy_trades = []
        self.sell_trades = []
        self.short_trades = []
        self.cover_trades = []
        self.profit_loss_list = []

    def fetch_trade_log(self):
        self.mongo_trades.connect()
        trade_log = {}
        trades = self.mongo_trades.Trading_Trades.find({}, {'_id': 0})
        for trade in trades:
            price = trade['price']
            details = {
                'action': trade['action'],
                'step': trade['step'],
                'closing_price': trade['closing_price'],
                'profit_or_loss': trade['profit_or_loss']
            }
            trade_log[price] = details
        self.mongo_trades.disconnect()
        return trade_log
        

    def process_trades(self):
        for price, details in self.trade_log.items():
            action = details['action']
            if action == 'Buy':
                self.buy_trades.append(details)
            elif action == 'Sell':
                self.sell_trades.append(details)
            elif action == 'Short':
                self.short_trades.append(details)
            elif action == 'Cover':
                self.cover_trades.append(details)

    def get_trade_stats(self, trade_type):
        if trade_type == "Short":
            listvar = self.short_trades
        elif trade_type == "Buy":
            listvar = self.buy_trades
        elif trade_type == "Sell":
            listvar = self.sell_trades
        elif trade_type == "Cover":
            listvar = self.cover_trades

        total_trades = len(listvar)
        profit_loss_values = [trade['profit_or_loss'] for trade in listvar if trade['profit_or_loss'] is not None]

        if not profit_loss_values:
            return {
                "total_trades": 0,
                "total_profit_loss": 0,
                "best_trade": 0,
                "worst_trade": 0
            }

        net_profit = sum(profit_loss_values)
        max_profit = max(profit_loss_values)
        max_loss = min(profit_loss_values)

        return {
            "total_trades": total_trades,
            "total_profit_loss": net_profit,
            "best_trade": max_profit,
            "worst_trade": max_loss
        }


class MongoMovesHoldings:
    def connect(self):
        uri = "mongodb+srv://AdminBoi:Thenims123@cluster0.4t4pyyk.mongodb.net/"
        self.client = MongoClient(uri)
        self.db = self.client['Trading_Holdings']
        self.Trading_Holdings = self.db['Trading_Holdings']

    def disconnect(self):
        self.client.close()

    def reset_holdings(self):
        self.Trading_Holdings.delete_many({})

        initial_holdings = [
            {'type': 'Buy', 'count': 0, 'total_value': 0, 'price_when_added': []},
            {'type': 'Short', 'count': 0, 'total_value': 0, 'price_when_added': []}
        ]
        
        for holding in initial_holdings:
            self.Trading_Holdings.insert_one(holding)
            
    def get_prices_for_all_types(self):
        prices = {}
        for trade_type in ['Buy', 'Short']:
            holding = self.Trading_Holdings.find_one({'type': trade_type})

            prices[trade_type] = holding.get('price_when_added', []) if holding else []
        return prices
    
    def collective_holdings_updates(self, buy_shares, total_buy_value, buy_list, total_short_shares, total_short_value, short_list):

        holdings_to_update = [
            {'type': 'Buy', 'count': buy_shares, 'total_value': total_buy_value, 'price_when_added': buy_list},
            {'type': 'Short', 'count': total_short_shares, 'total_value': total_short_value, 'price_when_added': short_list}
        ]

        for holding in holdings_to_update:
            trade_type = holding['type']
            self.Trading_Holdings.update_one(
                {'type': trade_type},
                {'$set': {
                    'count': holding['count'],
                    'total_value': holding['total_value'],
                    'price_when_added': holding['price_when_added']
                }},
                upsert=True
            )

    def get_current_holdings(self):
        self.connect()
        holdings = list(self.Trading_Holdings.find({}, {'_id': 0}))
        self.disconnect()
        return holdings


class MongoMovesTrades:
    def connect(self):
        uri = "mongodb+srv://AdminBoi:Thenims123@cluster0.4t4pyyk.mongodb.net/"
        self.client = MongoClient(uri)
        self.db = self.client['Trading_Trades']
        self.Trading_Trades = self.db['Trading_Trades']

    def disconnect(self):
        self.client.close()

    def reset_trades(self):
        self.Trading_Trades.delete_many({})

        initial_trades = [
        {
            'price': 0,
            'action': None,
            'step': 0,
            "closing_step" : None,
            'closing_price': None,
            'profit_or_loss': None,
        }
    ]

        for trade in initial_trades:
            self.Trading_Trades.insert_one(trade)

    def update_trades_with_logs(self, trades_to_update):

        for trade in trades_to_update['buying_buys']:
            self.Trading_Trades.insert_one(trade)
        for trade in trades_to_update['buying_shorts']:
            self.Trading_Trades.insert_one(trade)

        for trade in trades_to_update['selling_buys']:
            self.Trading_Trades.update_one(
                {'price': trade['price'], 'action': 'Buy'},
                {'$set': {
                    'action': 'Sell',
                    'closing_step': trade['closing_step'],
                    'closing_price': trade['closing_price'],
                    'profit_or_loss': trade['profit_or_loss']
                }}
            )

        for trade in trades_to_update['selling_shorts']:
            self.Trading_Trades.update_one(
                {'price': trade['price'], 'action': 'Short'},
                {'$set': {
                    'action': 'Cover',
                    'closing_step': trade['closing_step'],
                    'closing_price': trade['closing_price'],
                    'profit_or_loss': trade['profit_or_loss']
                }}
            )

class Backtesting():
    def __init__(self, strategy):
        self.strategy = strategy
        self.mongo_trades = MongoMovesTrades()
        self.mongo_holdings = MongoMovesHoldings()
        self.grapher = Graphing()
        self.open_prices = [price for price in yfinance.Ticker("AAPL").history(period='5y')["Open"]]
        

    def run_yourStrategy_backtest(self):
        total_funds = 100000
        portfolio_values = []
        covered_values = []
        step = 0
        self.mongo_holdings.connect()
        self.mongo_trades.connect()
        self.mongo_holdings.reset_holdings()
        self.mongo_trades.reset_trades()

        for current_price in self.open_prices:
            step +=1
            covered_values.append(current_price)

            trades_to_update = {
                'buying_buys': [],
                'buying_shorts': [],
                'selling_buys': [],
                'selling_shorts': []
                                    }

            prices_dict = self.mongo_holdings.get_prices_for_all_types()
            bought_list = prices_dict["Buy"]
            short_list = prices_dict["Short"]
            total_buy_shares = len(bought_list)
            total_short_shares = len(short_list)
            
            # SELLING
            trade_types = [
                {"type": "Buy", "unload_dict": self.strategy.selling_strategy(iterated_price_list=covered_values, purchased_prices=prices_dict["Buy"], type="Buy"), "trade_list": bought_list, "update_key": 'selling_buys'},
                {"type": "Short", "unload_dict": self.strategy.selling_strategy(iterated_price_list=covered_values, purchased_prices=prices_dict["Short"], type="Short"), "trade_list": short_list, "update_key": 'selling_shorts'}
                    ]           
            
            for trade in trade_types:
                unloads = trade["unload_dict"][f"{trade['type']}_Unloads_Front"] + trade["unload_dict"][f"{trade['type']}_Unloads_Back"]
                
                for item in unloads:
                    trades_to_update[trade["update_key"]].append({
                        "price": item,
                        'action': 'Sell' if trade['type'] == 'Buy' else 'Cover',
                        'closing_step': step,
                        'closing_price': current_price,
                        'profit_or_loss': current_price - item if trade['type'] == 'Buy' else item - current_price
                    })
                
                trade["trade_list"][:] = [item for item in trade["trade_list"] if item not in unloads]
                if trade['type'] == 'Buy':
                    total_funds += len(unloads) * current_price 
                else:
                    total_funds -= len(unloads) * current_price 

            total_buy_shares = len(bought_list)
            total_short_shares = len(short_list)


            # BUYING
            buy_outcome = self.strategy.buying_strategy(iterated_price_list=covered_values)
                
            if buy_outcome in ["Buy", "Short"] and total_funds > current_price:
                if buy_outcome == "Buy":
                    total_buy_shares += 1
                    total_funds -= current_price
                    index = bisect.bisect_left(bought_list, current_price)
                    bought_list.insert(index, current_price)
                    trades_to_update['buying_buys'].append({
                        'price': current_price,
                        'action': 'Buy',
                        'step': step,
                        'closing_step': None,
                        'closing_price': None,
                        'profit_or_loss': None
                    })
                elif buy_outcome == "Short":
                    total_short_shares += 1
                    total_funds += current_price
                    index = bisect.bisect_left(short_list, current_price)
                    short_list.insert(index, current_price)
                    trades_to_update['buying_shorts'].append({
                        'price': current_price,
                        'action': 'Short',
                        'step': step,
                        'closing_step': None,
                        'closing_price': None,
                        'profit_or_loss': None
                    })

            #UPDATE MONGO AND METRICS
            current_short_value = sum(short_list) - (current_price * total_short_shares)
            current_buy_value =(total_buy_shares*current_price)

            self.mongo_holdings.collective_holdings_updates(buy_shares=total_buy_shares, total_buy_value=current_buy_value, buy_list=bought_list, total_short_shares=total_short_shares, total_short_value=current_short_value, short_list=short_list)
            self.mongo_trades.update_trades_with_logs(trades_to_update=trades_to_update)

            money = total_funds + (total_buy_shares*current_price) + current_short_value
            portfolio_values.append(money)

        final_metrics = {
            'total_funds': total_funds,
            'buy_holdings_value': (total_buy_shares*current_price),
            'short_holdings_value': current_short_value
        }
        
        self.mongo_holdings.disconnect()
        self.mongo_trades.disconnect()
        return portfolio_values, final_metrics



strategy2 = RollingMeanStrategy()

backtesting2 = Backtesting(strategy2)

results2, final_metrics_2 = backtesting2.run_yourStrategy_backtest()

current_holdings = backtesting2.mongo_holdings.get_current_holdings()

trade_analysis2 = TradeAnalysis(backtesting2.mongo_trades)
trade_analysis2.process_trades()
stats2 = {
    'Sell': trade_analysis2.get_trade_stats('Sell'),
    'Cover': trade_analysis2.get_trade_stats('Cover')
}

grapher = Graphing()

combined_results = {'Rolling Mean Strategy': results2}

grapher.plot_portfolio_values_with_stats(combined_results, stats2, stats2, final_metrics_2, final_metrics_2, use_first_strategy=False)