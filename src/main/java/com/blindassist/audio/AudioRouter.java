package com.blindassist.audio;

import android.content.Context;
import com.blindassist.audio.model.AudioRequest;

public class AudioRouter {
    private final PriorityAudioMixer mixer;
    private final BluetoothAudioManager btManager;
    private final LatencyBenchmark benchmark;
    private volatile boolean running = false;

    public AudioRouter(Context ctx) {
        this.mixer = new PriorityAudioMixer();
        this.btManager = new BluetoothAudioManager(ctx);
        this.benchmark = new LatencyBenchmark();
    }

    public void start() {
        running = true;
        new Thread(this::playbackLoop, "AudioRouter-Thread").start();
    }

    public void stop() {
        running = false;
    }

    public void submit(AudioRequest req) {
        benchmark.markEnqueue(req);
        mixer.enqueue(req);
    }

    public void onBleConnectionState(boolean connected) {
        btManager.onConnectionEvent(connected);
    }

    private void playbackLoop() {
        while (running) {
            try {
                AudioRequest next = mixer.pollNext();
                if (next == null) continue;

                benchmark.markDequeue(next);
                
                if (btManager.isBluetoothAudioReady()) {
                    btManager.routeToBluetooth();
                } else {
                    btManager.routeToWiredOrSpeaker();
                }

                playStub(next);
                benchmark.markAudible(next);
                mixer.onPlaybackComplete(next);

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void playStub(AudioRequest req) {
        android.util.Log.d("AudioRouter", 
            "Playing [" + req.level + "] latency=" + benchmark.getLatencyMs(req) + "ms");
        try { Thread.sleep(100); } catch (InterruptedException ignored) {}
    }
}