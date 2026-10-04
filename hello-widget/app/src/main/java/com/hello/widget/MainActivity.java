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
    private View preview;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(getColor(R.color.brand_blue));
        getWindow().setNavigationBarColor(getColor(R.color.brand_blue));

        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(dp(20), dp(32), dp(20), dp(32));

        TextView title = text("Hello Widget", 28);
        col.addView(title);
        col.addView(text("Live preview", 14), lp(dp(24), 0));

        preview = getLayoutInflater().inflate(R.layout.widget_hello, col, false);
        col.addView(preview, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(170)));

        col.addView(button("Add widget to home screen", v -> pinWidget()), lp(dp(24), 0));
        col.addView(button("Use my location for weather", v -> useLocation()), lp(dp(10), 0));

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

        TextView tips = text("Tips: tap the date to open your calendar, the clock to open alarms, "
                + "the weather pill to refresh. Weather updates every 30 min (Open-Meteo).", 13);
        tips.setAlpha(0.7f);
        col.addView(tips, lp(dp(16), 0));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(getColor(R.color.brand_blue));
        scroll.addView(col);
        setContentView(scroll);

        bindPreview();
        if (Weather.cached(this) == null) refresh();
    }

    private void bindPreview() {
        ((ImageView) preview.findViewById(R.id.hello)).setImageBitmap(HelloText.render(this));
        Weather.Cached w = Weather.cached(this);
        ((TextView) preview.findViewById(R.id.temp)).setText(w == null ? "--°" : w.temp + "°");
        ((TextView) preview.findViewById(R.id.weather_icon)).setText(w == null ? "⛅" : w.icon);
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
        refresh();
    }

    private void pinWidget() {
        AppWidgetManager m = getSystemService(AppWidgetManager.class);
        if (m != null && m.isRequestPinAppWidgetSupported()) {
            m.requestPinAppWidget(new ComponentName(this, HelloWidgetProvider.class), null, null);
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
