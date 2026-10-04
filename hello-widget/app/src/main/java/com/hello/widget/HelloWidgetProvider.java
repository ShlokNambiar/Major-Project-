package com.hello.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.provider.AlarmClock;
import android.widget.RemoteViews;

public class HelloWidgetProvider extends AppWidgetProvider {

    public static final String ACTION_REFRESH = "com.hello.widget.REFRESH";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        render(context, manager, ids);
        refreshWeatherAsync(context);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            refreshWeatherAsync(context);
        }
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
        for (int id : ids) {
            manager.updateAppWidget(id, buildViews(context));
        }
    }

    static RemoteViews buildViews(Context context) {
        RemoteViews v = new RemoteViews(context.getPackageName(), R.layout.widget_hello);

        Weather.Cached w = Weather.cached(context);
        v.setTextViewText(R.id.temp, w == null ? "--°" : w.temp + "°");
        v.setTextViewText(R.id.weather_icon, w == null ? "⛅" : w.icon);

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
        Intent alarms = new Intent(AlarmClock.ACTION_SHOW_ALARMS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent alarmPi = PendingIntent.getActivity(context, 3, alarms, flags);
        v.setOnClickPendingIntent(R.id.analog, alarmPi);
        v.setOnClickPendingIntent(R.id.time, alarmPi);

        // weather pill -> refresh now
        Intent refresh = new Intent(context, HelloWidgetProvider.class).setAction(ACTION_REFRESH);
        v.setOnClickPendingIntent(R.id.weather_pill, PendingIntent.getBroadcast(context, 4, refresh, flags));
        return v;
    }
}
