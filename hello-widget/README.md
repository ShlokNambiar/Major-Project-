# Hello Widget (Android)

An iOS-style "hello" home-screen widget for Android:

> *hello* [● 09] Thu
> It's 🕕 6:15 PM , [22° ⛅]

- **Fonts**: Inter SemiBold for text (closest open match to SF Pro); "hello" is a hand-traced vector of the Apple-style lettering
- **Date / day / time / analog clock**: live, ticks every minute (uses `TextClock` / `AnalogClock`, no battery drain)
- **Weather**: real current temperature + condition from [Open-Meteo](https://open-meteo.com) (free, no API key), refreshes every 30 min
- Location: typed city → device location (if allowed) → IP-based fallback
- Taps: date → calendar, clock → alarms, weather → refresh, "hello" → settings

## Install
1. Copy `HelloWidget.apk` to your phone and open it (allow "install unknown apps").
2. Open **Hello Widget**, tap **Add widget to home screen** (or long-press home → Widgets → Hello Widget).
3. Optionally tap **Use my location** or type a city, and toggle °F.

## Build
```
./gradlew assembleRelease   # needs ANDROID_HOME / local.properties pointing at an SDK with platform 34
```
