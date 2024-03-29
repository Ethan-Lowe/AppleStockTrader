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
    def __init__(self, buy_percent_parameter=1.03, short_percent_paramter=.90,
                 time_series_length_parameter=50, sell_high_parameter=2.50, sell_low_parameter=.90):
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
                if (item / current_price) < self.sell_low_parameter:
                    short_unloads_front.append(item)
                else:
                    break
            for item in sorted_purchases[::-1]:
                if (item / current_price) > self.sell_high_parameter:
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
        # Create a grid for the plots
        fig = plt.figure(figsize=(14, 8))

        # Add the portfolio values plot
        ax1 = fig.add_subplot(121)
        for label, values in portfolio_values_dicts.items():
            ax1.plot(values, label=label)
        ax1.set_title('Portfolio Value Over Time')
        ax1.set_xlabel('Time Steps')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend()
        ax1.grid(True)
        ax1.patch.set_edgecolor('black')  # Set edge color
        ax1.patch.set_linewidth(2)  # Set line width

        # Add stats for the first strategy, including final metrics
        ax2 = fig.add_subplot(222)
        ax2.axis('off')
        ax2.set_title('Buy and Hold Strategy Stats')
        stats_text1 = self.create_stats_text(stats1) + "\n\nFinal Metrics:\n" + self.create_metrics_text(final_metrics1)
        ax2.text(0.5, 0.5, stats_text1, va='center', ha='center', fontsize=10)
        ax2.patch.set_edgecolor('black')  # Set edge color
        ax2.patch.set_linewidth(2)  # Set line width

        # Add stats for the second strategy, including final metrics
        ax3 = fig.add_subplot(224)
        ax3.axis('off')
        ax3.set_title('Active Strategy Stats')
        stats_text2 = self.create_stats_text(stats2) + "\n\nFinal Metrics:\n" + self.create_metrics_text(final_metrics2)
        ax3.text(0.5, 0.5, stats_text2, va='center', ha='center', fontsize=10)
        ax3.grid = True
        ax3.patch.set_edgecolor('black')  # Set edge color
        ax3.patch.set_linewidth(2)  # Set line width

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
        #print(listvar)

        total_trades = len(listvar)
        profit_loss_values = [trade['profit_or_loss'] for trade in listvar if trade['profit_or_loss'] is not None]

        if not profit_loss_values:  # If the list is empty, return zeros
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

    def get_prices_by_type(self, trade_type):
        holding = self.Trading_Holdings.find_one({'type': trade_type})
        if holding:
            return holding.get('price_when_added', [])
        return []
    
    def get_count_by_type(self, trade_type):
        holding = self.Trading_Holdings.find_one({'type': trade_type})
        if holding:
            return holding.get('count', 0)
        return 0
    
    def get_total_value_by_type(self, trade_type):
        holding = self.Trading_Holdings.find_one({'type': trade_type})
        if holding:
            return holding.get('total_value', 0)
        return 0
    
    def change_share_count_by_type(self, trade_type, change_value):
        holdings = self.Trading_Holdings.find_one({"type":trade_type})
        if holdings is not None:
            new_count = holdings["count"] + change_value
        else:
            new_count = change_value

        self.Trading_Holdings.update_one(
                {'type': trade_type},
                {'$set': {'count': new_count}}
            )
    
    def add_share_price_to_list_by_type(self, trade_type, new_price):
        holding = self.Trading_Holdings.find_one({'type': trade_type})
        
        if holding:
            prices = holding.get('price_when_added')
        else:
            # If no document is found, return an empty list or handle accordingly
            prices = []
            
        
        # Proceed with adding the new price to the list and updating the document
        prices.append(new_price)  # Add the new price to the list
        self.Trading_Holdings.update_one(
            {'type': trade_type},
            {'$set': {'price_when_added': prices}}
        )

    
    def update_share_list_by_type(self, trade_type, new_list):
        
        self.Trading_Holdings.update_one(
                {'type': trade_type},
                {'$set': {'price_when_added': new_list}}
            )

                                              
    def update_total_value_by_type(self, trade_type,shares,price_or_delta):

        new_total_value = shares * price_or_delta

        self.Trading_Holdings.update_one(
                {'type': trade_type},
                {'$set': {'total_value': new_total_value}}
            )
        
    def get_prices_for_all_types(self):
        prices = {}
        for trade_type in ['Buy', 'Short']:
            holding = self.Trading_Holdings.find_one({'type': trade_type})
            if holding:
                prices[trade_type] = holding.get('price_when_added', [])
            else:
                prices[trade_type] = []  # Default to empty list if not found
        return prices
    
    def collective_holdings_updates(self,update):
        for holding in update:
            trade_type = holding['type']
            existing_holding = self.Trading_Holdings.find_one({'type': trade_type})

            if existing_holding:
                self.Trading_Holdings.update_one(
                    {'type': trade_type},
                    {'$set': {
                        'count': holding['count'],
                        'total_value': holding['total_value'],
                        'price_when_added': holding['prices_when_added']
                    }}
                )
            else:
                self.Trading_Holdings.insert_one(holding)



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
            'closing_price': None,
            'profit_or_loss': None,
        }
    ]

        for trade in initial_trades:
            self.Trading_Trades.insert_one(trade)

    def add_trade(self, price, action, step, closing_price, profit_or_loss):
        trade = {
            'price': price,
            'action': action,
            'step': step,
            'closing_price': closing_price,
            'profit_or_loss': profit_or_loss,
        }
        self.Trading_Trades.insert_one(trade)

    def update_trade(self, price, action, sold_price, profit_or_loss):
        self.Trading_Trades.update_one({'price': price}, {'$set': {"action": action, 'closing_price': sold_price, 'profit_or_loss': profit_or_loss}})



