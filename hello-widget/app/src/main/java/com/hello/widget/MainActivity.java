package com.hello.widget;

import android.Manifest;
import android.app.Activity;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

/** Gallery of widgets and icons, grouped into tabs and categories, plus settings. */
public class MainActivity extends Activity {

    private static final int BG = 0xFF0E0E12, SURFACE = 0xFF1A1A20, ACCENT = 0xFFD9D4FF;
    private static final int REQ_LOCATION = 1, REQ_CALENDAR = 2;
    private static final String[] TABS = {"Widgets", "Icons", "Settings"};

    private LinearLayout content;
    private LinearLayout tabBar;
    private int tab = 0;
    private TextView status;
    private Typeface bold, medium;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        bold = getResources().getFont(R.font.inter_bold);
        medium = getResources().getFont(R.font.inter_medium);
        if (savedInstanceState != null) tab = savedInstanceState.getInt("tab", 0);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(28), dp(20), dp(32));

        TextView title = text("Hello Widget", 30, Color.WHITE, bold);
        root.addView(title);
        TextView sub = text("Widgets and icons for your home screen", 14, 0x99FFFFFF, medium);
        root.addView(sub, lp(dp(2)));

        tabBar = new LinearLayout(this);
        tabBar.setPadding(dp(4), dp(4), dp(4), dp(4));
        tabBar.setBackground(round(SURFACE, dp(22)));
        root.addView(tabBar, lp(dp(20)));

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        root.addView(content, lp(dp(8)));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);
        scroll.addView(root);
        setContentView(scroll);

        status = text("", 13, 0xB3FFFFFF, medium);
        showTab(tab);
        if (Weather.cached(this) == null) refresh();
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        out.putInt("tab", tab);
    }

    @Override
    protected void onResume() {
        super.onResume();
        TickReceiver.schedule(this);
        updateAllWidgets();
        if (content != null && tab == 0) showTab(0);
    }

    private void updateAllWidgets() {
        HelloWidgetProvider.updateAll(this);
        CanvasWidget.updateAll(this, VoidWidgetProvider.class);
        CanvasWidget.updateAll(this, CalendarWidgetProvider.class);
        CanvasWidget.updateAll(this, AgendaWidgetProvider.class);
        CanvasWidget.updateAll(this, SkyWidgetProvider.class);
        CanvasWidget.updateAll(this, RecorderWidgetProvider.class);
        CanvasWidget.updateAll(this, AlarmWidgetProvider.class);
        Alarms.schedule(this);
    }

    // ---------------------------------------------------------------- tabs

    private void showTab(int index) {
        tab = index;
        tabBar.removeAllViews();
        for (int i = 0; i < TABS.length; i++) {
            final int t = i;
            TextView b = text(TABS[i], 14, i == tab ? 0xFF15151A : 0xCCFFFFFF, bold);
            b.setGravity(Gravity.CENTER);
            b.setPadding(0, dp(10), 0, dp(10));
            if (i == tab) b.setBackground(round(ACCENT, dp(18)));
            b.setOnClickListener(v -> showTab(t));
            tabBar.addView(b, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        }
        content.removeAllViews();
        if (status.getParent() != null) ((ViewGroup) status.getParent()).removeView(status);
        if (tab == 0) buildWidgets();
        else if (tab == 1) buildIcons();
        else buildSettings();
    }

    private void buildWidgets() {
        category("Clock & Weather");
        FrameLayout hello = new FrameLayout(this);
        GradientDrawable blue = new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{0xFF3338E6, 0xFF4A3FD6});
        blue.setCornerRadius(dp(24));
        hello.setBackground(blue);
        hello.addView(HelloWidgetProvider.buildViews(this).apply(this, hello));
        widgetCard("hello", "Greeting, date, time and live weather", hello, dp(170), HelloWidgetProvider.class);
        canvasCard("Void · Weather", "Pixel clock with a 7-day weather strip", new VoidWidgetProvider());
        canvasCard("Sky", "Sun and moon follow your real sunrise and sunset", new SkyWidgetProvider());

        category("Calendar");
        canvasCard("Calendar", "Big date and this month at a glance", new CalendarWidgetProvider());
        canvasCard("Calendar · Up next", "Big date with your next events", new AgendaWidgetProvider());

        category("Tools");
        canvasCard("Recorder", "Record voice notes right from your home screen", new RecorderWidgetProvider(),
                "Recordings", RecordingsActivity.class);
        canvasCard("Alarm", "Your next alarm with quick on/off, skip, vibration and snooze", new AlarmWidgetProvider(),
                "Alarms", AlarmsActivity.class);
    }

    private void buildIcons() {
        category("Music");
        for (Icons.AppIcon icon : Icons.ALL) iconCard(icon);

        category("Icon widget style");
        Switch label = new Switch(this);
        label.setText("Show app name under icon");
        label.setTextColor(Color.WHITE);
        label.setTypeface(medium);
        label.setChecked(IconWidgetProvider.prefs(this).getBoolean("show_label", false));
        label.setOnCheckedChangeListener((b, on) -> {
            IconWidgetProvider.prefs(this).edit().putBoolean("show_label", on).apply();
            IconWidgetProvider.updateAll(this);
        });
        content.addView(label, lp(dp(6)));

        content.addView(text("Icon size — match your home screen icons", 13.5f, 0xCCFFFFFF, medium), lp(dp(16)));
        LinearLayout sizes = new LinearLayout(this);
        sizes.setPadding(dp(4), dp(4), dp(4), dp(4));
        sizes.setBackground(round(SURFACE, dp(20)));
        String[] names = {"S", "M", "L", "XL"};
        int current = IconWidgetProvider.prefs(this).getInt("size", IconWidgetProvider.DEFAULT_SIZE);
        for (int i = 0; i < names.length; i++) {
            final int size = IconWidgetProvider.SIZES[i];
            boolean on = size == current;
            TextView b = text(names[i], 14, on ? 0xFF15151A : 0xCCFFFFFF, bold);
            b.setGravity(Gravity.CENTER);
            b.setPadding(0, dp(9), 0, dp(9));
            if (on) b.setBackground(round(ACCENT, dp(16)));
            b.setOnClickListener(v -> {
                IconWidgetProvider.prefs(this).edit().putInt("size", size).apply();
                IconWidgetProvider.updateAll(this);
                showTab(1);
            });
            sizes.addView(b, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        }
        content.addView(sizes, lp(dp(8)));
        TextView note = text("Android doesn't let one app change another app's icon, so each icon can be "
                + "added as a 1×1 icon widget (looks like a normal icon, no badge) or as a shortcut. "
                + "Launchers that support icon packs (Nova, Lawnchair…) can also pick Hello Widget as an icon pack.",
                13, 0x80FFFFFF, medium);
        content.addView(note, lp(dp(18)));
    }

    private void buildSettings() {
        category("Weather");
        content.addView(button("Use my location", v -> useLocation()), lp(dp(4)));

        LinearLayout cityRow = new LinearLayout(this);
        cityRow.setGravity(Gravity.CENTER_VERTICAL);
        EditText city = new EditText(this);
        city.setHint("…or type a city");
        city.setSingleLine(true);
        city.setTextColor(Color.WHITE);
        city.setHintTextColor(0x80FFFFFF);
        cityRow.addView(city, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        cityRow.addView(button("Set", v -> setCity(city.getText().toString())));
        content.addView(cityRow, lp(dp(8)));

        Switch unit = new Switch(this);
        unit.setText("Show °F");
        unit.setTextColor(Color.WHITE);
        unit.setTypeface(medium);
        unit.setChecked(Weather.fahrenheit(this));
        unit.setOnCheckedChangeListener((b, on) -> {
            Weather.prefs(this).edit().putBoolean("fahrenheit", on).apply();
            refresh();
        });
        content.addView(unit, lp(dp(12)));
        content.addView(button("Refresh weather now", v -> refresh()), lp(dp(12)));
        content.addView(status, lp(dp(10)));
        showWeatherStatus();

        category("Calendar");
        boolean cal = AgendaWidgetProvider.hasPermission(this);
        content.addView(button(cal ? "Calendar access allowed ✓" : "Allow calendar access (for Up next)",
                v -> requestPermissions(new String[]{Manifest.permission.READ_CALENDAR}, REQ_CALENDAR)), lp(dp(4)));

        category("Reliability");
        content.addView(button("Keep clocks exact (disable battery optimisation)", v -> exemptBattery()), lp(dp(4)));
        TextView hint = text("OxygenOS and other battery savers can pause the per-minute clock updates. "
                + "Allowing this keeps every clock widget on time.", 13, 0x80FFFFFF, medium);
        content.addView(hint, lp(dp(8)));
    }

    // ---------------------------------------------------------------- building blocks

    private void category(String name) {
        TextView t = text(name.toUpperCase(), 12, 0x80FFFFFF, bold);
        t.setLetterSpacing(0.1f);
        content.addView(t, lp(dp(26)));
    }

    private void canvasCard(String name, String desc, CanvasWidget widget) {
        canvasCard(name, desc, widget, null, null);
    }

    /** Preview at the widget's design size; square widgets are shown narrower like on a home screen. */
    private void canvasCard(String name, String desc, CanvasWidget widget, String openLabel, Class<?> open) {
        ImageView img = new ImageView(this);
        img.setImageBitmap(widget.render(this, (int) widget.designW(), (int) widget.designH()));
        img.setAdjustViewBounds(true);
        View preview = img;
        int height = ViewGroup.LayoutParams.WRAP_CONTENT;
        if (widget.designW() < CanvasWidget.DESIGN_W) {
            FrameLayout box = new FrameLayout(this);
            int side = dp((int) (widget.designW() >= 250 ? 240 : 170));
            box.addView(img, new FrameLayout.LayoutParams(side, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.START));
            preview = box;
        }
        widgetCard(name, desc, preview, height, widget.getClass(), openLabel, open);
    }

    private void widgetCard(String name, String desc, View preview, int previewHeight, Class<?> provider) {
        widgetCard(name, desc, preview, previewHeight, provider, null, null);
    }

    private void widgetCard(String name, String desc, View preview, int previewHeight, Class<?> provider,
                            String openLabel, Class<?> open) {
        LinearLayout head = new LinearLayout(this);
        head.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        titles.addView(text(name, 16, Color.WHITE, bold));
        titles.addView(text(desc, 12.5f, 0x8CFFFFFF, medium));
        head.addView(titles, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        if (open != null) {
            TextView o = pill(openLabel, v -> startActivity(new Intent(this, open)));
            o.setBackground(round(SURFACE, dp(18)));
            o.setTextColor(Color.WHITE);
            head.addView(o);
            View gap = new View(this);
            head.addView(gap, new LinearLayout.LayoutParams(dp(8), 1));
        }
        head.addView(pill("Add", v -> pinWidget(provider, null)));
        content.addView(head, lp(dp(12)));

        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, previewHeight);
        p.topMargin = dp(10);
        content.addView(preview, p);
    }

    private void iconCard(Icons.AppIcon icon) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(14), dp(14), dp(14), dp(14));
        row.setBackground(round(SURFACE, dp(20)));

        ImageView img = new ImageView(this);
        img.setImageResource(icon.rounded);
        row.addView(img, new LinearLayout.LayoutParams(dp(64), dp(64)));

        LinearLayout right = new LinearLayout(this);
        right.setOrientation(LinearLayout.VERTICAL);
        right.setPadding(dp(14), 0, 0, 0);
        right.addView(text(icon.label + " · Disco", 16, Color.WHITE, bold));
        right.addView(text("Opens " + icon.label, 12.5f, 0x8CFFFFFF, medium));
        LinearLayout actions = new LinearLayout(this);
        actions.addView(pill("Add icon", v -> pinWidget(IconWidgetProvider.class, icon)));
        View gap = new View(this);
        actions.addView(gap, new LinearLayout.LayoutParams(dp(8), 1));
        actions.addView(pill("Add shortcut", v -> pinShortcut(icon)));
        right.addView(actions, lp(dp(8)));
        row.addView(right, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        content.addView(row, lp(dp(12)));
    }

    // ---------------------------------------------------------------- actions

    private void pinWidget(Class<?> provider, Icons.AppIcon icon) {
        AppWidgetManager m = getSystemService(AppWidgetManager.class);
        if (m != null && m.isRequestPinAppWidgetSupported()) {
            m.requestPinAppWidget(new ComponentName(this, provider), null,
                    icon == null ? null : IconWidgetProvider.bindCallback(this, icon));
        } else {
            toast("Long-press your home screen → Widgets → Hello Widget");
        }
    }

    private void pinShortcut(Icons.AppIcon icon) {
        ShortcutManager sm = getSystemService(ShortcutManager.class);
        if (sm == null || !sm.isRequestPinShortcutSupported()) {
            toast("Your launcher doesn't support pinned shortcuts — use Add icon instead");
            return;
        }
        Intent launch = new Intent(this, LaunchActivity.class)
                .setAction(Intent.ACTION_VIEW)
                .putExtra(LaunchActivity.EXTRA_PKG, icon.pkg);
        ShortcutInfo info = new ShortcutInfo.Builder(this, "icon_" + icon.key)
                .setShortLabel(icon.label)
                .setIcon(Icon.createWithAdaptiveBitmap(BitmapFactory.decodeResource(getResources(), icon.full)))
                .setIntent(launch)
                .build();
        sm.requestPinShortcut(info, null);
    }

    private void showWeatherStatus() {
        Weather.Cached w = Weather.cached(this);
        if (w != null) {
            status.setText("Weather for " + (w.place.isEmpty() ? "your area" : w.place) + " · updated "
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
            CanvasWidget.updateAll(this, SkyWidgetProvider.class);
            final String msg = err;
            runOnUiThread(() -> {
                if (msg != null) status.setText(msg);
                else showWeatherStatus();
                if (tab == 0) showTab(0);
            });
        }).start();
    }

    private void setCity(String q) {
        if (q.trim().isEmpty()) return;
        status.setText("Looking up " + q + "…");
        new Thread(() -> {
            try {
                String name = Weather.setCity(this, q);
                runOnUiThread(() -> {
                    if (name == null) status.setText("City not found");
                    else refresh();
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Lookup failed: " + e.getMessage()));
            }
        }).start();
    }

    private void useLocation() {
        Weather.prefs(this).edit().putBoolean("use_city", false).apply();
        if (checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != 0) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_LOCATION);
        } else {
            refresh();
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (code == REQ_CALENDAR) {
            CanvasWidget.updateAll(this, AgendaWidgetProvider.class);
            showTab(tab);
            return;
        }
        refresh();
    }

    private void exemptBattery() {
        PowerManager pm = getSystemService(PowerManager.class);
        if (pm.isIgnoringBatteryOptimizations(getPackageName())) {
            toast("Battery optimisation is already off ✓");
            return;
        }
        startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                Uri.parse("package:" + getPackageName())));
    }

    private void toast(String s) {
        android.widget.Toast.makeText(this, s, android.widget.Toast.LENGTH_LONG).show();
    }

    // ---------------------------------------------------------------- view helpers

    private TextView text(String s, float sp, int color, Typeface tf) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setTypeface(tf);
        return t;
    }

    private TextView pill(String label, View.OnClickListener l) {
        TextView b = text(label, 13.5f, 0xFF15151A, bold);
        b.setPadding(dp(16), dp(8), dp(16), dp(8));
        b.setBackground(round(ACCENT, dp(18)));
        b.setOnClickListener(l);
        return b;
    }

    private TextView button(String label, View.OnClickListener l) {
        TextView b = text(label, 14.5f, Color.WHITE, bold);
        b.setGravity(Gravity.CENTER);
        b.setPadding(dp(16), dp(14), dp(16), dp(14));
        b.setBackground(round(SURFACE, dp(16)));
        b.setOnClickListener(l);
        return b;
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
