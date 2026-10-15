import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val localProperties = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use(::load)
}
val dropboxAppKey = localProperties.getProperty("ND_GERMAN_DROPBOX_APP_KEY", "")
// Sample IDs are only manifest placeholders for a local preview; no ads may load
// until both real AdMob IDs have explicitly been configured.
val configuredAdMobAppId = localProperties.getProperty("ND_GERMAN_ADMOB_APP_ID", "").trim()
val configuredAdMobBannerId = localProperties.getProperty("ND_GERMAN_ADMOB_BANNER_ID", "").trim()
val realAdMobIdsConfigured =
    Regex("""ca-app-pub-\d{16}~\d{10}""").matches(configuredAdMobAppId) &&
        Regex("""ca-app-pub-\d{16}/\d{10}""").matches(configuredAdMobBannerId) &&
        !configuredAdMobAppId.startsWith("ca-app-pub-3940256099942544") &&
        !configuredAdMobBannerId.startsWith("ca-app-pub-3940256099942544")
val admobAppId =
    if (realAdMobIdsConfigured) configuredAdMobAppId
    else "ca-app-pub-3940256099942544~3347511713"
val admobBannerId =
    if (realAdMobIdsConfigured) configuredAdMobBannerId
    else "ca-app-pub-3940256099942544/6300978111"

// A dedicated upload certificate lives outside the repo/Dropbox; never check it in.
val playSigningProperties = Properties().apply {
    val config = file(System.getProperty("user.home") + "/.config/nd_german_play/upload-signing.properties")
    if (config.isFile) config.inputStream().use(::load)
}

val generatedAssetsDir = layout.buildDirectory.dir("generated/ndGermanAssets")
val syncSharedAssets = tasks.register<Sync>("syncSharedAssets") {
    // Authoritative dictionary used by the desktop app.
    from(rootProject.file("../../../../../data/nd_german_project")) {
        include("dictionary.sqlite3")
    }
    // Grammar exception databases used by the desktop app.
    from(rootProject.file("../../../../data")) {
        include("irregular_verbs.yaml")
        include("irregular_adjectives.yaml")
        include("irregular_nouns.yaml")
    }
    into(generatedAssetsDir)
}

android {
    namespace = "com.ndgerman.android"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.ndgerman.android"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.1.0"

        // Shared defaults.
        buildConfigField("boolean", "PLAY_DISTRIBUTION", "false")
        buildConfigField("boolean", "ADMOB_CONFIGURED", realAdMobIdsConfigured.toString())
        buildConfigField("String", "ADMOB_BANNER_ID", "\"$admobBannerId\"")
        buildConfigField("String", "REMOVE_ADS_PRODUCT_ID", "\"remove_ads\"")
        manifestPlaceholders["dropboxKey"] = "missing_nd_german_dropbox_app_key"
        manifestPlaceholders["adMobAppId"] = admobAppId
        manifestPlaceholders["appLabel"] = "ND Deutsch"
    }

    signingConfigs {
        create("playUpload") {
            if (playSigningProperties.isNotEmpty()) {
                storeFile = file(playSigningProperties.getProperty("storeFile"))
                storePassword = playSigningProperties.getProperty("storePassword")
                keyAlias = playSigningProperties.getProperty("keyAlias")
                keyPassword = playSigningProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        getByName("debug") {
            // The owner's private build: Dropbox sync enabled, no ads at runtime.
            buildConfigField("String", "DROPBOX_APP_KEY", "\"$dropboxAppKey\"")
            manifestPlaceholders["dropboxKey"] =
                dropboxAppKey.ifBlank { "missing_nd_german_dropbox_app_key" }
        }

        create("play") {
            // This package name becomes permanent after uploading to Google Play.
            applicationIdSuffix = ".play"
            isDebuggable = false
            // Never ship an APK/AAB signed by Android's debug keystore.
            signingConfig =
                if (playSigningProperties.isNotEmpty()) signingConfigs.getByName("playUpload")
                else null

            // Public build contains no Dropbox key and uses local-only storage.
            buildConfigField("boolean", "PLAY_DISTRIBUTION", "true")
            manifestPlaceholders["dropboxKey"] = "missing_nd_german_dropbox_app_key"
            manifestPlaceholders["appLabel"] = "German Learning"
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    sourceSets.getByName("main").assets.directories.add(
        generatedAssetsDir.get().asFile.absolutePath
    )

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin {
        jvmToolchain(17)
    }

    packaging {
        resources.excludes +=
            setOf("META-INF/DEPENDENCIES", "META-INF/LICENSE*", "META-INF/NOTICE*")
    }
}

tasks.named("preBuild").configure { dependsOn(syncSharedAssets) }

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.08.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.17.0")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    debugImplementation("androidx.compose.ui:ui-tooling")
    "playImplementation"("androidx.compose.ui:ui-tooling")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("androidx.sqlite:sqlite-bundled:2.7.1")
    implementation("org.yaml:snakeyaml:2.4")

    // Dropbox exists only in the owner's private debug build.
    debugImplementation("com.dropbox.core:dropbox-core-sdk:8.0.2")
    debugImplementation("com.dropbox.core:dropbox-android-sdk:8.0.2")

    // Monetization is runtime-disabled in the owner's personal build.
    implementation("com.google.android.gms:play-services-ads:25.5.0")
    implementation("com.google.android.ump:user-messaging-platform:4.0.0")
    implementation("com.android.billingclient:billing-ktx:9.1.0")
}
