package com.hello.widget;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.app.NotificationManager;
import android.app.TimePickerDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

import java.text.DateFormatSymbols;
import java.util.Calendar;
import java.util.List;

/** Add, edit, repeat and delete the alarms shown on the alarm widget. */
public class AlarmsActivity extends Activity {

    static final String EXTRA_ADD = "add";
    private static final int BG = 0xFF0E0E12, SURFACE = 0xFF1A1A20, ORANGE = 0xFFFF6A1A;
    private LinearLayout list, warnings;
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
        root.addView(text("Alarms", 28, Color.WHITE, bold));

        warnings = new LinearLayout(this);
        warnings.setOrientation(LinearLayout.VERTICAL);
        root.addView(warnings, lp(0));

        TextView add = text("+  Add alarm", 15, Color.WHITE, bold);
        add.setGravity(Gravity.CENTER);
        add.setPadding(0, dp(14), 0, dp(14));
        add.setBackground(round(ORANGE, dp(18)));
        add.setOnClickListener(v -> pickTime(null));
        root.addView(add, lp(dp(16)));

        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        root.addView(list, lp(dp(4)));

        root.addView(text("OPTIONS", 12, 0x80FFFFFF, bold), lp(dp(28)));
        root.addView(toggle("Vibration", Alarms.vibrate(this), on ->
                Alarms.prefs(this).edit().putBoolean("vibrate", on).apply()), lp(dp(8)));
        root.addView(toggle("Snooze (5 min, 3 times)", Alarms.snooze(this), on ->
                Alarms.prefs(this).edit().putBoolean("snooze", on).apply()), lp(dp(8)));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.addView(root);
        setContentView(scroll);

        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
        if (getIntent().getBooleanExtra(EXTRA_ADD, false)) pickTime(null);
    }

    @Override
    protected void onResume() {
        super.onResume();
        reload();
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        reload();
    }

    private void reload() {
        warnings.removeAllViews();
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (!nm.areNotificationsEnabled()) {
            warning("Notifications are off — alarms can't ring. Tap to allow.",
                    new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, getPackageName()));
        }
        if (Build.VERSION.SDK_INT >= 34 && !nm.canUseFullScreenIntent()) {
            warning("Allow full-screen alarms so they show over the lock screen. Tap to allow.",
                    new Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:" + getPackageName())));
        }

        list.removeAllViews();
        List<Alarms.Alarm> alarms = Alarms.load(this);
        if (alarms.isEmpty()) {
            list.addView(text("No alarms yet.", 14, 0x8CFFFFFF, medium), lp(dp(16)));
        }
        for (Alarms.Alarm a : alarms) list.addView(row(a), lp(dp(12)));
    }

    private LinearLayout row(Alarms.Alarm a) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(dp(16), dp(12), dp(16), dp(14));
        row.setBackground(round(SURFACE, dp(18)));

        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout texts = new LinearLayout(this);
        texts.setOrientation(LinearLayout.VERTICAL);
        texts.addView(text(timeText(a.hour, a.minute), 34, a.on ? Color.WHITE : 0x66FFFFFF, bold));
        long now = System.currentTimeMillis();
        String sub = repeatText(a.days);
        if (a.on && a.skipping(now)) sub += " · skipping next";
        texts.addView(text(sub, 12.5f, 0x8CFFFFFF, medium));
        top.addView(texts, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        Switch sw = new Switch(this);
        sw.setChecked(a.on);
        sw.setOnCheckedChangeListener((b, on) -> update(a.id, x -> { x.on = on; x.skip = 0; }));
        top.addView(sw);
        row.addView(top);

        // Repeat-day chips
        LinearLayout days = new LinearLayout(this);
        String[] names = DateFormatSymbols.getInstance().getShortWeekdays();
        int first = Calendar.getInstance().getFirstDayOfWeek();
        for (int i = 0; i < 7; i++) {
            int dow = (first - 1 + i) % 7 + 1, bit = 1 << (dow - 1);
            boolean on = (a.days & bit) != 0;
            TextView chip = text(names[dow].substring(0, 1).toUpperCase(), 13, on ? Color.WHITE : 0x99FFFFFF, bold);
            chip.setGravity(Gravity.CENTER);
            chip.setBackground(round(on ? ORANGE : 0xFF2A2A30, dp(16)));
            chip.setOnClickListener(v -> update(a.id, x -> x.days ^= bit));
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(32), 1);
            p.setMarginEnd(i < 6 ? dp(6) : 0);
            days.addView(chip, p);
        }
        row.addView(days, lp(dp(10)));

        row.setOnClickListener(v -> pickTime(a));
        row.setOnLongClickListener(v -> {
            new AlertDialog.Builder(this).setTitle("Delete " + timeText(a.hour, a.minute) + "?")
                    .setPositiveButton("Delete", (d, w) -> {
                        List<Alarms.Alarm> all = Alarms.load(this);
                        all.removeIf(x -> x.id == a.id);
                        Alarms.save(this, all);
                        reload();
                    }).setNegativeButton("Cancel", null).show();
            return true;
        });
        return row;
    }

    private interface Edit { void apply(Alarms.Alarm a); }

    private void update(int id, Edit e) {
        List<Alarms.Alarm> all = Alarms.load(this);
        Alarms.Alarm a = Alarms.find(all, id);
        if (a != null) e.apply(a);
        Alarms.save(this, all);
        reload();
    }

    private void pickTime(Alarms.Alarm existing) {
        Calendar now = Calendar.getInstance();
        int h = existing != null ? existing.hour : now.get(Calendar.HOUR_OF_DAY);
        int m = existing != null ? existing.minute : now.get(Calendar.MINUTE);
        new TimePickerDialog(this, android.R.style.Theme_DeviceDefault_Dialog_Alert, (view, hour, minute) -> {
            if (existing == null) Alarms.add(this, hour, minute);
            else update(existing.id, x -> { x.hour = hour; x.minute = minute; x.on = true; x.skip = 0; });
            reload();
        }, h, m, DateFormat.is24HourFormat(this)).show();
    }

    private String timeText(int h, int m) {
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, h);
        c.set(Calendar.MINUTE, m);
        return DateFormat.getTimeFormat(this).format(c.getTime());
    }

    static String repeatText(int days) {
        if (days == 0) return "Once";
        if (days == 0x7F) return "Every day";
        if (days == 0x3E) return "Weekdays";
        if (days == 0x41) return "Weekends";
        String[] names = DateFormatSymbols.getInstance().getShortWeekdays();
        StringBuilder b = new StringBuilder();
        for (int d = 1; d <= 7; d++) {
            if ((days & (1 << (d - 1))) != 0) {
                if (b.length() > 0) b.append(", ");
                b.append(names[d]);
            }
        }
        return b.toString();
    }

    private void warning(String msg, Intent fix) {
        TextView t = text(msg, 13.5f, 0xFFFFD9C2, medium);
        t.setPadding(dp(14), dp(12), dp(14), dp(12));
        t.setBackground(round(0x33FF6A1A, dp(14)));
        t.setOnClickListener(v -> {
            try { startActivity(fix); } catch (Exception ignored) { }
        });
        warnings.addView(t, lp(dp(12)));
    }

    private interface OnToggle { void set(boolean on); }

    private Switch toggle(String label, boolean value, OnToggle t) {
        Switch s = new Switch(this);
        s.setText(label);
        s.setTextColor(Color.WHITE);
        s.setTypeface(medium);
        s.setTextSize(15);
        s.setChecked(value);
        s.setOnCheckedChangeListener((b, on) -> { t.set(on); Alarms.changed(this); });
        return s;
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
