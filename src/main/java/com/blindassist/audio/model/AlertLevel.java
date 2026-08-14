package com.blindassist.audio.model;

public enum AlertLevel {
    INFO(1), WARNING(2), CRITICAL(3), NAVIGATION(0);

    private final int priority;
    AlertLevel(int p) { this.priority = p; }
    public int getPriority() { return priority; }
    
    public boolean interrupts(AlertLevel other) {
        return this.priority > other.priority;
    }
}