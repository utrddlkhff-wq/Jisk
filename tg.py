#!/usr/bin/env python3
"""
Помощник для входа в свой Telegram-аккаунт с телефона через сессию из tdata.

Использование:
  python tg.py convert <папка_tdata> [--passcode PASS]
      -> загружает tdata, конвертирует в Telethon-сессию (account.session),
         показывает данные аккаунта (подтверждение, что сессия живая).

  python tg.py code [--minutes 10]
      -> слушает входящие сообщения от службы Telegram (777000) и печатает
         код входа, как только ты запросишь вход на телефоне.

  python tg.py last
      -> показать последние сообщения от 777000 (если код уже пришёл).
"""
import argparse
import asyncio
import sys

from opentele.td import TDesktop
from opentele.api import UseCurrentSession

SESSION = "account"  # account.session
TG_SERVICE_ID = 777000  # официальный отправитель кодов входа


async def cmd_convert(args):
    tdesk = TDesktop(args.tdata, passcode=args.passcode) if args.passcode else TDesktop(args.tdata)
    if not tdesk.isLoaded():
        print("❌ Не удалось загрузить tdata. Проверь папку и passcode.")
        sys.exit(1)

    client = await tdesk.ToTelethon(session=f"{SESSION}.session", flag=UseCurrentSession)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Сессия не авторизована (возможно, разлогинена на десктопе).")
        sys.exit(1)

    me = await client.get_me()
    print("✅ Сессия живая. Аккаунт:")
    print(f"   id:       {me.id}")
    print(f"   имя:      {me.first_name or ''} {me.last_name or ''}".rstrip())
    print(f"   username: @{me.username}" if me.username else "   username: (нет)")
    print(f"   телефон:  +{me.phone}" if me.phone else "   телефон:  (скрыт)")
    print(f"\nСохранено в {SESSION}.session")
    print("Теперь: на телефоне начни обычный вход по номеру и запусти  python tg.py code")
    await client.disconnect()


async def _get_client():
    # Переоткрываем уже сконвертированную сессию через telethon напрямую
    from telethon import TelegramClient
    from opentele.api import API
    api = API.TelegramDesktop.Generate()
    client = TelegramClient(f"{SESSION}.session", api.api_id, api.api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("❌ Нет авторизованной сессии. Сначала запусти: python tg.py convert <tdata>")
        sys.exit(1)
    return client


async def cmd_last(args):
    client = await _get_client()
    print("Последние сообщения от службы Telegram (777000):\n")
    async for msg in client.iter_messages(TG_SERVICE_ID, limit=5):
        if msg.message:
            print(f"[{msg.date:%H:%M:%S}] {msg.message}\n")
    await client.disconnect()


async def cmd_code(args):
    from telethon import events
    client = await _get_client()
    print(f"⏳ Жду код входа от Telegram до {args.minutes} мин.")
    print("   Сейчас на телефоне: введи номер и запроси код. Код появится здесь.\n")

    @client.on(events.NewMessage(from_users=TG_SERVICE_ID))
    async def handler(event):
        text = event.message.message or ""
        print(f"📩 Сообщение от Telegram:\n{text}\n")
        import re
        m = re.search(r"(\d[\d\-\s]{3,})", text)
        if m:
            print(f"➡️  Код для ввода на телефоне: {m.group(1).strip()}")

    try:
        await asyncio.wait_for(client.run_until_disconnected(), timeout=args.minutes * 60)
    except asyncio.TimeoutError:
        print("⏰ Время вышло. Перезапусти, когда будешь готов запросить вход.")
    finally:
        await client.disconnect()


def main():
    p = argparse.ArgumentParser(description="Вход в Telegram с телефона через tdata")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert")
    c.add_argument("tdata", help="путь к папке tdata")
    c.add_argument("--passcode", default=None, help="локальный пароль Telegram Desktop, если был")

    sub.add_parser("last")

    cd = sub.add_parser("code")
    cd.add_argument("--minutes", type=int, default=10)

    args = p.parse_args()
    fn = {"convert": cmd_convert, "last": cmd_last, "code": cmd_code}[args.cmd]
    asyncio.run(fn(args))


if __name__ == "__main__":
    main()
