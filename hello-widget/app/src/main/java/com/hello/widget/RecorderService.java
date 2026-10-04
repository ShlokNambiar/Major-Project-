package com.hello.widget;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.provider.MediaStore;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Records audio in the foreground and keeps the recorder widget's waveform and timer live. */
public class RecorderService extends Service {

    static final String ACTION_START = "start", ACTION_PAUSE = "pause", ACTION_RESUME = "resume", ACTION_STOP = "stop";
    static final String FOLDER = "HelloWidget";
    private static final String CHANNEL = "recorder";
    private static final int NOTIF_ID = 42;

    enum State { IDLE, RECORDING, PAUSED }

    // Read by the widget; only touched on the main thread.
    static volatile State state = State.IDLE;
    static final int BARS = 64;
    static final float[] levels = new float[BARS];
    static int levelHead = 0;
    private static long startedAt, pausedTotal, pausedAt;

    private MediaRecorder recorder;
    private Uri pendingUri;
    private ParcelFileDescriptor pfd;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastWidgetUpdate;

    static long elapsedMs() {
        if (state == State.IDLE) return 0;
        long end = state == State.PAUSED ? pausedAt : System.currentTimeMillis();
        return end - startedAt - pausedTotal;
    }

    static Intent intent(Context c, String action) {
        return new Intent(c, RecorderService.class).setAction(action);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        if (ACTION_START.equals(action) && state == State.IDLE) start();
        else if (ACTION_PAUSE.equals(action) && state == State.RECORDING) pause();
        else if (ACTION_RESUME.equals(action) && state == State.PAUSED) resume();
        else if (ACTION_STOP.equals(action)) stop();
        else if (state == State.IDLE) stopSelf();
        return START_NOT_STICKY;
    }

    private void start() {
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIF_ID, notification(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        } else {
            startForeground(NOTIF_ID, notification());
        }
        try {
            recorder = Build.VERSION.SDK_INT >= 31 ? new MediaRecorder(this) : new MediaRecorder();
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioSamplingRate(44100);
            recorder.setAudioEncodingBitRate(128000);
            openOutput(recorder);
            recorder.prepare();
            recorder.start();
        } catch (Exception e) {
            cleanup(false);
            return;
        }
        java.util.Arrays.fill(levels, 0);
        levelHead = 0;
        startedAt = System.currentTimeMillis();
        pausedTotal = 0;
        state = State.RECORDING;
        handler.post(sampler);
        refresh();
    }

    private void openOutput(MediaRecorder r) throws Exception {
        String name = "Recording " + new SimpleDateFormat("yyyy-MM-dd HH-mm-ss", Locale.US).format(new Date());
        if (Build.VERSION.SDK_INT >= 29) {
            ContentValues v = new ContentValues();
            v.put(MediaStore.Audio.Media.DISPLAY_NAME, name + ".m4a");
            v.put(MediaStore.Audio.Media.MIME_TYPE, "audio/mp4");
            v.put(MediaStore.Audio.Media.RELATIVE_PATH,
                    (Build.VERSION.SDK_INT >= 31 ? Environment.DIRECTORY_RECORDINGS : Environment.DIRECTORY_MUSIC) + "/" + FOLDER);
            v.put(MediaStore.Audio.Media.IS_PENDING, 1);
            pendingUri = getContentResolver().insert(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, v);
            if (pendingUri == null) throw new IllegalStateException("No media store");
            pfd = getContentResolver().openFileDescriptor(pendingUri, "w");
            r.setOutputFile(pfd.getFileDescriptor());
        } else {
            File dir = new File(getExternalFilesDir(Environment.DIRECTORY_MUSIC), FOLDER);
            //noinspection ResultOfMethodCallIgnored
            dir.mkdirs();
            r.setOutputFile(new File(dir, name + ".m4a").getAbsolutePath());
        }
    }

    private void pause() {
        try { recorder.pause(); } catch (Exception ignored) { }
        pausedAt = System.currentTimeMillis();
        state = State.PAUSED;
        refresh();
    }

    private void resume() {
        try { recorder.resume(); } catch (Exception ignored) { }
        pausedTotal += System.currentTimeMillis() - pausedAt;
        state = State.RECORDING;
        refresh();
    }

    private void stop() {
        boolean ok = true;
        if (recorder != null) {
            try { recorder.stop(); } catch (Exception e) { ok = false; }
        }
        cleanup(ok);
    }

    private void cleanup(boolean keep) {
        handler.removeCallbacks(sampler);
        if (recorder != null) { recorder.release(); recorder = null; }
        try { if (pfd != null) pfd.close(); } catch (Exception ignored) { }
        pfd = null;
        if (pendingUri != null) {
            if (keep) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.Audio.Media.IS_PENDING, 0);
                getContentResolver().update(pendingUri, v, null, null);
            } else {
                getContentResolver().delete(pendingUri, null, null);
            }
            pendingUri = null;
        }
        state = State.IDLE;
        CanvasWidget.updateAll(this, RecorderWidgetProvider.class);
        stopForeground(true);
        stopSelf();
    }

    /** Samples the mic level ~12×/s into the waveform ring buffer; redraws the widget twice a second. */
    private final Runnable sampler = new Runnable() {
        @Override
        public void run() {
            if (recorder == null) return;
            if (state == State.RECORDING) {
                int amp = 0;
                try { amp = recorder.getMaxAmplitude(); } catch (Exception ignored) { }
                float level = amp <= 0 ? 0.03f : (float) Math.max(0.03, Math.min(1, Math.log10(amp) / 4.5 - 0.15));
                levels[levelHead] = level;
                levelHead = (levelHead + 1) % BARS;
            }
            long now = System.currentTimeMillis();
            if (now - lastWidgetUpdate >= 500) {
                lastWidgetUpdate = now;
                CanvasWidget.updateAll(RecorderService.this, RecorderWidgetProvider.class);
            }
            handler.postDelayed(this, 80);
        }
    };

    private void refresh() {
        getSystemService(NotificationManager.class).notify(NOTIF_ID, notification());
        CanvasWidget.updateAll(this, RecorderWidgetProvider.class);
    }

    private Notification notification() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Recorder", NotificationManager.IMPORTANCE_LOW));
        }
        boolean paused = state == State.PAUSED;
        Notification.Builder b = new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentTitle(paused ? "Recording paused" : "Recording…")
                .setOngoing(true)
                .setContentIntent(CanvasWidget.activityPi(this, 50, new Intent(this, RecordingsActivity.class)))
                .addAction(new Notification.Action.Builder(null, paused ? "Resume" : "Pause",
                        CanvasWidget.servicePi(this, 51, intent(this, paused ? ACTION_RESUME : ACTION_PAUSE))).build())
                .addAction(new Notification.Action.Builder(null, "Stop & save",
                        CanvasWidget.servicePi(this, 52, intent(this, ACTION_STOP))).build());
        if (!paused) {
            b.setUsesChronometer(true).setWhen(System.currentTimeMillis() - elapsedMs());
        }
        return b.build();
    }

    @Override
    public void onDestroy() {
        if (recorder != null) stop();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
