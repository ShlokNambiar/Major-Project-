package com.hello.widget;

import android.Manifest;
import android.app.Activity;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

public class MainActivity extends Activity {

    private TextView status;
    private static final int BG = 0xFF0E0E12;
    private LinearLayout previews;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(dp(20), dp(32), dp(20), dp(32));

        TextView title = text("Hello Widget", 28);
        col.addView(title);
        col.addView(text("Live previews · tap Add to place one on your home screen", 14), lp(dp(8), 0));

        previews = new LinearLayout(this);
        previews.setOrientation(LinearLayout.VERTICAL);
        col.addView(previews, lp(dp(8), 0));

        col.addView(text("Settings", 18), lp(dp(28), 0));
        col.addView(button("Allow calendar access (for Up next)", v -> requestPermissions(
                new String[]{Manifest.permission.READ_CALENDAR}, 2)), lp(dp(12), 0));
        col.addView(button("Use my location for weather", v -> useLocation()), lp(dp(10), 0));
        col.addView(button("Keep clock exact (disable battery optimisation)", v -> exemptBattery()), lp(dp(10), 0));

        LinearLayout cityRow = new LinearLayout(this);
        cityRow.setGravity(Gravity.CENTER_VERTICAL);
        EditText city = new EditText(this);
        city.setHint("…or type a city");
        city.setSingleLine(true);
        city.setTextColor(Color.WHITE);
        city.setHintTextColor(0x99FFFFFF);
        cityRow.addView(city, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        cityRow.addView(button("Set", v -> setCity(city.getText().toString())));
        col.addView(cityRow, lp(dp(10), 0));

        Switch unit = new Switch(this);
        unit.setText("Show °F");
        unit.setTextColor(Color.WHITE);
        unit.setChecked(Weather.fahrenheit(this));
        unit.setOnCheckedChangeListener((b, on) -> {
            Weather.prefs(this).edit().putBoolean("fahrenheit", on).apply();
            refresh();
        });
        col.addView(unit, lp(dp(16), 0));

        col.addView(button("Refresh weather now", v -> refresh()), lp(dp(16), 0));

        status = text("", 13);
        status.setAlpha(0.85f);
        col.addView(status, lp(dp(16), 0));

        TextView tips = text("Tips: on the hello widget tap the date for your calendar, the clock for alarms "
                + "and the weather pill to refresh. Calendar widgets open your calendar. "
                + "Weather updates every 30 min (Open-Meteo).", 13);
        tips.setAlpha(0.7f);
        col.addView(tips, lp(dp(16), 0));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.addView(col);
        setContentView(scroll);

        bindPreview();
        if (Weather.cached(this) == null) refresh();
    }

    private void bindPreview() {
        previews.removeAllViews();
        android.widget.FrameLayout hello = new android.widget.FrameLayout(this);
        hello.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{0xFF3338E6, 0xFF5B3FD6}));
        ((GradientDrawable) hello.getBackground()).setCornerRadius(dp(30));
        hello.addView(HelloWidgetProvider.buildViews(this).apply(this, hello));
        addPreview("hello", hello, HelloWidgetProvider.class);
        addCanvasPreview("Void · Weather", new VoidWidgetProvider());
        addCanvasPreview("Calendar", new CalendarWidgetProvider());
        addCanvasPreview("Calendar · Up next", new AgendaWidgetProvider());
        Weather.Cached w = Weather.cached(this);
        if (w != null) {
            status.setText("Weather for " + w.place + " · updated "
                    + DateFormat.getTimeFormat(this).format(w.time));
        }
    }

    private void refresh() {
        status.setText("Updating weather…");
        new Thread(() -> {
            String err = null;
            try {
                Weather.fetchAndStore(this);
            } catch (Exception e) {
                err = "Couldn't load weather: " + e.getMessage();
            }
            HelloWidgetProvider.updateAll(this);
            CanvasWidget.updateAll(this, VoidWidgetProvider.class);
            final String msg = err;
            runOnUiThread(() -> {
                bindPreview();
                if (msg != null) status.setText(msg);
            });
        }).start();
    }

    private void setCity(String q) {
        if (q.trim().isEmpty()) return;
        status.setText("Looking up " + q + "…");
        new Thread(() -> {
            try {
                String name = Weather.setCity(this, q);
                if (name == null) {
                    runOnUiThread(() -> status.setText("City not found"));
                    return;
                }
                runOnUiThread(this::refresh);
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Lookup failed: " + e.getMessage()));
            }
        }).start();
    }

    private void useLocation() {
        Weather.prefs(this).edit().putBoolean("use_city", false).apply();
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != 0) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_COARSE_LOCATION}, 1);
        } else {
            refresh();
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (code == 2) {
            CanvasWidget.updateAll(this, AgendaWidgetProvider.class);
            bindPreview();
            return;
        }
        refresh();
    }

    private void exemptBattery() {
        android.os.PowerManager pm = getSystemService(android.os.PowerManager.class);
        if (pm.isIgnoringBatteryOptimizations(getPackageName())) {
            status.setText("Battery optimisation is already off for Hello Widget ✓");
            return;
        }
        startActivity(new android.content.Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                android.net.Uri.parse("package:" + getPackageName())));
    }

    @Override
    protected void onResume() {
        super.onResume();
        TickReceiver.schedule(this);
        HelloWidgetProvider.updateAll(this);
        CanvasWidget.updateAll(this, VoidWidgetProvider.class);
        CanvasWidget.updateAll(this, CalendarWidgetProvider.class);
        CanvasWidget.updateAll(this, AgendaWidgetProvider.class);
        if (status != null) bindPreview();
    }

    private void addCanvasPreview(String name, CanvasWidget widget) {
        ImageView img = new ImageView(this);
        img.setImageBitmap(widget.render(this, (int) CanvasWidget.DESIGN_W, (int) CanvasWidget.DESIGN_H));
        img.setAdjustViewBounds(true);
        addPreview(name, img, widget.getClass());
    }

    private void addPreview(String name, View view, Class<?> provider) {
        LinearLayout head = new LinearLayout(this);
        head.setGravity(Gravity.CENTER_VERTICAL);
        TextView label = text(name, 15);
        head.addView(label, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        head.addView(button("Add", v -> pinWidget(provider)));
        previews.addView(head, lp(dp(20), 0));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                view instanceof ImageView ? ViewGroup.LayoutParams.WRAP_CONTENT : dp(170));
        p.topMargin = dp(8);
        previews.addView(view, p);
    }

    private void pinWidget(Class<?> provider) {
        AppWidgetManager m = getSystemService(AppWidgetManager.class);
        if (m != null && m.isRequestPinAppWidgetSupported()) {
            m.requestPinAppWidget(new ComponentName(this, provider), null, null);
        } else {
            status.setText("Long-press your home screen → Widgets → Hello Widget");
        }
    }

    private TextView text(String s, int sp) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(Color.WHITE);
        return t;
    }

    private Button button(String label, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextColor(0xFF2B2670);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xFFD9D4FF);
        bg.setCornerRadius(dp(24));
        b.setBackground(bg);
        b.setPadding(dp(18), 0, dp(18), 0);
        b.setOnClickListener(l);
        return b;
    }

    private LinearLayout.LayoutParams lp(int top, int bottom) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = top;
        p.bottomMargin = bottom;
        return p;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}
