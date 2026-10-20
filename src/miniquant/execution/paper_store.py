"""Durable, paper-only BTC/USDT ledger and reservation journal.

Integer micro-USDT / satoshis, serialized SQLite transactions, immutable fills.
This is a local fault-test broker, NOT an OKX adapter or a demo admission grant.
One DB represents synthetic Bot funds only. Legacy BTC is immutable protection.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3

QUOTE = 1_000_000
BASE = 100_000_000
TERMINAL = ('filled', 'cancelled', 'rejected')


def units(value, scale):
    if isinstance(value, (float, bool)):
        raise ValueError('Use exact decimal strings, not floats/bools')
    try:
        number = Decimal(value) * scale
        if not number.is_finite() or number < 0 or number != number.to_integral_value() or number > 9e15:
            raise ValueError('Invalid amount or precision')
        return int(number)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Invalid amount') from exc


class PaperStore:
    def __init__(self, path, *, environment='paper'):
        if environment != 'paper':
            raise ValueError('This broker only supports local paper')
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS wallets (
                    strategy TEXT PRIMARY KEY, cash INTEGER NOT NULL CHECK(cash>=0),
                    base INTEGER NOT NULL CHECK(base>=0));
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY, strategy TEXT NOT NULL REFERENCES wallets(strategy),
                    side TEXT NOT NULL, quantity INTEGER NOT NULL, remaining INTEGER NOT NULL,
                    price INTEGER NOT NULL, fee_bps INTEGER NOT NULL, state TEXT NOT NULL,
                    reserved_quote INTEGER NOT NULL, reserved_base INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS fills (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            ''')
            if db.execute('SELECT 1 FROM meta').fetchone():
                db.execute('BEGIN IMMEDIATE')
                db.execute('UPDATE meta SET value="1" WHERE key="halted"')
                self.event(db, 'halt', {'reason': 'process_open_requires_reconciliation'})

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def meta(db, key):
        row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        if row is None:
            raise ValueError('Paper ledger not initialized')
        return row['value']

    @staticmethod
    def event(db, kind, payload):
        db.execute('INSERT INTO events(kind,payload) VALUES (?,?)',
                   (kind, json.dumps(payload, sort_keys=True)))

    def initialize(self, allocations, protected_btc='0'):
        amounts = {k: units(v, QUOTE) for k, v in allocations.items()}
        protected = units(protected_btc, BASE)
        if not amounts or any(not isinstance(k, str) or not k or v <= 0 for k, v in amounts.items()) or sum(amounts.values()) > 9e15:
            raise ValueError('Invalid strategy allocation')
        with self.transaction() as db:
            if db.execute('SELECT 1 FROM meta').fetchone():
                raise ValueError('Cannot reset an existing ledger')
            db.executemany('INSERT INTO wallets VALUES (?,?,0)', amounts.items())
            db.executemany('INSERT INTO meta VALUES (?,?)',
                           [('schema_version', '1'), ('environment', 'paper'), ('initial_quote', str(sum(amounts.values()))),
                            ('protected_base', str(protected)), ('halted', '1'), ('snapshot_ms', '-1'), ('mark_price', '0')])
            self.event(db, 'initialize', {'allocations': amounts, 'protected_base': protected})

    def reconcile(self, usdt, btc, now_ms, *, mark_price):
        """Compare a synthetic broker snapshot; mismatch halts and stays durable."""
        cash, base = units(usdt, QUOTE), units(btc, BASE)
        mark = units(mark_price, QUOTE)
        if mark <= 0:
            raise ValueError('Positive valuation mark required')
        if type(now_ms) is not int or now_ms < 0:
            raise ValueError('Invalid timestamp')
        with self.transaction() as db:
            expected = db.execute('SELECT SUM(cash),SUM(base) FROM wallets').fetchone()
            matched = cash == expected[0] and base == expected[1] + int(self.meta(db, 'protected_base'))
            previous = int(self.meta(db, 'snapshot_ms'))
            if now_ms < previous:
                matched = False
            db.execute('UPDATE meta SET value=? WHERE key="snapshot_ms"', (str(now_ms),))
            db.execute('UPDATE meta SET value=? WHERE key="mark_price"', (str(mark),))
            if not matched:
                db.execute('UPDATE meta SET value="1" WHERE key="halted"')
            self.event(db, 'reconcile', {'matched': matched, 'snapshot_ms': now_ms})
            return matched

    def halt(self, reason):
        with self.transaction() as db:
            db.execute('UPDATE meta SET value="1" WHERE key="halted"')
            self.event(db, 'halt', {'reason': reason})

    def resume(self):
        """Explicit local acknowledgement; require latest reconciliation to match."""
        with self.transaction() as db:
            last = db.execute('SELECT seq,payload FROM events WHERE kind="reconcile" ORDER BY seq DESC LIMIT 1').fetchone()
            last_stop = db.execute('SELECT COALESCE(MAX(seq),0) FROM events WHERE kind IN ("halt","fill") OR (kind="transition" AND json_extract(payload,"$.state")="unknown")').fetchone()[0]
            if last is None or last['seq'] < last_stop or not json.loads(last['payload'])['matched']:
                raise ValueError('Reconciliation required')
            if db.execute('SELECT 1 FROM orders WHERE state="unknown"').fetchone():
                raise ValueError('Unknown orders require reconciliation')
            db.execute('UPDATE meta SET value="0" WHERE key="halted"')
            self.event(db, 'resume', {})

    @staticmethod
    def reserved(db, strategy):
        return db.execute('SELECT COALESCE(SUM(reserved_quote),0),COALESCE(SUM(reserved_base),0) '
                          'FROM orders WHERE strategy=?', (strategy,)).fetchone()

    def reserve(self, order_id, strategy, side, quantity, limit_price, *, fee_bps, now_ms,
                max_age_ms, max_order_usdt, max_initial_loss_fraction):
        """A capped paper limit intent. Repeating the same ID is idempotent."""
        qty, price = units(quantity, BASE), units(limit_price, QUOTE)
        cap = units(max_order_usdt, QUOTE)
        if (not isinstance(order_id, str) or not order_id or side not in ('buy', 'sell') or qty <= 0 or price <= 0
                or type(fee_bps) is not int or not 0 <= fee_bps < 10000
                or type(now_ms) is not int or type(max_age_ms) is not int or max_age_ms < 0):
            raise ValueError('Invalid intent')
        loss = Decimal(max_initial_loss_fraction)
        if not loss.is_finite() or not 0 < loss < 1:
            raise ValueError('Missing/invalid loss limit')
        worst_quote = (qty * price + BASE - 1) // BASE
        needed = (worst_quote * (10000 + fee_bps) + 9999) // 10000
        with self.transaction() as db:
            old = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if old:
                if (old['strategy'], old['side'], old['quantity'], old['price'], old['fee_bps']) != (strategy, side, qty, price, fee_bps):
                    raise ValueError('Conflicting idempotency key')
                return dict(old)
            snapshot = int(self.meta(db, 'snapshot_ms'))
            if self.meta(db, 'halted') != '0' or not 0 <= now_ms - snapshot <= max_age_ms:
                raise ValueError('Halted or stale/unreconciled paper state')
            if worst_quote > cap:
                raise ValueError('Order notional limit')
            totals = db.execute('SELECT SUM(cash),SUM(base) FROM wallets').fetchone()
            nav = totals[0] + totals[1] * int(self.meta(db, 'mark_price')) // BASE
            if side == 'buy' and nav <= Decimal(self.meta(db, 'initial_quote')) * (1 - loss):
                raise ValueError('Initial principal loss limit')
            wallet = db.execute('SELECT * FROM wallets WHERE strategy=?', (strategy,)).fetchone()
            if wallet is None:
                raise ValueError('Unknown strategy')
            rq, rb = self.reserved(db, strategy)
            if side == 'buy' and needed > wallet['cash'] - rq:
                raise ValueError('Insufficient unreserved budget')
            if side == 'sell' and qty > wallet['base'] - rb:
                raise ValueError('Protected or reserved inventory')
            db.execute('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (order_id, strategy, side, qty, qty, price, fee_bps, 'reserved',
                        needed if side == 'buy' else 0, qty if side == 'sell' else 0))
            self.event(db, 'reserve', {'id': order_id})
            return dict(db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())

    def transition(self, order_id, state):
        """unknown holds reservations; cancellation must be explicitly confirmed."""
        allowed = {'reserved': ('submitted', 'cancelled', 'rejected'),
                   'submitted': ('acknowledged', 'unknown', 'cancelled', 'rejected'),
                   'acknowledged': ('unknown', 'cancelled'),
                   'partial': ('unknown', 'cancelled'),
                   'unknown': ('acknowledged', 'partial', 'cancelled', 'rejected')}
        with self.transaction() as db:
            row = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if row is None:
                raise ValueError('Unknown order')
            if state == row['state']:
                return
            if state not in allowed.get(row['state'], ()) or state == 'rejected' and row['remaining'] != row['quantity']:
                raise ValueError('Invalid lifecycle transition')
            if state in TERMINAL:
                db.execute('UPDATE orders SET state=?,reserved_quote=0,reserved_base=0 WHERE id=?', (state, order_id))
            else:
                db.execute('UPDATE orders SET state=? WHERE id=?', (state, order_id))
            if state == 'unknown':
                db.execute('UPDATE meta SET value="1" WHERE key="halted"')
            self.event(db, 'transition', {'id': order_id, 'state': state})

    def fill(self, fill_id, order_id, quantity, price, fee, fee_currency):
        qty, px = units(quantity, BASE), units(price, QUOTE)
        if not isinstance(fill_id, str) or not fill_id or qty <= 0 or px <= 0 or fee_currency not in ('BTC', 'USDT'):
            raise ValueError('Invalid fill')
        fee_units = units(fee, BASE if fee_currency == 'BTC' else QUOTE)
        payload = json.dumps([order_id, qty, px, fee_units, fee_currency])
        with self.transaction() as db:
            prior = db.execute('SELECT payload FROM fills WHERE id=?', (fill_id,)).fetchone()
            if prior:
                if prior[0] != payload:
                    raise ValueError('Conflicting fill ID')
                return False
            row = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if row is None or row['state'] not in ('submitted', 'acknowledged', 'partial', 'unknown') or qty > row['remaining']:
                raise ValueError('Unexpected or excessive fill; reconcile first')
            buy = row['side'] == 'buy'
            if buy and px > row['price'] or not buy and px < row['price']:
                raise ValueError('Paper limit price violated')
            if fee_currency == 'BTC' and not buy:
                raise ValueError('BTC sell commission not supported by this paper contract')
            gross = (qty * px + (BASE - 1 if buy else 0)) // BASE
            max_fee = (qty * row['fee_bps'] + 9999) // 10000 if fee_currency == 'BTC' else (gross * row['fee_bps'] + 9999) // 10000
            if fee_units > max_fee or fee_currency == 'BTC' and fee_units > qty:
                raise ValueError('Fee exceeds reservation contract')
            remaining = row['remaining'] - qty
            spend = gross + (fee_units if fee_currency == 'USDT' and buy else 0)
            # Retain the original worst-case budget, less actual spend, until terminal.
            rq = row['reserved_quote'] - spend if buy and remaining else 0
            rb = remaining if not buy else 0
            if rq < 0:
                raise ValueError('Reservation exhausted')
            dc = -spend if buy else gross - fee_units
            dbtc = qty - (fee_units if fee_currency == 'BTC' else 0) if buy else -qty
            db.execute('UPDATE wallets SET cash=cash+?,base=base+? WHERE strategy=?', (dc, dbtc, row['strategy']))
            state = 'filled' if remaining == 0 else 'partial'
            db.execute('UPDATE orders SET remaining=?,state=?,reserved_quote=?,reserved_base=? WHERE id=?',
                       (remaining, state, rq, rb, order_id))
            db.execute('INSERT INTO fills VALUES (?,?)', (fill_id, payload))
            self.event(db, 'fill', {'id': fill_id, 'order': order_id})
            return True

    def snapshot(self):
        with self.transaction() as db:
            return dict(wallets=[dict(x) for x in db.execute('SELECT * FROM wallets ORDER BY strategy')],
                        orders=[dict(x) for x in db.execute('SELECT * FROM orders ORDER BY id')],
                        halted=self.meta(db, 'halted') == '1',
                        protected_base=int(self.meta(db, 'protected_base')),
                        submission_authorized=False, environment='paper')
