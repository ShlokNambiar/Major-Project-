package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.widget.RemoteViews;

import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Locale;

/** Upcoming alarm with an on/off toggle, "turn off this time", vibration and snooze switches. */
public class AlarmWidgetProvider extends CanvasWidget {

    private static final int ORANGE = 0xFFFF6A1A, GREY = 0xFF8E8E93, WHITE = 0xFFFFFFFF;

    // Row bands as fractions of the height; the tap-zone weights in widget_alarm.xml match these.
    private static final float HEADER_END = 0.24f, UPCOMING_END = 0.52f, SKIP_TOP = 0.53f, SKIP_END = 0.66f,
            VIB_TOP = 0.68f, SNOOZE_TOP = 0.84f;

    @Override float designW() { return 282; }
    @Override float designH() { return 274; }
    @Override int layoutId() { return R.layout.widget_alarm; }

    @Override
    Intent clickIntent(Context c) {
        return new Intent(c, AlarmsActivity.class);
    }

    @Override
    void bindClicks(Context c, RemoteViews v, int widgetId) {
        v.setOnClickPendingIntent(R.id.zone_title, activityPi(c, 80, new Intent(c, AlarmsActivity.class)));
        v.setOnClickPendingIntent(R.id.zone_add, activityPi(c, 81,
                new Intent(c, AlarmsActivity.class).putExtra(AlarmsActivity.EXTRA_ADD, true)));
        v.setOnClickPendingIntent(R.id.zone_time, activityPi(c, 82, new Intent(c, AlarmsActivity.class)));
        boolean any = Alarms.featured(c) != null;
        v.setOnClickPendingIntent(R.id.zone_toggle, any
                ? broadcastPi(c, 83, receiver(c, AlarmReceiver.ACTION_TOGGLE))
                : activityPi(c, 84, new Intent(c, AlarmsActivity.class).putExtra(AlarmsActivity.EXTRA_ADD, true)));
        v.setOnClickPendingIntent(R.id.zone_skip, broadcastPi(c, 85, receiver(c, AlarmReceiver.ACTION_SKIP)));
        v.setOnClickPendingIntent(R.id.zone_vibrate, broadcastPi(c, 86, receiver(c, AlarmReceiver.ACTION_TOGGLE_VIBRATE)));
        v.setOnClickPendingIntent(R.id.zone_snooze, broadcastPi(c, 87, receiver(c, AlarmReceiver.ACTION_TOGGLE_SNOOZE)));
    }

