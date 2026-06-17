import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector

# Список публичных прокси (обновляется автоматически)
PROXY_LISTS = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
]

async def test_proxy(proxy_url: str, timeout: int = 5) -> bool:
    """Проверяет, работает ли прокси для Telegram API"""
    try:
        connector = ProxyConnector.from_url(proxy_url)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                'https://api.telegram.org/bot123/getMe',
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                # Если получили ответ (даже 401 Unauthorized) — прокси работает
                return response.status in [200, 401, 403]
    except Exception:
        return False

async def find_working_proxy(max_proxies: int = 50) -> str | None:
    """Находит первый рабочий прокси"""
    print("🔍 Загружаю список прокси...")

    all_proxies = []
    async with aiohttp.ClientSession() as session:
        for url in PROXY_LISTS:
            try:
                async with session.get(url, timeout=10) as response:
                    text = await response.text()
                    proxies = [p.strip() for p in text.split('\n') if ':' in p and p.strip()]
                    all_proxies.extend(proxies[:max_proxies])
            except Exception as e:
                print(f"⚠️ Не удалось загрузить {url}: {e}")

    print(f"📋 Загружено {len(all_proxies)} прокси. Начинаю проверку...\n")

    # Проверяем батчами по 10
    for i in range(0, len(all_proxies), 10):
        batch = all_proxies[i:i+10]
        tasks = [test_proxy(f"http://{proxy}") for proxy in batch]
        results = await asyncio.gather(*tasks)

        for proxy, works in zip(batch, results):
            if works:
                print(f"✅ НАЙДЕН РАБОЧИЙ ПРОКСИ: http://{proxy}")
                return f"http://{proxy}"
            else:
                print(f"❌ {proxy} — не работает")

    return None

async def main():
    proxy = await find_working_proxy()

    if proxy:
        print(f"\n🎉 Используй этот прокси в main.py:")
        print(f'   proxy_url = "{proxy}"')
    else:
        print("\n😔 Рабочие прокси не найдены. Попробуй позже или используй VPN.")

if __name__ == "__main__":
    asyncio.run(main())
