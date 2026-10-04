package com.hello.widget;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Full-screen ringing screen shown over the lock screen. The sound comes from the notification. */
public class AlarmRingActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setStatusBarColor(Color.BLACK);
        getWindow().setNavigationBarColor(Color.BLACK);
        int id = getIntent().getIntExtra(AlarmReceiver.EXTRA_ID, -1);
        Typeface bold = getResources().getFont(R.font.inter_bold);
        Typeface medium = getResources().getFont(R.font.inter_medium);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.BLACK);
        root.setPadding(dp(28), dp(28), dp(28), dp(48));

        TextView label = text("Alarm", 20, 0xFFFF7A1A, medium);
        root.addView(label);
        TextView time = text(DateFormat.getTimeFormat(this).format(System.currentTimeMillis()), 76, Color.WHITE, bold);
        root.addView(time);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.VERTICAL);
        buttons.setPadding(0, dp(64), 0, 0);
        if (Alarms.snooze(this) && Alarms.prefs(this).getInt("snooze_count", 0) < Alarms.SNOOZE_MAX) {
            buttons.addView(button("Snooze · 5 min", 0xFF2C2C2E, Color.WHITE, bold, () -> send(AlarmReceiver.ACTION_SNOOZE, id)), lp(0));
        }
        buttons.addView(button("Stop", 0xFFFF6A1A, Color.WHITE, bold, () -> send(AlarmReceiver.ACTION_DISMISS, id)), lp(dp(12)));
        root.addView(buttons, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        setContentView(root);
    }

    private void send(String action, int id) {
        try {
            AlarmReceiver.action(this, action, id, action.hashCode()).send();
        } catch (Exception ignored) { }
        finish();
    }

    private TextView text(String s, float sp, int color, Typeface tf) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setTypeface(tf);
        t.setGravity(Gravity.CENTER);
        return t;
    }

    private TextView button(String s, int bg, int fg, Typeface tf, Runnable r) {
        TextView b = text(s, 18, fg, tf);
        b.setPadding(0, dp(18), 0, dp(18));
        GradientDrawable d = new GradientDrawable();
        d.setColor(bg);
        d.setCornerRadius(dp(30));
        b.setBackground(d);
        b.setOnClickListener(v -> r.run());
        return b;
    }

    private LinearLayout.LayoutParams lp(int top) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        p.topMargin = top;
        return p;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
