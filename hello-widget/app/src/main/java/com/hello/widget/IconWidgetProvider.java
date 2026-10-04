package com.hello.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.TypedValue;
import android.view.View;
import android.widget.RemoteViews;

/** A 1×1 widget that looks like an app icon (custom artwork + label) and launches the real app. */
public class IconWidgetProvider extends AppWidgetProvider {

    static final String ACTION_BIND = "com.hello.widget.BIND_ICON";
    static final String EXTRA_ICON = "icon";

    /** Icon sizes offered in the app (dp); default matches typical launcher icons. */
    static final int[] SIZES = {48, 52, 56, 60};
    static final int DEFAULT_SIZE = 52;

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("icon_widgets", Context.MODE_PRIVATE);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (ACTION_BIND.equals(intent.getAction())) {
            // Pinned from inside the app: remember which icon this new widget shows.
            int id = intent.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, AppWidgetManager.INVALID_APPWIDGET_ID);
            if (id != AppWidgetManager.INVALID_APPWIDGET_ID) {
                prefs(context).edit().putString("w" + id, intent.getStringExtra(EXTRA_ICON)).apply();
                AppWidgetManager.getInstance(context).updateAppWidget(id, build(context, id));
            }
            return;
        }
        super.onReceive(context, intent);
    }

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) manager.updateAppWidget(id, build(context, id));
    }

    @Override
    public void onDeleted(Context context, int[] ids) {
        SharedPreferences.Editor e = prefs(context).edit();
        for (int id : ids) e.remove("w" + id);
        e.apply();
    }

    static RemoteViews build(Context c, int id) {
        Icons.AppIcon icon = Icons.byKey(prefs(c).getString("w" + id, Icons.ALL[0].key));
        RemoteViews v = new RemoteViews(c.getPackageName(), R.layout.widget_icon);
        v.setImageViewResource(R.id.icon, icon.rounded);
        v.setTextViewText(R.id.label, icon.label);
        SharedPreferences p = prefs(c);
        v.setViewVisibility(R.id.label, p.getBoolean("show_label", false) ? View.VISIBLE : View.GONE);
        if (Build.VERSION.SDK_INT >= 31) {
            float size = p.getInt("size", DEFAULT_SIZE);
            v.setViewLayoutWidth(R.id.icon, size, TypedValue.COMPLEX_UNIT_DIP);
            v.setViewLayoutHeight(R.id.icon, size, TypedValue.COMPLEX_UNIT_DIP);
        }
        Intent launch = new Intent(c, LaunchActivity.class)
                .putExtra(LaunchActivity.EXTRA_PKG, icon.pkg)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        v.setOnClickPendingIntent(R.id.icon_root, PendingIntent.getActivity(c, id, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
        return v;
    }

    /** Re-draws every icon widget, e.g. after the label or size setting changes. */
    static void updateAll(Context c) {
        AppWidgetManager m = AppWidgetManager.getInstance(c);
        for (int id : m.getAppWidgetIds(new ComponentName(c, IconWidgetProvider.class))) {
            m.updateAppWidget(id, build(c, id));
        }
    }

    /** Callback for requestPinAppWidget; must be mutable so the system can add the new widget id. */
    static PendingIntent bindCallback(Context c, Icons.AppIcon icon) {
        Intent i = new Intent(c, IconWidgetProvider.class).setAction(ACTION_BIND).putExtra(EXTRA_ICON, icon.key);
        return PendingIntent.getBroadcast(c, icon.key.hashCode(), i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE);
    }
}
