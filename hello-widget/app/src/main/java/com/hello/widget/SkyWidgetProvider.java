package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.Locale;
import java.util.Map;

/** Sun / moon travelling along an arc over a sky gradient that follows real sunrise and sunset. */
public class SkyWidgetProvider extends CanvasWidget {

    enum Phase { NIGHT, DAWN, DAY, DUSK }

    @Override
    Intent clickIntent(Context c) {
        return new Intent(c, MainActivity.class);
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        long now = System.currentTimeMillis();
        long[] sun = sunTimes(c);   // sunrise, sunset, next sunrise, previous sunset
        long rise = sun[0], set = sun[1];
        long dawnStart = rise - 40 * 60_000L, dawnEnd = rise + 75 * 60_000L;
        long duskStart = set - 75 * 60_000L, duskEnd = set + 40 * 60_000L;

        Phase phase;
        if (now < dawnStart || now > duskEnd) phase = Phase.NIGHT;
        else if (now < dawnEnd) phase = Phase.DAWN;
        else if (now > duskStart) phase = Phase.DUSK;
        else phase = Phase.DAY;

        // Position along the arc: 0 = left end, 1 = right end.
        float t;
        if (phase == Phase.NIGHT) {
            long from = now > set ? set : sun[3], to = now > set ? sun[2] : rise;
            t = (now - from) / (float) Math.max(1, to - from);
        } else {
            t = (now - rise) / (float) Math.max(1, set - rise);
        }
        t = Math.max(0.04f, Math.min(0.96f, t));

        // ---- card: sky gradient inside a soft white glass frame
        float r = 24;
        RectF box = new RectF(1.5f, 1.5f, w - 1.5f, h - 1.5f);
        Paint sky = new Paint(Paint.ANTI_ALIAS_FLAG);
        int[] colors;
        float[] stops;
        switch (phase) {
            case NIGHT: colors = new int[]{0xFF050507, 0xFF1B1B20, 0xFF34343B}; stops = new float[]{0, 0.55f, 1}; break;
            case DAWN:  colors = new int[]{0xFF8E6FD9, 0xFFE59AB0, 0xFFF7B57A}; stops = new float[]{0, 0.55f, 1}; break;
            case DUSK:  colors = new int[]{0xFF5A3FA0, 0xFFD0679A, 0xFFF59A5E}; stops = new float[]{0, 0.55f, 1}; break;
            default:    colors = new int[]{0xFF4F86FF, 0xFF7E8DFF, 0xFFC48DFF}; stops = new float[]{0, 0.5f, 1}; break;
        }
        boolean diagonal = phase == Phase.DAY;
        sky.setShader(new LinearGradient(0, 0, diagonal ? w : w * 0.25f, h, colors, stops, Shader.TileMode.CLAMP));
        cv.drawRoundRect(box, r, r, sky);

        // ---- arc
        float peakY = h * 0.5f, half = w * 0.42f;
        float R = (half * half + (h - peakY) * (h - peakY)) / (2 * (h - peakY));
        float cx = w / 2, cy = peakY + R;
        double a0 = Math.atan2(h - cy, (cx - half) - cx), a1 = Math.atan2(h - cy, (cx + half) - cx);
        if (a1 < a0) a1 += 2 * Math.PI;
        RectF oval = new RectF(cx - R, cy - R, cx + R, cy + R);
        float startDeg = (float) Math.toDegrees(a0), sweepDeg = (float) Math.toDegrees(a1 - a0);

        cv.save();
        Path clip = new Path();
        clip.addRoundRect(box, r, r, Path.Direction.CW);
        cv.clipPath(clip);

        Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
        glow.setStyle(Paint.Style.STROKE);
        glow.setStrokeWidth(16);
        glow.setColor(phase == Phase.NIGHT ? 0x33FFFFFF : 0x55FFFFFF);
        glow.setMaskFilter(new BlurMaskFilter(9, BlurMaskFilter.Blur.NORMAL));
        cv.drawArc(oval, startDeg - 20, sweepDeg + 40, false, glow);

        Paint arc = new Paint(Paint.ANTI_ALIAS_FLAG);
        arc.setStyle(Paint.Style.STROKE);
        arc.setStrokeWidth(7);
        arc.setStrokeCap(Paint.Cap.ROUND);
        arc.setShader(new LinearGradient(0, peakY, 0, h, phase == Phase.NIGHT ? 0xB3FFFFFF : 0xF2FFFFFF,
                phase == Phase.NIGHT ? 0x26FFFFFF : 0x80FFFFFF, Shader.TileMode.CLAMP));
        cv.drawArc(oval, startDeg - 20, sweepDeg + 40, false, arc);

        // ---- sun / moon
        double a = a0 + t * (a1 - a0);
        float sx = (float) (cx + R * Math.cos(a)), sy = (float) (cy + R * Math.sin(a));
        Paint halo = new Paint(Paint.ANTI_ALIAS_FLAG);
        if (phase == Phase.NIGHT) {
            halo.setShader(new RadialGradient(sx, sy, 34, new int[]{0x99FFFFFF, 0x26FFFFFF, 0x00FFFFFF},
                    new float[]{0, 0.4f, 1}, Shader.TileMode.CLAMP));
            cv.drawCircle(sx, sy, 34, halo);
            Paint moon = new Paint(Paint.ANTI_ALIAS_FLAG);
            moon.setShader(new RadialGradient(sx - 3, sy - 3, 13, 0xFFFFFFFF, 0xFFDADADF, Shader.TileMode.CLAMP));
            cv.drawCircle(sx, sy, 10.5f, moon);
        } else {
            int glowColor = phase == Phase.DAY ? 0xCCFFD27A : 0xCCFFB15C;
            halo.setShader(new RadialGradient(sx, sy, 36, new int[]{glowColor, 0x40FFB15C, 0x00FFB15C},
                    new float[]{0, 0.35f, 1}, Shader.TileMode.CLAMP));
            cv.drawCircle(sx, sy, 36, halo);
            Paint core = new Paint(Paint.ANTI_ALIAS_FLAG);
            core.setShader(new RadialGradient(sx - 2, sy - 2, 11, new int[]{0xFFFFFFFF, 0xFFFFE08A, 0xFFFF9E3D},
                    new float[]{0, 0.45f, 1}, Shader.TileMode.CLAMP));
            cv.drawCircle(sx, sy, 9.5f, core);
        }
        cv.restore();

        // ---- glass frame
        Paint frame = new Paint(Paint.ANTI_ALIAS_FLAG);
        frame.setStyle(Paint.Style.STROKE);
        frame.setStrokeWidth(3.5f);
        frame.setColor(phase == Phase.NIGHT ? 0xD9E8E8EE : 0xE6FFFFFF);
        RectF fr = new RectF(box);
        fr.inset(1.5f, 1.5f);
        cv.drawRoundRect(fr, r - 1.5f, r - 1.5f, frame);

        // ---- text
        String title, subtitle;
        switch (phase) {
            case NIGHT: title = "Night"; subtitle = moonPhase(now); break;
            case DAWN: title = "Dawn"; subtitle = "Golden Sun"; break;
            case DUSK: title = "Dusk"; subtitle = "Golden Hour"; break;
            default:
                title = "Day";
                long noon = (rise + set) / 2;
                subtitle = Math.abs(now - noon) < 60 * 60_000L ? "The Very Peak" : titleCase(Weather.condition(c), "Clear Skies");
        }
        cv.drawText(title, 18, 31, Draw.text(Draw.interBold, 17, 0xFFFFFFFF));
        cv.drawText(subtitle, 18, 45, Draw.text(Draw.interMedium, 9.5f, 0xC7FFFFFF));

        Weather.Cached wc = Weather.cached(c);
        if (wc != null) {
            String temp = wc.temp + (Weather.fahrenheit(c) ? " °F" : " °C");
            Paint tp = Draw.text(Draw.interSemibold, 12.5f, 0xFFFFFFFF);
            cv.drawText(temp, w - 18 - tp.measureText(temp), 30, tp);
        }
    }

