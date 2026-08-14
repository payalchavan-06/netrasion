package com.blindassist.audio;

import com.blindassist.audio.model.AlertLevel;
import com.blindassist.audio.model.AudioRequest;
import org.junit.Test;
import static org.junit.Assert.*;

public class PriorityAudioMixerTest {

    @Test
    public void testCriticalClearsQueue() throws InterruptedException {
        PriorityAudioMixer mixer = new PriorityAudioMixer();
        
        AudioRequest nav = new AudioRequest.Builder()
            .setLevel(AlertLevel.NAVIGATION).build();
        AudioRequest critical = new AudioRequest.Builder()
            .setLevel(AlertLevel.CRITICAL).build();
            
        mixer.enqueue(nav);
        mixer.enqueue(critical);
        
        AudioRequest next = mixer.pollNext();
        assertEquals(AlertLevel.CRITICAL, next.level);
    }

    @Test
    public void testInfoDroppedWhenNotSilent() throws InterruptedException {
        PriorityAudioMixer mixer = new PriorityAudioMixer();
        
        AudioRequest info = new AudioRequest.Builder()
            .setLevel(AlertLevel.INFO).build();
            
        mixer.enqueue(info);
        
        AudioRequest next = mixer.pollNext();
        assertNull(next);
    }
}