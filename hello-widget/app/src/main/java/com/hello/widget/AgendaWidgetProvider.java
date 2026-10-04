package com.hello.widget;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.provider.CalendarContract;
import android.text.format.DateFormat;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

/** Big date on the left, the next few calendar events on the right. */
public class AgendaWidgetProvider extends CanvasWidget {

    private static final int MAX_EVENTS = 3;

    static final class Event {
        final String title; final long begin, end; final boolean allDay; final int color;
        Event(String title, long begin, long end, boolean allDay, int color) {
            this.title = title; this.begin = begin; this.end = end; this.allDay = allDay; this.color = color;
        }
    }

    static boolean hasPermission(Context c) {
        return c.checkSelfPermission(Manifest.permission.READ_CALENDAR) == PackageManager.PERMISSION_GRANTED;
    }

    @Override
    Intent clickIntent(Context c) {
        return hasPermission(c) ? CalendarWidgetProvider.openCalendar() : new Intent(c, MainActivity.class);
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        Draw.card(cv, w, h, 26, CalendarWidgetProvider.CARD);
        cv.translate((w - DESIGN_W) / 2, (h - DESIGN_H) / 2);
        CalendarWidgetProvider.drawDateBlock(cv);

        List<String[]> rows = new ArrayList<>();
        List<Integer> colors = new ArrayList<>();
        if (!hasPermission(c)) {
            rows.add(new String[]{"Allow calendar access", "Tap to set up"});
            colors.add(0xFF8E8E93);
        } else {
            for (Event e : upcoming(c)) {
                rows.add(new String[]{e.title, subtitle(c, e)});
                colors.add(e.color);
            }
            if (rows.isEmpty()) {
                rows.add(new String[]{"Nothing coming up", "Next 7 days are clear"});
                colors.add(0xFF30D158);
            }
        }

        float x0 = CalendarWidgetProvider.PANEL_X, maxW = DESIGN_W - 16 - x0 - 11;
        float block = 34, gap = 10, label = 20;
        float total = label + rows.size() * block + (rows.size() - 1) * gap;
        float y = (DESIGN_H - total) / 2;

        Paint lp = Draw.text(Draw.interSemibold, 10, CalendarWidgetProvider.GREY);
        lp.setLetterSpacing(0.08f);
        cv.drawText("UP NEXT", x0, y + 8, lp);
        y += label;

        Paint title = Draw.text(Draw.interSemibold, 13.5f, CalendarWidgetProvider.WHITE);
        Paint sub = Draw.text(Draw.interMedium, 11.5f, 0xFFA8A8AD);
        Paint bar = new Paint(Paint.ANTI_ALIAS_FLAG);
        for (int i = 0; i < rows.size(); i++) {
            bar.setColor(colors.get(i) | 0xFF000000);
            cv.drawRoundRect(new RectF(x0, y, x0 + 3, y + block), 1.5f, 1.5f, bar);
            cv.drawText(Draw.fit(rows.get(i)[0], title, maxW), x0 + 11, y + 13, title);
            cv.drawText(Draw.fit(rows.get(i)[1], sub, maxW), x0 + 11, y + 29, sub);
            y += block + gap;
        }
    }

    /** Next events in the coming week that haven't finished yet. */
    static List<Event> upcoming(Context c) {
        List<Event> out = new ArrayList<>();
        long now = System.currentTimeMillis();
        String[] proj = {CalendarContract.Instances.TITLE, CalendarContract.Instances.BEGIN,
                CalendarContract.Instances.END, CalendarContract.Instances.ALL_DAY,
                CalendarContract.Instances.DISPLAY_COLOR};
        android.net.Uri uri = CalendarContract.Instances.CONTENT_URI.buildUpon()
                .appendPath(String.valueOf(now - 86_400_000L))
                .appendPath(String.valueOf(now + 7 * 86_400_000L)).build();
        Calendar todayStart = startOfDay(now);

        try (Cursor cur = c.getContentResolver().query(uri, proj,
                CalendarContract.Instances.VISIBLE + "=1", null,
                CalendarContract.Instances.BEGIN + " ASC")) {
            while (cur != null && cur.moveToNext() && out.size() < MAX_EVENTS) {
                boolean allDay = cur.getInt(3) == 1;
                long begin = cur.getLong(1), end = cur.getLong(2);
                if (allDay) {
                    // All-day instances are stored as UTC midnights; move them to local midnights.
                    begin = utcDateToLocal(begin);
                    end = utcDateToLocal(end);
                    if (end <= todayStart.getTimeInMillis()) continue;
                } else if (end <= now) {
                    continue;
                }
                String title = cur.getString(0);
                out.add(new Event(title == null || title.isEmpty() ? "(No title)" : title,
                        begin, end, allDay, cur.getInt(4)));
            }
        } catch (SecurityException ignored) { }
        out.sort((a, b) -> Long.compare(a.begin, b.begin));
        return out;
    }

    private static Calendar startOfDay(long t) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(t);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c;
    }

    private static long utcDateToLocal(long utcMillis) {
        Calendar u = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        u.setTimeInMillis(utcMillis);
        Calendar l = Calendar.getInstance();
        l.clear();
        l.set(u.get(Calendar.YEAR), u.get(Calendar.MONTH), u.get(Calendar.DAY_OF_MONTH));
        return l.getTimeInMillis();
    }

    private static String subtitle(Context c, Event e) {
        java.text.DateFormat tf = DateFormat.getTimeFormat(c);
        long now = System.currentTimeMillis();
        String day = dayLabel(e.begin);
        if (e.allDay) return day.isEmpty() ? "All day" : day + " · All day";
        if (e.begin <= now) return "Now · until " + tf.format(e.end);
        if (day.isEmpty()) return tf.format(e.begin) + " – " + tf.format(e.end);
        return day + " · " + tf.format(e.begin);
    }

    /** "" for today, "Tomorrow", or e.g. "Thu 24". */
    private static String dayLabel(long t) {
        Calendar a = startOfDay(System.currentTimeMillis()), b = startOfDay(t);
        long diff = Math.round((b.getTimeInMillis() - a.getTimeInMillis()) / 86_400_000.0);
        if (diff <= 0) return "";
        if (diff == 1) return "Tomorrow";
        return new SimpleDateFormat("EEE d", Locale.getDefault()).format(b.getTime());
    }
}
