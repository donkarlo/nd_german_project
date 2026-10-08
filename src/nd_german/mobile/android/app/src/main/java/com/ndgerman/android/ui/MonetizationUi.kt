package com.ndgerman.android.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView

@Composable
fun MonetizationBanner(adUnitId: String) {
    val context = LocalContext.current
    val adView =
        remember(adUnitId) {
            AdView(context).apply {
                setAdSize(AdSize.BANNER)
                this.adUnitId = adUnitId
                loadAd(AdRequest.Builder().build())
            }
        }

    DisposableEffect(adView) {
        onDispose { adView.destroy() }
    }

    Box(
        modifier = Modifier.fillMaxWidth().height(50.dp),
        contentAlignment = Alignment.Center,
    ) {
        AndroidView(
            factory = { adView },
            modifier = Modifier.width(320.dp).height(50.dp),
        )
    }
}
