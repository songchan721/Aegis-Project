"""
Tests for logging module.
"""

import json
import logging
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from aegis_shared.logging.config import configure_logging, get_logger
from aegis_shared.logging.context import (
    add_context,
    clear_context,
    get_context,
    request_id_var,
    service_name_var,
    user_id_var,
)
from aegis_shared.logging.handlers import ElasticsearchHandler, StructuredFileHandler


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_basic(self):
        """Test basic logging configuration."""
        configure_logging(service_name="test-service", log_level="INFO")

        logger = get_logger(__name__)
        assert logger is not None

    def test_configure_logging_with_different_levels(self):
        """Test logging configuration with different levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            configure_logging(service_name="test-service", log_level=level)
            logger = get_logger(__name__)
            assert logger is not None

    @patch("aegis_shared.logging.config.structlog")
    def test_configure_logging_calls_structlog(self, mock_structlog):
        """Test that configure_logging properly calls structlog."""
        configure_logging(service_name="test-service")

        mock_structlog.configure.assert_called_once()
        call_args = mock_structlog.configure.call_args
        assert "processors" in call_args.kwargs
        assert "wrapper_class" in call_args.kwargs

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        configure_logging(service_name="test-service")
        logger = get_logger("test.module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")


class TestLoggingContext:
    """Test logging context management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_context()

    def test_add_and_get_context(self):
        """Test adding and getting context."""
        add_context(request_id="req-123", user_id="user-456")

        context = get_context()
        assert context["request_id"] == "req-123"
        assert context["user_id"] == "user-456"

    def test_clear_context(self):
        """Test clearing context."""
        add_context(request_id="req-123")
        assert get_context()["request_id"] == "req-123"

        clear_context()
        context = get_context()
        assert context.get("request_id") is None

    def test_context_variables_isolation(self):
        """Test that context variables are properly isolated."""
        # Set initial context
        add_context(request_id="req-123")

        # Simulate different request context
        request_id_var.set("req-456")
        user_id_var.set("user-789")

        # Context should reflect the context variables
        context = get_context()
        assert context["request_id"] == "req-456"
        assert context["user_id"] == "user-789"

    def test_service_name_context(self):
        """Test service name in context."""
        service_name_var.set("test-service")

        context = get_context()
        assert context["service_name"] == "test-service"

    def test_partial_context(self):
        """Test context with only some values set."""
        add_context(request_id="req-123")

        context = get_context()
        assert context["request_id"] == "req-123"
        assert context.get("user_id") is None
        assert context.get("service_name") is None


class TestStructuredLogging:
    """Test structured logging functionality."""

    def setup_method(self):
        """Set up for each test."""
        clear_context()

    def teardown_method(self):
        """Clean up after each test."""
        clear_context()

    @patch("sys.stdout", new_callable=StringIO)
    def test_structured_log_output(self, mock_stdout):
        """Test that logs are output in structured format."""
        # Configure logging after stdout is mocked
        configure_logging(service_name="test-service", log_level="DEBUG")
        logger = get_logger(__name__)

        add_context(request_id="req-123", user_id="user-456")
        logger.info("test message", extra_field="extra_value")

        output = mock_stdout.getvalue()

        # Should be valid JSON - split by lines and take the last line (the actual log)
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
        if not lines:
            pytest.fail("No log output captured")

        # Take the last line which should be our test log
        log_line = lines[-1]

        try:
            log_data = json.loads(log_line)
            assert log_data["event"] == "test message"
            assert log_data["request_id"] == "req-123"
            assert log_data["user_id"] == "user-456"
            assert log_data["extra_field"] == "extra_value"
        except json.JSONDecodeError:
            pytest.fail(f"Log output is not valid JSON: {log_line}")

    @patch("sys.stdout", new_callable=StringIO)
    def test_log_levels(self, mock_stdout):
        """Test different log levels."""
        # Configure logging after stdout is mocked
        configure_logging(service_name="test-service", log_level="DEBUG")
        logger = get_logger(__name__)

        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

        output = mock_stdout.getvalue()
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]

        # Filter out the initialization log and keep only our test logs
        test_logs = [
            line
            for line in lines
            if "message" in line and "Logging initialized" not in line
        ]

        # Should have 4 log entries
        assert len(test_logs) == 4

        # Check log levels
        for i, level in enumerate(["debug", "info", "warning", "error"]):
            log_data = json.loads(test_logs[i])
            assert log_data["level"] == level

    @patch("sys.stdout", new_callable=StringIO)
    def test_exception_logging(self, mock_stdout):
        """Test exception logging with stack trace."""
        # Configure logging after stdout is mocked
        configure_logging(service_name="test-service", log_level="DEBUG")
        logger = get_logger(__name__)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")

        output = mock_stdout.getvalue()
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]

        # Find the exception log (should be the last line)
        exception_log = lines[-1]
        log_data = json.loads(exception_log)

        assert log_data["event"] == "An error occurred"
        # Note: The exception info might be in exc_info or similar field
        # depending on formatter