    /** {today's sunrise, today's sunset, tomorrow's sunrise, yesterday's sunset} in millis. */
    static long[] sunTimes(Context c) {
        Map<String, Weather.Day> daily = Weather.daily(c);
        SimpleDateFormat iso = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        Calendar day = Calendar.getInstance();
        String today = iso.format(day.getTime());
        day.add(Calendar.DAY_OF_MONTH, 1);
        String tomorrow = iso.format(day.getTime());
        day.add(Calendar.DAY_OF_MONTH, -2);
        String yesterday = iso.format(day.getTime());

        long rise = parse(daily.get(today), true, 0, 6, 0);
        long set = parse(daily.get(today), false, 0, 18, 0);
        long nextRise = parse(daily.get(tomorrow), true, 1, 6, 0);
        long prevSet = parse(daily.get(yesterday), false, -1, 18, 0);
        return new long[]{rise, set, nextRise, prevSet};
    }

    private static long parse(Weather.Day d, boolean sunrise, int dayOffset, int fallbackH, int fallbackM) {
        String s = d == null ? null : (sunrise ? d.sunrise : d.sunset);
        if (s != null) {
            try {
                Date t = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm", Locale.US).parse(s);
                if (t != null) return t.getTime();
            } catch (Exception ignored) { }
        }
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DAY_OF_MONTH, dayOffset);
        cal.set(Calendar.HOUR_OF_DAY, fallbackH);
        cal.set(Calendar.MINUTE, fallbackM);
        cal.set(Calendar.SECOND, 0);
        return cal.getTimeInMillis();
    }

    /** Moon phase name from the synodic month, anchored to the 6 Jan 2000 new moon. */
    static String moonPhase(long now) {
        double days = (now - 947182440000L) / 86_400_000.0;
        double age = ((days % 29.530588853) + 29.530588853) % 29.530588853;
        String[] names = {"New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
                "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"};
        return names[(int) Math.floor((age / 29.530588853) * 8 + 0.5) % 8];
    }

    private static String titleCase(String s, String fallback) {
        if (s == null || s.isEmpty()) return fallback;
        StringBuilder b = new StringBuilder();
        for (String word : s.toLowerCase(Locale.getDefault()).split(" ")) {
            if (word.isEmpty()) continue;
            if (b.length() > 0) b.append(' ');
            b.append(Character.toUpperCase(word.charAt(0))).append(word.substring(1));
        }
        return b.toString();
    }
}
