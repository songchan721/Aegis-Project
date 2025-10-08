from prometheus_client import Counter, Gauge, Histogram

def create_counter(name: str, documentation: str, labels: list[str] = None) -> Counter:
    return Counter(name, documentation, labels)

def create_gauge(name: str, documentation: str, labels: list[str] = None) -> Gauge:
    return Gauge(name, documentation, labels)

def create_histogram(name: str, documentation: str, labels: list[str] = None) -> Histogram:
    return Histogram(name, documentation, labels)

class CustomMetricsManager:
    """커스텀 메트릭 관리자"""
    
    def __init__(self):
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def create_counter(self, name: str, documentation: str, labels: list[str] = None) -> Counter:
        counter = create_counter(name, documentation, labels)
        self.counters[name] = counter
        return counter
    
    def create_gauge(self, name: str, documentation: str, labels: list[str] = None) -> Gauge:
        gauge = create_gauge(name, documentation, labels)
        self.gauges[name] = gauge
        return gauge
    
    def create_histogram(self, name: str, documentation: str, labels: list[str] = None) -> Histogram:
        histogram = create_histogram(name, documentation, labels)
        self.histograms[name] = histogram
        return histogram
