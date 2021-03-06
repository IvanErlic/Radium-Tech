import numpy as np
import pandas as pd
from radium.helpers import _truncate


def returns(self):
    """
    Calculates returns accounting for budget and commission

    Returns: Returns as 2D array
    """

    # Get the optimal positions determined by the strategy
    optimal_positions = self.positions()

    # Calculate integer positions determined by rounding optimal positions to 3 d.p.
    rounded_positions = np.zeros(optimal_positions.shape)
    for i in range(self.lookback, optimal_positions.shape[0] - 1):
        rounded_positions[i, 0] = _truncate(optimal_positions[i, 0],
                                            3) * 10 ** 3
        rounded_positions[i, 1] = _truncate(optimal_positions[i, 1],
                                            3) * 10 ** 3

    # Get closed prices
    prices = pd.concat([self.pair.equity1.closed, self.pair.equity2.closed],
                       axis=1)

    # Calculate orders
    equity1_orders = np.diff(rounded_positions[:, 0])
    equity1_orders = np.append(0, equity1_orders)
    equity2_orders = np.diff(rounded_positions[:, 1])
    equity2_orders = np.append(0, equity2_orders)

    # Calculate commissions per daily order (minimum price of 0.35)
    equity1_comm = np.array(
        [max(abs(x) * 0.0035, 0.35) if x != 0 else 0 for x in equity1_orders])
    equity2_comm = np.array(
        [max(abs(x) * 0.0035, 0.35) if x != 0 else 0 for x in equity2_orders])

    # Calculate Initial Budget, equal to buy 1000 units of each equity
    init_budget = 1000 * (self.pair.equity1.closed.iloc[0] +
                          self.pair.equity2.closed.iloc[0])
    # Truncate to 2 d.p.
    budget = _truncate(init_budget, 2)

    # Calculate returns from Equity 1 and Equity 2
    for i in range(0, len(equity1_orders) - 1):
        budget += -1 * equity1_orders[i] * self.pair.equity1.closed.iloc[i] - \
                  equity1_comm[i]
        budget += -1 * equity2_orders[i] * self.pair.equity2.closed.iloc[i] - \
                  equity2_comm[i]

    return budget / init_budget - 1
