##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Unit tests for logging source location fix
******************************************

:module: test_logging_source_location

:synopsis: Test that custom logging levels show correct source location
    instead of always showing logging_initializer.py as the source.

.. currentmodule:: test_logging_source_location
"""

import logging
import unittest
from io import StringIO
from unittest.mock import patch

from pykiso.logging_initializer import add_internal_log_levels, add_logging_level


class TestLoggingSourceLocation(unittest.TestCase):
    """Test that custom logging levels show the correct source location."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a string buffer to capture log output
        self.log_stream = StringIO()

        # Create a test logger
        self.logger = logging.getLogger(f"test_logger_{id(self)}")
        self.logger.setLevel(1)  # Set to lowest level to capture everything

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create a handler that captures logs with source location info
        self.handler = logging.StreamHandler(self.log_stream)
        formatter = logging.Formatter('%(levelname)s:%(filename)s:%(lineno)d:%(funcName)s - %(message)s')
        self.handler.setFormatter(formatter)
        self.handler.setLevel(1)  # Set handler to lowest level too
        self.logger.addHandler(self.handler)

        # Add internal log levels if not already present
        add_internal_log_levels()

    def tearDown(self):
        """Clean up after each test method."""
        # Remove handler before closing stream
        if hasattr(self, 'handler') and self.handler in self.logger.handlers:
            self.logger.removeHandler(self.handler)
        if hasattr(self, 'log_stream') and not self.log_stream.closed:
            self.log_stream.close()
        self.logger.handlers.clear()

    def test_custom_level_shows_correct_source_location(self):
        """Test that custom logging levels show the correct source location."""
        # This should show this test file and line number, not logging_initializer.py
        self.logger.internal_info("Test message from test method")  # Line for verification

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Verify that the log shows this test file, not logging_initializer.py
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertNotIn("logging_initializer.py", log_output)

        # Verify it shows the correct function name
        self.assertIn("test_custom_level_shows_correct_source_location", log_output)

        # Verify the message is present
        self.assertIn("Test message from test method", log_output)

    def test_nested_function_shows_correct_location(self):
        """Test that logs from nested functions show the correct location."""
        def nested_function():
            self.logger.internal_info("Message from nested function")  # Line for verification

        # Call the nested function
        nested_function()

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Verify it shows this test file and the nested function
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertIn("nested_function", log_output)
        self.assertNotIn("logging_initializer.py", log_output)

    def test_multiple_stack_levels(self):
        """Test logging through multiple function calls."""
        def level_one():
            level_two()

        def level_two():
            level_three()

        def level_three():
            self.logger.internal_warning("Deep nested message")  # Line for verification

        # Clear previous output
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Call through multiple levels
        level_one()

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Should show level_three as the source, not logging_initializer.py
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertIn("level_three", log_output)
        self.assertNotIn("logging_initializer.py", log_output)

    def test_regular_logging_unaffected(self):
        """Test that regular logging methods are not affected by the fix."""
        # Clear previous output
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Use regular logging method
        self.logger.info("Regular info message")  # Line for verification

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Should still show correct location for regular logging
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertIn("test_regular_logging_unaffected", log_output)

    def test_custom_level_with_args_and_kwargs(self):
        """Test that custom logging with arguments and keyword arguments works."""
        # Clear previous output
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Test with arguments and keyword arguments
        test_value = 42
        self.logger.internal_info("Value is %d", test_value, extra={'custom_field': 'test'})  # Line for verification

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Verify location is correct
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertIn("test_custom_level_with_args_and_kwargs", log_output)
        self.assertNotIn("logging_initializer.py", log_output)

        # Verify message formatting worked
        self.assertIn("Value is 42", log_output)

    def test_dynamically_added_level(self):
        """Test that dynamically added custom levels also show correct source."""
        # Add a new custom level
        add_logging_level("CUSTOM_TEST", 25)

        # Clear previous output
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Use the newly added level
        self.logger.custom_test("Message with custom level")  # Line for verification

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # Verify location is correct
        self.assertIn("test_logging_source_location.py", log_output)
        self.assertIn("test_dynamically_added_level", log_output)
        self.assertNotIn("logging_initializer.py", log_output)

    def test_root_logger_custom_levels(self):
        """Test that root logger custom levels also work correctly."""
        # Create a separate handler for root logger testing
        root_stream = StringIO()
        root_handler = logging.StreamHandler(root_stream)
        formatter = logging.Formatter('%(levelname)s:%(filename)s:%(lineno)d:%(funcName)s - %(message)s')
        root_handler.setFormatter(formatter)
        root_handler.setLevel(1)

        # Configure root logger with our handler
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(1)
        root_logger.addHandler(root_handler)

        try:
            # Use root logger's custom method
            logging.internal_info("Root logger message")  # Line for verification

            # Get the captured log output
            log_output = root_stream.getvalue()

            # Verify location is correct
            self.assertIn("test_logging_source_location.py", log_output)
            self.assertIn("test_root_logger_custom_levels", log_output)
            self.assertNotIn("logging_initializer.py", log_output)
        finally:
            # Clean up
            root_logger.removeHandler(root_handler)
            root_logger.setLevel(original_level)
            root_stream.close()

    def test_stacklevel_parameter_preservation(self):
        """Test that explicit stacklevel parameter is preserved if provided."""
        def wrapper_function():
            # Explicitly set stacklevel=3 to skip this wrapper frame
            self.logger.internal_info("Message with explicit stacklevel", stacklevel=3)

        # Call the wrapper
        wrapper_function()

        # Get the captured log output
        log_output = self.log_stream.getvalue()

        # The important thing is that it doesn't show logging_initializer.py
        # and that the stacklevel parameter was respected (not showing wrapper_function)
        self.assertNotIn("logging_initializer.py", log_output)
        self.assertNotIn("wrapper_function", log_output)
        # Should show the test method name since we skipped the wrapper
        self.assertIn("test_stacklevel_parameter_preservation", log_output)


if __name__ == '__main__':
    unittest.main()
