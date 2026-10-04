package com.hello.widget;

import android.Manifest;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;

/** Live weather from Open-Meteo (free, no API key). */
final class Weather {

    static final String PREFS = "hello_widget";

    static final class Cached {
        final String temp, icon, place;
        final long time;
        Cached(String temp, String icon, String place, long time) {
            this.temp = temp; this.icon = icon; this.place = place; this.time = time;
        }
    }

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static Cached cached(Context c) {
        SharedPreferences p = prefs(c);
        if (!p.contains("temp")) return null;
        return new Cached(p.getString("temp", "--"), p.getString("icon", "⛅"),
                p.getString("place", ""), p.getLong("time", 0));
    }

    static boolean fahrenheit(Context c) {
        return prefs(c).getBoolean("fahrenheit", false);
    }

    /** Blocking: resolve location, fetch current conditions + 7-day strip, store them. Off main thread. */
    static void fetchAndStore(Context c) throws Exception {
        double[] loc = resolveLocation(c);
        String unit = fahrenheit(c) ? "fahrenheit" : "celsius";
        JSONObject res = new JSONObject(get("https://api.open-meteo.com/v1/forecast?latitude=" + loc[0]
                + "&longitude=" + loc[1] + "&current=temperature_2m,weather_code,is_day"
                + "&daily=weather_code,temperature_2m_max,temperature_2m_min"
                + "&past_days=3&forecast_days=4&timezone=auto"
                + "&temperature_unit=" + unit));
        JSONObject cur = res.getJSONObject("current");
        int code = cur.getInt("weather_code");
        long temp = Math.round(cur.getDouble("temperature_2m"));
        String icon = icon(code, cur.optInt("is_day", 1) == 1);
        prefs(c).edit()
                .putString("temp", String.valueOf(temp))
                .putString("icon", icon)
                .putString("condition", condition(code))
                .putString("daily", res.getJSONObject("daily").toString())
                .putLong("time", System.currentTimeMillis())
                .apply();
    }

    /** One day of the 7-day strip (3 past days, today, 3 ahead). */
    static final class Day {
        final String date; final long max, min; final int code;
        Day(String date, long max, long min, int code) { this.date = date; this.max = max; this.min = min; this.code = code; }
    }

    /** Daily forecast keyed by ISO date (yyyy-MM-dd), or empty if not fetched yet. */
    static java.util.Map<String, Day> daily(Context c) {
        java.util.Map<String, Day> out = new java.util.HashMap<>();
        try {
            JSONObject d = new JSONObject(prefs(c).getString("daily", "{}"));
            JSONArray t = d.getJSONArray("time"), mx = d.getJSONArray("temperature_2m_max"),
                    mn = d.getJSONArray("temperature_2m_min"), wc = d.getJSONArray("weather_code");
            for (int i = 0; i < t.length(); i++) {
                out.put(t.getString(i), new Day(t.getString(i), Math.round(mx.optDouble(i)),
                        Math.round(mn.optDouble(i)), wc.optInt(i)));
            }
        } catch (Exception ignored) { }
        return out;
    }

    static String condition(Context c) {
        return prefs(c).getString("condition", "");
    }

    static String place(Context c) {
        return prefs(c).getString("place", "");
    }

    static String condition(int code) {
        if (code == 0) return "CLEAR";
        if (code == 1) return "MOSTLY CLEAR";
        if (code == 2) return "PARTLY CLOUDY";
        if (code == 3) return "OVERCAST";
        if (code == 45 || code == 48) return "FOGGY";
        if (code >= 51 && code <= 57) return "DRIZZLE";
        if (code >= 61 && code <= 67) return "RAIN";
        if (code >= 71 && code <= 77) return "SNOW";
        if (code >= 80 && code <= 82) return "SHOWERS";
        if (code == 85 || code == 86) return "SNOW SHOWERS";
        if (code >= 95) return "THUNDERSTORM";
        return "";
    }

    /** Manual city > device location > IP geolocation. */
    static double[] resolveLocation(Context c) throws Exception {
        SharedPreferences p = prefs(c);
        if (p.getBoolean("use_city", false) && p.contains("city_lat")) {
            p.edit().putString("place", p.getString("city_name", "")).apply();
            return new double[]{p.getFloat("city_lat", 0), p.getFloat("city_lon", 0)};
        }
        if (c.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            LocationManager lm = (LocationManager) c.getSystemService(Context.LOCATION_SERVICE);
            Location best = null;
            for (String provider : lm.getProviders(true)) {
                try {
                    Location l = lm.getLastKnownLocation(provider);
                    if (l != null && (best == null || l.getTime() > best.getTime())) best = l;
                } catch (SecurityException ignored) { }
            }
            if (best != null) {
                p.edit().putString("place", cityName(c, best.getLatitude(), best.getLongitude())).apply();
                return new double[]{best.getLatitude(), best.getLongitude()};
            }
        }
        JSONObject ip = new JSONObject(get("https://get.geojs.io/v1/ip/geo.json"));
        p.edit().putString("place", ip.optString("city", "Approximate location")).apply();
        return new double[]{ip.getDouble("latitude"), ip.getDouble("longitude")};
    }

    /** Reverse-geocodes to a city name; falls back to a generic label. */
    private static String cityName(Context c, double lat, double lon) {
        try {
            if (android.location.Geocoder.isPresent()) {
                java.util.List<android.location.Address> a =
                        new android.location.Geocoder(c, java.util.Locale.getDefault()).getFromLocation(lat, lon, 1);
                if (a != null && !a.isEmpty()) {
                    String city = a.get(0).getLocality();
                    if (city == null) city = a.get(0).getSubAdminArea();
                    if (city == null) city = a.get(0).getAdminArea();
                    if (city != null) return city;
                }
            }
        } catch (Exception ignored) { }
        return "Current location";
    }

    /** Looks up a city name; returns {lat, lon} and stores it as the manual location. */
    static String setCity(Context c, String query) throws Exception {
        JSONObject res = new JSONObject(get("https://geocoding-api.open-meteo.com/v1/search?count=1&name="
                + URLEncoder.encode(query.trim(), "UTF-8")));
        JSONArray arr = res.optJSONArray("results");
        if (arr == null || arr.length() == 0) return null;
        JSONObject r = arr.getJSONObject(0);
        String name = r.getString("name");
        prefs(c).edit()
                .putBoolean("use_city", true)
                .putString("city_name", name)
                .putFloat("city_lat", (float) r.getDouble("latitude"))
                .putFloat("city_lon", (float) r.getDouble("longitude"))
                .apply();
        return name;
    }

    /** WMO weather code -> emoji, matching the iOS-style colour icons. */
    static String icon(int code, boolean day) {
        if (code == 0) return day ? "☀️" : "🌙";
        if (code == 1) return day ? "🌤️" : "🌙";
        if (code == 2) return day ? "⛅" : "☁️";
        if (code == 3) return "☁️";
        if (code == 45 || code == 48) return "🌫️";
        if (code >= 51 && code <= 57) return "🌦️";
        if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return "🌧️";
        if ((code >= 71 && code <= 77) || code == 85 || code == 86) return "🌨️";
        if (code >= 95) return "⛈️";
        return "⛅";
    }

    private static String get(String url) throws Exception {
        HttpURLConnection con = (HttpURLConnection) new URL(url).openConnection();
        con.setConnectTimeout(10000);
        con.setReadTimeout(10000);
        con.setRequestProperty("User-Agent", "HelloWidget/1.0");
        try (BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), "UTF-8"))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) sb.append(line);
            return sb.toString();
        } finally {
            con.disconnect();
        }
    }
}