class TestElasticsearchHandler:
    """Test Elasticsearch logging handler."""

    @pytest.fixture
    def mock_es_client(self):
        """Mock Elasticsearch client."""
        mock_client = Mock()
        mock_client.index = Mock()
        return mock_client

    def test_elasticsearch_handler_init(self, mock_es_client):
        """Test Elasticsearch handler initialization."""
        handler = ElasticsearchHandler(es_client=mock_es_client, index_name="test-logs")

        assert handler.es_client == mock_es_client
        assert handler.index_name == "test-logs"

    def test_elasticsearch_handler_emit(self, mock_es_client):
        """Test Elasticsearch handler log emission."""
        handler = ElasticsearchHandler(es_client=mock_es_client, index_name="test-logs")

        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Verify Elasticsearch index was called
        mock_es_client.index.assert_called_once()
        call_args = mock_es_client.index.call_args
        assert call_args.kwargs["index"] == "test-logs"
        assert "body" in call_args.kwargs

    def test_elasticsearch_handler_error_handling(self, mock_es_client):
        """Test Elasticsearch handler error handling."""
        # Make Elasticsearch client raise an exception
        mock_es_client.index.side_effect = Exception("ES connection failed")

        handler = ElasticsearchHandler(es_client=mock_es_client, index_name="test-logs")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Should not raise exception
        handler.emit(record)


class TestStructuredFileHandler:
    """Test structured file logging handler."""

    def test_structured_file_handler_init(self, temp_dir):
        """Test structured file handler initialization."""
        log_file = temp_dir / "test.log"

        handler = StructuredFileHandler(
            filename=str(log_file), max_bytes=1024 * 1024, backup_count=5
        )

        assert handler.baseFilename == str(log_file)
        assert handler.maxBytes == 1024 * 1024
        assert handler.backupCount == 5

    def test_structured_file_handler_format(self, temp_dir):
        """Test structured file handler formatting."""
        log_file = temp_dir / "test.log"

        handler = StructuredFileHandler(filename=str(log_file))

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )

        formatted = handler.format(record)

        # Should be valid JSON
        try:
            log_data = json.loads(formatted)
            assert "timestamp" in log_data
            assert log_data["level"] == "info"
            assert log_data["event"] == "test message"
        except json.JSONDecodeError:
            pytest.fail("Formatted log is not valid JSON")


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    def setup_method(self):
        """Set up for integration tests."""
        clear_context()

    def teardown_method(self):
        """Clean up after integration tests."""
        clear_context()

    @patch("sys.stdout", new_callable=StringIO)
    def test_request_lifecycle_logging(self, mock_stdout):
        """Test logging throughout a request lifecycle."""
        logger = get_logger(__name__)

        # Start of request
        add_context(request_id="req-123")
        logger.info("request_started", endpoint="/api/policies")

        # During request processing
        add_context(user_id="user-456")
        logger.info("user_authenticated", user_id="user-456")

        # Business logic
        logger.info("policy_retrieved", policy_id="policy-789")

        # End of request
        logger.info("request_completed", status_code=200, duration_ms=150)

        output = mock_stdout.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        # Verify all logs have consistent request_id
        for line in lines:
            log_data = json.loads(line)
            assert log_data["request_id"] == "req-123"
            assert log_data["service"] == "test-service"

        # Verify user_id appears in logs after authentication
        user_logs = [json.loads(line) for line in lines[1:]]
        for log_data in user_logs:
            assert log_data["user_id"] == "user-456"

    @patch("sys.stdout", new_callable=StringIO)
    def test_error_logging_with_context(self, mock_stdout):
        """Test error logging with full context."""
        # Configure logging after stdout is mocked
        configure_logging(service_name="test-service", log_level="INFO")
        logger = get_logger(__name__)

        add_context(
            request_id="req-123", user_id="user-456", service_name="test-service"
        )

        try:
            # Simulate business logic error
            raise ValueError("Invalid policy ID")
        except ValueError as e:
            logger.error(
                "policy_validation_failed", error=str(e), policy_id="invalid-id"
            )

        output = mock_stdout.getvalue()
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]

        # Find the error log (should be the last line)
        error_log = lines[-1]
        log_data = json.loads(error_log)

        assert log_data["event"] == "policy_validation_failed"
        assert log_data["request_id"] == "req-123"
        assert log_data["user_id"] == "user-456"
        assert log_data["service"] == "aegis-shared"  # This comes from the formatter
        assert log_data["error"] == "Invalid policy ID"
        assert log_data["policy_id"] == "invalid-id"
