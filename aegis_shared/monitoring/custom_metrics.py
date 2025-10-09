from prometheus_client import Counter, Gauge, Histogram

def create_counter(name: str, documentation: str, labels: list[str] = None) -> Counter:
    return Counter(name, documentation, labels)

def create_gauge(name: str, documentation: str, labels: list[str] = None) -> Gauge:
    return Gauge(name, documentation, labels)

def create_histogram(name: str, documentation: str, labels: list[str] = None) -> Histogram:
    return Histogram(name, documentation, labels)

class CustomMetricsManager:
    """커스텀 메트릭 관리자"""
    
    def __init__(self, registry=None):
        """커스텀 메트릭 관리자 초기화

        Args:
            registry: Prometheus CollectorRegistry (optional)
        """
        self.registry = registry
        self.counters = {}
        self.gauges = {}
        self.histograms = {}
    
    def create_counter(self, name: str, documentation: str = None, description: str = None, labels: list[str] = None) -> Counter:
        doc = description or documentation or f"Counter metric: {name}"
        counter = Counter(name, doc, labelnames=labels or [], registry=self.registry)
        self.counters[name] = counter
        return counter
    
    def create_gauge(self, name: str, documentation: str = None, description: str = None, labels: list[str] = None) -> Gauge:
        doc = description or documentation or f"Gauge metric: {name}"
        gauge = Gauge(name, doc, labelnames=labels or [], registry=self.registry)
        self.gauges[name] = gauge
        return gauge
    
    def create_histogram(self, name: str, description: str = None, documentation: str = None,
                         labels: list[str] = None, buckets: list[float] = None) -> Histogram:
        """히스토그램 생성

        Args:
            name: 메트릭 이름
            description: 설명 (documentation의 별칭)
            documentation: 설명
            labels: 라벨 키 리스트
            buckets: 히스토그램 버킷 경계값 리스트
        """
        # description과 documentation 중 하나를 사용
        doc = description or documentation or f"Histogram metric: {name}"

        # buckets 설정
        kwargs = {"registry": self.registry}
        if buckets:
            kwargs["buckets"] = buckets

        histogram = Histogram(name, doc, labelnames=labels or [], **kwargs)
        self.histograms[name] = histogram
        return histogram

    def get_metric(self, name: str):
        """메트릭 조회

        Args:
            name: 메트릭 이름

        Returns:
            메트릭 객체 또는 None
        """
        if name in self.counters:
            return self.counters[name]
        if name in self.gauges:
            return self.gauges[name]
        if name in self.histograms:
            return self.histograms[name]
        return None