class Backtesting():
    def __init__(self, strategy):
        self.strategy = strategy
        self.mongo_trades = MongoMovesTrades()
        self.mongo_holdings = MongoMovesHoldings()
        #self.holdings = {"Buy": {"count": 0, "total_value": 0, "price_when_added" : []}, "Short": {"count": 0, "total_value": 0, "price_when_added" : []}}
        self.grapher = Graphing()
        #self.trade_log = {}
        self.open_prices = [price for price in yfinance.Ticker("AAPL").history(period='5y')["Open"]][:200]
        

    def run_yourStrategy_backtest(self):
        total_funds = 100000
        portfolio_values = []
        covered_values = []
        step = 0
        self.mongo_holdings.connect()
        self.mongo_trades.connect()
        self.mongo_holdings.reset_holdings()
        self.mongo_trades.reset_trades()

        # main run through price data
        for current_price in self.open_prices:
            step +=1
            covered_values.append(current_price)
            trades_to_update = {}
            holdings_to_update = [{'type': 'Buy', 'count': 0, "total_value":0,"prices_when_added" : []},
            {'type': 'Buy', 'count': 0, "total_value":0,"prices_when_added" : []}]

    

            prices_dict = self.mongo_holdings.get_prices_for_all_types()
            total_buy_shares = len(prices_dict["Buy"])
            total_short_shares = len(prices_dict["Short"])
            
            # SELLING
            #buys
            
            bought_list = prices_dict["Buy"]
            short_list = prices_dict["Short"]

            buy_unload_dict = self.strategy.selling_strategy(iterated_price_list=covered_values, purchased_prices=prices_dict["Buy"], type="Buy")

            front = len(buy_unload_dict["Buy_Unloads_Front"])
            back = len(buy_unload_dict["Buy_Unloads_Back"])

            if front or back > 0:
                reduction_shares = (front + back)*-1
                holdings_to_update[0]["change_in_shares"] += reduction_shares

                if front > 0:
                    for item in buy_unload_dict["Buy_Unloads_Front"]:
                        #LOG SELLING A BUY, CAN PROB GROUP THESE
                        self.mongo_trades.update_trade(price = item, action = "Sell", sold_price=current_price, profit_or_loss=(current_price-item))
                if back > 0:
                    for item in buy_unload_dict["Buy_Unloads_Back"]:
                        #LOG SELLING A BUY, CAN PROB GROUP THESE
                        self.mongo_trades.update_trade(price = item, action = "Sell", sold_price=current_price, profit_or_loss=(current_price-item))

                total_funds += (reduction_shares*current_price)

                #HAVE THE MAIN UPDATE FUNCTION AUTOMATICALLY LOG THE TOTAL BUY VALUE GIVEN THE CHANGES TO THE HOLDINGS AND THE CURRENT PRICE

                if front > 0:
                    del bought_list[:front]
                    total_buy_shares -= len(bought_list[:front])
                if back > 0:
                    del bought_list[-back:]
                    total_buy_shares -= len(bought_list[:back])

                #RETURN TO THE BOUGHT LIST AFTER ANY BUYS, ADDING THEM, AND THEN INSERT THAT INTO THE HOLDINGS FUNCTION
            
            #WAIT TO UPDATE TOTAL BUY VALUE UNTIL AFTER THE BUYING OF A SHARE IS POTENTIALLY DONE, ADD THAT TO THE COUNT VARIABLE TO GET THE SHARES
                    
            #shorts
            total_short_shares = len(prices_dict["Short"])
            short_unload_dict = self.strategy.selling_strategy(iterated_price_list=covered_values, purchased_prices=prices_dict["Short"],type="Short")
            
            front = len(short_unload_dict["Short_Unloads_Front"])
            back = len(short_unload_dict["Short_Unloads_Back"])

            if front or back > 0:
                reduction_shares = (front + back)*-1
                holdings_to_update[1]["change_in_shares"] += reduction_shares

                if front > 0:
                    for item in short_unload_dict["Short_Unloads_Front"]:
                        #LOG SELLING A SHORT, CAN PROB GROUP THESE
                        self.mongo_trades.update_trade(price = item, action = "Cover", sold_price=current_price, profit_or_loss=(current_price-item))
                if back > 0:
                    for item in short_unload_dict["Short_Unloads_Back"]:
                        #LOG SELLING A SHORT, CAN PROB GROUP THESE
                        self.mongo_trades.update_trade(price = item, action = "Cover", sold_price=current_price, profit_or_loss=(current_price-item))

                

                
                
                front_sum = sum(short_list[:front])
                back_sum = sum(short_list[-back:])
                total_sum = front_sum + back_sum

                short_profit = total_sum + (reduction_shares*current_price)
                total_funds += short_profit

                if front > 0:
                    del short_list[:front]
                    total_short_shares -= len(short_list[:front])
                if back > 0:
                    del short_list[-back:]
                    total_short_shares -= len(short_list[:back])
                #WAIT UNTIL LAST SHORT OPERATION TO ADJUST TOTAL SHORT SHARES AND ALL THAT
            
          #A bunch of total value by type bullshit for shorts, again we shall wait on it

            # BUYING
            #buys
            if total_funds >= current_price:

                if self.strategy.buying_strategy(iterated_price_list=covered_values) == "Buy":
                    total_buy_shares += 1

                    #LOG THE TRADE (BUYING A BUY)                
        
                    total_funds -= current_price

                    index = bisect.bisect_left(bought_list, current_price)
                    bought_list.insert(index, current_price)
                
            #shorts
                if (self.strategy.buying_strategy(iterated_price_list=covered_values) == "Short"):
                    total_short_shares += 1

                    #LOG THAT MF TRADE (BUYING A SHORT)

                    total_funds -= current_price

                    index = bisect.bisect_left(short_list, current_price)
                    short_list.insert(index, current_price)

            #UPDATE USING THE COLLECTIVE FUNCTIONS
            holdings_to_update[0]["count"] = total_buy_shares
            holdings_to_update[1]["count"] = total_short_shares
            holdings_to_update[0]["total_value"] = (total_buy_shares*current_price)
            current_short_value = 0
            if total_short_shares == 0:
                holdings_to_update[1]["total_value"] = 0
            else:
                mean = sum(short_list)/len(short_list)
                current_short_value = (mean-current_price)*total_short_shares
                holdings_to_update[1]["total_value"] = current_short_value
            holdings_to_update[0]["prices_when_added"] = bought_list
            holdings_to_update[1]["prices_when_added"] = short_list
            self.mongo_holdings.collective_holdings_updates(holdings_to_update)

             

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


