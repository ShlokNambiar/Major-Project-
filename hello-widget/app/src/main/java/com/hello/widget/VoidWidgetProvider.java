package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.provider.AlarmClock;
import android.text.format.DateFormat;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import java.util.Map;

/** Pixel clock + 7-day strip (3 past days, today with live weather, 3 days of forecast). */
public class VoidWidgetProvider extends CanvasWidget {

    private static final int WHITE = 0xFFFFFFFF, RED = 0xFFFF453A;

    @Override
    Intent clickIntent(Context c) {
        return new Intent(AlarmClock.ACTION_SHOW_ALARMS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        Draw.card(cv, w, h, 26, 0xC21C1C1E);
        cv.translate((w - DESIGN_W) / 2, (h - DESIGN_H) / 2);

        Date now = new Date();
        boolean h24 = DateFormat.is24HourFormat(c);

        // 06:21 PM
        String time = new SimpleDateFormat(h24 ? "HH:mm" : "hh:mm", Locale.US).format(now);
        Paint tp = Draw.pixel(34, WHITE, 1.1f);
        cv.drawText(time, 16, 40, tp);
        if (!h24) {
            String ampm = new SimpleDateFormat("a", Locale.US).format(now).toUpperCase(Locale.US);
            cv.drawText(ampm, 16 + tp.measureText(time) + 7, 38, Draw.pixel(13, RED, 0.35f));
        }

        // Day tiles
        String unit = Weather.fahrenheit(c) ? "°F" : "°C";
        Map<String, Weather.Day> daily = Weather.daily(c);
        Weather.Cached cur = Weather.cached(c);
        SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        SimpleDateFormat dow = new SimpleDateFormat("EEE", Locale.getDefault());

        float y0 = 56, gap = 5, tw = (DESIGN_W - 32 - 6 * gap) / 7, th = 44;
        Calendar day = Calendar.getInstance();
        day.add(Calendar.DAY_OF_MONTH, -3);
        for (int i = 0; i < 7; i++, day.add(Calendar.DAY_OF_MONTH, 1)) {
            float x = 16 + i * (tw + gap), cx = x + tw / 2;
            boolean past = i < 3, today = i == 3;
            String num = String.valueOf(day.get(Calendar.DAY_OF_MONTH));
            if (num.length() == 1) num = "0" + num;
            String name = dow.format(day.getTime()).toUpperCase(Locale.getDefault()).replace(".", "");
            Weather.Day d = daily.get(iso.format(day.getTime()));

            RectF r = new RectF(x, y0, x + tw, y0 + (today ? 92 : th));
            Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
            fill.setColor(today ? 0xFF2A2A2D : past ? 0xFF3A3A3D : 0xFF4A4A4E);
            cv.drawRoundRect(r, 7, 7, fill);
            Paint border = new Paint(Paint.ANTI_ALIAS_FLAG);
            border.setStyle(Paint.Style.STROKE);
            border.setStrokeWidth(today ? 1.5f : 0.9f);
            border.setColor(today ? RED : past ? 0xFF48484B : 0xFF606064);
            RectF br = new RectF(r);
            br.inset(border.getStrokeWidth() / 2, border.getStrokeWidth() / 2);
            cv.drawRoundRect(br, 6.5f, 6.5f, border);

            int numColor = today ? RED : past ? 0xFF8A8A8F : WHITE;
            Draw.centered(cv, num, cx, y0 + 23, Draw.pixel(17, numColor, past ? 0.15f : 0.4f));
            Paint np = Draw.pixel(7.5f, today ? WHITE : past ? 0xFF6E6E73 : 0xFFD6D6DA, 0f);
            np.setLetterSpacing(0.06f);
            Draw.centered(cv, name, cx, y0 + 35, np);

            if (today) {
                String icon = cur != null ? cur.icon : (d != null ? Weather.icon(d.code, true) : "⛅");
                monoEmoji(cv, icon, cx, y0 + 55, 15);
                String t = cur != null ? cur.temp + unit : "--" + unit;
                Draw.centered(cv, t, cx, y0 + 81, Draw.pixel(11, WHITE, 0.45f));
            } else if (!past) {
                String hi = d != null ? d.max + unit : "--";
                String lo = d != null ? d.min + unit : "--";
                Draw.centered(cv, hi, cx, y0 + th + 14, Draw.pixel(10, WHITE, 0.45f));
                Draw.centered(cv, lo, cx, y0 + th + 28, Draw.pixel(10, 0xFFA0A0A5, 0.1f));
            }
        }

        // PARTLY CLOUDY / ➤ CITY, under the past days
        float maxW = 3 * (tw + gap) - 6;
        String cond = Weather.condition(c);
        if (cond.isEmpty()) cond = cur == null ? "LOADING WEATHER" : "";
        Paint cp = Draw.pixel(12, 0xFFD0D0D4, 0f);
        cv.drawText(Draw.fit(cond, cp, maxW), 16, 140, cp);

        String place = Weather.place(c).toUpperCase(Locale.getDefault());
        if (!place.isEmpty()) {
            Path arrow = new Path();
            float ax = 16, ay = 149;
            arrow.moveTo(ax, ay + 4);
            arrow.lineTo(ax + 9, ay);
            arrow.lineTo(ax + 5, ay + 9);
            arrow.lineTo(ax + 4.2f, ay + 4.8f);
            arrow.close();
            Paint ap = new Paint(Paint.ANTI_ALIAS_FLAG);
            ap.setColor(WHITE);
            cv.drawPath(arrow, ap);
            Paint pp = Draw.pixel(11, WHITE, 0.5f);
            cv.drawText(Draw.fit(place, pp, maxW - 14), 30, 158, pp);
        }
    }

    /** Draws an emoji desaturated to a soft white, matching the monochrome pixel style. */
    private static void monoEmoji(Canvas cv, String emoji, float cx, float cy, float size) {
        ColorMatrix m = new ColorMatrix(new float[]{
                0.15f, 0.5f, 0.05f, 0, 95,
                0.15f, 0.5f, 0.05f, 0, 95,
                0.15f, 0.5f, 0.05f, 0, 95,
                0, 0, 0, 1, 0});
        Paint layer = new Paint();
        layer.setColorFilter(new ColorMatrixColorFilter(m));
        RectF bounds = new RectF(cx - size, cy - size, cx + size, cy + size);
        cv.saveLayer(bounds, layer);
        Paint e = new Paint(Paint.ANTI_ALIAS_FLAG);
        e.setTextSize(size);
        Paint.FontMetrics fm = e.getFontMetrics();
        cv.drawText(emoji, cx - e.measureText(emoji) / 2, cy - (fm.ascent + fm.descent) / 2, e);
        cv.restore();
    }
}
