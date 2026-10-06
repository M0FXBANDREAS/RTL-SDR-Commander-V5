"""Read-only HamQTH feed, fetched independently of the USB/audio threads."""
import asyncio
import csv
import math
import time
from datetime import datetime, timezone

from aiohttp import ClientSession, ClientTimeout, web

FEED = 'https://www.hamqth.com/dxc_csv.php'
DX = web.AppKey('dx_feed', dict)


def parse_spots(text):
    spots = []
    for row in csv.reader(text.splitlines(), delimiter='^', quoting=csv.QUOTE_NONE):
        if len(row) < 9:
            continue
        try:
            hz = float(row[1]) * 1000
            if not math.isfinite(hz) or not 500000 <= hz <= 1766000000:
                continue
            stamp = datetime.strptime(row[4].strip(), '%H%M %Y-%m-%d')
        except (ValueError, OverflowError):
            continue
        spots.append(dict(spotter=row[0][:40], freq=round(hz), call=row[2][:40],
                          comment=row[3][:300], time=stamp.strftime('%H:%M %Y-%m-%d'),
                          band=row[8].strip().upper(), _stamp=stamp))
    spots.sort(key=lambda s: s['_stamp'], reverse=True)
    for spot in spots:
        del spot['_stamp']
    return spots[:100]


async def fetch_spots(session):
    async with session.get(FEED, allow_redirects=False) as response:
        response.raise_for_status()
        # Do not buffer an arbitrarily large upstream response.
        data = bytearray()
        async for chunk in response.content.iter_chunked(16384):
            data.extend(chunk)
            if len(data) > 1_000_000:
                raise ValueError('Feed exceeds expected size')
        spots = parse_spots(data.decode('utf-8', errors='replace'))
        if not spots:
            raise ValueError('Feed contained no valid spots within RTL coverage')
        return spots


def install_dx_routes(app, port):
    app[DX] = dict(lock=asyncio.Lock(), expires=0, payload=None, session=None)

    async def lifetime(app):
        async with ClientSession(timeout=ClientTimeout(total=12),
                                 headers={'User-Agent': 'HamTech-RTL-Comander/7'}) as session:
            app[DX]['session'] = session
            yield
    app.cleanup_ctx.append(lifetime)

    async def get_spots(request):
        if request.host not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
            raise web.HTTPForbidden()
        origin = request.headers.get('Origin')
        if origin and origin != f'http://{request.host}':
            raise web.HTTPForbidden()
        state = request.app[DX]
        async with state['lock']:
            if time.monotonic() >= state['expires']:
                try:
                    spots = await fetch_spots(state['session'])
                    state['payload'] = dict(spots=spots, source='HamQTH',
                        fetched_at=datetime.now(timezone.utc).strftime('%H:%M:%S %Y-%m-%d UTC'))
                    state['expires'] = time.monotonic() + 30
                except Exception:
                    return web.json_response({'error': 'Unable to fetch HamQTH. Check internet access or try again later.'}, status=502)
            return web.json_response(state['payload'], headers={'Cache-Control': 'no-store'})
    app.router.add_get('/api/dx-spots', get_spots)
