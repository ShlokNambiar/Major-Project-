package com.hello.widget;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;

/** Renders the handwritten "hello" with the bundled script font (RemoteViews can't load custom fonts). */
final class HelloText {
    private static Bitmap cache;

    static synchronized Bitmap render(Context context) {
        if (cache != null) return cache;
        float d = context.getResources().getDisplayMetrics().density;
        // Cap the size so the bitmap stays well under the RemoteViews memory limit.
        float scale = Math.min(d, 3f);
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setTypeface(Typeface.createFromAsset(context.getAssets(), "Sacramento.ttf"));
        p.setColor(Color.WHITE);
        p.setTextSize(44 * scale);
        p.setStyle(Paint.Style.FILL_AND_STROKE);
        p.setStrokeWidth(1.6f * scale);
        p.setStrokeJoin(Paint.Join.ROUND);

        String text = "hello";
        Rect b = new Rect();
        p.getTextBounds(text, 0, text.length(), b);
        int pad = (int) (3 * scale);
        Bitmap bmp = Bitmap.createBitmap(b.width() + pad * 2, b.height() + pad * 2, Bitmap.Config.ARGB_8888);
        new Canvas(bmp).drawText(text, pad - b.left, pad - b.top, p);
        cache = bmp;
        return bmp;
    }
}
