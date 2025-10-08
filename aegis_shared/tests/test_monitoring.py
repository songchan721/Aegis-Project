"""
Tests for monitoring module.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge

from aegis_shared.monitoring.metrics import (
    track_metrics,
    MetricsCollector,
    PrometheusMetrics
)
from aegis_shared.monitoring.custom_metrics import (
    create_counter,
    create_histogram,
    create_gauge,
    CustomMetricsManager
)
from aegis_shared.monitoring.endpoints import create_metrics_endpoint
from aegis_shared.monitoring.health import HealthChecker, HealthStatus
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
        for collector in registry._collector_to_names:
            if hasattr(collector, '_name') and 'requests_total' in collector._name:
                assert True
                break
        else:
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
            counter_name,
            labels={"service": "test"},
            value=5
        )
        
        # Verify counter was created and incremented
        assert counter_name in prometheus_metrics._counters
    
    def test_observe_histogram(self, prometheus_metrics):
        """Test histogram observation."""
        histogram_name = "test_histogram"
        prometheus_metrics.observe_histogram(
            histogram_name,
            value=0.5,
            labels={"endpoint": "/api/test"}
        )
        
        # Verify histogram was created and observed
        assert histogram_name in prometheus_metrics._histograms
    
    def test_set_gauge(self, prometheus_metrics):
        """Test gauge setting."""
        gauge_name = "test_gauge"
        prometheus_metrics.set_gauge(
            gauge_name,
            value=42.0,
            labels={"resource": "memory"}
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
            labels=["service", "method"]
        )
        
        assert isinstance(counter, Counter)
        assert counter._name == "test_counter"
    
    def test_create_histogram(self, metrics_manager):
        """Test histogram creation."""
        histogram = metrics_manager.create_histogram(
            name="test_histogram",
            description="Test histogram",
            labels=["endpoint"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        assert isinstance(histogram, Histogram)
        assert histogram._name == "test_histogram"
    
    def test_create_gauge(self, metrics_manager):
        """Test gauge creation."""
        gauge = metrics_manager.create_gauge(
            name="test_gauge",
            description="Test gauge",
            labels=["resource"]
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
