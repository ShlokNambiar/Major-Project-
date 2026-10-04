package com.hello.widget;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;

/** The custom app icons in the pack. Add new ones to ALL (and to res/xml/appfilter.xml). */
final class Icons {

    static final class AppIcon {
        final String key, label, pkg;
        /** Rounded-square artwork for the icon widget / in-app preview. */
        final int rounded;
        /** Full-bleed artwork for adaptive shortcut icons and icon-pack launchers. */
        final int full;

        AppIcon(String key, String label, String pkg, int rounded, int full) {
            this.key = key; this.label = label; this.pkg = pkg; this.rounded = rounded; this.full = full;
        }
    }

    static final AppIcon[] ALL = {
            new AppIcon("spotify_disco", "Spotify", "com.spotify.music",
                    R.drawable.icon_spotify_disco, R.drawable.icon_spotify_disco_full),
    };

    static AppIcon byKey(String key) {
        for (AppIcon i : ALL) if (i.key.equals(key)) return i;
        return ALL[0];
    }

    /** Opens the target app, or its Play Store page if it isn't installed. */
    static Intent launchIntent(Context c, String pkg) {
        Intent i = c.getPackageManager().getLaunchIntentForPackage(pkg);
        if (i == null) {
            i = new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + pkg));
        }
        return i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    }
}
