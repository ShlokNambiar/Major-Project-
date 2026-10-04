package com.hello.widget;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentUris;
import android.content.Intent;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.text.format.DateUtils;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Locale;

/** Lists recordings made by the recorder widget: tap to play, long-press to share or delete. */
public class RecordingsActivity extends Activity {

    private static final int BG = 0xFF0E0E12, SURFACE = 0xFF1A1A20;
    private LinearLayout list;
    private Typeface bold, medium;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        bold = getResources().getFont(R.font.inter_bold);
        medium = getResources().getFont(R.font.inter_medium);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(28), dp(20), dp(32));
        root.addView(text("Recordings", 28, Color.WHITE, bold));

        TextView record = text("", 15, 0xFF15151A, bold);
        record.setGravity(Gravity.CENTER);
        record.setPadding(dp(16), dp(14), dp(16), dp(14));
        record.setBackground(round(0xFFFF453A, dp(18)));
        record.setTextColor(Color.WHITE);
        record.setOnClickListener(v -> {
            if (RecorderService.state == RecorderService.State.IDLE) {
                startActivity(new Intent(this, RecordActivity.class));
            } else {
                startService(RecorderService.intent(this, RecorderService.ACTION_STOP));
            }
            v.postDelayed(this::reload, 600);
        });
        root.addView(record, lp(dp(16)));
        root.setTag(record);

        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        root.addView(list, lp(dp(8)));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.addView(root);
        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        reload();
    }

    private void reload() {
        TextView record = (TextView) ((ViewGroup) list.getParent()).getTag();
        record.setText(RecorderService.state == RecorderService.State.IDLE ? "● Start recording" : "■ Stop & save");
        list.removeAllViews();
        if (Build.VERSION.SDK_INT < 29) {
            list.addView(text("Recordings are saved in Android/data/" + getPackageName() + "/files/Music/"
                    + RecorderService.FOLDER, 13, 0x8CFFFFFF, medium), lp(dp(12)));
            return;
        }
        String[] proj = {MediaStore.Audio.Media._ID, MediaStore.Audio.Media.DISPLAY_NAME,
                MediaStore.Audio.Media.DURATION, MediaStore.Audio.Media.DATE_ADDED};
        int count = 0;
        try (Cursor c = getContentResolver().query(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, proj,
                MediaStore.Audio.Media.RELATIVE_PATH + " LIKE ?", new String[]{"%/" + RecorderService.FOLDER + "/%"},
                MediaStore.Audio.Media.DATE_ADDED + " DESC")) {
            while (c != null && c.moveToNext()) {
                Uri uri = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, c.getLong(0));
                addRow(uri, c.getString(1), c.getLong(2), c.getLong(3) * 1000);
                count++;
            }
        }
        if (count == 0) {
            list.addView(text("No recordings yet — tap the red button on the widget or above.", 14, 0x8CFFFFFF, medium), lp(dp(16)));
        }
    }

    private void addRow(Uri uri, String name, long durationMs, long addedMs) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(dp(16), dp(14), dp(16), dp(14));
        row.setBackground(round(SURFACE, dp(16)));
        row.addView(text(name.replace(".m4a", ""), 15, Color.WHITE, bold));
        long s = durationMs / 1000;
        String meta = String.format(Locale.US, "%d:%02d", s / 60, s % 60) + " · "
                + DateUtils.getRelativeTimeSpanString(addedMs);
        row.addView(text(meta, 12.5f, 0x8CFFFFFF, medium));
        row.setOnClickListener(v -> startActivity(new Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "audio/mp4").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)));
        row.setOnLongClickListener(v -> {
            new AlertDialog.Builder(this)
                    .setTitle(name)
                    .setItems(new String[]{"Share", "Delete"}, (d, which) -> {
                        if (which == 0) {
                            startActivity(Intent.createChooser(new Intent(Intent.ACTION_SEND).setType("audio/mp4")
                                    .putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION), "Share"));
                        } else {
                            getContentResolver().delete(uri, null, null);
                            reload();
                        }
                    }).show();
            return true;
        });
        list.addView(row, lp(dp(10)));
    }

    private TextView text(String s, float sp, int color, Typeface tf) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setTypeface(tf);
        return t;
    }

    private GradientDrawable round(int color, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius);
        return d;
    }

    private LinearLayout.LayoutParams lp(int top) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = top;
        return p;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
