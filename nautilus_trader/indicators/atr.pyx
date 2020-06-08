# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2020 Nautech Systems Pty Ltd. All rights reserved.
#  The use of this source code is governed by the license as found in the LICENSE file.
#  https://nautechsystems.io
# -------------------------------------------------------------------------------------------------

import cython

from nautilus_trader.core.correctness cimport Condition
from nautilus_trader.indicators.base.indicator cimport Indicator
from nautilus_trader.indicators.average.ma_factory import MovingAverageFactory, MovingAverageType


cdef class AverageTrueRange(Indicator):
    """
    An indicator which calculates the average true range across a rolling window.
    Different moving average types can be selected for the inner calculation.
    """

    def __init__(self,
                 int period,
                 ma_type not None: MovingAverageType=MovingAverageType.SIMPLE,
                 bint use_previous=True,
                 double value_floor=0.0,
                 bint check_inputs=False):
        """
        Initializes a new instance of the AverageTrueRange class.

        :param period: The rolling window period for the indicator (> 0).
        :param ma_type: The moving average type for the indicator (cannot be None).
        :param use_previous: The boolean flag indicating whether previous price values should be used.
        (note: only applicable for update(). update_mid() will need to use previous price.
        :param value_floor: The floor (minimum) output value for the indicator (>= 0).
        :param check_inputs: The flag indicating whether the input values should be checked.
        """
        Condition.positive_int(period, 'period')
        Condition.not_negative(value_floor, 'value_floor')

        super().__init__(params=[period,
                                 ma_type.name,
                                 use_previous,
                                 value_floor],
                         check_inputs=check_inputs)

        self.period = period
        self._moving_average = MovingAverageFactory.create(self.period, ma_type)
        self._use_previous = use_previous
        self._value_floor = value_floor
        self._previous_close = 0.0
        self.value = 0.0

    @cython.binding(True)
    cpdef void update(
            self,
            double high,
            double low,
            double close):
        """
        Update the indicator with the given values.

        :param high: The high price (> 0).
        :param low: The low price (> 0).
        :param close: The close price (> 0).
        """
        if self.check_inputs:
            Condition.positive(high, 'high')
            Condition.positive(low, 'low')
            Condition.positive(close, 'close')
            Condition.true(high >= low, 'high >= low')
            Condition.true(high >= close, 'high >= close')
            Condition.true(low <= close, 'low <= close')

        # Calculate average
        if self._use_previous:
            if not self.has_inputs:
                self._previous_close = close
            self._moving_average.update(max(self._previous_close, high) - min(low, self._previous_close))
            self._previous_close = close
        else:
            self._moving_average.update(high - low)

        self._floor_value()
        self._check_initialized()

    @cython.binding(True)
    cpdef void update_mid(self, double close):
        """
        Update the indicator with the given value.
        
        :param close: The mid close price (> 0).
        """
        if self.check_inputs:
            Condition.positive(close, 'close')

        if not self.has_inputs:
            self._previous_close = close

        # Calculate average
        self._moving_average.update(max(self._previous_close, close) - min(close, self._previous_close))
        self._previous_close = close

        self._floor_value()
        self._check_initialized()

    cdef void _floor_value(self):
        if self._value_floor == 0:
            self.value = self._moving_average.value
        elif self._value_floor < self._moving_average.value:
            self.value = self._moving_average.value
        else:
            # Floor the value
            self.value = self._value_floor

    cdef void _check_initialized(self):
        """
        Initialization logic.
        """
        if not self.initialized:
            self.has_inputs = True
            if self._moving_average.initialized:
                self.initialized = True

    cpdef void reset(self):
        """
        Reset the indicator by clearing all stateful values.
        """
        self._reset_base()
        self._moving_average.reset()
        self._previous_close = 0.0
        self.value = 0.0