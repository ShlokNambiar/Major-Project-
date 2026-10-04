package com.hello.widget;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import java.util.Calendar;

/**
 * Wakes on every minute while any widget is placed. Clock widgets redraw each minute, calendar
 * widgets every 5 minutes (which also covers midnight), and stale weather is re-fetched.
 */
public class TickReceiver extends BroadcastReceiver {

    static final String ACTION_TICK = "com.hello.widget.TICK";
    private static final long WEATHER_MAX_AGE = 30 * 60 * 1000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        boolean tick = ACTION_TICK.equals(intent.getAction());
        if (!tick) Alarms.schedule(context);   // reboot / clock change: re-arm alarms regardless of widgets
        if (!anyWidgets(context)) return;
        int minute = Calendar.getInstance().get(Calendar.MINUTE);

        HelloWidgetProvider.updateAll(context);
        CanvasWidget.updateAll(context, VoidWidgetProvider.class);
        if (!tick || minute % 5 == 0) {
            CanvasWidget.updateAll(context, CalendarWidgetProvider.class);
            CanvasWidget.updateAll(context, AgendaWidgetProvider.class);
            CanvasWidget.updateAll(context, SkyWidgetProvider.class);
            CanvasWidget.updateAll(context, AlarmWidgetProvider.class);
        }
        schedule(context);

        Weather.Cached w = Weather.cached(context);
        if (w == null || System.currentTimeMillis() - w.time > WEATHER_MAX_AGE) {
            refreshWeatherAsync(context, goAsync());
        }
    }

    /** Fetch weather off the main thread, then redraw everything that shows it. */
    static void refreshWeatherAsync(Context context, PendingResult pending) {
        final Context app = context.getApplicationContext();
        new Thread(() -> {
            try {
                Weather.fetchAndStore(app);
            } catch (Exception ignored) {
                // keep showing the last cached reading
            } finally {
                HelloWidgetProvider.updateAll(app);
                CanvasWidget.updateAll(app, VoidWidgetProvider.class);
                CanvasWidget.updateAll(app, SkyWidgetProvider.class);
                if (pending != null) pending.finish();
            }
        }).start();
    }

    static void schedule(Context c) {
        long next = (System.currentTimeMillis() / 60000 + 1) * 60000;
        AlarmManager am = c.getSystemService(AlarmManager.class);
        PendingIntent pi = tickIntent(c);
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC, next, pi);
        } else {
            am.setWindow(AlarmManager.RTC, next, 5000, pi);
        }
    }

    /** Called when a provider's last widget is removed. */
    static void cancelIfUnused(Context c) {
        if (!anyWidgets(c)) c.getSystemService(AlarmManager.class).cancel(tickIntent(c));
    }

    private static PendingIntent tickIntent(Context c) {
        Intent i = new Intent(c, TickReceiver.class).setAction(ACTION_TICK);
        return PendingIntent.getBroadcast(c, 10, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static boolean anyWidgets(Context c) {
        AppWidgetManager m = AppWidgetManager.getInstance(c);
        for (Class<?> cls : new Class<?>[]{HelloWidgetProvider.class, VoidWidgetProvider.class,
                CalendarWidgetProvider.class, AgendaWidgetProvider.class, SkyWidgetProvider.class,
                AlarmWidgetProvider.class}) {
            if (m.getAppWidgetIds(new ComponentName(c, cls)).length > 0) return true;
        }
        return false;
    }
}
