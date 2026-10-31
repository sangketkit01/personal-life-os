"""Pack complete Markdown blocks without breaking escapes or Telegram's text limit."""


def telegram_length(text):
    return len(text.encode('utf-16-le')) // 2


def split_plain_text(text, limit=1400):
    """Split before Markdown escaping; preserve every character, including whitespace."""
    start, size = 0, 0
    for index, char in enumerate(text):
        units = 2 if ord(char) > 0xFFFF else 1
        if size + units > limit:
            yield text[start:index]
            start, size = index, 0
        size += units
    if start < len(text):
        yield text[start:]


def pack_blocks(blocks, limit=3900):
    current = ''
    for block in blocks:
        if telegram_length(block) > limit:
            raise ValueError('Markdown block exceeds Telegram message budget')
        candidate = current + '\n' + block if current else block
        if current and telegram_length(candidate) > limit:
            yield current
            current = block
        else:
            current = candidate
    if current:
        yield current
