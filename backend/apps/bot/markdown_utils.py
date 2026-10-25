"""
Telegram legacy-Markdown escaping helpers.

The bot sends with parse_mode='Markdown' (legacy), where only
`_`, `*`, `` ` `` and `[` carry meaning. Any of those characters inside
user-provided content (task titles, client names, news headlines, ...)
breaks rendering - escape them everywhere before interpolation.
"""

_MD_SPECIAL = ('_', '*', '`', '[')


def escape_md(text) -> str:
    """Escape legacy Markdown special characters in dynamic content."""
    if text is None:
        return ''
    text = str(text)
    if not any(ch in text for ch in _MD_SPECIAL):
        return text
    out = []
    for ch in text:
        if ch in _MD_SPECIAL:
            out.append('\\' + ch)
        else:
            out.append(ch)
    return ''.join(out)
