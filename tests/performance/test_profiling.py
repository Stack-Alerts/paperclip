"""
Task 1.5.3: Performance Profiling
Profile optimization performance to identify bottlenecks
Sprint 1.5 - Testing & Polish
"""
import cProfile
import pstats
import io
import json
import time
import psutil
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class PerformanceProfiler:
    """Performance profiling utility for optimization runs"""
    
    def __init__(self, output_dir: str = "profiles"):
        """Initialize profiler with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profiler = cProfile.Profile()
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.start_memory = None
        
    def start(self):
        """Start profiling"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.profiler.enable()
        
    def stop(self):
        """Stop profiling"""
        self.profiler.disable()
        return {
            'duration': time.time() - self.start_time,
            'memory_used': (self.process.memory_info().rss / 1024 / 1024) - self.start_memory
        }
    
    def get_stats(self, sort_by: str = 'cumtime', limit: int = 20) -> pstats.Stats:
        """Get profiling statistics"""
        stats = pstats.Stats(self.profiler)
        stats.sort_stats(sort_by)
        return stats
    
    def print_stats(self, sort_by: str = 'cumtime', limit: int = 20):
        """Print profiling statistics"""
        stats = self.get_stats(sort_by)
        stats.print_stats(limit)
    
    def save_stats(self, filename: str):
        """Save profiling statistics to file"""
        filepath = self.output_dir / filename
        self.profiler.dump_stats(str(filepath))
        
    def generate_report(self, name: str, sort_by: str = 'cumtime', limit: int = 20) -> Dict[str, Any]:
        """Generate performance report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get stats
        stats_io = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stats_io)
        stats.sort_stats(sort_by)
        stats.print_stats(limit)
        
        # Extract top functions
        top_functions = []
        stats.sort_stats(sort_by)
        for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:limit]:
            top_functions.append({
                'function': f"{func[0]}:{func[1]}({func[2]})",
                'calls': nc,
                'total_time': tt,
                'cumulative_time': ct,
                'time_per_call': tt/nc if nc > 0 else 0
            })
        
        report = {
            'name': name,
            'timestamp': timestamp,
            'sort_by': sort_by,
            'top_functions': top_functions,
            'raw_stats': stats_io.getvalue()
        }
        
        # Save report
        report_file = self.output_dir / f"{name}_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


class MemoryProfiler:
    """Memory profiling utility"""
    
    def __init__(self, sample_interval: int = 1):
        """Initialize memory profiler"""
        self.sample_interval = sample_interval
        self.process = psutil.Process(os.getpid())
        self.samples: List[Dict[str, Any]] = []
        self.baseline = None
        
    def start(self):
        """Start memory profiling"""
        self.baseline = self.process.memory_info().rss / 1024 / 1024  # MB
        self.samples = []
        
    def sample(self, label: str = ""):
        """Take memory sample"""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        sample = {
            'timestamp': time.time(),
            'label': label,
            'memory_mb': memory_mb,
            'growth_mb': memory_mb - self.baseline if self.baseline else 0
        }
        self.samples.append(sample)
        return sample
    
    def get_peak_memory(self) -> float:
        """Get peak memory usage"""
        if not self.samples:
            return 0
        return max(s['memory_mb'] for s in self.samples)
    
    def get_memory_growth(self) -> float:
        """Get total memory growth"""
        if not self.samples or not self.baseline:
            return 0
        return self.samples[-1]['memory_mb'] - self.baseline
    
    def detect_leaks(self, threshold_mb: float = 100) -> bool:
        """Detect potential memory leaks"""
        growth = self.get_memory_growth()
        return growth > threshold_mb
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate memory profiling report"""
        if not self.samples:
            return {'error': 'No samples collected'}
        
        return {
            'baseline_mb': self.baseline,
            'peak_mb': self.get_peak_memory(),
            'final_mb': self.samples[-1]['memory_mb'],
            'growth_mb': self.get_memory_growth(),
            'sample_count': len(self.samples),
            'samples': self.samples
        }


