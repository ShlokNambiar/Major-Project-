package com.hello.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.provider.AlarmClock;
import android.text.format.DateFormat;
import android.widget.RemoteViews;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class HelloWidgetProvider extends AppWidgetProvider {

    public static final String ACTION_REFRESH = "com.hello.widget.REFRESH";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        render(context, manager, ids);
        TickReceiver.schedule(context);
        TickReceiver.refreshWeatherAsync(context, goAsync());
    }

    @Override
    public void onDisabled(Context context) {
        TickReceiver.cancelIfUnused(context);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            TickReceiver.refreshWeatherAsync(context, goAsync());
        }
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
