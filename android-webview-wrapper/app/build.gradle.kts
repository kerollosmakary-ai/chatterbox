val prodUrl: String = providers.gradleProperty("STUDIO_PROD_URL")
    .orElse("https://your-deployed-studio.example.com")
    .get()

val localUrl: String = providers.gradleProperty("STUDIO_LOCAL_URL")
    .orElse("http://192.168.1.100:7860")
    .get()

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ai.kerollosmakary.chatterboxwrapper"
    compileSdk = 35

    defaultConfig {
        applicationId = "ai.kerollosmakary.chatterboxwrapper"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        manifestPlaceholders["usesCleartextTraffic"] = "false"

        buildConfigField("String", "PROD_URL", "\"$prodUrl\"")
        buildConfigField("String", "LOCAL_URL", "\"$localUrl\"")
    }

    buildTypes {
        debug {
            manifestPlaceholders["usesCleartextTraffic"] = "true"
            isMinifyEnabled = false
        }
        release {
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
}
