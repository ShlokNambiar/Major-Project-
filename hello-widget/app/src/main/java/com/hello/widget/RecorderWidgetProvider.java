package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.widget.RemoteViews;

import java.util.Locale;

/** 2×2 voice recorder: live waveform, timer, settings / record-pause / stop buttons. */
public class RecorderWidgetProvider extends CanvasWidget {

    private static final int RED = 0xFFFF3B30, ORANGE = 0xFFFF7A3D;

    @Override float designW() { return 170; }
    @Override float designH() { return 170; }
    @Override int layoutId() { return R.layout.widget_recorder; }

    @Override
    Intent clickIntent(Context c) {
        return new Intent(c, RecordingsActivity.class);
    }

    @Override
    void bindClicks(Context c, RemoteViews v, int widgetId) {
        v.setOnClickPendingIntent(R.id.zone_top, activityPi(c, 60, new Intent(c, RecordingsActivity.class)));
        v.setOnClickPendingIntent(R.id.zone_left, activityPi(c, 61, new Intent(c, RecordingsActivity.class)));
        switch (RecorderService.state) {
            case IDLE:
                v.setOnClickPendingIntent(R.id.zone_mid, activityPi(c, 62, new Intent(c, RecordActivity.class)));
                break;
            case RECORDING:
                v.setOnClickPendingIntent(R.id.zone_mid, servicePi(c, 63, RecorderService.intent(c, RecorderService.ACTION_PAUSE)));
                break;
            case PAUSED:
                v.setOnClickPendingIntent(R.id.zone_mid, servicePi(c, 64, RecorderService.intent(c, RecorderService.ACTION_RESUME)));
                break;
        }
        // The service only exists while recording; when idle, "stop" just opens the recordings list.
        v.setOnClickPendingIntent(R.id.zone_right, RecorderService.state == RecorderService.State.IDLE
                ? activityPi(c, 66, new Intent(c, RecordingsActivity.class))
                : servicePi(c, 65, RecorderService.intent(c, RecorderService.ACTION_STOP)));
    }

