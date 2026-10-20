import concurrent.futures
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from miniquant.execution.paper_store import PaperStore, units, QUOTE


class PaperStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'paper.sqlite'
        self.store = PaperStore(self.path)
        self.store.initialize({'a': '100', 'b': '100'}, protected_btc='1')
        self.assertTrue(self.store.reconcile('200', '1', 1000, mark_price='10000'))
        self.store.resume()

    def reserve(self, oid='o1', **changes):
        args = dict(order_id=oid, strategy='a', side='buy', quantity='0.009', limit_price='10000',
                    fee_bps=10, now_ms=1000, max_age_ms=100, max_order_usdt='100',
                    max_initial_loss_fraction='0.4')
        args.update(changes)
        return self.store.reserve(**args)

    def buy(self):
        self.reserve()
        self.store.transition('o1', 'submitted')
        self.store.fill('f1', 'o1', '0.009', '10000', '0.000009', 'BTC')

    def test_concurrent_reservations_do_not_reuse_strategy_cash(self):
        def attempt(i):
            try:
                self.reserve('race' + str(i))
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, range(2))), 1)
        # Other strategy uses its OWN allocation; account surplus cannot expand either.
        self.reserve('b1', strategy='b')
        with self.assertRaises(ValueError):
            self.reserve('b2', strategy='b')

    def test_idempotent_order_and_conflicting_id(self):
        first = self.reserve()
        self.assertEqual(first, self.reserve())
        with self.assertRaises(ValueError):
            self.reserve(quantity='0.001')
        self.assertEqual(len(self.store.snapshot()['orders']), 1)

    def test_unknown_order_keeps_budget_across_restart(self):
        self.reserve()
        self.store.transition('o1', 'submitted')
        self.store.transition('o1', 'unknown')
        self.store = PaperStore(self.path)
        snap = self.store.snapshot()
        self.assertTrue(snap['halted'])
        self.assertEqual(snap['orders'][0]['reserved_quote'], 90_090_000)
        with self.assertRaises(ValueError):
            self.reserve('o2')
        self.assertTrue(self.store.reconcile('200', '1', 1001, mark_price='10000'))
        with self.assertRaises(ValueError):
            self.store.resume()
        self.store.transition('o1', 'cancelled')
        self.store.resume()
        self.reserve('o2', now_ms=1001)

    def test_partial_fill_duplicate_then_cancel_releases_only_unfilled(self):
        self.reserve()
        self.store.transition('o1', 'submitted')
        self.assertTrue(self.store.fill('p1', 'o1', '0.004', '10000', '0.04', 'USDT'))
        self.assertFalse(self.store.fill('p1', 'o1', '0.004', '10000', '0.04', 'USDT'))
        with self.assertRaises(ValueError):
            self.store.fill('p1', 'o1', '0.003', '10000', '0.03', 'USDT')
        snap = self.store.snapshot()
        self.assertEqual(snap['wallets'][0]['cash'], 59_960_000)
        self.assertEqual(snap['orders'][0]['reserved_quote'], 50_050_000)
        self.store.transition('o1', 'cancelled')
        snap = PaperStore(self.path).snapshot()
        self.assertEqual(snap['orders'][0]['reserved_quote'], 0)
        self.assertEqual(snap['wallets'][0]['base'], 400_000)
        self.assertTrue(self.store.reconcile('159.96', '1.004', 1001, mark_price='10000'))

    def test_only_bot_inventory_sellable_and_cannot_double_reserve(self):
        with self.assertRaises(ValueError):
            self.reserve('sell', side='sell', quantity='0.001')
        self.buy()
        self.reserve('s1', side='sell', quantity='0.008991')
        with self.assertRaises(ValueError):
            self.reserve('s2', side='sell', quantity='0.000001')
        self.store.transition('s1', 'submitted')
        self.store.fill('sfill', 's1', '0.008991', '10000', '0.08991', 'USDT')
        snap = self.store.snapshot()
        self.assertEqual(snap['protected_base'], 100_000_000)
        self.assertEqual(snap['wallets'][0]['base'], 0)
        self.assertEqual(snap['wallets'][0]['cash'], 99_820_090)

    def test_reconciliation_mismatch_halts_durably(self):
        self.assertFalse(self.store.reconcile('200', '0.99', 1001, mark_price='10000'))
        self.assertTrue(PaperStore(self.path).snapshot()['halted'])
        with self.assertRaises(ValueError):
            self.store.resume()
        with self.assertRaises(ValueError):
            self.reserve()

    def test_stale_snapshot_live_mode_reset_and_numeric_errors(self):
        with self.assertRaises(ValueError):
            self.reserve(now_ms=1101)
        with self.assertRaises(ValueError):
            PaperStore(self.path, environment='demo')
        with self.assertRaises(ValueError):
            self.store.initialize({'a': '100'})
        for value in (0.1, True, 'NaN', '-1', '0.0000001'):
            with self.assertRaises(ValueError):
                units(value, QUOTE)
        with self.assertRaises(ValueError):
            self.reserve(max_order_usdt='89')

    def test_fill_failure_is_atomic_and_halt_still_accepts_known_fills(self):
        self.reserve()
        self.store.transition('o1', 'submitted')
        before = self.store.snapshot()
        for args in [('bad', 'o1', '0.01', '10000', '0', 'USDT'),
                     ('bad', 'o1', '0.009', '10001', '0', 'USDT'),
                     ('bad', 'o1', '0.009', '10000', '1', 'USDT')]:
            with self.assertRaises(ValueError):
                self.store.fill(*args)
            self.assertEqual(self.store.snapshot(), before)
        self.store.halt('network fault')
        with self.assertRaises(ValueError):
            self.store.resume()
        self.store.fill('ok', 'o1', '0.009', '10000', '0.09', 'USDT')
        self.assertTrue(self.store.snapshot()['halted'])
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'filled')
        with self.assertRaises(ValueError):
            self.store.transition('o1', 'cancelled')

    def test_initial_principal_loss_blocks_buy_but_allows_inventory_reduction(self):
        self.buy()
        self.reserve('b-buy', strategy='b')
        self.store.transition('b-buy', 'submitted')
        self.store.fill('bfill', 'b-buy', '0.009', '10000', '0', 'USDT')
        self.assertTrue(self.store.reconcile('20', '1.017991', 1001, mark_price='100'))
        with self.assertRaisesRegex(ValueError, 'Initial principal'):
            self.reserve('more', quantity='0.0001', now_ms=1001)
        self.reserve('reduce', side='sell', quantity='0.001', now_ms=1001)
        self.assertFalse(self.store.snapshot()['submission_authorized'])

    def test_restart_requires_new_reconciliation_even_without_unknown_orders(self):
        self.store = PaperStore(self.path)
        with self.assertRaises(ValueError):
            self.store.resume()
        with self.assertRaises(ValueError):
            self.reserve()
        self.assertTrue(self.store.reconcile('200', '1', 1001, mark_price='10000'))
        self.store.resume()
        self.reserve(now_ms=1001)

    def test_fill_from_unknown_is_processed_but_does_not_automatically_resume(self):
        self.reserve()
        self.store.transition('o1', 'submitted')
        self.store.transition('o1', 'unknown')
        self.store.fill('late', 'o1', '0.009', '10000', '0.09', 'USDT')
        self.assertTrue(self.store.snapshot()['halted'])
        with self.assertRaises(ValueError):
            self.store.resume()
        self.assertTrue(self.store.reconcile('109.91', '1.009', 1001, mark_price='10000'))
        self.store.resume()
        self.assertFalse(self.store.snapshot()['halted'])

    def test_abrupt_process_exit_rolls_back_uncommitted_budget_mutation(self):
        code = ("import sqlite3,sys,os; "
                "db=sqlite3.connect(sys.argv[1],isolation_level=None); "
                "db.execute('BEGIN IMMEDIATE'); "
                "db.execute(\"UPDATE wallets SET cash=0 WHERE strategy='a'\"); os._exit(17)")
        result = subprocess.run([sys.executable, '-c', code, str(self.path)], timeout=10)
        self.assertEqual(result.returncode, 17)
        snapshot = PaperStore(self.path).snapshot()
        self.assertEqual(snapshot['wallets'][0]['cash'], 100_000_000)
        self.assertTrue(snapshot['halted'])
