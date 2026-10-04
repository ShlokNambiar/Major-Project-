package com.hello.widget;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;

/**
 * Invisible step between the widget's record button and the service: a visible activity may
 * start a microphone foreground service and ask for the mic permission the first time.
 */
public class RecordActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startAndFinish();
        } else {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) startAndFinish();
        else finish();
    }

    private void startAndFinish() {
        startForegroundService(RecorderService.intent(this, RecorderService.ACTION_START));
        finish();
        overridePendingTransition(0, 0);
    }
}
