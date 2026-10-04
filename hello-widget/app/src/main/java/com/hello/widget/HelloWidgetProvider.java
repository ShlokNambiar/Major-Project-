package com.hello.widget;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.AlarmClock;
import android.text.format.DateFormat;
import android.widget.RemoteViews;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class HelloWidgetProvider extends AppWidgetProvider {

    public static final String ACTION_REFRESH = "com.hello.widget.REFRESH";
    public static final String ACTION_TICK = "com.hello.widget.TICK";
    private static final long WEATHER_MAX_AGE = 30 * 60 * 1000L;

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        render(context, manager, ids);
        scheduleTick(context);
        refreshWeatherAsync(context);
    }

    @Override
    public void onEnabled(Context context) {
        scheduleTick(context);
    }

    @Override
    public void onDisabled(Context context) {
        alarms(context).cancel(tickIntent(context));
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        String action = intent.getAction();
        if (action == null) return;
        switch (action) {
            case ACTION_REFRESH:
                refreshWeatherAsync(context);
                break;
            case ACTION_TICK:
            case Intent.ACTION_TIME_CHANGED:
            case Intent.ACTION_TIMEZONE_CHANGED:
            case Intent.ACTION_LOCALE_CHANGED:
            case Intent.ACTION_BOOT_COMPLETED:
            case Intent.ACTION_MY_PACKAGE_REPLACED:
                if (!hasWidgets(context)) return;
                updateAll(context);
                scheduleTick(context);
                Weather.Cached w = Weather.cached(context);
                if (w == null || System.currentTimeMillis() - w.time > WEATHER_MAX_AGE) {
                    refreshWeatherAsync(context);
                }
                break;
        }
    }

    // ---- per-minute tick: time text is a bitmap, so it has to be redrawn on each minute ----

    private static AlarmManager alarms(Context c) {
        return c.getSystemService(AlarmManager.class);
    }

    private static PendingIntent tickIntent(Context c) {
        Intent i = new Intent(c, HelloWidgetProvider.class).setAction(ACTION_TICK);
        return PendingIntent.getBroadcast(c, 10, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static void scheduleTick(Context c) {
        long next = (System.currentTimeMillis() / 60000 + 1) * 60000;
        AlarmManager am = alarms(c);
        PendingIntent pi = tickIntent(c);
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) {
            am.setExactAndAllowWhileIdle(AlarmManager.RTC, next, pi);
        } else {
            am.setWindow(AlarmManager.RTC, next, 5000, pi);
        }
    }

    private static boolean hasWidgets(Context c) {
        return AppWidgetManager.getInstance(c)
                .getAppWidgetIds(new ComponentName(c, HelloWidgetProvider.class)).length > 0;
    }

    private void refreshWeatherAsync(Context context) {
        final PendingResult pending = goAsync();
        final Context app = context.getApplicationContext();
        new Thread(() -> {
            try {
                Weather.fetchAndStore(app);
            } catch (Exception ignored) {
                // keep showing the last cached reading
            } finally {
                updateAll(app);
                pending.finish();
            }
        }).start();
    }

    /** Re-draws every placed instance of the widget. */
    public static void updateAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        int[] ids = manager.getAppWidgetIds(new ComponentName(context, HelloWidgetProvider.class));
        render(context, manager, ids);
    }

    static void render(Context context, AppWidgetManager manager, int[] ids) {
        if (ids.length == 0) return;
        RemoteViews views = buildViews(context);
        for (int id : ids) manager.updateAppWidget(id, views);
    }

    static RemoteViews buildViews(Context context) {
        RemoteViews v = new RemoteViews(context.getPackageName(), R.layout.widget_hello);
        WidgetArt art = new WidgetArt(context);
        Date now = new Date();
        Locale locale = Locale.getDefault();
        String timePattern = DateFormat.is24HourFormat(context) ? "HH:mm" : "h:mm a";

        v.setImageViewBitmap(R.id.date_pill, art.datePill(new SimpleDateFormat("dd", locale).format(now)));
        v.setImageViewBitmap(R.id.day, art.label(new SimpleDateFormat("EEE", locale).format(now)));
        v.setImageViewBitmap(R.id.its, art.label("It's"));
        v.setImageViewBitmap(R.id.time,
                art.label(new SimpleDateFormat(timePattern, locale).format(now).toUpperCase(locale) + " ,"));

        Weather.Cached w = Weather.cached(context);
        v.setImageViewBitmap(R.id.weather_pill,
                art.weatherPill(w == null ? "--°" : w.temp + "°", w == null ? "⛅" : w.icon));

        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;

        // hello -> app settings
        Intent open = new Intent(context, MainActivity.class);
        v.setOnClickPendingIntent(R.id.hello, PendingIntent.getActivity(context, 1, open, flags));

        // date pill / day -> calendar on today
        Uri today = Uri.parse("content://com.android.calendar/time/" + System.currentTimeMillis());
        Intent cal = new Intent(Intent.ACTION_VIEW, today).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent calPi = PendingIntent.getActivity(context, 2, cal, flags);
        v.setOnClickPendingIntent(R.id.date_pill, calPi);
        v.setOnClickPendingIntent(R.id.day, calPi);

        // clock / time -> alarms
        Intent alarmsIntent = new Intent(AlarmClock.ACTION_SHOW_ALARMS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent alarmPi = PendingIntent.getActivity(context, 3, alarmsIntent, flags);
        v.setOnClickPendingIntent(R.id.analog, alarmPi);
        v.setOnClickPendingIntent(R.id.time, alarmPi);

        // weather pill -> refresh now
        Intent refresh = new Intent(context, HelloWidgetProvider.class).setAction(ACTION_REFRESH);
        v.setOnClickPendingIntent(R.id.weather_pill, PendingIntent.getBroadcast(context, 4, refresh, flags));
        return v;
    }
}
