package com.hello.widget;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.util.DisplayMetrics;

/**
 * Draws the widget's text and pills in-process. Launchers (e.g. One UI) ignore custom fonts in
 * widget layouts, so everything except the vector "hello" and the analog clock is a bitmap.
 */
final class WidgetArt {

    private static Typeface semibold;

    private final Context c;
    private final float dp, sp;

    WidgetArt(Context context) {
        c = context;
        DisplayMetrics dm = context.getResources().getDisplayMetrics();
        dp = dm.density;
        sp = dm.scaledDensity;
        if (semibold == null) semibold = context.getResources().getFont(R.font.inter_semibold);
    }

    private Paint textPaint(float sizeSp, int color) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.SUBPIXEL_TEXT_FLAG);
        p.setTypeface(semibold);
        p.setTextSize(sizeSp * sp);
        p.setColor(color);
        p.setLetterSpacing(-0.015f);
        return p;
    }

    private Bitmap bitmap(float w, float h) {
        Bitmap b = Bitmap.createBitmap(Math.max(1, Math.round(w)), Math.max(1, Math.round(h)), Bitmap.Config.ARGB_8888);
        b.setDensity(c.getResources().getDisplayMetrics().densityDpi);
        return b;
    }

    /** Plain white label; every label shares the same line box so baselines line up. */
    Bitmap label(String text) {
        Paint p = textPaint(17, Color.WHITE);
        Paint.FontMetrics fm = p.getFontMetrics();
        float w = p.measureText(text) + 2 * dp;
        Bitmap b = bitmap(w, fm.descent - fm.ascent);
        new Canvas(b).drawText(text, dp, -fm.ascent, p);
        return b;
    }

    /** [● 09] — lavender glass pill with the coral dot. */
    Bitmap datePill(String day) {
        float h = 30 * dp, r = h / 2, dot = 24 * dp, inset = (h - dot) / 2;
        Paint num = textPaint(16, 0xFF29235F);
        float w = inset + dot + 8 * dp + num.measureText(day) + 12 * dp;
        Bitmap b = bitmap(w, h);
        Canvas cv = new Canvas(b);
        RectF box = new RectF(0.5f * dp, 0.5f * dp, w - 0.5f * dp, h - 0.5f * dp);

        Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        fill.setShader(new LinearGradient(0, 0, 0, h, 0xE6CFCBFF, 0xD9AEA6F7, Shader.TileMode.CLAMP));
        cv.drawRoundRect(box, r, r, fill);
        rim(cv, box, r, 1 * dp, 0x8CFFFFFF, 0x26FFFFFF);

        float cx = inset + dot / 2, cy = h / 2;
        Paint red = new Paint(Paint.ANTI_ALIAS_FLAG);
        red.setShader(new RadialGradient(cx - dot * 0.12f, cy - dot * 0.18f, dot * 0.7f,
                0xFFFF8F7E, 0xFFEC5446, Shader.TileMode.CLAMP));
        cv.drawCircle(cx, cy, dot / 2, red);
        Paint dots = new Paint(Paint.ANTI_ALIAS_FLAG);
        dots.setColor(0xE6FFFFFF);
        for (int i = -1; i <= 1; i++) cv.drawCircle(cx + i * 2.6f * dp, cy + 0.5f * dp, 0.85f * dp, dots);

        drawCentered(cv, day, num, inset + dot + 8 * dp, h);
        return b;
    }

    /** [22° ⛅] — brighter glass pill with a thick soft rim. */
    Bitmap weatherPill(String temp, String icon) {
        float h = 32 * dp, r = h / 2;
        Paint t = textPaint(16, Color.WHITE);
        Paint e = new Paint(Paint.ANTI_ALIAS_FLAG);
        e.setTextSize(15 * sp);
        float gap = 5 * dp;
        float w = 13 * dp + t.measureText(temp) + gap + e.measureText(icon) + 11 * dp;
        Bitmap b = bitmap(w, h);
        Canvas cv = new Canvas(b);
        RectF box = new RectF(dp, dp, w - dp, h - dp);

        Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        fill.setShader(new LinearGradient(0, 0, 0, h, 0xD9B9B1FF, 0xCC9A8FF2, Shader.TileMode.CLAMP));
        cv.drawRoundRect(box, r, r, fill);
        rim(cv, box, r, 1.8f * dp, 0xD9F1EFFF, 0x73E2DEFF);

        float x = drawCentered(cv, temp, t, 13 * dp, h) + gap;
        drawCentered(cv, icon, icon, e, x, h);
        return b;
    }

    /** Gradient stroke: bright on top, softer at the bottom, like light catching glass. */
    private void rim(Canvas cv, RectF box, float r, float width, int top, int bottom) {
        Paint s = new Paint(Paint.ANTI_ALIAS_FLAG);
        s.setStyle(Paint.Style.STROKE);
        s.setStrokeWidth(width);
        s.setShader(new LinearGradient(0, box.top, 0, box.bottom, top, bottom, Shader.TileMode.CLAMP));
        RectF in = new RectF(box);
        in.inset(width / 2, width / 2);
        cv.drawRoundRect(in, r - width / 2, r - width / 2, s);
    }

    /** Draws text vertically centred on its cap height; returns the x where it ends. */
    private float drawCentered(Canvas cv, String text, Paint p, float x, float h) {
        return drawCentered(cv, text, "0", p, x, h);
    }

    private float drawCentered(Canvas cv, String text, String ref, Paint p, float x, float h) {
        android.graphics.Rect bounds = new android.graphics.Rect();
        p.getTextBounds(ref, 0, ref.length(), bounds);
        float y = h / 2 - bounds.exactCenterY();
        cv.drawText(text, x, y, p);
        return x + p.measureText(text);
    }
}
