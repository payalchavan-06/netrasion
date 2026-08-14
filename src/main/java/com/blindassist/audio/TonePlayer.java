package com.blindassist.audio;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.SoundPool;
import com.blindassist.audio.model.AlertLevel;

public class TonePlayer {
    private SoundPool soundPool;
    private int criticalToneId = -1;
    private int warningToneId = -1;
    private int infoToneId = -1;

    public TonePlayer(Context ctx) {
        AudioAttributes attrs = new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build();

        soundPool = new SoundPool.Builder()
            .setMaxStreams(3)
            .setAudioAttributes(attrs)
            .build();

        // TODO: Replace with actual raw resource IDs
        // criticalToneId = soundPool.load(ctx, R.raw.tone_critical, 1);
        // warningToneId = soundPool.load(ctx, R.raw.tone_warning, 1);
        // infoToneId = soundPool.load(ctx, R.raw.tone_info, 1);
    }

    public void play(AlertLevel level, float volume) {
        int id;
        switch (level) {
            case CRITICAL: id = criticalToneId; break;
            case WARNING: id = warningToneId; break;
            case INFO: id = infoToneId; break;
            default: return;
        }
        if (id != -1) {
            soundPool.play(id, volume, volume, 1, 0, 1.0f);
        }
    }

    public void stopAll() {
        soundPool.autoPause();
    }

    public void release() {
        soundPool.release();
    }
}