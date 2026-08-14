package com.blindassist.audio;

import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;

public class SonarPlayer {
    private static final int SAMPLE_RATE = 44100;
    private AudioTrack audioTrack;
    private boolean playing = false;
    private Thread generatorThread;

    public SonarPlayer() {
        int minBuffer = AudioTrack.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        );

        audioTrack = new AudioTrack.Builder()
            .setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build())
            .setAudioFormat(new AudioFormat.Builder()
                .setSampleRate(SAMPLE_RATE)
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build())
            .setBufferSizeInBytes(minBuffer)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build();
    }

    public void startSonar() {
        if (playing) return;
        playing = true;
        audioTrack.play();

        generatorThread = new Thread(() -> {
            short[] buffer = new short[SAMPLE_RATE / 10]; // 100ms buffer
            double phase = 0.0;
            double freq = 880.0; // A5 tone
            while (playing) {
                for (int i = 0; i < buffer.length; i++) {
                    buffer[i] = (short) (Math.sin(phase) * 3000);
                    phase += 2 * Math.PI * freq / SAMPLE_RATE;
                    if (phase > 2 * Math.PI) phase -= 2 * Math.PI;
                }
                audioTrack.write(buffer, 0, buffer.length);
            }
        }, "SonarGenerator");
        generatorThread.start();
    }

    public void stopSonar() {
        playing = false;
        if (generatorThread != null) {
            try { generatorThread.join(200); } catch (InterruptedException ignored) {}
        }
        audioTrack.stop();
        audioTrack.reloadStaticData();
    }

    public boolean isPlaying() {
        return playing;
    }

    public void release() {
        stopSonar();
        audioTrack.release();
    }
}