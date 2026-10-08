package com.ndgerman.android.monetization

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import com.google.android.gms.ads.MobileAds
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform
import com.ndgerman.android.BuildConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class MonetizationState(
    val playDistribution: Boolean = BuildConfig.PLAY_DISTRIBUTION,
    val adFree: Boolean = !BuildConfig.PLAY_DISTRIBUTION,
    val canRequestAds: Boolean = false,
    val billingReady: Boolean = false,
    val removeAdsPrice: String? = null,
    val privacyOptionsRequired: Boolean = false,
    val message: String? = null,
) {
    val showAds: Boolean
        get() = playDistribution && !adFree && canRequestAds
}

class MonetizationManager(context: Context) {
    private val appContext = context.applicationContext
    private val prefs =
        appContext.getSharedPreferences("nd_german_monetization", Context.MODE_PRIVATE)

    private val _state = MutableStateFlow(
        MonetizationState(
            adFree = !BuildConfig.PLAY_DISTRIBUTION || prefs.getBoolean("ad_free", false),
        )
    )
    val state: StateFlow<MonetizationState> = _state.asStateFlow()

    private var adsInitialized = false
    private var productDetails: ProductDetails? = null

    private val purchasesUpdatedListener =
        PurchasesUpdatedListener { billingResult, purchases ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK &&
                purchases != null
            ) {
                handleOwnedPurchases(purchases, authoritative = false)
            } else if (billingResult.responseCode != BillingClient.BillingResponseCode.USER_CANCELED) {
                _state.update { it.copy(message = billingResult.debugMessage) }
            }
        }

    private val billingClient: BillingClient? =
        if (BuildConfig.PLAY_DISTRIBUTION) {
            BillingClient.newBuilder(appContext)
                .setListener(purchasesUpdatedListener)
                .enablePendingPurchases(
                    PendingPurchasesParams.newBuilder()
                        .enableOneTimeProducts()
                        .build()
                )
                .build()
        } else {
            null
        }

    fun start(activity: Activity) {
        if (!BuildConfig.PLAY_DISTRIBUTION) return
        startBilling()
        requestConsent(activity)
    }

    fun refreshPurchases() {
        if (!BuildConfig.PLAY_DISTRIBUTION) return
        val client = billingClient ?: return
        if (!client.isReady) {
            startBilling()
            return
        }
        queryOwnedPurchases()
    }

    private fun startBilling() {
        val client = billingClient ?: return
        if (client.isReady) {
            _state.update { it.copy(billingReady = true) }
            queryOwnedPurchases()
            queryRemoveAdsProduct()
            return
        }

        client.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                val ready =
                    billingResult.responseCode == BillingClient.BillingResponseCode.OK
                _state.update {
                    it.copy(
                        billingReady = ready,
                        message = if (ready) it.message else billingResult.debugMessage,
                    )
                }
                if (ready) {
                    queryOwnedPurchases()
                    queryRemoveAdsProduct()
                }
            }

            override fun onBillingServiceDisconnected() {
                _state.update { it.copy(billingReady = false) }
            }
        })
    }

    private fun queryOwnedPurchases() {
        val client = billingClient ?: return
        if (!client.isReady) return

        val params =
            QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.INAPP)
                .build()

        client.queryPurchasesAsync(params) { billingResult, purchases ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                handleOwnedPurchases(purchases, authoritative = true)
            }
        }
    }

    private fun handleOwnedPurchases(
        purchases: List<Purchase>,
        authoritative: Boolean,
    ) {
        val owned =
            purchases.any { purchase ->
                BuildConfig.REMOVE_ADS_PRODUCT_ID in purchase.products &&
                    purchase.purchaseState == Purchase.PurchaseState.PURCHASED
            }

        if (owned || authoritative) {
            prefs.edit().putBoolean("ad_free", owned).apply()
            _state.update { it.copy(adFree = owned) }
        }

        purchases
            .filter {
                BuildConfig.REMOVE_ADS_PRODUCT_ID in it.products &&
                    it.purchaseState == Purchase.PurchaseState.PURCHASED &&
                    !it.isAcknowledged
            }
            .forEach(::acknowledgePurchase)
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        val client = billingClient ?: return
        val params =
            AcknowledgePurchaseParams.newBuilder()
                .setPurchaseToken(purchase.purchaseToken)
                .build()

        client.acknowledgePurchase(params) { billingResult ->
            if (billingResult.responseCode != BillingClient.BillingResponseCode.OK) {
                _state.update { it.copy(message = billingResult.debugMessage) }
            }
        }
    }

    private fun queryRemoveAdsProduct() {
        val client = billingClient ?: return
        if (!client.isReady) return

        val params =
            QueryProductDetailsParams.newBuilder()
                .setProductList(
                    listOf(
                        QueryProductDetailsParams.Product.newBuilder()
                            .setProductId(BuildConfig.REMOVE_ADS_PRODUCT_ID)
                            .setProductType(BillingClient.ProductType.INAPP)
                            .build()
                    )
                )
                .build()

        client.queryProductDetailsAsync(params) { billingResult, result ->
            if (billingResult.responseCode != BillingClient.BillingResponseCode.OK) {
                return@queryProductDetailsAsync
            }

            productDetails =
                result.productDetailsList.firstOrNull {
                    it.productId == BuildConfig.REMOVE_ADS_PRODUCT_ID
                }

            val price =
                productDetails
                    ?.oneTimePurchaseOfferDetailsList
                    ?.firstOrNull()
                    ?.formattedPrice

            _state.update { it.copy(removeAdsPrice = price) }
        }
    }

    fun purchaseRemoveAds(activity: Activity) {
        if (!BuildConfig.PLAY_DISTRIBUTION || _state.value.adFree) return

        val client = billingClient
        val details = productDetails
        if (client == null || !client.isReady || details == null) {
            _state.update { it.copy(message = "Google Play purchase is not ready yet.") }
            startBilling()
            return
        }

        val productBuilder =
            BillingFlowParams.ProductDetailsParams.newBuilder()
                .setProductDetails(details)

        details.oneTimePurchaseOfferDetailsList
            ?.firstOrNull()
            ?.offerToken
            ?.takeIf { it.isNotBlank() }
            ?.let(productBuilder::setOfferToken)

        val flowParams =
            BillingFlowParams.newBuilder()
                .setProductDetailsParamsList(listOf(productBuilder.build()))
                .build()

        val result = client.launchBillingFlow(activity, flowParams)
        if (result.responseCode != BillingClient.BillingResponseCode.OK) {
            _state.update { it.copy(message = result.debugMessage) }
        }
    }

    private fun requestConsent(activity: Activity) {
        val consentInformation = UserMessagingPlatform.getConsentInformation(activity)
        val params = ConsentRequestParameters.Builder().build()

        consentInformation.requestConsentInfoUpdate(
            activity,
            params,
            {
                updatePrivacyState(consentInformation)
                UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity) { formError ->
                    if (formError != null) {
                        _state.update { it.copy(message = formError.message) }
                    }
                    updatePrivacyState(consentInformation)
                    initializeAdsIfAllowed()
                }
            },
            { requestError ->
                _state.update { it.copy(message = requestError.message) }
                updatePrivacyState(consentInformation)
                initializeAdsIfAllowed()
            },
        )
    }

    private fun updatePrivacyState(consentInformation: ConsentInformation) {
        _state.update {
            it.copy(
                canRequestAds = consentInformation.canRequestAds(),
                privacyOptionsRequired =
                    consentInformation.privacyOptionsRequirementStatus ==
                        ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED,
            )
        }
    }

    private fun initializeAdsIfAllowed() {
        if (!_state.value.showAds || adsInitialized) return
        adsInitialized = true
        MobileAds.initialize(appContext)
    }

    fun showPrivacyOptions(activity: Activity) {
        if (!BuildConfig.PLAY_DISTRIBUTION || !_state.value.privacyOptionsRequired) return

        val consentInformation = UserMessagingPlatform.getConsentInformation(activity)
        UserMessagingPlatform.showPrivacyOptionsForm(activity) { formError ->
            if (formError != null) {
                _state.update { it.copy(message = formError.message) }
            }
            updatePrivacyState(consentInformation)
            initializeAdsIfAllowed()
        }
    }
}
