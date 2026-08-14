package com.blindassist.audio.model;

public class AudioRequest {
    public final AlertLevel level;
    public final byte[] pcmData;
    public final int soundResId;
    public final boolean isTTS;
    public final long enqueuedAt;

    private AudioRequest(Builder b) {
        this.level = b.level;
        this.pcmData = b.pcmData;
        this.soundResId = b.soundResId;
        this.isTTS = b.isTTS;
        this.enqueuedAt = System.nanoTime();
    }

    public static class Builder {
        private AlertLevel level;
        private byte[] pcmData;
        private int soundResId = -1;
        private boolean isTTS = false;

        public Builder setLevel(AlertLevel l) { this.level = l; return this; }
        public Builder setPcmData(byte[] d) { this.pcmData = d; return this; }
        public Builder setSoundResId(int id) { this.soundResId = id; return this; }
        public Builder setTTS(boolean tts) { this.isTTS = tts; return this; }
        public AudioRequest build() { return new AudioRequest(this); }
    }
}