"""Causal join of actual first-observed OI to received books, never gap filling."""
from datetime import datetime
from miniquant.data.okx_public import DataError, number


def milliseconds(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise DataError('As-of time lacks timezone')
    return round(result.timestamp()*1000)


def unique(records, kind):
    seen = {}
    for row in records:
        if row.get('kind') != kind or row.get('venue') != 'OKX' or row.get('environment') != 'public_market' or row.get('inst_id') != 'BTC-USDT-SWAP':
            raise DataError('As-of source identity mismatch')
        received = milliseconds(row['available_at'])
        if row['available_at'] != row['ingested_at'] or milliseconds(row['event_time']) > received:
            raise DataError('As-of source time contract violated')
        if received in seen and seen[received] != row:
            raise DataError('Conflicting reception timestamp')
        seen[received] = row
    return sorted(seen.items())


def join_snapshots(interest, books):
    oi = unique(interest, 'open_interest')
    quotes = unique(books, 'books')
    result, cursor, latest = [], 0, None
    for decision, book in quotes:
        while cursor < len(oi) and oi[cursor][0] <= decision:
            latest = oi[cursor]
            cursor += 1
        item = dict(decision_at=book['available_at'], book_sha256=book['source_sha256'], eligible=False)
        if decision-milliseconds(book['event_time']) > 30_000:
            item['reason'] = 'stale_book'
        elif latest is None:
            item['reason'] = 'no_OI_received_before_decision'
        elif decision-latest[0] > 60_000 or decision-milliseconds(latest[1]['event_time']) > 60_000:
            item['reason'] = 'stale_OI_no_gap_fill'
        else:
            row = latest[1]
            count = number(row['values']['oi'])
            bid = number(book['values']['bids'][0][0]);ask = number(book['values']['asks'][0][0])
            if count < 0 or bid <= 0 or ask < bid:
                raise DataError('Invalid joined values')
            item.update(eligible=True, oi_sha256=row['source_sha256'], oi_available_at=row['available_at'],
                        oi_contract_count=str(count), bid=str(bid), ask=str(ask),
                        mid=str((bid+ask)/2), timestamp_note='OI REST ts is data return time, not certified trade event')
        result.append(item)
    return result