    @Override
    void draw(Context c, Canvas cv, float w, float h) {
        Draw.loadFonts(c);
        Draw.card(cv, w, h, 30, 0xE61C1C1F);
        RecorderService.State st = RecorderService.state;
        float u = Math.min(w, h) / 170f;

        // ---- waveform panel
        float pad = 10 * u;
        RectF panel = new RectF(pad, pad, w - pad, h * 0.48f);
        Paint pf = new Paint(Paint.ANTI_ALIAS_FLAG);
        pf.setShader(new LinearGradient(0, panel.top, 0, panel.bottom, 0xFF333338, 0xFF26262A, Shader.TileMode.CLAMP));
        cv.drawRoundRect(panel, 20 * u, 20 * u, pf);
        Paint pb = new Paint(Paint.ANTI_ALIAS_FLAG);
        pb.setStyle(Paint.Style.STROKE);
        pb.setStrokeWidth(0.8f);
        pb.setColor(0x26FFFFFF);
        cv.drawRoundRect(panel, 20 * u, 20 * u, pb);

        float mid = panel.centerY(), maxH = panel.height() * 0.36f;
        float headX = panel.left + panel.width() * 0.72f, step = 2.6f * u;
        Paint base = new Paint(Paint.ANTI_ALIAS_FLAG);
        base.setColor(0x33FFFFFF);
        base.setStrokeWidth(0.8f * u);
        cv.drawLine(headX, mid, panel.right - 12 * u, mid, base);

        Paint bar = new Paint(Paint.ANTI_ALIAS_FLAG);
        bar.setStrokeCap(Paint.Cap.ROUND);
        bar.setStrokeWidth(1.5f * u);
        int n = (int) ((headX - panel.left - 12 * u) / step);
        for (int i = 0; i < n && i < RecorderService.BARS; i++) {
            // newest sample sits just left of the playhead
            int idx = (RecorderService.levelHead - 1 - i + RecorderService.BARS * 2) % RecorderService.BARS;
            float level = st == RecorderService.State.IDLE ? 0.03f : RecorderService.levels[idx];
            float x = headX - 3 * u - i * step;
            float alpha = 1f - (i / (float) n) * 0.55f;
            bar.setColor(((int) (alpha * 235) << 24) | 0xFFFFFF);
            float bh = Math.max(0.8f * u, level * maxH);
            cv.drawLine(x, mid - bh, x, mid + bh, bar);
        }
        Paint head = new Paint(Paint.ANTI_ALIAS_FLAG);
        head.setColor(ORANGE);
        head.setStrokeWidth(1.6f * u);
        head.setStrokeCap(Paint.Cap.ROUND);
        cv.drawLine(headX, panel.top + 14 * u, headX, panel.bottom - 14 * u, head);

        // ---- timer row
        float rowY = h * 0.6f;
        long secs = RecorderService.elapsedMs() / 1000;
        String time = String.format(Locale.US, "%02d:%02d", secs / 60, secs % 60);
        boolean blinkOn = st == RecorderService.State.RECORDING ? (System.currentTimeMillis() / 500) % 2 == 0 : st == RecorderService.State.PAUSED;
        Paint dot = new Paint(Paint.ANTI_ALIAS_FLAG);
        dot.setColor(st == RecorderService.State.IDLE ? 0x66FF3B30 : blinkOn ? RED : 0x55FF3B30);
        cv.drawCircle(pad + 8 * u, rowY - 6 * u, 2.8f * u, dot);
        Paint tp = Draw.text(Draw.interMedium, 22 * u, 0xFFFFFFFF);
        tp.setLetterSpacing(0.02f);
        float tx = pad + 16 * u;
        cv.drawText(time, tx, rowY + 2 * u, tp);
        Paint lp = Draw.pixel(6.6f * u, 0xB3FFFFFF, 0f);
        lp.setLetterSpacing(0.05f);
        float lx = tx + tp.measureText(time) + 8 * u;
        String[] label = st == RecorderService.State.RECORDING ? new String[]{"NEW AUDIO", "RECORDING..."}
                : st == RecorderService.State.PAUSED ? new String[]{"RECORDING", "PAUSED"}
                : new String[]{"TAP TO", "RECORD"};
        cv.drawText(label[0], lx, rowY - 6 * u, lp);
        cv.drawText(label[1], lx, rowY + 3 * u, lp);

        // ---- buttons (centres line up with the three tap zones)
        float by = h * 0.82f, br = Math.min(w, h) * 0.1f;
        float[] bx = {w * 0.26f, w * 0.5f, w * 0.74f};
        greyButton(cv, bx[0], by, br);
        drawSliders(cv, bx[0], by, br);
        Paint red = new Paint(Paint.ANTI_ALIAS_FLAG);
        red.setShader(new RadialGradient(bx[1], by - br * 0.3f, br * 1.3f, 0xFFFF5A4F, 0xFFE8271C, Shader.TileMode.CLAMP));
        cv.drawCircle(bx[1], by, br, red);
        Paint white = new Paint(Paint.ANTI_ALIAS_FLAG);
        white.setColor(0xFFFFFFFF);
        if (st == RecorderService.State.RECORDING) {
            float bw = br * 0.14f, bh2 = br * 0.34f;
            cv.drawRoundRect(new RectF(bx[1] - bw * 2.2f, by - bh2, bx[1] - bw * 0.6f, by + bh2), bw, bw, white);
            cv.drawRoundRect(new RectF(bx[1] + bw * 0.6f, by - bh2, bx[1] + bw * 2.2f, by + bh2), bw, bw, white);
        } else {
            cv.drawCircle(bx[1], by, br * 0.32f, white);
        }
        greyButton(cv, bx[2], by, br);
        Paint stop = new Paint(Paint.ANTI_ALIAS_FLAG);
        stop.setColor(st == RecorderService.State.IDLE ? 0x66FFFFFF : 0xFFFFFFFF);
        float sq = br * 0.3f;
        cv.drawRoundRect(new RectF(bx[2] - sq, by - sq, bx[2] + sq, by + sq), sq * 0.35f, sq * 0.35f, stop);
    }

    private static void greyButton(Canvas cv, float x, float y, float r) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setShader(new LinearGradient(0, y - r, 0, y + r, 0xFF3C3C41, 0xFF2C2C30, Shader.TileMode.CLAMP));
        cv.drawCircle(x, y, r, p);
        Paint e = new Paint(Paint.ANTI_ALIAS_FLAG);
        e.setStyle(Paint.Style.STROKE);
        e.setStrokeWidth(0.8f);
        e.setColor(0x1FFFFFFF);
        cv.drawCircle(x, y, r, e);
    }

    /** The "settings" sliders glyph. */
    private static void drawSliders(Canvas cv, float x, float y, float r) {
        Paint l = new Paint(Paint.ANTI_ALIAS_FLAG);
        l.setColor(0xFFE5E5EA);
        l.setStrokeWidth(r * 0.09f);
        l.setStrokeCap(Paint.Cap.ROUND);
        float half = r * 0.38f, gap = r * 0.2f;
        cv.drawLine(x - half, y - gap, x + half, y - gap, l);
        cv.drawLine(x - half, y + gap, x + half, y + gap, l);
        Paint k = new Paint(Paint.ANTI_ALIAS_FLAG);
        k.setColor(0xFF2E2E33);
        Paint ks = new Paint(l);
        ks.setStyle(Paint.Style.STROKE);
        cv.drawCircle(x + half * 0.35f, y - gap, r * 0.1f, k);
        cv.drawCircle(x + half * 0.35f, y - gap, r * 0.1f, ks);
        cv.drawCircle(x - half * 0.35f, y + gap, r * 0.1f, k);
        cv.drawCircle(x - half * 0.35f, y + gap, r * 0.1f, ks);
    }
}
