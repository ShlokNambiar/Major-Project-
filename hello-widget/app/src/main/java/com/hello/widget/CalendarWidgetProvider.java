package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.net.Uri;

import java.text.DateFormatSymbols;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Locale;

/** Big date on the left, this month's grid on the right with today circled. */
public class CalendarWidgetProvider extends CanvasWidget {

    static final int WHITE = 0xFFFFFFFF, GREY = 0xFF8E8E93, RED = 0xFFFF3B30;
    static final int CARD = 0xC21C1C1E;
    /** Right-hand panel starts here (design units). */
    static final float PANEL_X = 164;

    @Override
    Intent clickIntent(Context c) {
        return openCalendar();
    }

    static Intent openCalendar() {
        Uri today = Uri.parse("content://com.android.calendar/time/" + System.currentTimeMillis());
        return new Intent(Intent.ACTION_VIEW, today).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        Draw.card(cv, w, h, 26, CARD);
        cv.translate((w - DESIGN_W) / 2, (h - DESIGN_H) / 2);
        drawDateBlock(cv);
        drawMonth(cv);
    }

    /** 2026.07 / 21 / July 21 Tuesday / 202/365 */
    static void drawDateBlock(Canvas cv) {
        Calendar now = Calendar.getInstance();
        Locale l = Locale.getDefault();
        float cx = 16 + (PANEL_X - 28) / 2;

        Draw.centered(cv, new SimpleDateFormat("yyyy.MM", l).format(now.getTime()), cx, 39,
                Draw.text(Draw.interBold, 15, WHITE));
        Paint big = Draw.text(Draw.interBold, 66, WHITE);
        big.setLetterSpacing(-0.045f);
        Draw.centered(cv, String.valueOf(now.get(Calendar.DAY_OF_MONTH)), cx, 101, big);
        Paint full = Draw.text(Draw.interBold, 12.5f, WHITE);
        Draw.centered(cv, Draw.fit(new SimpleDateFormat("MMMM d EEEE", l).format(now.getTime()), full, PANEL_X - 30),
                cx, 123, full);
        int days = now.getActualMaximum(Calendar.DAY_OF_YEAR);
        Draw.centered(cv, now.get(Calendar.DAY_OF_YEAR) + "/" + days, cx, 141,
                Draw.text(Draw.interMedium, 12, GREY));
    }

    private static void drawMonth(Canvas cv) {
        Calendar today = Calendar.getInstance();
        int first = today.getFirstDayOfWeek();
        Calendar cal = (Calendar) today.clone();
        cal.set(Calendar.DAY_OF_MONTH, 1);
        int lead = (cal.get(Calendar.DAY_OF_WEEK) - first + 7) % 7;
        int daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH);
        int weeks = (lead + daysInMonth + 6) / 7;

        float x0 = PANEL_X, x1 = DESIGN_W - 14, colW = (x1 - x0) / 7;
        float rowH = Math.min(20, (DESIGN_H - 26) / (weeks + 1));
        float top = (DESIGN_H - rowH * (weeks + 1)) / 2;

        String[] names = DateFormatSymbols.getInstance().getShortWeekdays();
        Paint head = Draw.text(Draw.interBold, 10.5f, WHITE);
        Paint num = Draw.text(Draw.interBold, 11.5f, WHITE);
        float capOffset = 4.1f;

        for (int i = 0; i < 7; i++) {
            int dowIdx = (first - 1 + i) % 7 + 1;
            head.setColor(isWeekend(dowIdx) ? GREY : WHITE);
            Draw.centered(cv, names[dowIdx].substring(0, 1).toUpperCase(), x0 + colW * (i + 0.5f),
                    top + rowH * 0.5f + capOffset - 0.5f, head);
        }

        Paint red = new Paint(Paint.ANTI_ALIAS_FLAG);
        red.setColor(RED);
        for (int d = 1; d <= daysInMonth; d++) {
            int idx = lead + d - 1, col = idx % 7, row = idx / 7 + 1;
            int dowIdx = (first - 1 + col) % 7 + 1;
            float cx = x0 + colW * (col + 0.5f), cy = top + rowH * (row + 0.5f);
            if (d == today.get(Calendar.DAY_OF_MONTH)) {
                cv.drawCircle(cx, cy, Math.min(10.5f, rowH / 2 + 0.5f), red);
                num.setColor(WHITE);
            } else {
                num.setColor(isWeekend(dowIdx) ? GREY : WHITE);
            }
            Draw.centered(cv, String.valueOf(d), cx, cy + capOffset, num);
        }
    }

    private static boolean isWeekend(int dow) {
        return dow == Calendar.SATURDAY || dow == Calendar.SUNDAY;
    }
}
