from datetime import datetime, date
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import statsmodels.formula.api as sm

from radium import Equity
from radium.helpers import _truncate, _convert_date


class Pair:
    """
    Class for a pair of equities.

    Attributes
    ----------
    price_spread
    equity1 : radium.Equity
    equity2 : radium.Equity
    start_date : datetime.date
    end_date : datetime.date
    hedge_ratios : float np.ndarray[][2]
        ndarray of pairs of hedge ratios.
    """

    def __init__(self, equity1, equity2):
        """
        Initialise Pair class

        Parameters
        ----------
        equity1 : radium.Equity 
        equity2 : radium.Equity 

        Raises
        ------
        TypeError
            If equity1 or equity2 is not of type radium.Equity.
        ValueError
            If equity1 and equity2 do not share any date ranges
        """
        if not isinstance(equity1, Equity):
            raise TypeError('equity1 must of type radium.Equity')
        elif not isinstance(equity2, Equity):
            raise TypeError('equity2 must of type radium.Equity')

        self.equity1 = equity1
        self.equity2 = equity2

        # Sets start date as latest start date of equities
        if equity1.start_date >= equity2.start_date:
            self.start_date = equity1.start_date
        else:
            self.start_date = equity2.start_date

        # Sets end date as earliest end date of equities
        if equity1.end_date <= equity2.end_date:
            self.end_date = equity1.end_date
        else:
            self.end_date = equity2.end_date

        # If end date is before start date then date ranges of equities is
        # incompatible
        if self.end_date <= self.start_date:
            raise ValueError("There is no shared date ranges between equity1"
                             "and equity2")

    def hedge(self, method, lookback):
        """
        Calculates the hedge_ratios given a method and lookback and stores it
        in self.hedge_ratios

        Parameters
        ----------
        method : str
            Method for calculating hedge ratios ('ols')
        lookback: int
            Number of signals to lookback on when calculating hedge ratios

        Raises
        ------
        TypeError
            If method isn't a string.
            If lookback isn't an integer.
        ValueError
            If lookback <= 0.
            If method isn't available.

        Notes
        -----
        Available methods: 'OLS'
        """

        # Exception handling of method
        if not isinstance(method, str):
            raise TypeError('method must be a string')
        
        # Exception handling of lookback
        if not isinstance(lookback, int):
            raise TypeError('lookback must be an integer.')
        elif lookback <= 0:
            raise ValueError('lookback must be > 0')

        # Calculate hedge ratios based on the method provided
        if method == 'OLS':
            self.hedge_ratios = self._hedge_ols(lookback)
        else:
            raise ValueError('Available method strings: "OLS"')

    @property
    def price_spread(self):
        """
        float np.ndarray[] : ndarray of price spread of equities for self.hedge_ratios

        Raises
        ------
        TypeError
            If self.hedge_ratios isn't defined.

        Notes
        -----
        Spread calculated using y = h1*y1 + h2*y2.
        """

        if hasattr(self, 'hedge_ratios') == False:
            raise Exception('Pair.hedge_ratios is not defined.')

        # Calculate price_spread if undefined
        if hasattr(self, '_price_spread') == False:
            # Construct dataframe of closed prices
            prices = pd.concat([self.equity1.closed, self.equity2.closed],
                                axis=1)
            prices.columns = [self.equity1.symbol, self.equity2.symbol]

            # Multiply and add for each date
            self._price_spread = np.sum(self.hedge_ratios * prices, axis=1)

        return self._price_spread

    def budget(self, hedge_ratio, dec):
        """
        Calculates budget needed to buy integer number of equities.

        Parameters
        ----------
        hedge_ratio : int np.ndarray[2]
            Hedge ratios of pair
        dec : int
            Number of decimals to truncate to 

        Returns
        -------
        budget : float
            Budget needed rounded to 2 d.p.

        Raises
        -----
        TypeError
            If hedge_ratio isnt a list of floats, or dec isnt an integer.
        ValueError
            If hedge_ratio isn't length 2 or dec < 0.
        """

        if not isinstance(hedge_ratio, list):
            raise TypeError('hedge_ratio must be a list')
        elif not len(hedge_ratio) == 2:
            raise ValueError('hedge_ratio must have length 2')
        elif not isinstance(hedge_ratio[0], float):
            raise TypeError('hedge_ratio must be a list of floats')
        elif not isinstance(hedge_ratio[1], float):
            raise TypeError('hedge_ratio must be a list of floats')

        if not isinstance(dec, int):
            raise TypeError('Decimal places must be an integer.')
        elif dec < 0:
            raise ValueError('Decimal places has to be >= 0.')

        # Get the prices at end_date
        equity1_price = self.equity1.closed.iloc[-1]
        equity2_price = self.equity2.closed.iloc[-1]

        # Calculate truncated ratios to given number of decimals 
        truncated_ratios = np.array([_truncate(n, dec) for n in hedge_ratio])

        # Calculate budget to buy integer number of equites
        budget = equity1_price * abs(truncated_ratios[0]) * 10 ** dec \
                 + equity2_price * abs(truncated_ratios[1]) * 10 ** dec

        # Truncated budget to 2 decimals places
        budget = _truncate(budget, 2)

        return budget

    def plot_closed(self, start_date=None, end_date=None):
        """
        Plots closed prices of both equities between two dates as a line graph

        Parameters
        ----------
        start_date : (optional) str or datetime or datetime.date
            First date to plot in YYYY-MM-DD form, defaults to equity start date
        end_date : (optional) str of datetime or datetime.date
            Last date to plot in YYYY-MM-DD form, defaults to equity end date

        Raises
        ------
        ValueError
            End date is same as or before start date
        """

        # If no start/end date specified use default
        if start_date is None:
            start_date = self.start_date
        else:
            start_date = _convert_date(start_date)

        if end_date is None:
            end_date = self.end_date
        else:
            end_date = _convert_date(end_date)

        # Raises error if date range invalid
        if end_date <= start_date:
            raise ValueError('end_date is the same as or before start_date')
        elif start_date < self.start_date:
            raise ValueError('start_date can\'t be before pair.start_date')
        elif end_date > self.end_date:
            raise ValueError('end_date can\'t be after pair.end_date')

        # Gets required range only for both equities
        equity1_closed = self.equity1.closed
        mask = (equity1_closed.index >= start_date) \
               & (equity1_closed.index <= end_date)
        equity1_closed = equity1_closed.loc[mask]

        equity2_closed = self.equity2.closed
        mask = (equity2_closed.index >= start_date) \
               & (equity2_closed.index <= end_date)
        equity2_closed = equity2_closed.loc[mask]

        fig, ax = plt.subplots()
        plt.plot(equity1_closed, label=self.equity1.symbol)
        plt.plot(equity2_closed, label=self.equity2.symbol)

        title = (f'{self.equity1.symbol} and {self.equity2.symbol} '
                 f'from {start_date} to {end_date}')
        plt.title(title)
        plt.xlabel("Date")
        plt.ylabel("Adjusted closed prices ($)")

        # Put dollar marks infront of y axis
        formatter = ticker.FormatStrFormatter('$%1.2f')
        ax.yaxis.set_major_formatter(formatter)

        plt.legend()
        plt.grid()
        plt.show()

    def plot_price_spread(self):
        """
        Plots price spread of the pair given hedge_ratios

        Raises
        ------
        Exception
            If self.hedge_ratios is not defined.
        """

        if hasattr(self, '_hedge_ratios') == False:
            raise Exception('Pair.hedge_ratios is not defined.')

        dates = self.equity1.closed.index.values
        price_spread = self.price_spread

        plt.plot(dates, price_spread)

        title = f'{self.equity1.symbol} and {self.equity2.symbol} price spread'
        plt.title(title)
        plt.xlabel('Date')
        plt.ylabel('Price Spread ($)')

        plt.grid()
        plt.show()

    def _hedge_ols(self, lookback):
        """
        Calculate pair hedge ratios by OLS regression.

        self.equity1 will be used as response variable when regressing.

        Parameters
        ----------
        lookback : int
            Number of signals to lookback on when regressing.

        Returns 
        -------
        hedge_ratios : float np.ndarray[][2]
            Hedge ratios as [[1, -1*(OLS gradient)],...].
        """

        # Construct dataframe of closed prices
        df = pd.concat([self.equity1.closed, self.equity2.closed], axis=1)
        df.columns = [self.equity1.symbol, self.equity2.symbol]

        # Get ols regression result for each date
        hedge_ratios = np.zeros(df.shape)
        for i in range(lookback, hedge_ratios.shape[0]):
            formula = f"{self.equity1.symbol} ~ {self.equity2.symbol}"
            df_lookback = df[(i - lookback):i]
            ols = sm.ols(formula, df_lookback).fit()

            # Hedge ratio for equity2 is -1*(OLS gradient)
            hedge_ratios[i - 1][0] = 1
            hedge_ratios[i - 1][1] = -1*ols.params[1]

        return hedge_ratios
