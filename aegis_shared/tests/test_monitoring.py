"""
Tests for monitoring module.
"""

import time

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from aegis_shared.monitoring.custom_metrics import (
    CustomMetricsManager,
)
from aegis_shared.monitoring.endpoints import create_metrics_endpoint
from aegis_shared.monitoring.health import HealthChecker, HealthStatus
from aegis_shared.monitoring.metrics import (
    MetricsCollector,
    PrometheusMetrics,
)
from aegis_shared.monitoring.tracing import TracingManager


class TestMetricsCollector:
    """Test metrics collector functionality."""

    @pytest.fixture
    def metrics_collector(self):
        """Create metrics collector with custom registry."""
        registry = CollectorRegistry()
        return MetricsCollector(registry=registry)

    def test_track_request_metrics(self, metrics_collector):
        """Test request metrics tracking."""

        @metrics_collector.track_requests()
        def sample_endpoint():
            time.sleep(0.01)  # Simulate processing time
            return "success"

        # Call the decorated function
        result = sample_endpoint()

        assert result == "success"

        # Verify metrics were recorded
        registry = metrics_collector.registry

        # Check that request counter exists
        found = False
        for collector, names in registry._collector_to_names.items():
            if "requests_total" in names:
                found = True
                break

        if not found:
            pytest.fail("Request counter not found")

    def test_track_database_metrics(self, metrics_collector):
        """Test database metrics tracking."""

        @metrics_collector.track_database_queries()
        async def sample_query():
            time.sleep(0.005)  # Simulate query time
            return [{"id": 1, "name": "test"}]

        # Call the decorated function
        import asyncio

        result = asyncio.run(sample_query())

        assert len(result) == 1
        assert result[0]["name"] == "test"

    def test_custom_metric_tracking(self, metrics_collector):
        """Test custom metric tracking."""

        @metrics_collector.track_custom("business_operation", labels=["operation_type"])
        def business_operation(operation_type="default"):
            return f"Completed {operation_type}"

        result = business_operation(operation_type="policy_creation")
        assert result == "Completed policy_creation"

    def test_increment_counter_with_labels(self, metrics_collector):
        """Test counter increment with labels."""
        metrics_collector.increment_counter("test_counter", {"service": "test"}, 5)
        assert "test_counter" in metrics_collector._counters

    def test_increment_counter_without_labels(self, metrics_collector):
        """Test counter increment without labels."""
        metrics_collector.increment_counter("test_counter_no_labels")
        assert "test_counter_no_labels" in metrics_collector._counters

    def test_observe_histogram_with_labels(self, metrics_collector):
        """Test histogram observation with labels."""
        metrics_collector.observe_histogram(
            "test_histogram", 0.5, {"endpoint": "/api/test"}
        )
        assert "test_histogram" in metrics_collector._histograms

    def test_observe_histogram_without_labels(self, metrics_collector):
        """Test histogram observation without labels."""
        metrics_collector.observe_histogram("test_histogram_no_labels", 0.3)
        assert "test_histogram_no_labels" in metrics_collector._histograms

    def test_set_gauge_with_labels(self, metrics_collector):
        """Test gauge setting with labels."""
        metrics_collector.set_gauge("test_gauge", 42.0, {"resource": "memory"})
        assert "test_gauge" in metrics_collector._gauges

    def test_set_gauge_without_labels(self, metrics_collector):
        """Test gauge setting without labels."""
        metrics_collector.set_gauge("test_gauge_no_labels", 100.0)
        assert "test_gauge_no_labels" in metrics_collector._gauges

    def test_track_requests_decorator_sync(self, metrics_collector):
        """Test track_requests decorator with sync function."""

        @metrics_collector.track_requests()
        def sync_request():
            return "sync_result"

        result = sync_request()
        assert result == "sync_result"

    def test_track_requests_decorator_async(self, metrics_collector):
        """Test track_requests decorator with async function."""

        @metrics_collector.track_requests()
        async def async_request():
            return "async_result"

        import asyncio

        result = asyncio.run(async_request())
        assert result == "async_result"

    def test_track_database_queries_decorator_sync(self, metrics_collector):
        """Test track_database_queries decorator with sync function."""

        @metrics_collector.track_database_queries()
        def sync_query():
            return [{"id": 1}]

        result = sync_query()
        assert len(result) == 1

    def test_track_custom_decorator_sync(self, metrics_collector):
        """Test track_custom decorator with sync function."""

        @metrics_collector.track_custom("sync_operation", labels=["op_type"])
        def sync_operation(op_type="test"):
            return f"Completed {op_type}"

        result = sync_operation(op_type="custom")
        assert result == "Completed custom"

    def test_track_custom_decorator_async(self, metrics_collector):
        """Test track_custom decorator with async function."""

        @metrics_collector.track_custom("async_operation", labels=["op_type"])
        async def async_operation(op_type="test"):
            return f"Async completed {op_type}"

        import asyncio

        result = asyncio.run(async_operation(op_type="custom"))
        assert result == "Async completed custom"


