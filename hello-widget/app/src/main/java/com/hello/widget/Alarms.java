package com.hello.widget;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

/** The app's own alarms: storage, next-occurrence maths and scheduling via setAlarmClock. */
final class Alarms {

    static final long SNOOZE_MS = 5 * 60_000L;
    static final int SNOOZE_MAX = 3;

    static final class Alarm {
        int id, hour, minute;
        boolean on = true;
        /** Bit (DAY_OF_WEEK - 1) set = repeats that day; 0 = one-time. */
        int days;
        /** An occurrence (millis) to skip ("Turn off this time"), or 0. */
        long skip;

        JSONObject toJson() throws Exception {
            return new JSONObject().put("id", id).put("h", hour).put("m", minute)
                    .put("on", on).put("days", days).put("skip", skip);
        }

        static Alarm fromJson(JSONObject o) {
            Alarm a = new Alarm();
            a.id = o.optInt("id"); a.hour = o.optInt("h"); a.minute = o.optInt("m");
            a.on = o.optBoolean("on", true); a.days = o.optInt("days"); a.skip = o.optLong("skip");
            return a;
        }

        /** Next time this alarm would ring after {@code from}, honouring repeat days and a skip. */
        long next(long from) {
            Calendar c = Calendar.getInstance();
            c.setTimeInMillis(from);
            c.set(Calendar.HOUR_OF_DAY, hour);
            c.set(Calendar.MINUTE, minute);
            c.set(Calendar.SECOND, 0);
            c.set(Calendar.MILLISECOND, 0);
            for (int i = 0; i < 15; i++) {
                long t = c.getTimeInMillis();
                boolean dayOk = days == 0 || (days & (1 << (c.get(Calendar.DAY_OF_WEEK) - 1))) != 0;
                if (t > from && dayOk && t != skip) return t;
                c.add(Calendar.DAY_OF_MONTH, 1);
            }
            return Long.MAX_VALUE;
        }

        boolean skipping(long now) {
            return skip > now;
        }
    }

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("alarms", Context.MODE_PRIVATE);
    }

    static List<Alarm> load(Context c) {
        List<Alarm> out = new ArrayList<>();
        try {
            JSONArray a = new JSONArray(prefs(c).getString("list", "[]"));
            for (int i = 0; i < a.length(); i++) out.add(Alarm.fromJson(a.getJSONObject(i)));
        } catch (Exception ignored) { }
        out.sort((x, y) -> Integer.compare(x.hour * 60 + x.minute, y.hour * 60 + y.minute));
        return out;
    }

    static void save(Context c, List<Alarm> list) {
        JSONArray a = new JSONArray();
        try {
            for (Alarm al : list) a.put(al.toJson());
        } catch (Exception ignored) { }
        prefs(c).edit().putString("list", a.toString()).apply();
        changed(c);
    }

    static Alarm find(List<Alarm> list, int id) {
        for (Alarm a : list) if (a.id == id) return a;
        return null;
    }

    static Alarm add(Context c, int hour, int minute) {
        List<Alarm> list = load(c);
        Alarm a = new Alarm();
        a.id = prefs(c).getInt("next_id", 1);
        a.hour = hour;
        a.minute = minute;
        prefs(c).edit().putInt("next_id", a.id + 1).putInt("featured", a.id).apply();
        list.add(a);
        save(c, list);
        return a;
    }

    static boolean vibrate(Context c) { return prefs(c).getBoolean("vibrate", true); }
    static boolean snooze(Context c) { return prefs(c).getBoolean("snooze", true); }

    static int enabledCount(Context c) {
        int n = 0;
        for (Alarm a : load(c)) if (a.on) n++;
        return n;
    }

    /**
     * The alarm the widget is about: one just switched off from the widget (so it can be switched
     * back on), otherwise the next one to ring, otherwise the soonest disabled one.
     */
    static Alarm featured(Context c) {
        List<Alarm> list = load(c);
        if (list.isEmpty()) return null;
        long now = System.currentTimeMillis();
        Alarm pinned = find(list, prefs(c).getInt("featured", -1));
        if (pinned != null && !pinned.on) return pinned;
        Alarm best = null;
        for (Alarm a : list) if (a.on && (best == null || a.next(now) < best.next(now))) best = a;
        if (best != null) return best;
        for (Alarm a : list) if (best == null || a.next(now) < best.next(now)) best = a;
        return best;
    }

    // ---------------------------------------------------------------- scheduling

    /** Re-arms the single system alarm for whichever alarm (or snooze) rings next. */
    static void schedule(Context c) {
        AlarmManager am = c.getSystemService(AlarmManager.class);
        long now = System.currentTimeMillis();
        long best = Long.MAX_VALUE;
        int bestId = -1;
        boolean bestSnooze = false;
        for (Alarm a : load(c)) {
            if (!a.on) continue;
            long t = a.next(now);
            if (t < best) { best = t; bestId = a.id; bestSnooze = false; }
        }
        long snoozeAt = prefs(c).getLong("snooze_at", 0);
        if (snoozeAt > now && snoozeAt < best) {
            best = snoozeAt;
            bestId = prefs(c).getInt("snooze_id", -1);
            bestSnooze = true;
        }
        PendingIntent fire = firePi(c, bestId, bestSnooze);
        if (best == Long.MAX_VALUE) {
            am.cancel(firePi(c, -1, false));
            return;
        }
        PendingIntent show = PendingIntent.getActivity(c, 71, new Intent(c, AlarmsActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        try {
            am.setAlarmClock(new AlarmManager.AlarmClockInfo(best, show), fire);
        } catch (SecurityException e) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, best, fire);
        }
    }

    private static PendingIntent firePi(Context c, int id, boolean snooze) {
        Intent i = new Intent(c, AlarmReceiver.class).setAction(AlarmReceiver.ACTION_FIRE)
                .putExtra(AlarmReceiver.EXTRA_ID, id).putExtra(AlarmReceiver.EXTRA_SNOOZE, snooze);
        // One request code: there is only ever one pending alarm, so updating replaces it.
        return PendingIntent.getBroadcast(c, 70, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    /** After any change: re-arm and redraw the widget. */
    static void changed(Context c) {
        schedule(c);
        CanvasWidget.updateAll(c, AlarmWidgetProvider.class);
    }
}
