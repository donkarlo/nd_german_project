package com.ndgerman.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import com.ndgerman.android.ui.GermanApp
import com.ndgerman.android.ui.GermanViewModel
import com.ndgerman.android.ui.theme.NDGermanTheme

class MainActivity : ComponentActivity() {
    private val viewModel: GermanViewModel by viewModels {
        GermanViewModel.Factory(application as GermanApplication)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            NDGermanTheme { GermanApp(viewModel) }
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.finishDropboxAuthentication()
    }
}
