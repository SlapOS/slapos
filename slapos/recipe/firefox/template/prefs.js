// Don't ask if we want to switch default browsers
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");

// disable application updates
user_pref("app.update.enabled", false)

// disables the 'know your rights' button from displaying on first run
user_pref("browser.rights.3.shown", true);

// Disable pop-up blocking
user_pref("browser.allowpopups", true);
user_pref("dom.disable_open_during_load", false);
user_pref("browser.tabs.warnOnClose", false);

// Configure us as the local proxy
//user_pref("network.proxy.type", 2);

// Disable security warnings
user_pref("security.warn_submit_insecure", false);
user_pref("security.warn_submit_insecure.show_once", false);
user_pref("security.warn_entering_secure", false);
user_pref("security.warn_entering_secure.show_once", false);
user_pref("security.warn_entering_weak", false);
user_pref("security.warn_entering_weak.show_once", false);
user_pref("security.warn_leaving_secure", false);
user_pref("security.warn_leaving_secure.show_once", false);
user_pref("security.warn_viewing_mixed", false);
user_pref("security.warn_viewing_mixed.show_once", false);

// Disable "do you want to remember this password?"
user_pref("signon.rememberSignons", false);

// increase the timeout before warning of unresponsive script
user_pref("dom.max_script_run_time", 120);

// this is required to upload files
// user_pref("capability.principal.codebase.p1.granted", "UniversalFileRead");
// user_pref("signed.applets.codebase_principal_support", true);
// user_pref("capability.principal.codebase.p1.id", "http://");
// user_pref("capability.principal.codebase.p1.subjectName", "");

user_pref("browser.link.open_external", 3);
user_pref("browser.link.open_newwindow", 3);

// disables the request to send performance data from displaying
user_pref("toolkit.telemetry.prompted", 2);
user_pref("toolkit.telemetry.rejected", true);

user_pref("browser.migration.version", 5);
user_pref("extensions.SelectionUI", true);
user_pref("network.cookie.prefsMigrated", true);
user_pref("browser.bookmarks.restore_default_bookmarks", false);
user_pref("browser.places.smartBookmarksVersion", 2);
user_pref("privacy.sanitize.migrateFx3Prefs", true);
