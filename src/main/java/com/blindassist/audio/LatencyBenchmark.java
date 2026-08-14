package com.blindassist.audio;

import com.blindassist.audio.model.AudioRequest;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class LatencyBenchmark {
    private final Map<String, Long> enqueueTimes = new ConcurrentHashMap<>();
    private final Map<String, Long> dequeueTimes = new ConcurrentHashMap<>();
    private final Map<String, Long> audibleTimes = new ConcurrentHashMap<>();
    private final List<Long> measurements = new ArrayList<>();

    public void markEnqueue(AudioRequest req) {
        enqueueTimes.put(req.toString(), System.nanoTime());
    }

    public void markDequeue(AudioRequest req) {
        dequeueTimes.put(req.toString(), System.nanoTime());
    }

    public void markAudible(AudioRequest req) {
        long t2 = System.nanoTime();
        audibleTimes.put(req.toString(), t2);
        long t0 = enqueueTimes.getOrDefault(req.toString(), t2);
        measurements.add((t2 - t0) / 1_000_000);
    }

    public long getLatencyMs(AudioRequest req) {
        Long start = enqueueTimes.get(req.toString());
        Long end = audibleTimes.get(req.toString());
        return (start != null && end != null) ? (end - start) / 1_000_000 : -1;
    }

    public String generateReport() {
        if (measurements.isEmpty()) {
            return "# End-to-End Latency Report\n\nNo measurements recorded yet.\n";
        }

        double avg = measurements.stream().mapToLong(Long::longValue).average().orElse(0);
        long min = measurements.stream().mapToLong(Long::longValue).min().orElse(0);
        long max = measurements.stream().mapToLong(Long::longValue).max().orElse(0);

        StringBuilder sb = new StringBuilder();
        sb.append("# End-to-End Latency Report\n\n");
        sb.append("| Stage | Description |\n");
        sb.append("|-------|-------------|\n");
        sb.append("| t0    | Request enqueued by submitter |\n");
        sb.append("| t1    | Mixer dequeued for playback |\n");
        sb.append("| t2    | Audio actually audible (post-routing) |\n");
        sb.append("| **E2E** | t2 - t0 |\n\n");
        sb.append("## Statistics\n");
        sb.append(String.format("- **Samples:** %d\n", measurements.size()));
        sb.append(String.format("- **Average:** %.2f ms\n", avg));
        sb.append(String.format("- **Min:** %d ms\n", min));
        sb.append(String.format("- **Max:** %d ms\n", max));
        sb.append("\n## Raw Measurements (ms)\n");
        sb.append(measurements.toString());
        sb.append("\n");
        return sb.toString();
    }

    public void reset() {
        enqueueTimes.clear();
        dequeueTimes.clear();
        audibleTimes.clear();
        measurements.clear();
    }
}