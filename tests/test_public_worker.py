import unittest,tempfile,fcntl,subprocess,signal,json
from pathlib import Path
from unittest.mock import Mock,patch
from tools.observe_btc_worker import admission,run_public_command,require_quality

class PublicWorkerTests(unittest.TestCase):
    def test_manual_quota_cache_boundaries(self):
        self.assertIsNone(admission({'action':'continue'},100,110,False,False))
        self.assertIsNotNone(admission({'action':'continue'},100,110,True,False))
        self.assertIsNotNone(admission({'action':'continue'},100,110,None,False))
        self.assertIsNotNone(admission({'action':'wait_for_quota'},100,110,False,False))
        self.assertIsNotNone(admission({'action':'continue'},100,1901,False,False))
        self.assertIsNotNone(admission({'action':'continue'},120,110,False,False))
        self.assertIsNotNone(admission({'action':'continue'},100,110,False,True))
    def test_only_fixed_command_argv(self):
        with patch('tools.observe_btc_worker.subprocess.Popen') as popen:
            for bad in (-1,3,True,'tools/okx_demo_audit.py'):
                with self.assertRaises(ValueError):run_public_command(bad)
            popen.assert_not_called()
            p=Mock(pid=123,returncode=0);p.communicate.return_value=('public','');popen.return_value=p
            run_public_command(2);self.assertEqual(popen.call_args.args[0][1:],['tools/run_oi_study.py','--mode','prepare'])
    def test_timeout_terminates_only_own_child_group(self):
        p=Mock(pid=123);p.communicate.side_effect=[subprocess.TimeoutExpired('public',90),('','')]
        with patch('tools.observe_btc_worker.subprocess.Popen',return_value=p),patch('tools.observe_btc_worker.os.killpg') as kill:
            r=run_public_command(0);self.assertEqual(r['error_type'],'TimeoutExpired');kill.assert_called_once_with(123,signal.SIGTERM)
    def test_real_lock_excludes_second_owner(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'worker.lock'
            with p.open('a') as a,p.open('a') as b:
                fcntl.flock(a,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):fcntl.flock(b,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_remaining_deadline_bounds_child_timeout(self):
        p=Mock(pid=123,returncode=0);p.communicate.return_value=('','')
        with patch('tools.observe_btc_worker.subprocess.Popen',return_value=p):
            run_public_command(0,12);p.communicate.assert_called_once_with(timeout=12)
        with self.assertRaises(ValueError):run_public_command(0,0)
    def test_incomplete_or_stale_quality_blocks_pipeline(self):
        for value in ({'complete':True,'jobs':[{'fresh':False}]},{'complete':True,'jobs':[]},{'complete':False,'jobs':[{'fresh':True}]}):
            with patch('tools.observe_btc_worker.Path.read_text',return_value=json.dumps(value)):
                with self.assertRaises(ValueError):require_quality(0,0)
        with patch('tools.observe_btc_worker.Path.read_text',return_value=json.dumps({'complete':True,'jobs':[{'fresh':True}]})):
            require_quality(0,0)
