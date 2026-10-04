package com.hello.widget;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;

import java.util.List;

/** Rings, snoozes and dismisses alarms, and handles the alarm widget's toggles. */
public class AlarmReceiver extends BroadcastReceiver {

    static final String ACTION_FIRE = "com.hello.widget.alarm.FIRE";
    static final String ACTION_SNOOZE = "com.hello.widget.alarm.SNOOZE";
    static final String ACTION_DISMISS = "com.hello.widget.alarm.DISMISS";
    static final String ACTION_TOGGLE = "com.hello.widget.alarm.TOGGLE";
    static final String ACTION_SKIP = "com.hello.widget.alarm.SKIP";
    static final String ACTION_TOGGLE_VIBRATE = "com.hello.widget.alarm.VIBRATE";
    static final String ACTION_TOGGLE_SNOOZE = "com.hello.widget.alarm.SNOOZE_SETTING";
    static final String EXTRA_ID = "id", EXTRA_SNOOZE = "snooze";
    static final int NOTIF_ID = 77;

    @Override
    public void onReceive(Context c, Intent intent) {
        String action = intent.getAction();
        if (action == null) return;
        int id = intent.getIntExtra(EXTRA_ID, -1);
        List<Alarms.Alarm> list = Alarms.load(c);
        switch (action) {
            case ACTION_FIRE: {
                Alarms.Alarm a = Alarms.find(list, id);
                boolean snoozed = intent.getBooleanExtra(EXTRA_SNOOZE, false);
                if (!snoozed) {
                    Alarms.prefs(c).edit().putInt("snooze_count", 0).remove("snooze_at").apply();
                    if (a != null && a.days == 0) a.on = false; // one-time alarm is done
                    if (a != null) a.skip = 0;
                } else {
                    Alarms.prefs(c).edit().remove("snooze_at").apply();
                }
                Alarms.save(c, list);
                if (a != null || snoozed) ring(c, a == null ? id : a.id);
                break;
            }
            case ACTION_SNOOZE: {
                int count = Alarms.prefs(c).getInt("snooze_count", 0) + 1;
                c.getSystemService(NotificationManager.class).cancel(NOTIF_ID);
                if (count <= Alarms.SNOOZE_MAX) {
                    Alarms.prefs(c).edit().putInt("snooze_count", count).putInt("snooze_id", id)
                            .putLong("snooze_at", System.currentTimeMillis() + Alarms.SNOOZE_MS).apply();
                }
                Alarms.changed(c);
                break;
            }
            case ACTION_DISMISS:
                c.getSystemService(NotificationManager.class).cancel(NOTIF_ID);
                Alarms.prefs(c).edit().putInt("snooze_count", 0).remove("snooze_at").apply();
                Alarms.changed(c);
                break;
            case ACTION_TOGGLE: {
                Alarms.Alarm a = Alarms.featured(c);
                if (a == null) break;
                a = Alarms.find(list, a.id);
                a.on = !a.on;
                a.skip = 0;
                Alarms.prefs(c).edit().putInt("featured", a.id).apply();
                Alarms.save(c, list);
                break;
            }
            case ACTION_SKIP: {
                Alarms.Alarm f = Alarms.featured(c);
                if (f == null) break;
                Alarms.Alarm a = Alarms.find(list, f.id);
                long now = System.currentTimeMillis();
                if (a.skipping(now)) a.skip = 0;                    // undo
                else if (a.on) a.skip = a.next(now);                 // skip just the next one
                Alarms.save(c, list);
                break;
            }
            case ACTION_TOGGLE_VIBRATE:
                Alarms.prefs(c).edit().putBoolean("vibrate", !Alarms.vibrate(c)).apply();
                Alarms.changed(c);
                break;
            case ACTION_TOGGLE_SNOOZE:
                Alarms.prefs(c).edit().putBoolean("snooze", !Alarms.snooze(c)).apply();
                Alarms.changed(c);
                break;
        }
    }

    /** Insistent alarm notification (loops the alarm sound) with a full-screen ringing screen. */
    static void ring(Context c, int alarmId) {
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        boolean vibrate = Alarms.vibrate(c);
        String channel = vibrate ? "alarm_vibrate" : "alarm_quiet";
        if (nm.getNotificationChannel(channel) == null) {
            NotificationChannel ch = new NotificationChannel(channel, vibrate ? "Alarms" : "Alarms (no vibration)",
                    NotificationManager.IMPORTANCE_HIGH);
            Uri sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (sound == null) sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            ch.setSound(sound, new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build());
            ch.enableVibration(vibrate);
            if (vibrate) ch.setVibrationPattern(new long[]{0, 600, 400, 600, 400, 600});
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(ch);
        }

        Intent full = new Intent(c, AlarmRingActivity.class).putExtra(EXTRA_ID, alarmId)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_NO_USER_ACTION);
        PendingIntent fullPi = PendingIntent.getActivity(c, 72, full,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder b = new Notification.Builder(c, channel)
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle("Alarm")
                .setContentText(android.text.format.DateFormat.getTimeFormat(c).format(System.currentTimeMillis()))
                .setCategory(Notification.CATEGORY_ALARM)
                .setOngoing(true)
                .setTimeoutAfter(10 * 60_000L)
                .setFullScreenIntent(fullPi, true)
                .setContentIntent(fullPi)
                .setVisibility(Notification.VISIBILITY_PUBLIC);
        if (Alarms.snooze(c) && Alarms.prefs(c).getInt("snooze_count", 0) < Alarms.SNOOZE_MAX) {
            b.addAction(new Notification.Action.Builder(null, "Snooze 5 min", action(c, ACTION_SNOOZE, alarmId, 73)).build());
        }
        b.addAction(new Notification.Action.Builder(null, "Stop", action(c, ACTION_DISMISS, alarmId, 74)).build());
        Notification n = b.build();
        n.flags |= Notification.FLAG_INSISTENT;
        nm.notify(NOTIF_ID, n);
    }

    static PendingIntent action(Context c, String action, int id, int code) {
        Intent i = new Intent(c, AlarmReceiver.class).setAction(action).putExtra(EXTRA_ID, id);
        return PendingIntent.getBroadcast(c, code, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }
}