    private static Intent receiver(Context c, String action) {
        return new Intent(c, AlarmReceiver.class).setAction(action);
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        Draw.card(cv, w, h, 26, 0xF21C1C1E);
        Paint border = new Paint(Paint.ANTI_ALIAS_FLAG);
        border.setStyle(Paint.Style.STROKE);
        border.setStrokeWidth(1.4f);
        border.setColor(0x40FFFFFF);
        cv.drawRoundRect(new RectF(1, 1, w - 1, h - 1), 26, 26, border);

        float u = Math.min(w / 282f, h / 274f);
        float px = 18 * u;
        long now = System.currentTimeMillis();
        Alarms.Alarm a = Alarms.featured(c);
        int count = Alarms.enabledCount(c);

        // ---- header
        float hy = h * HEADER_END * 0.55f;
        Paint circle = new Paint(Paint.ANTI_ALIAS_FLAG);
        circle.setColor(0xFF3A3A3E);
        float ir = 20 * u, icx = px + ir;
        cv.drawCircle(icx, hy, ir, circle);
        Paint emoji = new Paint(Paint.ANTI_ALIAS_FLAG);
        emoji.setTextSize(21 * u);
        Paint.FontMetrics fm = emoji.getFontMetrics();
        cv.drawText("⏰", icx - emoji.measureText("⏰") / 2, hy - (fm.ascent + fm.descent) / 2, emoji);
        float tx = icx + ir + 11 * u;
        cv.drawText("Alarm", tx, hy - 1 * u, Draw.text(Draw.interSemibold, 19 * u, WHITE));
        String sub = count == 0 ? "No alarms on" : count == 1 ? "1 Alarm On" : count + " Alarms On";
        cv.drawText(sub, tx, hy + 15 * u, Draw.text(Draw.interMedium, 11.5f * u, GREY));
        Paint plus = new Paint(Paint.ANTI_ALIAS_FLAG);
        plus.setColor(WHITE);
        plus.setStrokeWidth(2.2f * u);
        plus.setStrokeCap(Paint.Cap.ROUND);
        float pcx = w - px - 10 * u, pl = 9 * u;
        cv.drawLine(pcx - pl, hy, pcx + pl, hy, plus);
        cv.drawLine(pcx, hy - pl, pcx, hy + pl, plus);

        // ---- upcoming alarm + big toggle
        boolean on = a != null && a.on;
        boolean skipping = a != null && a.on && a.skipping(now);
        float top = h * HEADER_END;
        cv.drawText(skipping ? "Next Alarm (skipping one)" : "Upcoming Alarm", px, top + 0.07f * h,
                Draw.text(Draw.interMedium, 12 * u, GREY));
        String time = "--:--", ampm = "";
        if (a != null) {
            Calendar cal = Calendar.getInstance();
            cal.set(Calendar.HOUR_OF_DAY, a.hour);
            cal.set(Calendar.MINUTE, a.minute);
            boolean h24 = android.text.format.DateFormat.is24HourFormat(c);
            time = new SimpleDateFormat(h24 ? "HH:mm" : "h:mm", Locale.getDefault()).format(cal.getTime());
            ampm = h24 ? "" : new SimpleDateFormat("a", Locale.US).format(cal.getTime()).toUpperCase(Locale.US);
        }
        Paint big = Draw.text(Draw.interBold, 46 * u, on ? WHITE : 0x73FFFFFF);
        big.setLetterSpacing(-0.02f);
        float timeBase = h * UPCOMING_END - 0.025f * h;
        cv.drawText(time, px, timeBase, big);
        if (!ampm.isEmpty()) {
            cv.drawText(ampm, px + big.measureText(time) + 4 * u, timeBase,
                    Draw.text(Draw.interMedium, 18 * u, on ? WHITE : 0x73FFFFFF));
        }
        // vertical switch
        float sw = 34 * u, sh = 0.23f * h, sx = w - px - sw, sy = top + 0.03f * h;
        Paint track = new Paint(Paint.ANTI_ALIAS_FLAG);
        track.setColor(on ? ORANGE : 0xFF3A3A3E);
        cv.drawRoundRect(new RectF(sx, sy, sx + sw, sy + sh), sw / 2, sw / 2, track);
        Paint knob = new Paint(Paint.ANTI_ALIAS_FLAG);
        knob.setColor(WHITE);
        knob.setShadowLayer(3 * u, 0, 1 * u, 0x40000000);
        float kr = sw / 2 - 3 * u;
        cv.drawCircle(sx + sw / 2, on ? sy + sw / 2 : sy + sh - sw / 2, kr, knob);

        // ---- turn off this time
        RectF btn = new RectF(px - 2 * u, h * SKIP_TOP, w - px + 2 * u, h * SKIP_END);
        Paint bf = new Paint(Paint.ANTI_ALIAS_FLAG);
        bf.setColor(0xFF2A2A2D);
        cv.drawRoundRect(btn, 9 * u, 9 * u, bf);
        Paint bs = new Paint(Paint.ANTI_ALIAS_FLAG);
        bs.setStyle(Paint.Style.STROKE);
        bs.setStrokeWidth(1);
        bs.setColor(0xFF3C3C40);
        cv.drawRoundRect(btn, 9 * u, 9 * u, bs);
        String btnText = a == null ? "Tap + to add an alarm" : !on ? "Alarm is off"
                : skipping ? "Turned off this time · Undo" : "Turn off this time";
        Paint bt = Draw.text(Draw.interMedium, 12.5f * u, a != null && on ? ORANGE : GREY);
        Draw.centered(cv, btnText, btn.centerX(), btn.centerY() + 4.3f * u, bt);

        // ---- vibration / snooze rows
        settingRow(cv, w, h * VIB_TOP, h * SNOOZE_TOP, u, px, "Vibration",
                Alarms.vibrate(c) ? "On" : "Off", Alarms.vibrate(c));
        boolean sn = Alarms.snooze(c);
        settingRow(cv, w, h * SNOOZE_TOP, h, u, px, "Snooze",
                sn ? "On · 5 min, 3 times" : "Off", sn);
    }

    private static void settingRow(Canvas cv, float w, float top, float bottom, float u, float px,
                                   String title, String sub, boolean on) {
        float cy = (top + bottom) / 2 - 2 * u;
        cv.drawText(title, px, cy - 1 * u, Draw.text(Draw.interMedium, 14 * u, WHITE));
        Paint sp = Draw.text(Draw.interMedium, 11 * u, on ? ORANGE : GREY);
        if (on && sub.contains("·")) {
            // "On" in orange, details in grey, like the reference
            String head = sub.substring(0, sub.indexOf('·'));
            cv.drawText(head, px, cy + 14 * u, sp);
            cv.drawText(sub.substring(sub.indexOf('·')), px + sp.measureText(head),
                    cy + 14 * u, Draw.text(Draw.interMedium, 11 * u, GREY));
        } else {
            cv.drawText(sub, px, cy + 14 * u, sp);
        }
        float tw = 42 * u, th = 24 * u, tx = w - px - tw, ty = cy + 4 * u - th / 2;
        Paint track = new Paint(Paint.ANTI_ALIAS_FLAG);
        track.setColor(on ? ORANGE : 0xFF3A3A3E);
        cv.drawRoundRect(new RectF(tx, ty, tx + tw, ty + th), th / 2, th / 2, track);
        Paint knob = new Paint(Paint.ANTI_ALIAS_FLAG);
        knob.setColor(WHITE);
        float kr = th / 2 - 2.5f * u;
        cv.drawCircle(on ? tx + tw - th / 2 : tx + th / 2, ty + th / 2, kr, knob);
    }
}
