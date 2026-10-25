"""
Bilingual (EN / TH) message catalog for Telegram bot notifications.

This is the ONLY backend module allowed to hold Thai text: bot messages
are rendered per user.preferred_language so alerts reach the user in
their chosen language.
"""

BOT_MESSAGES = {
    'en': {
        'watchdog.title': "\U0001F6A8 *VPS Watchdog Alert*",
        'watchdog.offline': "\U0001F534 Server unreachable over SSH",
        'watchdog.cpu': "CPU: {value}% (threshold {threshold}%)",
        'watchdog.ram': "RAM: {value}% (threshold {threshold}%)",
        'watchdog.disk': "Disk: {value}% (threshold {threshold}%)",
        'watchdog.container_down': "\u26A0\uFE0F Stopped container: {name} ({status})",
        'watchdog.recovered': "\U0001F7E2 *VPS Recovered* \u2014 {name} is back ONLINE",
        'watchdog.probe_again': "\U0001F504 Probe Again",
        'servers.title': "\U0001F5A5 *Servers & Infrastructure*",
        'servers.empty': "No servers tracked yet. Add them from the project's MA & Infra tab.",
        'servers.refresh': "\U0001F504 Refresh Status",
        'servers.never': "never probed",
        'ma.title': "\U0001F4E1 *MA Contracts*",
        'ma.empty': "No MA contracts yet. Set one up in a project's MA & Infra tab.",
        'ma.ends': "ends {date} ({days}d)",
        'ma.expired': "expired {date}",
        'ma.next_billing': "next billing {date}",
        'expiry.ma.title': "\U0001F4C5 *MA Contract Expiry Reminder*",
        'expiry.asset.title': "\U0001F4C5 *Domain / Server Expiry Reminder*",
        'expiry.days_left': "expires in {n} days",
        'expiry.today': "expires TODAY",
        'billing.ma_inflow': "\U0001F4B0 *MA / Client Invoice Due*",
        'billing.ma_button': "\u2705 Received MA Payment",
        'billing.infra_button': "\u2705 Paid Server Bill",
        'test.title': "\u2705 *Telegram Test Alert*",
        'test.body': "Hello {username}, this is a test alert from Personal Life OS. Your bot connection works.",
        'pay.already_settled': "This item was already settled today - no duplicate payment recorded.",
        'probe.running': "Probing {name}...",
        'brief.events': "\U0001F4C5 *Today's Calendar Events:*",
        'brief.no_events': "\U0001F4C5 *Calendar:* No events scheduled today",
    },
    'th': {
        'watchdog.title': "\U0001F6A8 *\u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19\u0e40\u0e1d\u0e49\u0e32\u0e23\u0e30\u0e27\u0e31\u0e07 VPS*",
        'watchdog.offline': "\U0001F534 \u0e40\u0e0a\u0e37\u0e48\u0e2d\u0e21\u0e15\u0e48\u0e2d SSH \u0e44\u0e1b\u0e22\u0e31\u0e07\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49",
        'watchdog.cpu': "CPU: {value}% (\u0e40\u0e1e\u0e14\u0e32\u0e19 {threshold}%)",
        'watchdog.ram': "RAM: {value}% (\u0e40\u0e1e\u0e14\u0e32\u0e19 {threshold}%)",
        'watchdog.disk': "\u0e14\u0e34\u0e2a\u0e01\u0e4c: {value}% (\u0e40\u0e1e\u0e14\u0e32\u0e19 {threshold}%)",
        'watchdog.container_down': "\u26A0\uFE0F \u0e04\u0e2d\u0e19\u0e40\u0e17\u0e19\u0e40\u0e19\u0e2d\u0e23\u0e4c\u0e2b\u0e22\u0e38\u0e14\u0e17\u0e33\u0e07\u0e32\u0e19: {name} ({status})",
        'watchdog.recovered': "\U0001F7E2 *\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c\u0e01\u0e25\u0e31\u0e1a\u0e21\u0e32\u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c* \u2014 {name} \u0e2d\u0e2d\u0e19\u0e44\u0e25\u0e19\u0e4c\u0e41\u0e25\u0e49\u0e27",
        'watchdog.probe_again': "\U0001F504 \u0e27\u0e31\u0e14\u0e2a\u0e16\u0e32\u0e19\u0e30\u0e2d\u0e35\u0e01\u0e04\u0e23\u0e31\u0e49\u0e07",
        'servers.title': "\U0001F5A5 *\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c & \u0e42\u0e04\u0e23\u0e07\u0e2a\u0e23\u0e49\u0e32\u0e07\u0e1e\u0e37\u0e49\u0e19\u0e10\u0e32\u0e19*",
        'servers.empty': "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c\u0e43\u0e19\u0e23\u0e30\u0e1a\u0e1a \u2014 \u0e40\u0e1e\u0e34\u0e48\u0e21\u0e44\u0e14\u0e49\u0e08\u0e32\u0e01\u0e41\u0e17\u0e47\u0e1a MA & Infra \u0e43\u0e19\u0e42\u0e1b\u0e23\u0e40\u0e08\u0e01\u0e15\u0e4c",
        'servers.refresh': "\U0001F504 \u0e23\u0e35\u0e40\u0e1f\u0e23\u0e0a\u0e2a\u0e16\u0e32\u0e19\u0e30",
        'servers.never': "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e40\u0e04\u0e22\u0e27\u0e31\u0e14\u0e04\u0e48\u0e32",
        'ma.title': "\U0001F4E1 *\u0e2a\u0e31\u0e0d\u0e0d\u0e32 MA \u0e17\u0e35\u0e48\u0e14\u0e39\u0e41\u0e25\u0e2d\u0e22\u0e39\u0e48*",
        'ma.empty': "\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35\u0e2a\u0e31\u0e0d\u0e0d\u0e32 MA \u2014 \u0e15\u0e31\u0e49\u0e07\u0e04\u0e48\u0e32\u0e44\u0e14\u0e49\u0e43\u0e19\u0e41\u0e17\u0e47\u0e1a MA & Infra \u0e02\u0e2d\u0e07\u0e42\u0e1b\u0e23\u0e40\u0e08\u0e01\u0e15\u0e4c",
        'ma.ends': "\u0e2a\u0e34\u0e49\u0e19\u0e2a\u0e38\u0e14 {date} (\u0e40\u0e2b\u0e25\u0e37\u0e2d {days} \u0e27\u0e31\u0e19)",
        'ma.expired': "\u0e2b\u0e21\u0e14\u0e2a\u0e31\u0e0d\u0e0d\u0e32\u0e44\u0e1b\u0e41\u0e25\u0e49\u0e27\u0e15\u0e31\u0e49\u0e07\u0e41\u0e15\u0e48 {date}",
        'ma.next_billing': "\u0e40\u0e01\u0e47\u0e1a\u0e40\u0e07\u0e34\u0e19\u0e23\u0e2d\u0e1a\u0e16\u0e31\u0e14\u0e44\u0e1b {date}",
        'expiry.ma.title': "\U0001F4C5 *\u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19\u0e27\u0e31\u0e19\u0e2b\u0e21\u0e14\u0e2a\u0e31\u0e0d\u0e0d\u0e32 MA*",
        'expiry.asset.title': "\U0001F4C5 *\u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19\u0e27\u0e31\u0e19\u0e2b\u0e21\u0e14\u0e2d\u0e32\u0e22\u0e38 Domain / \u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c*",
        'expiry.days_left': "\u0e08\u0e30\u0e2b\u0e21\u0e14\u0e2d\u0e32\u0e22\u0e38\u0e43\u0e19\u0e2d\u0e35\u0e01 {n} \u0e27\u0e31\u0e19",
        'expiry.today': "\u0e2b\u0e21\u0e14\u0e2d\u0e32\u0e22\u0e38\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49!",
        'billing.ma_inflow': "\U0001F4B0 *\u0e16\u0e36\u0e07\u0e23\u0e2d\u0e1a\u0e40\u0e01\u0e47\u0e1a\u0e40\u0e07\u0e34\u0e19\u0e04\u0e48\u0e32 MA \u0e08\u0e32\u0e01\u0e25\u0e39\u0e01\u0e04\u0e49\u0e32*",
        'billing.ma_button': "\u2705 \u0e23\u0e31\u0e1a\u0e40\u0e07\u0e34\u0e19\u0e04\u0e48\u0e32 MA \u0e41\u0e25\u0e49\u0e27",
        'billing.infra_button': "\u2705 \u0e08\u0e48\u0e32\u0e22\u0e04\u0e48\u0e32\u0e40\u0e0b\u0e34\u0e23\u0e4c\u0e1f\u0e40\u0e27\u0e2d\u0e23\u0e4c\u0e41\u0e25\u0e49\u0e27",
        'test.title': "\u2705 *\u0e17\u0e14\u0e2a\u0e2d\u0e1a\u0e01\u0e32\u0e23\u0e41\u0e08\u0e49\u0e07\u0e40\u0e15\u0e37\u0e2d\u0e19 Telegram*",
        'test.body': "\u0e2a\u0e27\u0e31\u0e2a\u0e14\u0e35 {username} \u0e19\u0e35\u0e48\u0e04\u0e37\u0e2d\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e17\u0e14\u0e2a\u0e2d\u0e1a\u0e08\u0e32\u0e01 Personal Life OS \u0e01\u0e32\u0e23\u0e40\u0e0a\u0e37\u0e48\u0e2d\u0e21\u0e15\u0e48\u0e2d\u0e1a\u0e2d\u0e17\u0e02\u0e2d\u0e07\u0e04\u0e38\u0e13\u0e43\u0e0a\u0e49\u0e07\u0e32\u0e19\u0e44\u0e14\u0e49\u0e1b\u0e01\u0e15\u0e34",
        'pay.already_settled': "\u0e23\u0e32\u0e22\u0e01\u0e32\u0e23\u0e19\u0e35\u0e49\u0e16\u0e39\u0e01\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e01\u0e32\u0e23\u0e0a\u0e33\u0e23\u0e30\u0e44\u0e1b\u0e41\u0e25\u0e49\u0e27\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49 \u2014 \u0e44\u0e21\u0e48\u0e1a\u0e31\u0e19\u0e17\u0e36\u0e01\u0e0b\u0e49\u0e33",
        'probe.running': "\u0e01\u0e33\u0e25\u0e31\u0e07\u0e27\u0e31\u0e14\u0e2a\u0e16\u0e32\u0e19\u0e30 {name}...",
        'brief.events': "\U0001F4C5 *\u0e19\u0e31\u0e14\u0e2b\u0e21\u0e32\u0e22\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49:*",
        'brief.no_events': "\U0001F4C5 *\u0e1b\u0e0f\u0e34\u0e17\u0e34\u0e19:* \u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e44\u0e21\u0e48\u0e21\u0e35\u0e19\u0e31\u0e14\u0e2b\u0e21\u0e32\u0e22",
    }
}


def bot_msg(user, key: str, **params) -> str:
    """Resolve a bot message in the user's preferred language (EN fallback)."""
    locale = getattr(user, 'preferred_language', 'en') or 'en'
    catalog = BOT_MESSAGES.get(locale) or BOT_MESSAGES['en']
    text = catalog.get(key)
    if text is None:
        text = BOT_MESSAGES['en'].get(key, key)
    if params:
        for param_key, param_value in params.items():
            text = text.replace('{' + param_key + '}', str(param_value))
    return text
