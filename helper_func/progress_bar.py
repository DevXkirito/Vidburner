import time
import math

async def progress_bar(current, total, text, message, start):
    now = time.time()
    diff = now - start

    # Update only every 5 seconds or at completion
    if (round(diff) % 5 == 0) or (current == total):
        percentage = (current / total) * 100
        speed = current / diff if diff > 0 else 0
        elapsed_ms = int(diff * 1000)
        eta_ms = int(((total - current) / speed) * 1000) if speed > 0 else 0
        total_eta = eta_ms + elapsed_ms

        bar_filled = math.floor(percentage / 5)
        bar_empty = 20 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty

        formatted = (
            f"`[{bar}]`\n\n"
            f"**Progress:** {round(percentage, 2)}%\n"
            f"**Done:** {humanbytes(current)} of {humanbytes(total)}\n"
            f"**Speed:** {humanbytes(speed)}/s\n"
            f"**Elapsed:** {TimeFormatter(elapsed_ms)}\n"
            f"**ETA:** {TimeFormatter(total_eta)}"
        )

        try:
            await message.edit(text=f"**{text}**\n\n{formatted}")
        except:
            pass

def humanbytes(size):
    if size is None:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size >= power and n < 4:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(ms: int) -> str:
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    if ms: parts.append(f"{ms}ms")
    return ", ".join(parts) if parts else "0s"
