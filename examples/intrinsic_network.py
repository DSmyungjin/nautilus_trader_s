#!/usr/bin/env python3
# -------------------------------------------------------------------------------------------------
# <copyright file="ema_cross.py" company="Invariance Pte">
#  Copyright (C) 2018-2019 Invariance Pte. All rights reserved.
#  The use of this source code is governed by the license as found in the LICENSE.md file.
#  http://www.invariance.com
# </copyright>
# -------------------------------------------------------------------------------------------------

from inv_trader.model.enums import OrderSide, MarketPosition
from inv_trader.model.objects import Tick, BarType, Bar, Instrument, Quantity
from inv_trader.model.events import Event, PositionOpened
from inv_trader.strategy import TradeStrategy

from inv_indicators.intrinsic_network import IntrinsicNetwork


class INStrategyExample(TradeStrategy):
    """"
    An example strategy utilizing an Intrinsic Network.
    """

    def __init__(self,
                 order_id_tag: str,
                 flatten_on_sl_reject: bool,
                 flatten_on_stop: bool,
                 cancel_all_orders_on_stop: bool,
                 instrument: Instrument,
                 bar_type: BarType,
                 position_size=1000000,
                 threshold_entry=0.0020,
                 threshold_close=0.0020):
        """
        Initializes a new instance of the IntrinsicNetworkExample class.

        :param order_id_tag: The order identifier tag for the strategy (must be unique at trader level).
        :param flatten_on_sl_reject: The flag indicating whether the position with an
        associated stop order should be flattened if the order is rejected.
        :param flatten_on_stop: The flag indicating whether the strategy should
        be flattened on stop.
        :param cancel_all_orders_on_stop: The flag indicating whether all residual
        orders should be cancelled on stop.
        :param instrument: The instrument for the strategy.
        :param bar_type: The bar type for the strategy.
        :param position_size: The position size.
        :param threshold_entry: The threshold for the IntrinsicNetwork entry direction.
        :param threshold_entry: The threshold for the IntrinsicNetwork close direction.
        """
        # Send the below arguments into the base class
        super().__init__(order_id_tag=order_id_tag,
                         flatten_on_sl_reject=flatten_on_sl_reject,
                         flatten_on_stop=flatten_on_stop,
                         cancel_all_orders_on_stop=cancel_all_orders_on_stop)

        # Custom strategy variables
        self.instrument = instrument
        self.symbol = instrument.symbol
        self.bar_type = bar_type
        self.position_size = position_size
        self.in_state = 0
        self.position = None

        # Create the indicators for the strategy
        self.intrinsic_network = IntrinsicNetwork(threshold_entry, threshold_close)

        # Register the indicators for updating
        self.register_indicator(self.bar_type, self.intrinsic_network,
                                self.intrinsic_network.update)

    def on_start(self):
        """
        This method is called when self.start() is called, and after internal start logic.
        """
        # Put custom code to be run on strategy start here (or pass)
        self.historical_bars(self.bar_type)
        self.subscribe_bars(self.bar_type)
        self.subscribe_ticks(self.symbol)

    def on_tick(self, tick: Tick):
        """
        This method is called whenever a Tick is received by the strategy, and
        after the Tick has been processed by the base class.
        The received Tick object is then passed into this method.

        :param tick: The received tick.
        """
        # self.log.info(f"Received Tick({tick})")  # For demonstration purposes

    def on_bar(self, bar_type: BarType, bar: Bar):
        """
        This method is called whenever the strategy receives a Bar, and after the
        Bar has been processed by the base class.
        The received BarType and Bar objects are then passed into this method.

        :param bar_type: The received bar type.
        :param bar: The received bar.
        """
        if not self.intrinsic_network.initialized:
            # Wait for indicator to warm up...
            return

        if self.in_state != self.intrinsic_network.state:
            self.log.info(f"IN STATE CHANGE from {self.in_state} to {self.intrinsic_network.state}")
            self.in_state = self.intrinsic_network.state

            # BUY LOGIC
            if self.intrinsic_network.state == -1:
                if self.position is None:
                    self._go_long()
                elif self.position.is_flat:
                    self._go_long()
                elif self.position.is_long:
                    pass  # Stay long
                elif self.position.is_short:
                    self.flatten_position(self.position.id)
                    self._go_long()

            # SELL LOGIC
            elif self.intrinsic_network.state == 1:
                if self.position is None:
                    self._go_short()
                elif self.position.is_flat:
                    self._go_short()
                elif self.position.is_short:
                    pass  # Stay short
                elif self.position.is_long:
                    self.flatten_position(self.position.id)
                    self._go_short()

    def on_event(self, event: Event):
        """
        This method is called whenever the strategy receives an Event object,
        and after the event has been processed by the TradeStrategy base class.
        These events could be AccountEvent, OrderEvent, PositionEvent, TimeEvent.

        :param event: The received event.
        """
        # Put custom code for event handling here (or pass)
        if isinstance(event, PositionOpened):
            self.position = event.position

    def on_stop(self):
        """
        This method is called when self.stop() is called and after internal
        stopping logic.
        """
        # Put custom code to be run on strategy stop here (or pass)
        pass

    def on_reset(self):
        """
        This method is called when self.reset() is called, and after internal
        reset logic such as clearing the internally held bars, ticks and resetting
        all indicators.
        """
        # Put custom code to be run on a strategy reset here (or pass)
        pass

    def on_dispose(self):
        """
        This method is called when self.dispose() is called. Dispose of any
        resources that had been used by the strategy here.
        """
        # Put custom code to be run on a strategy disposal here (or pass)
        self.unsubscribe_bars(self.bar_type)
        self.unsubscribe_ticks(self.symbol)

    def _go_long(self):
        """
        Custom method for going long.
        """
        entry = self.order_factory.market(
            symbol=self.symbol,
            order_side=OrderSide.BUY,
            quantity=Quantity(self.position_size))

        self.submit_entry_order(entry, self.generate_position_id(self.symbol))

    def _go_short(self):
        """
        Custom method for going short.
        """
        entry = self.order_factory.market(
            symbol=self.symbol,
            order_side=OrderSide.SELL,
            quantity=Quantity(self.position_size))

        self.submit_entry_order(entry, self.generate_position_id(self.symbol))