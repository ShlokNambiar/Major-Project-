package com.hello.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.os.Bundle;
import android.widget.RemoteViews;

/**
 * A widget drawn entirely into one bitmap sized to the widget's real bounds. Launchers ignore
 * custom fonts in widget layouts, so this is the only way to get the exact typography.
 */
public abstract class CanvasWidget extends AppWidgetProvider {

    /** Design box in dp; content is laid out in these units and scaled to fit the widget. */
    static final float DESIGN_W = 340, DESIGN_H = 168;
    private static final int MAX_PIXELS = 1_600_000;

    /** Draw the widget. The canvas is already scaled so 1 unit = 1 design dp; w/h are in units. */
    abstract void draw(Context c, Canvas canvas, float w, float h);

    /** Where a tap on the widget goes. */
    abstract Intent clickIntent(Context c);

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) manager.updateAppWidget(id, build(context, manager, id));
        TickReceiver.schedule(context);
    }

    @Override
    public void onAppWidgetOptionsChanged(Context context, AppWidgetManager manager, int id, Bundle options) {
        manager.updateAppWidget(id, build(context, manager, id));
    }

    @Override
    public void onDisabled(Context context) {
        TickReceiver.cancelIfUnused(context);
    }

    static void updateAll(Context context, Class<? extends CanvasWidget> cls) {
        AppWidgetManager m = AppWidgetManager.getInstance(context);
        int[] ids = m.getAppWidgetIds(new ComponentName(context, cls));
        if (ids.length == 0) return;
        try {
            CanvasWidget w = cls.getDeclaredConstructor().newInstance();
            for (int id : ids) m.updateAppWidget(id, w.build(context, m, id));
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException(e);
        }
    }

    RemoteViews build(Context c, AppWidgetManager m, int id) {
        Bundle o = m.getAppWidgetOptions(id);
        boolean landscape = c.getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE;
        int wDp = o.getInt(landscape ? AppWidgetManager.OPTION_APPWIDGET_MAX_WIDTH : AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH);
        int hDp = o.getInt(landscape ? AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT : AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT);
        if (wDp <= 0 || hDp <= 0) { wDp = (int) DESIGN_W; hDp = (int) DESIGN_H; }

        RemoteViews v = new RemoteViews(c.getPackageName(), R.layout.widget_canvas);
        v.setImageViewBitmap(R.id.canvas, render(c, wDp, hDp));
        Intent click = clickIntent(c);
        if (click != null) {
            v.setOnClickPendingIntent(R.id.canvas, PendingIntent.getActivity(c, getClass().hashCode(), click,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
        }
        return v;
    }

    /** Renders at the given size in dp (also used for the in-app preview). */
    Bitmap render(Context c, int wDp, int hDp) {
        float density = c.getResources().getDisplayMetrics().density;
        float px = density;
        if (wDp * hDp * px * px > MAX_PIXELS) px = (float) Math.sqrt(MAX_PIXELS / (double) (wDp * hDp));
        Bitmap b = Bitmap.createBitmap(Math.round(wDp * px), Math.round(hDp * px), Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(b);

        // Fit the design box inside the widget, keeping proportions; the card fills the full widget.
        float s = Math.min(wDp / DESIGN_W, hDp / DESIGN_H) * px;
        float w = b.getWidth() / s, h = b.getHeight() / s;
        canvas.scale(s, s);
        draw(c, canvas, w, h);
        return b;
    }
}
