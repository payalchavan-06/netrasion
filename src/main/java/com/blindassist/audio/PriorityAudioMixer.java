package com.blindassist.audio;

import com.blindassist.audio.model.AlertLevel;
import com.blindassist.audio.model.AudioRequest;
import java.util.ArrayList;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;

public class PriorityAudioMixer {
    private final BlockingQueue<AudioRequest> deferredQueue = 
        new PriorityBlockingQueue<>(16, (a, b) -> 
            Integer.compare(b.level.getPriority(), a.level.getPriority()));
    
    private final AtomicReference<AudioRequest> current = new AtomicReference<>();
    private volatile long lastAudibleEnd = 0L;
    private static final long SILENCE_THRESHOLD_MS = 2000;

    public void enqueue(AudioRequest req) {
        if (req.level == AlertLevel.CRITICAL) {
            handleCritical(req);
        } else if (req.level == AlertLevel.WARNING) {
            pruneLowerThan(AlertLevel.WARNING);
            deferredQueue.offer(req);
        } else if (req.level == AlertLevel.INFO) {
            long silentFor = System.currentTimeMillis() - lastAudibleEnd;
            if (silentFor >= SILENCE_THRESHOLD_MS) {
                deferredQueue.offer(req);
            }
        } else {
            deferredQueue.offer(req);
        }
    }

    public AudioRequest pollNext() throws InterruptedException {
        return deferredQueue.poll(500, TimeUnit.MILLISECONDS);
    }

    public void onPlaybackComplete(AudioRequest finished) {
        lastAudibleEnd = System.currentTimeMillis();
        current.compareAndSet(finished, null);
    }

    private void handleCritical(AudioRequest req) {
        deferredQueue.drainTo(new ArrayList<>());
        deferredQueue.offer(req);
    }

    private void pruneLowerThan(AlertLevel minLevel) {
        deferredQueue.removeIf(r -> r.level.getPriority() < minLevel.getPriority());
    }

    public boolean isIdle() {
        return current.get() == null && deferredQueue.isEmpty();
    }
}