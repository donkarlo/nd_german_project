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

        buildConfigField("String", "DROPBOX_APP_KEY", "\"$dropboxAppKey\"")
        manifestPlaceholders["dropboxKey"] = dropboxAppKey.ifBlank { "missing_nd_german_dropbox_app_key" }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    sourceSets.getByName("main").assets.directories.add(generatedAssetsDir.get().asFile.absolutePath)

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin {
        jvmToolchain(17)
    }

    packaging {
        resources.excludes += setOf("META-INF/DEPENDENCIES", "META-INF/LICENSE*", "META-INF/NOTICE*")
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

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("androidx.sqlite:sqlite-bundled:2.7.1")
    implementation("org.yaml:snakeyaml:2.4")

    implementation("com.dropbox.core:dropbox-core-sdk:8.0.2")
    implementation("com.dropbox.core:dropbox-android-sdk:8.0.2")
}
