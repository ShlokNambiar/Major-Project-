package com.hello.widget;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.text.TextUtils;

/** Shared fonts and drawing helpers for the canvas widgets. Sizes are in design dp. */
final class Draw {

    static Typeface interMedium, interSemibold, interBold, pixel;

    static void loadFonts(Context c) {
        if (pixel != null) return;
        interMedium = c.getResources().getFont(R.font.inter_medium);
        interSemibold = c.getResources().getFont(R.font.inter_semibold);
        interBold = c.getResources().getFont(R.font.inter_bold);
        pixel = c.getResources().getFont(R.font.departure_mono);
    }

    static Paint text(Typeface tf, float size, int color) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.SUBPIXEL_TEXT_FLAG);
        p.setTypeface(tf);
        p.setTextSize(size);
        p.setColor(color);
        return p;
    }

    /** Pixel font thickened slightly with a stroke, like the Void widget's bold digits. */
    static Paint pixel(float size, int color, float weight) {
        Paint p = text(pixel, size, color);
        if (weight > 0) {
            p.setStyle(Paint.Style.FILL_AND_STROKE);
            p.setStrokeWidth(weight);
            p.setStrokeJoin(Paint.Join.MITER);
        }
        return p;
    }

    static void centered(Canvas c, String s, float cx, float baseline, Paint p) {
        c.drawText(s, cx - p.measureText(s) / 2, baseline, p);
    }

    static String fit(String s, Paint p, float maxWidth) {
        return TextUtils.ellipsize(s, new android.text.TextPaint(p), maxWidth, TextUtils.TruncateAt.END).toString();
    }

    /**
     * Dark glass card: translucent fill with light catching the top-left and bottom-right edges,
     * fading out along the sides.
     */
    static void card(Canvas c, float w, float h, float radius, int fill) {
        RectF r = new RectF(0.75f, 0.75f, w - 0.75f, h - 0.75f);
        Paint f = new Paint(Paint.ANTI_ALIAS_FLAG);
        f.setColor(fill);
        c.drawRoundRect(r, radius, radius, f);

        Paint edge = new Paint(Paint.ANTI_ALIAS_FLAG);
        edge.setStyle(Paint.Style.STROKE);
        edge.setStrokeWidth(1.1f);
        edge.setShader(new LinearGradient(0, 0, w, h,
                new int[]{0x66FFFFFF, 0x00FFFFFF, 0x00FFFFFF, 0x47FFFFFF},
                new float[]{0f, 0.32f, 0.68f, 1f}, Shader.TileMode.CLAMP));
        c.drawRoundRect(r, radius, radius, edge);
    }
}
