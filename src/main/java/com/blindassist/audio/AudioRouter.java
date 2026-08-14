package com.blindassist.audio;

import android.content.Context;
import com.blindassist.audio.model.AlertLevel;
import com.blindassist.audio.model.AudioRequest;

public class AudioRouter {
    private final PriorityAudioMixer mixer;
    private final BluetoothAudioManager btManager;
    private final LatencyBenchmark benchmark;
    private final TonePlayer tonePlayer;
    private final SonarPlayer sonarPlayer;
    private volatile boolean running = false;
    private volatile boolean interrupted = false;

    public AudioRouter(Context ctx) {
        this.mixer = new PriorityAudioMixer();
        this.btManager = new BluetoothAudioManager(ctx);
        this.benchmark = new LatencyBenchmark();
        this.tonePlayer = new TonePlayer(ctx);
        this.sonarPlayer = new SonarPlayer();
        
        // Wire the hard-interrupt for CRITICAL alerts
        this.mixer.setInterruptCallback(() -> interrupted = true);
    }

    public void start() {
        running = true;
        new Thread(this::playbackLoop, "AudioRouter-Thread").start();
    }

    public void stop() {
        running = false;
        tonePlayer.release();
        sonarPlayer.release();
    }

    public void submit(AudioRequest req) {
        benchmark.markEnqueue(req);
        mixer.enqueue(req);
    }

    public void onBleConnectionState(boolean connected) {
        btManager.onConnectionEvent(connected);
    }

    public String getBenchmarkReport() {
        return benchmark.generateReport();
    }

    private void playbackLoop() {
        while (running) {
            try {
                if (interrupted) {
                    // CRITICAL came in — stop everything immediately
                    sonarPlayer.stopSonar();
                    tonePlayer.stopAll();
                    interrupted = false;
                }

                AudioRequest next = mixer.pollNext();
                if (next == null) continue;

                benchmark.markDequeue(next);
                
                if (btManager.isBluetoothAudioReady()) {
                    btManager.routeToBluetooth();
                } else {
                    btManager.routeToWiredOrSpeaker();
                }

                playRequest(next);
                benchmark.markAudible(next);
                mixer.onPlaybackComplete(next);

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void playRequest(AudioRequest req) {
        switch (req.level) {
            case CRITICAL:
            case WARNING:
            case INFO:
                tonePlayer.play(req.level, 1.0f);
                try { Thread.sleep(300); } catch (InterruptedException ignored) {}
                break;
            case NAVIGATION:
                sonarPlayer.startSonar();
                try { Thread.sleep(500); } catch (InterruptedException ignored) {}
                break;
        }
    }
}