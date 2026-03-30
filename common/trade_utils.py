def apply_trailing_sl(df, initial_sl_factor=0.80, trail_factor=0.60, rsi_sl=0.85):
    # Prepare arrays for speed
    closes = df['Close'].values
    buys = df['buy_flag'].values
    reversals = df['bear_reversal'].values

    sl_column = [0.0] * len(df)
    peak_price = 0.0
    entry_price = 0.0
    in_position = False
    current_active_sl = 0.0

    for i in range(len(df)):
        current_close = closes[i]

        # 1. Trigger Entry
        if buys[i] and not in_position:
            in_position = True
            entry_price = current_close
            peak_price = current_close
            # Set Initial SL at exactly 16% below entry
            current_active_sl = entry_price * initial_sl_factor

        if in_position:
            # 2. Update the running high (Peak)
            if current_close > peak_price:
                peak_price = current_close

            # 3. Profit Threshold for tighter exit (50% gain)
            is_high_profit = current_close >= (entry_price * 2.4)

            # 4. Calculate the "Candidate" SL
            # If high profit + reversal, use tighter rsi_sl (e.g., 0.92)
            if is_high_profit and reversals[i]:
                new_sl_calculation = peak_price * rsi_sl
            else:
                # Standard trailing logic at 70% of peak
                new_sl_calculation = peak_price * trail_factor

            # 5. The Ratchet: SL can only move UP
            if new_sl_calculation > current_active_sl:
                current_active_sl = new_sl_calculation

            sl_column[i] = current_active_sl

            # 6. Check for SL breach
            if current_close < current_active_sl:
                in_position = False
                peak_price = 0.0
                entry_price = 0.0
                current_active_sl = 0.0
        else:
            sl_column[i] = 0.0

    return sl_column