def profile_optimizer_run(strategy_file: str, max_configs: int = 20) -> Dict[str, Any]:
    """
    Profile a complete optimizer run
    
    Args:
        strategy_file: Path to strategy JSON file
        max_configs: Maximum number of configurations to test
        
    Returns:
        Dictionary with profiling results
    """
    # NOTE: This is a placeholder. When OptimizerV3 is ready, uncomment and use:
    # from src.optimizer_v3.core.optimizer import OptimizerV3
    
    print(f"Profiling optimizer run for {strategy_file} with {max_configs} configs...")
    
    # Initialize profilers
    perf_profiler = PerformanceProfiler()
    mem_profiler = MemoryProfiler()
    
    # Start profiling
    perf_profiler.start()
    mem_profiler.start()
    
    try:
        # Load strategy
        with open(strategy_file, 'r') as f:
            strategy = json.load(f)
        
        mem_profiler.sample("Strategy loaded")
        
        # TODO: When OptimizerV3 is ready, uncomment:
        # optimizer = OptimizerV3(strategy)
        # mem_profiler.sample("Optimizer initialized")
        # 
        # optimizer.set_max_configs(max_configs)
        # mem_profiler.sample("Configs generated")
        # 
        # results = optimizer.optimize()
        # mem_profiler.sample("Optimization complete")
        
        # For now, simulate some work
        time.sleep(0.1)
        mem_profiler.sample("Simulation complete")
        
    finally:
        # Stop profiling
        perf_stats = perf_profiler.stop()
        
    # Generate reports
    perf_report = perf_profiler.generate_report(
        name=f"optimizer_{Path(strategy_file).stem}",
        sort_by='cumtime',
        limit=20
    )
    
    mem_report = mem_profiler.generate_report()
    
    # Combined report
    report = {
        'strategy_file': strategy_file,
        'max_configs': max_configs,
        'duration_seconds': perf_stats['duration'],
        'memory_used_mb': perf_stats['memory_used'],
        'performance': perf_report,
        'memory': mem_report,
        'bottlenecks': identify_bottlenecks(perf_report),
        'recommendations': generate_recommendations(perf_report, mem_report)
    }
    
    return report


def identify_bottlenecks(perf_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify performance bottlenecks from profiling data"""
    bottlenecks = []
    
    top_functions = perf_report.get('top_functions', [])
    
    for func in top_functions[:5]:  # Top 5 slowest
        if func['cumulative_time'] > 1.0:  # More than 1 second
            bottlenecks.append({
                'function': func['function'],
                'cumulative_time': func['cumulative_time'],
                'calls': func['calls'],
                'severity': 'high' if func['cumulative_time'] > 5.0 else 'medium'
            })
    
    return bottlenecks


def generate_recommendations(perf_report: Dict[str, Any], mem_report: Dict[str, Any]) -> List[str]:
    """Generate optimization recommendations"""
    recommendations = []
    
    # Check duration
    top_functions = perf_report.get('top_functions', [])
    if top_functions:
        total_time = sum(f['cumulative_time'] for f in top_functions[:5])
        if total_time > 10.0:
            recommendations.append(
                "Consider parallelizing slow functions or adding caching"
            )
    
    # Check memory
    memory_growth = mem_report.get('growth_mb', 0)
    if memory_growth > 500:
        recommendations.append(
            "High memory usage detected. Consider implementing cleanup between configs"
        )
    
    # Check for database operations
    for func in top_functions:
        if 'database' in func['function'].lower() or 'query' in func['function'].lower():
            recommendations.append(
                "Database operations detected in hot path. Consider adding indexes or caching"
            )
            break
    
    return recommendations


# Test functions for pytest
def test_profiler_initialization():
    """Test profiler can be initialized"""
    profiler = PerformanceProfiler()
    assert profiler.output_dir.exists()
    
def test_memory_profiler():
    """Test memory profiler"""
    profiler = MemoryProfiler()
    profiler.start()
    
    # Take some samples
    profiler.sample("start")
    _ = [i**2 for i in range(1000000)]  # Allocate some memory
    profiler.sample("after allocation")
    
    report = profiler.generate_report()
    assert report['sample_count'] == 2
    assert report['growth_mb'] >= 0


if __name__ == "__main__":
    # Example usage
    print("Performance Profiling Tool")
    print("=" * 50)
    
    # Test with a sample strategy
    strategy_file = "tests/strategies/hod_rejection.json"
    
    if Path(strategy_file).exists():
        report = profile_optimizer_run(strategy_file, max_configs=10)
        
        print(f"\nDuration: {report['duration_seconds']:.2f} seconds")
        print(f"Memory used: {report['memory_used_mb']:.2f} MB")
        
        if report['bottlenecks']:
            print("\nBottlenecks identified:")
            for bottleneck in report['bottlenecks']:
                print(f"  - {bottleneck['function']}: {bottleneck['cumulative_time']:.2f}s")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
    else:
        print(f"Strategy file not found: {strategy_file}")