class TestPrometheusMetrics:
    """Test Prometheus metrics functionality."""

    @pytest.fixture
    def prometheus_metrics(self):
        """Create Prometheus metrics instance."""
        registry = CollectorRegistry()
        return PrometheusMetrics(registry=registry)

    def test_increment_counter(self, prometheus_metrics):
        """Test counter increment."""
        counter_name = "test_counter"
        prometheus_metrics.increment_counter(
            counter_name, labels={"service": "test"}, value=5
        )

        # Verify counter was created and incremented
        assert counter_name in prometheus_metrics._counters

    def test_observe_histogram(self, prometheus_metrics):
        """Test histogram observation."""
        histogram_name = "test_histogram"
        prometheus_metrics.observe_histogram(
            histogram_name, value=0.5, labels={"endpoint": "/api/test"}
        )

        # Verify histogram was created and observed
        assert histogram_name in prometheus_metrics._histograms

    def test_set_gauge(self, prometheus_metrics):
        """Test gauge setting."""
        gauge_name = "test_gauge"
        prometheus_metrics.set_gauge(
            gauge_name, value=42.0, labels={"resource": "memory"}
        )

        # Verify gauge was created and set
        assert gauge_name in prometheus_metrics._gauges

    def test_get_metrics_output(self, prometheus_metrics):
        """Test metrics output generation."""
        # Create some metrics
        prometheus_metrics.increment_counter("requests_total", {"method": "GET"})
        prometheus_metrics.set_gauge("active_connections", {}, 10)

        # Get metrics output
        output = prometheus_metrics.get_metrics_output()

        assert isinstance(output, str)
        assert "requests_total" in output
        assert "active_connections" in output


