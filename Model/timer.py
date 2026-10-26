

def format_time(seconds):
    tenths_total = round(max(0, seconds) * 10)
    minutes, remaining_tenths = divmod(tenths_total, 600)
    whole_seconds, tenths = divmod(remaining_tenths, 10)
    return f"{minutes:02d}:{whole_seconds:02d}.{tenths}"