mongo_trades = MongoMovesTrades()
mongo_holdings = MongoMovesHoldings()

# Instantiate the BuyAndHoldStrategy and RollingMeanStrategy
strategy1 = BuyAndHoldStrategy()
strategy2 = RollingMeanStrategy()

# Start profiling here
with cProfile.Profile() as pr:
    # Instantiate the Backtesting class with the respective strategies
    backtesting1 = Backtesting(strategy1)
    backtesting2 = Backtesting(strategy2)

    # Run the backtesting and get the results for both strategies
    results1, final_metrics_1 = backtesting1.run_yourStrategy_backtest()
    results2, final_metrics_2 = backtesting2.run_yourStrategy_backtest()

# End profiling here
pr.dump_stats('backtesting_profile.prof')

# Processing and viewing the stats
ps = pstats.Stats('backtesting_profile.prof')
ps.sort_stats('cumulative').print_stats(10)

# Instantiate the TradeAnalysis class with the respective mongo_trades instances for the second strategy
trade_analysis1 = TradeAnalysis(backtesting1.mongo_trades)
trade_analysis1.process_trades()
stats1 = {
    'Sell': trade_analysis1.get_trade_stats('Sell'),
    'Cover': trade_analysis1.get_trade_stats('Cover')
}

trade_analysis2 = TradeAnalysis(backtesting2.mongo_trades)
trade_analysis2.process_trades()
stats2 = {
    'Sell': trade_analysis2.get_trade_stats('Sell'),
    'Cover': trade_analysis2.get_trade_stats('Cover')
}

# Combine the results for plotting
combined_results = {'Buy and Hold': results1, 'Active Strategy': results2}

# Instantiate the Graphing class and plot the results and statistics for both strategies
grapher = Graphing()
grapher.plot_portfolio_values_with_stats(combined_results, stats1, stats2, final_metrics_1, final_metrics_2)