class TestCustomMetricsManager:
    """Test custom metrics manager."""

    @pytest.fixture
    def metrics_manager(self):
        """Create custom metrics manager."""
        registry = CollectorRegistry()
        return CustomMetricsManager(registry=registry)

    def test_create_counter(self, metrics_manager):
        """Test counter creation."""
        counter = metrics_manager.create_counter(
            name="test_counter",
            description="Test counter",
            labels=["service", "method"],
        )

        assert isinstance(counter, Counter)
        assert counter._name == "test_counter"

    def test_create_histogram(self, metrics_manager):
        """Test histogram creation."""
        histogram = metrics_manager.create_histogram(
            name="test_histogram",
            description="Test histogram",
            labels=["endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
        )

        assert isinstance(histogram, Histogram)
        assert histogram._name == "test_histogram"

    def test_create_gauge(self, metrics_manager):
        """Test gauge creation."""
        gauge = metrics_manager.create_gauge(
            name="test_gauge", description="Test gauge", labels=["resource"]
        )

        assert isinstance(gauge, Gauge)
        assert gauge._name == "test_gauge"

    def test_get_metric(self, metrics_manager):
        """Test metric retrieval."""
        # Create a counter
        counter = metrics_manager.create_counter("test_counter", "Test counter")

        # Retrieve the same counter
        retrieved = metrics_manager.get_metric("test_counter")

        assert retrieved is counter

    def test_get_nonexistent_metric(self, metrics_manager):
        """Test retrieval of non-existent metric."""
        retrieved = metrics_manager.get_metric("nonexistent_metric")
        assert retrieved is None


class TestHealthChecker:
    """Test health checker functionality."""

    @pytest.fixture
    def health_checker(self):
        """Create health checker."""
        return HealthChecker()

    def test_register_health_check(self, health_checker):
        """Test health check registration."""

        def database_check():
            return HealthStatus.HEALTHY, "Database is responsive"

        health_checker.register_check("database", database_check)

        assert "database" in health_checker.checks

    @pytest.mark.asyncio
    async def test_check_health_all_healthy(self, health_checker):
        """Test health check when all services are healthy."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def cache_check():
            return HealthStatus.HEALTHY, "OK"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        status, details = await health_checker.check_health()

        assert status == HealthStatus.HEALTHY
        assert details["database"]["status"] == HealthStatus.HEALTHY
        assert details["cache"]["status"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_health_with_unhealthy_service(self, health_checker):
        """Test health check with unhealthy service."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def cache_check():
            return HealthStatus.UNHEALTHY, "Connection timeout"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        status, details = await health_checker.check_health()

        assert status == HealthStatus.UNHEALTHY
        assert details["database"]["status"] == HealthStatus.HEALTHY
        assert details["cache"]["status"] == HealthStatus.UNHEALTHY
        assert details["cache"]["message"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_check_health_with_degraded_service(self, health_checker):
        """Test health check with degraded service."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def external_api_check():
            return HealthStatus.DEGRADED, "Slow response times"

        health_checker.register_check("database", db_check)
        health_checker.register_check("external_api", external_api_check)

        status, details = await health_checker.check_health()

        assert status == HealthStatus.DEGRADED
        assert details["external_api"]["status"] == HealthStatus.DEGRADED

    def test_add_check_legacy_api(self, health_checker):
        """Test legacy add_check API."""

        async def legacy_check():
            return True

        health_checker.add_check("legacy", legacy_check)

        assert "legacy" in health_checker.checks

    def test_remove_check(self, health_checker):
        """Test removing health check."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        health_checker.register_check("database", db_check)
        assert "database" in health_checker.checks

        health_checker.remove_check("database")
        assert "database" not in health_checker.checks

    def test_remove_check_nonexistent(self, health_checker):
        """Test removing non-existent check."""
        # Should not raise error
        health_checker.remove_check("nonexistent")
        assert "nonexistent" not in health_checker.checks

    @pytest.mark.asyncio
    async def test_run_check_with_bool_return(self, health_checker):
        """Test run_check with bool return value."""

        def bool_check():
            return True

        result = await health_checker.run_check("test", bool_check)

        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_run_check_with_bool_false(self, health_checker):
        """Test run_check with bool False."""

        def bool_check():
            return False

        result = await health_checker.run_check("test", bool_check)

        assert result.name == "test"
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_run_check_with_async_function(self, health_checker):
        """Test run_check with async function."""

        async def async_check():
            return True

        result = await health_checker.run_check("test", async_check)

        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_run_check_with_async_function_false(self, health_checker):
        """Test run_check with async function returning False."""

        async def async_check():
            return False

        result = await health_checker.run_check("test", async_check)

        assert result.name == "test"
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_run_check_with_exception(self, health_checker):
        """Test run_check when check raises exception."""

        def failing_check():
            raise RuntimeError("Database connection failed")

        result = await health_checker.run_check("test", failing_check)

        assert result.name == "test"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Database connection failed" in result.message
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_check_health_no_checks(self, health_checker):
        """Test check_health when no checks registered."""
        status, details = await health_checker.check_health()

        assert status == HealthStatus.HEALTHY
        assert details == {}

    @pytest.mark.asyncio
    async def test_check_all(self, health_checker):
        """Test check_all method."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def cache_check():
            return HealthStatus.DEGRADED, "Slow"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        results = await health_checker.check_all()

        assert len(results) == 2
        assert results[0].name in ["database", "cache"]
        assert results[1].name in ["database", "cache"]

    @pytest.mark.asyncio
    async def test_check_all_no_checks(self, health_checker):
        """Test check_all when no checks registered."""
        results = await health_checker.check_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_overall_status_healthy(self, health_checker):
        """Test get_overall_status when all healthy."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def cache_check():
            return HealthStatus.HEALTHY, "OK"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        status = await health_checker.get_overall_status()

        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_overall_status_degraded(self, health_checker):
        """Test get_overall_status when some unhealthy."""

        def db_check():
            return HealthStatus.HEALTHY, "OK"

        def cache_check():
            return HealthStatus.UNHEALTHY, "Error"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        status = await health_checker.get_overall_status()

        assert status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_get_overall_status_unhealthy(self, health_checker):
        """Test get_overall_status when all unhealthy."""

        def db_check():
            return HealthStatus.UNHEALTHY, "Error"

        def cache_check():
            return HealthStatus.UNHEALTHY, "Error"

        health_checker.register_check("database", db_check)
        health_checker.register_check("cache", cache_check)

        status = await health_checker.get_overall_status()

        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_overall_status_no_checks(self, health_checker):
        """Test get_overall_status when no checks."""
        status = await health_checker.get_overall_status()

        assert status == HealthStatus.HEALTHY


class TestTracingManager:
    """Test tracing manager functionality."""

    @pytest.fixture
    def tracing_manager(self):
        """Create tracing manager."""
        return TracingManager(service_name="test-service")

    def test_create_span(self, tracing_manager):
        """Test span creation."""
        with tracing_manager.create_span("test_operation") as span:
            assert span is not None
            span.set_attribute("test.attribute", "test_value")

    def test_trace_function(self, tracing_manager):
        """Test function tracing decorator."""

        @tracing_manager.trace_function("business_operation")
        def business_function(param1, param2):
            return f"{param1}_{param2}"

        result = business_function("test", "value")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_trace_async_function(self, tracing_manager):
        """Test async function tracing."""

        @tracing_manager.trace_function("async_operation")
        async def async_business_function(param):
            return f"async_{param}"

        result = await async_business_function("test")
        assert result == "async_test"

    def test_get_current_trace_id(self, tracing_manager):
        """Test getting current trace ID."""
        with tracing_manager.create_span("test_operation"):
            trace_id = tracing_manager.get_current_trace_id()
            assert trace_id is not None

    def test_inject_trace_context(self, tracing_manager):
        """Test trace context injection."""
        headers = {}

        with tracing_manager.create_span("test_operation"):
            tracing_manager.inject_trace_context(headers)

        # Should have tracing headers
        assert len(headers) > 0

    def test_extract_trace_context(self, tracing_manager):
        """Test trace context extraction."""
        headers = {
            "traceparent": "00-12345678901234567890123456789012-1234567890123456-01"
        }

        context = tracing_manager.extract_trace_context(headers)
        assert context is not None


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""

    def test_create_metrics_endpoint(self):
        """Test metrics endpoint creation."""
        app = create_metrics_endpoint()
        assert app is not None

    def test_metrics_endpoint_response(self):
        """Test metrics endpoint response."""
        from fastapi.testclient import TestClient

        app = create_metrics_endpoint()
        client = TestClient(app)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_health_endpoint_response(self):
        """Test health endpoint response."""
        from fastapi.testclient import TestClient

        app = create_metrics_endpoint()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        health_data = response.json()
        assert "status" in health_data
        assert "timestamp" in health_data


class TestMonitoringIntegration:
    """Test monitoring integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_monitoring_stack(self):
        """Test full monitoring stack integration."""
        # Create components
        registry = CollectorRegistry()
        metrics_collector = MetricsCollector(registry=registry)
        health_checker = HealthChecker()
        tracing_manager = TracingManager(service_name="integration-test")

        # Register health checks
        def mock_db_check():
            return HealthStatus.HEALTHY, "Database OK"

        health_checker.register_check("database", mock_db_check)

        # Create monitored function
        @metrics_collector.track_requests()
        @tracing_manager.trace_function("integration_test")
        async def monitored_function(param):
            # Simulate some work
            time.sleep(0.01)
            return f"processed_{param}"

        # Execute function
        result = await monitored_function("test_data")

        assert result == "processed_test_data"

        # Check health
        health_status, health_details = await health_checker.check_health()
        assert health_status == HealthStatus.HEALTHY

        # Verify metrics were collected
        metrics_output = metrics_collector.get_metrics_output()
        assert isinstance(metrics_output, str)
        assert len(metrics_output) > 0
