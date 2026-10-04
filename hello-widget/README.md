# Hello Widget (Android)

Four home-screen widgets in one app:

| Widget | What it shows |
|---|---|
| **hello** | *hello* · date pill · day / analog clock · time · live weather pill |
| **Void · Weather** | Pixel clock, 7-day strip (3 past days, today with current weather, 3-day forecast high/low), condition + city |
| **Calendar** | `2026.07`, big date, full date, day-of-year, month grid with today circled |
| **Calendar · Up next** | Same date block plus your next 3 calendar events (colour bar, title, time) |

Fonts: Inter (SemiBold/Bold), Departure Mono for the Void widget (OFL, see `licenses/`).

## The hello widget

An iOS-style "hello" home-screen widget for Android:

> *hello* [● 09] Thu
> It's 🕕 6:15 PM , [22° ⛅]

- **Fonts**: text and pills are drawn in-app with Inter SemiBold (launchers ignore custom widget fonts), redrawn every minute; "hello" is a hand-traced vector of the Apple-style lettering
- On OxygenOS/ColorOS, tap "Keep clock exact" in the app so battery optimisation never pauses the minute updates
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
