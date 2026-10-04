package com.hello.widget;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.os.Bundle;

/** Invisible trampoline used by icon shortcuts and icon widgets: opens the target app and exits. */
public class LaunchActivity extends Activity {

    static final String EXTRA_PKG = "pkg";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String pkg = getIntent().getStringExtra(EXTRA_PKG);
        if (pkg != null) {
            try {
                startActivity(Icons.launchIntent(this, pkg));
            } catch (ActivityNotFoundException ignored) {
                // neither the app nor a store is available
            }
        }
        finish();
        overridePendingTransition(0, 0);
    }
}
