package com.blindassist.audio;

import android.bluetooth.BluetoothA2dp;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothProfile;
import android.content.Context;
import android.media.AudioManager;
import android.media.AudioDeviceInfo;
import android.util.Log;
import java.util.List;

public class BluetoothAudioManager {
    private static final String TAG = "BTAudio";
    private final Context ctx;
    private final AudioManager audioManager;
    private BluetoothA2dp a2dpProxy;
    private volatile boolean btConnected = false;

    public BluetoothAudioManager(Context ctx) {
        this.ctx = ctx.getApplicationContext();
        this.audioManager = (AudioManager) ctx.getSystemService(Context.AUDIO_SERVICE);
        initA2dp();
    }

    private void initA2dp() {
        BluetoothAdapter.getDefaultAdapter()
            .getProfileProxy(ctx, new BluetoothProfile.ServiceListener() {
                @Override public void onServiceConnected(int profile, BluetoothProfile proxy) {
                    if (profile == BluetoothProfile.A2DP) {
                        a2dpProxy = (BluetoothA2dp) proxy;
                        refreshConnectionState();
                    }
                }
                @Override public void onServiceDisconnected(int profile) {
                    if (profile == BluetoothProfile.A2DP) a2dpProxy = null;
                }
            }, BluetoothProfile.A2DP);
    }

    public boolean isBluetoothAudioReady() {
        return btConnected && a2dpProxy != null;
    }

    public void routeToBluetooth() {
        if (audioManager.isBluetoothA2dpOn()) return;
        audioManager.setBluetoothA2dpOn(true);
        audioManager.startBluetoothSco();
    }

    public void routeToWiredOrSpeaker() {
        audioManager.stopBluetoothSco();
        audioManager.setBluetoothA2dpOn(false);
        AudioDeviceInfo[] devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS);
        for (AudioDeviceInfo d : devices) {
            if (d.getType() == AudioDeviceInfo.TYPE_WIRED_HEADPHONES ||
                d.getType() == AudioDeviceInfo.TYPE_WIRED_HEADSET) {
                return;
            }
        }
    }

    private void refreshConnectionState() {
        if (a2dpProxy == null) return;
        try {
            java.lang.reflect.Method method = a2dpProxy.getClass().getMethod("getConnectedDevices");
            @SuppressWarnings("unchecked")
            List<BluetoothDevice> devices = (List<BluetoothDevice>) method.invoke(a2dpProxy);
            btConnected = devices != null && !devices.isEmpty();
        } catch (Exception e) {
            Log.e(TAG, "Reflection failed", e);
        }
    }

    public void onConnectionEvent(boolean connected) {
        this.btConnected = connected;
        if (!connected) routeToWiredOrSpeaker();
        else routeToBluetooth();
    }
}