import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from status.core import check_monitor, MonitorStatus
from status.cli import main

class TestStatus(unittest.TestCase):

    def test_check_monitor_success(self):
        async def run_test():
            session = MagicMock()
            context_manager = AsyncMock()
            context_manager.__aenter__.return_value.status = 200
            session.get.return_value = context_manager
            monitor = {'name': 'example', 'url': 'http://example.com', 'type': 'url'}
            result = await check_monitor(session, monitor)
            self.assertIsInstance(result, MonitorStatus)
            self.assertEqual(result.name, 'example')
            self.assertEqual(result.host_or_url, 'http://example.com')
            self.assertEqual(result.status, 200)
            self.assertEqual(result.message, 'OK')
        asyncio.run(run_test())

    def test_check_monitor_timeout(self):
        async def run_test():
            session = MagicMock()
            session.get.side_effect = asyncio.TimeoutError
            monitor = {'name': 'example', 'url': 'http://example.com', 'type': 'url'}
            result = await check_monitor(session, monitor)
            self.assertIsInstance(result, MonitorStatus)
            self.assertEqual(result.name, 'example')
            self.assertEqual(result.host_or_url, 'http://example.com')
            self.assertEqual(result.status, 'Timeout')
            self.assertEqual(result.message, '')
        asyncio.run(run_test())

    @patch('status.cli.print_results')
    @patch('status.cli.check_monitor', new_callable=AsyncMock)
    @patch('status.cli.get_config')
    @patch('status.cli.argparse.ArgumentParser')
    def test_main_console_mode(self, mock_parser, mock_get_config, mock_check_monitor, mock_print_results):
        async def run_test():
            mock_args = MagicMock()
            mock_args.console = True
            mock_args.follow = False
            mock_args.web = False
            mock_args.monitor_name = None
            mock_args.monitor = None
            mock_args.down = False
            mock_args.up = False
            mock_args.output = "text"
            mock_args.config = "config.yaml"
            mock_parser.return_value.parse_args.return_value = mock_args

            monitors = [{'name': 'example', 'url': 'http://example.com'}]
            mock_get_config.return_value = {'monitors': monitors}
            
            results = [MonitorStatus(name='example', host_or_url='http://example.com', status=200, message='OK', monitor_type='url')]
            mock_check_monitor.return_value = results[0]

            await main()

            mock_print_results.assert_called_once_with(results)
        asyncio.run(run_test())

    @patch('status.cli.asyncio.sleep', new_callable=AsyncMock)
    @patch('status.cli.print_results')
    @patch('status.cli.check_monitor', new_callable=AsyncMock)
    @patch('status.cli.get_config')
    @patch('status.cli.argparse.ArgumentParser')
    def test_main_follow_mode(self, mock_parser, mock_get_config, mock_check_monitor, mock_print_results, mock_asyncio_sleep):
        async def run_test():
            mock_args = MagicMock()
            mock_args.follow = True
            mock_args.console = False
            mock_args.web = False
            mock_args.monitor_name = None
            mock_args.monitor = None
            mock_args.down = False
            mock_args.up = False
            mock_args.output = "text"
            mock_args.config = "config.yaml"
            mock_args.interval = 1
            mock_parser.return_value.parse_args.return_value = mock_args

            monitors = [{'name': 'example', 'url': 'http://example.com'}]
            mock_get_config.return_value = {'monitors': monitors, 'follow': {'interval': 1}}
            
            results = [MonitorStatus(name='example', host_or_url='http://example.com', status=200, message='OK', monitor_type='url')]
            mock_check_monitor.return_value = results[0]

            # To prevent an infinite loop in the test, we'll raise an exception after a few calls
            mock_asyncio_sleep.side_effect = [None, None, KeyboardInterrupt]

            with self.assertRaises(KeyboardInterrupt):
                await main()

            self.assertEqual(mock_check_monitor.call_count, 3)
            self.assertEqual(mock_print_results.call_count, 3)
        asyncio.run(run_test())

    @patch('status.cli.run_web_server')
    @patch('status.cli.create_web_app')
    @patch('status.cli.get_config')
    @patch('status.cli.argparse.ArgumentParser')
    def test_main_web_mode(self, mock_parser, mock_get_config, mock_create_web_app, mock_run_web_server):
        async def run_test():
            mock_args = MagicMock()
            mock_args.web = True
            mock_args.console = False
            mock_args.follow = False
            mock_args.monitor_name = None
            mock_args.monitor = None
            mock_args.down = False
            mock_args.up = False
            mock_args.output = "text"
            mock_args.config = "config.yaml"
            mock_parser.return_value.parse_args.return_value = mock_args

            monitors = [{'name': 'example', 'url': 'http://example.com'}]
            mock_get_config.return_value = {'monitors': monitors}
            
            await main()

            mock_create_web_app.assert_called_once_with(monitors)
            mock_run_web_server.assert_called_once()
        asyncio.run(run_test())

    @patch('status.cli.check_monitor', new_callable=AsyncMock)
    @patch('status.cli.get_config')
    @patch('status.cli.argparse.ArgumentParser')
    def test_main_ignore_monitors(self, mock_parser, mock_get_config, mock_check_monitor):
        async def run_test():
            mock_args = MagicMock()
            mock_args.console = True
            mock_args.follow = False
            mock_args.web = False
            mock_args.monitor_name = None
            mock_args.monitor = None
            mock_args.down = False
            mock_args.up = False
            mock_args.output = "text"
            mock_args.config = "config.yaml"
            mock_parser.return_value.parse_args.return_value = mock_args

            monitors = [
                {'name': 'example1', 'url': 'http://example.com'},
                {'name': 'example2', 'url': 'http://example.org'}
            ]
            ignored_monitors = ['example2']
            mock_get_config.return_value = {'monitors': monitors, 'ignore': ignored_monitors}
            
            await main()

            # Check that check_monitor is called only for the non-ignored monitor
            self.assertEqual(mock_check_monitor.call_count, 1)
            self.assertEqual(mock_check_monitor.call_args[0][1]['name'], 'example1')
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()