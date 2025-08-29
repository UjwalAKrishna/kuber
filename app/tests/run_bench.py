#!/usr/bin/env python3
"""
Benchmark script for Kuber AI Voice system.
Measures latency and throughput for Mode A endpoint.
"""

import asyncio
import aiohttp
import time
import statistics
import argparse
from pathlib import Path
import json


async def single_request(session: aiohttp.ClientSession, server_url: str, audio_file: str, request_id: int):
    """Make a single voice query request and measure timing."""
    start_time = time.time()
    
    try:
        with open(audio_file, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('audio', f, filename=f'test_{request_id}.wav', content_type='audio/wav')
            data.add_field('session_id', f'bench_session_{request_id}')
            
            async with session.post(f"{server_url}/v1/voice/query", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    end_time = time.time()
                    
                    return {
                        "success": True,
                        "request_id": request_id,
                        "total_time": (end_time - start_time) * 1000,  # ms
                        "server_timings": result.get("timings", {}),
                        "transcript_length": len(result.get("transcript", "")),
                        "response_length": len(result.get("llm_text", ""))
                    }
                else:
                    return {
                        "success": False,
                        "request_id": request_id,
                        "error": f"HTTP {response.status}",
                        "total_time": (time.time() - start_time) * 1000
                    }
    
    except Exception as e:
        return {
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "total_time": (time.time() - start_time) * 1000
        }


async def run_concurrent_benchmark(server_url: str, audio_file: str, num_requests: int, concurrency: int):
    """Run concurrent requests and measure performance."""
    print(f"🚀 Running benchmark: {num_requests} requests with concurrency {concurrency}")
    
    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_request(request_id):
            async with semaphore:
                return await single_request(session, server_url, audio_file, request_id)
        
        # Start all requests
        start_time = time.time()
        tasks = [bounded_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        return results, end_time - start_time


def analyze_results(results: list, total_duration: float):
    """Analyze benchmark results and print statistics."""
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    print(f"\n📊 Benchmark Results:")
    print(f"Total requests: {len(results)}")
    print(f"Successful: {len(successful_results)}")
    print(f"Failed: {len(failed_results)}")
    print(f"Success rate: {len(successful_results)/len(results)*100:.1f}%")
    print(f"Total duration: {total_duration:.2f}s")
    print(f"Throughput: {len(results)/total_duration:.2f} req/s")
    
    if successful_results:
        # Client-side latencies
        client_times = [r["total_time"] for r in successful_results]
        print(f"\n⏱️  Client-side Latencies (ms):")
        print(f"Mean: {statistics.mean(client_times):.1f}")
        print(f"Median: {statistics.median(client_times):.1f}")
        print(f"P95: {sorted(client_times)[int(len(client_times) * 0.95)]:.1f}")
        print(f"P99: {sorted(client_times)[int(len(client_times) * 0.99)]:.1f}")
        print(f"Min: {min(client_times):.1f}")
        print(f"Max: {max(client_times):.1f}")
        
        # Server-side component timings
        server_timings = [r["server_timings"] for r in successful_results if r.get("server_timings")]
        if server_timings:
            stt_times = [t.get("stt_ms", 0) for t in server_timings]
            llm_times = [t.get("llm_ms", 0) for t in server_timings]
            tts_times = [t.get("tts_ms", 0) for t in server_timings]
            total_server_times = [t.get("total_ms", 0) for t in server_timings]
            
            print(f"\n🔧 Server Component Timings (ms):")
            print(f"STT - Mean: {statistics.mean(stt_times):.1f}, P95: {sorted(stt_times)[int(len(stt_times) * 0.95)]:.1f}")
            print(f"LLM - Mean: {statistics.mean(llm_times):.1f}, P95: {sorted(llm_times)[int(len(llm_times) * 0.95)]:.1f}")
            print(f"TTS - Mean: {statistics.mean(tts_times):.1f}, P95: {sorted(tts_times)[int(len(tts_times) * 0.95)]:.1f}")
            print(f"Total Server - Mean: {statistics.mean(total_server_times):.1f}, P95: {sorted(total_server_times)[int(len(total_server_times) * 0.95)]:.1f}")
    
    if failed_results:
        print(f"\n❌ Failed Requests:")
        error_counts = {}
        for result in failed_results:
            error = result.get("error", "Unknown")
            error_counts[error] = error_counts.get(error, 0) + 1
        
        for error, count in error_counts.items():
            print(f"  {error}: {count}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Kuber AI Voice system")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    parser.add_argument("--audio", default="sample.wav", help="Audio file to test with")
    parser.add_argument("--requests", type=int, default=20, help="Number of requests to make")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of concurrent requests")
    parser.add_argument("--warmup", type=int, default=2, help="Number of warmup requests")
    
    args = parser.parse_args()
    
    # Check if audio file exists
    if not Path(args.audio).exists():
        print(f"❌ Audio file not found: {args.audio}")
        print("Please provide a valid audio file or create sample_audio.wav")
        return
    
    print(f"🎯 Benchmarking Kuber AI Voice at {args.server}")
    print(f"Audio file: {args.audio}")
    print(f"Requests: {args.requests}, Concurrency: {args.concurrency}")
    
    # Warmup requests
    if args.warmup > 0:
        print(f"\n🔥 Running {args.warmup} warmup requests...")
        warmup_results, _ = await run_concurrent_benchmark(
            args.server, args.audio, args.warmup, min(args.concurrency, args.warmup)
        )
        warmup_success = len([r for r in warmup_results if r["success"]])
        print(f"Warmup complete: {warmup_success}/{args.warmup} successful")
    
    # Main benchmark
    print(f"\n🏁 Starting main benchmark...")
    results, total_duration = await run_concurrent_benchmark(
        args.server, args.audio, args.requests, args.concurrency
    )
    
    # Analyze and display results
    analyze_results(results, total_duration)
    
    # Save detailed results
    output_file = f"benchmark_results_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "config": {
                "server": args.server,
                "audio_file": args.audio,
                "requests": args.requests,
                "concurrency": args.concurrency
            },
            "results": results,
            "total_duration": total_duration
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())