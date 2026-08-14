package com.blindassist.audio;

import com.blindassist.audio.model.AudioRequest;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class LatencyBenchmark {
    private final Map<String, Long> enqueueTimes = new ConcurrentHashMap<>();
    private final Map<String, Long> dequeueTimes = new ConcurrentHashMap<>();
    private final Map<String, Long> audibleTimes = new ConcurrentHashMap<>();

    public void markEnqueue(AudioRequest req) {
        enqueueTimes.put(req.toString(), System.nanoTime());
    }

    public void markDequeue(AudioRequest req) {
        dequeueTimes.put(req.toString(), System.nanoTime());
    }

    public void markAudible(AudioRequest req) {
        audibleTimes.put(req.toString(), System.nanoTime());
    }

    public long getLatencyMs(AudioRequest req) {
        Long start = enqueueTimes.get(req.toString());
        Long end = audibleTimes.get(req.toString());
        return (start != null && end != null) ? (end - start) / 1_000_000 : -1;
    }

    public String generateReport() {
        StringBuilder sb = new StringBuilder();
        sb.append("# End-to-End Latency Report\n\n");
        sb.append("| Stage | Description |\n");
        sb.append("|-------|-------------|\n");
        sb.append("| t0 | Request enqueued by submitter |\n");
        sb.append("| t1 | Mixer dequeued for playback |\n");
        sb.append("| t2 | Audio actually audible (post-routing) |\n");
        sb.append("| **E2E** | t2 - t0 |\n\n");
        sb.append("## Measurements\n");
        sb.append("(Populate after running benchmark)\n");
        return sb.toString();
    }

    public void reset() {
        enqueueTimes.clear();
        dequeueTimes.clear();
        audibleTimes.clear();
    }
}