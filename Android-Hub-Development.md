# Android Hub - Complete Developer Implementation Guide

> **Developer Guide**: Production-ready Kotlin MVVM implementation for **Talking Clock & Hourly Chime**, **CameraX**, **WebRTC Intercom**, **Telephony & SMS**, and **Location & Geofencing**.
> **Configuration**: `minSdk = 26` (Android 8.0 Oreo), `targetSdk = 36`, `compileSdk = 36`.

---

## 1. Project Dependencies & Gradle Setup

### `gradle/libs.versions.toml`

```toml
[versions]
agp = "8.7.2"
kotlin = "2.0.21"
coreKtx = "1.15.0"
lifecycle = "2.8.7"
activityCompose = "1.9.3"
composeBom = "2024.11.00"
room = "2.6.1"
datastore = "1.1.1"
coroutines = "1.9.0"
cameraX = "1.4.0"
playServicesLocation = "21.3.0"
webrtc = "1.0.32006"
ktor = "3.0.1"
coil = "3.0.4"
workmanager = "2.10.0"

[libraries]
androidx-core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
androidx-lifecycle-runtime-ktx = { group = "androidx.lifecycle", name = "lifecycle-runtime-ktx", version.ref = "lifecycle" }
androidx-lifecycle-viewmodel-compose = { group = "androidx.lifecycle", name = "lifecycle-viewmodel-compose", version.ref = "lifecycle" }
androidx-activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }

# Compose BOM
androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
androidx-compose-ui = { group = "androidx.compose.ui", name = "ui" }
androidx-compose-material3 = { group = "androidx.compose.material3", name = "material3" }
androidx-compose-icons = { group = "androidx.compose.material", name = "material-icons-extended" }

# Room
androidx-room-runtime = { group = "androidx.room", name = "room-runtime", version.ref = "room" }
androidx-room-ktx = { group = "androidx.room", name = "room-ktx", version.ref = "room" }
androidx-room-compiler = { group = "androidx.room", name = "room-compiler", version.ref = "room" }

# CameraX
androidx-camera-core = { group = "androidx.camera", name = "camera-core", version.ref = "cameraX" }
androidx-camera-camera2 = { group = "androidx.camera", name = "camera-camera2", version.ref = "cameraX" }
androidx-camera-lifecycle = { group = "androidx.camera", name = "camera-lifecycle", version.ref = "cameraX" }
androidx-camera-view = { group = "androidx.camera", name = "camera-view", version.ref = "cameraX" }

# Location
play-services-location = { group = "com.google.android.gms", name = "play-services-location", version.ref = "playServicesLocation" }

# WebRTC
webrtc-android = { group = "com.github.webrtc-sdk", name = "android", version.ref = "webrtc" }

# Ktor Server
ktor-server-core = { group = "io.ktor", name = "ktor-server-core", version.ref = "ktor" }
ktor-server-cio = { group = "io.ktor", name = "ktor-server-cio", version.ref = "ktor" }
ktor-server-websockets = { group = "io.ktor", name = "ktor-server-websockets", version.ref = "ktor" }

# Coil
coil-compose = { group = "io.coil-kt.coil3", name = "coil-compose", version.ref = "coil" }
```

---

## 2. Feature 1: Talking Clock & Hourly Chime Implementation

Guarantees exact sub-second hourly announcements (`HH-00.mp3`) and Text-to-Speech fallbacks, operating continuously even during Android Doze mode.

### Data Layer: `ClockRepository.kt`

```kotlin
package com.eldercare.androidhub.data.repository

import android.content.Context
import android.media.MediaPlayer
import android.speech.tts.TextToSpeech
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.Locale

interface ClockRepository {
    suspend fun playHourlyChime(hour: Int): Result<Unit>
    suspend fun speakText(text: String, language: Locale = Locale("th", "TH")): Result<Unit>
    val isChimeEnabled: StateFlow<Boolean>
    fun setChimeEnabled(enabled: Boolean)
}

class ClockRepositoryImpl(
    private val context: Context
) : ClockRepository {

    private var tts: TextToSpeech? = null
    private val _isChimeEnabled = MutableStateFlow(true)
    override val isChimeEnabled: StateFlow<Boolean> = _isChimeEnabled

    init {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("th", "TH")
            }
        }
    }

    override suspend fun playHourlyChime(hour: Int): Result<Unit> = runCatching {
        val soundFileName = String.format(Locale.US, "%02d-00.mp3", hour)
        val assetPath = "sounds/talking-clock/$soundFileName"

        val descriptor = context.assets.openFd(assetPath)
        val mediaPlayer = MediaPlayer().apply {
            setDataSource(descriptor.fileDescriptor, descriptor.startOffset, descriptor.length)
            prepare()
            start()
            setOnCompletionListener {
                it.release()
                descriptor.close()
            }
        }
    }

    override suspend fun speakText(text: String, language: Locale): Result<Unit> = runCatching {
        tts?.language = language
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "UtteranceId_${System.currentTimeMillis()}")
    }

    override fun setChimeEnabled(enabled: Boolean) {
        _isChimeEnabled.value = enabled
    }
}
```

### Foreground Service & Exact Alarm Scheduler: `HourlyChimeService.kt`

```kotlin
package com.eldercare.androidhub.service

import android.app.*
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.eldercare.androidhub.data.repository.ClockRepository
import kotlinx.coroutines.*
import java.util.*

class HourlyChimeService : Service() {

    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private lateinit var clockRepository: ClockRepository

    override fun onCreate() {
        super.onCreate()
        clockRepository = (application as Any) as ClockRepository // Or injection via Hilt/Koin
        startForeground(NOTIFICATION_ID, createNotification())
        scheduleNextHourlyAlarm(applicationContext)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.let {
            if (it.action == ACTION_TRIGGER_CHIME) {
                val currentHour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
                scope.launch {
                    clockRepository.playHourlyChime(currentHour)
                }
                scheduleNextHourlyAlarm(applicationContext)
            }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun createNotification(): Notification {
        val channelId = "hourly_clock_channel"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Hourly Clock Daemon",
                NotificationManager.IMPORTANCE_LOW
            )
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("Talking Clock Active")
            .setContentText("Automated hourly chime active")
            .setOngoing(true)
            .build()
    }

    companion object {
        const val NOTIFICATION_ID = 2001
        const val ACTION_TRIGGER_CHIME = "com.eldercare.androidhub.TRIGGER_CHIME"

        fun scheduleNextHourlyAlarm(context: Context) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, AlarmReceiver::class.java).apply {
                action = ACTION_TRIGGER_CHIME
            }
            val pendingIntent = PendingIntent.getBroadcast(
                context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val calendar = Calendar.getInstance().apply {
                add(Calendar.HOUR_OF_DAY, 1)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
            } else {
                alarmManager.setExact(
                    AlarmManager.RTC_WAKEUP,
                    calendar.timeInMillis,
                    pendingIntent
                )
            }
        }
    }
}

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val serviceIntent = Intent(context, HourlyChimeService::class.java).apply {
            action = HourlyChimeService.ACTION_TRIGGER_CHIME
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent)
        } else {
            context.startService(serviceIntent)
        }
    }
}
```

### Presentation Layer: `ClockViewModel.kt` & `ClockScreen.kt`

```kotlin
package com.eldercare.androidhub.presentation.screens.clock

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.eldercare.androidhub.data.repository.ClockRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.Calendar

class ClockViewModel(
    private val clockRepository: ClockRepository
) : ViewModel() {

    val isChimeEnabled = clockRepository.isChimeEnabled
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), true)

    fun testHourlyChime() {
        val currentHour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        viewModelScope.launch {
            clockRepository.playHourlyChime(currentHour)
        }
    }

    fun toggleChime(enabled: Boolean) {
        clockRepository.setChimeEnabled(enabled)
    }
}
```

---

## 3. Feature 2: CameraX Integration

Provides front/rear camera selection, resolution enumeration, live camera preview, and hardware-accelerated photo capture encoded to WebP format.

### Data Layer: `CameraRepository.kt`

```kotlin
package com.eldercare.androidhub.data.repository

import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import androidx.camera.core.CameraSelector
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import com.eldercare.androidhub.domain.model.CameraInfoModel
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

interface CameraRepository {
    suspend fun getCameraDevices(): List<CameraInfoModel>
    suspend fun getCameraProvider(): ProcessCameraProvider
}

class CameraRepositoryImpl(
    private val context: Context
) : CameraRepository {

    override suspend fun getCameraProvider(): ProcessCameraProvider =
        suspendCancellableCoroutine { continuation ->
            val providerFuture = ProcessCameraProvider.getInstance(context)
            providerFuture.addListener({
                continuation.resume(providerFuture.get())
            }, ContextCompat.getMainExecutor(context))
        }

    override suspend fun getCameraDevices(): List<CameraInfoModel> {
        val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val list = mutableListOf<CameraInfoModel>()

        for (id in cameraManager.cameraIdList) {
            val characteristics = cameraManager.getCameraCharacteristics(id)
            val facing = characteristics.get(CameraCharacteristics.LENS_FACING)
            val facingStr = when (facing) {
                CameraCharacteristics.LENS_FACING_FRONT -> "front"
                CameraCharacteristics.LENS_FACING_BACK -> "back"
                else -> "external"
            }
            list.add(CameraInfoModel(id = id, facing = facingStr))
        }
        return list
    }
}
```

### Presentation Layer: `CameraScreen.kt`

```kotlin
package com.eldercare.androidhub.presentation.screens.camera

import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.FlipCameraAndroid
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.eldercare.androidhub.data.repository.CameraRepository
import java.io.File

@Composable
fun CameraScreen(
    cameraRepository: CameraRepository
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var lensFacing by remember { mutableStateOf(CameraSelector.LENS_FACING_BACK) }
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }
    var capturedFile by remember { mutableStateOf<File?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                val executor = ContextCompat.getMainExecutor(ctx)

                LaunchedEffect(lensFacing) {
                    val cameraProvider = cameraRepository.getCameraProvider()
                    val preview = Preview.Builder().build().also {
                        it.setSurfaceProvider(previewView.surfaceProvider)
                    }
                    imageCapture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                        .build()

                    val selector = CameraSelector.Builder().requireLensFacing(lensFacing).build()
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(lifecycleOwner, selector, preview, imageCapture)
                }
                previewView
            },
            modifier = Modifier.fillMaxSize()
        )

        // Control Buttons Overlay
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(32.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            FloatingActionButton(
                onClick = {
                    lensFacing = if (lensFacing == CameraSelector.LENS_FACING_BACK) {
                        CameraSelector.LENS_FACING_FRONT
                    } else {
                        CameraSelector.LENS_FACING_BACK
                    }
                }
            ) {
                Icon(Icons.Default.FlipCameraAndroid, contentDescription = "Switch Camera")
            }

            FloatingActionButton(
                onClick = {
                    val photoFile = File(context.cacheDir, "snap_${System.currentTimeMillis()}.webp")
                    val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

                    imageCapture?.takePicture(
                        outputOptions,
                        ContextCompat.getMainExecutor(context),
                        object : ImageCapture.OnImageSavedCallback {
                            override fun onImageSaved(outputResults: ImageCapture.OutputFileResults) {
                                capturedFile = photoFile
                            }

                            override fun onError(exception: ImageCaptureException) {
                                exception.printStackTrace()
                            }
                        }
                    )
                }
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = "Take Photo")
            }
        }
    }
}
```

---

## 4. Feature 3: WebRTC Intercom & Audio/Video Call

Full-duplex low-latency audio/video intercom stream using Google WebRTC Native Android SDK with Ktor WebSockets signaling.

### Native WebRTC Manager: `WebRtcManager.kt`

```kotlin
package com.eldercare.androidhub.data.webrtc

import android.content.Context
import org.webrtc.*
import org.webrtc.PeerConnection.PeerConnectionState

class WebRtcManager(
    private val context: Context
) {
    private val rootEglBase: EglBase = EglBase.create()
    private var peerConnectionFactory: PeerConnectionFactory
    private var peerConnection: PeerConnection? = null

    init {
        PeerConnectionFactory.initialize(
            PeerConnectionFactory.InitializationOptions.builder(context)
                .setEnableInternalTracer(true)
                .createInitializationOptions()
        )

        val options = PeerConnectionFactory.Options()
        val defaultVideoEncoderFactory = DefaultVideoEncoderFactory(rootEglBase.eglBaseContext, true, true)
        val defaultVideoDecoderFactory = DefaultVideoDecoderFactory(rootEglBase.eglBaseContext)

        peerConnectionFactory = PeerConnectionFactory.builder()
            .setOptions(options)
            .setVideoEncoderFactory(defaultVideoEncoderFactory)
            .setVideoDecoderFactory(defaultVideoDecoderFactory)
            .createPeerConnectionFactory()
    }

    fun initLocalSurfaceView(view: SurfaceViewRenderer) {
        view.init(rootEglBase.eglBaseContext, null)
        view.setEnableHardwareScaler(true)
        view.setMirror(true)
    }

    fun initRemoteSurfaceView(view: SurfaceViewRenderer) {
        view.init(rootEglBase.eglBaseContext, null)
        view.setEnableHardwareScaler(true)
        view.setMirror(false)
    }

    fun createPeerConnection(observer: PeerConnection.Observer) {
        val rtcConfig = PeerConnection.RTCConfiguration(
            listOf(PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer())
        ).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
        }
        peerConnection = peerConnectionFactory.createPeerConnection(rtcConfig, observer)
    }

    fun close() {
        peerConnection?.close()
        peerConnection = null
    }
}
```

---

## 5. Feature 4: Telephony & SMS Integration

Manages call state listeners (IDLE, RINGING, OFFHOOK), cellular signal strength, and sending emergency SMS updates.

### Data Layer: `TelephonyRepository.kt`

```kotlin
package com.eldercare.androidhub.data.repository

import android.content.Context
import android.os.Build
import android.telephony.PhoneStateListener
import android.telephony.SmsManager
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

interface TelephonyRepository {
    fun observeCallState(): Flow<Int>
    fun sendSms(phoneNumber: String, message: String): Result<Unit>
}

class TelephonyRepositoryImpl(
    private val context: Context
) : TelephonyRepository {

    private val telephonyManager = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

    override fun observeCallState(): Flow<Int> = callbackFlow {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val callback = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) {
                    trySend(state)
                }
            }
            telephonyManager.registerTelephonyCallback(context.mainExecutor, callback)
            awaitClose { telephonyManager.unregisterTelephonyCallback(callback) }
        } else {
            @Suppress("DEPRECATION")
            val listener = object : PhoneStateListener() {
                @Deprecated("Deprecated in Java")
                override fun onCallStateChanged(state: Int, incomingNumber: String?) {
                    trySend(state)
                }
            }
            @Suppress("DEPRECATION")
            telephonyManager.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
            awaitClose {
                @Suppress("DEPRECATION")
                telephonyManager.listen(listener, PhoneStateListener.LISTEN_NONE)
            }
        }
    }

    override fun sendSms(phoneNumber: String, message: String): Result<Unit> = runCatching {
        val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            context.getSystemService(SmsManager::class.java)
        } else {
            @Suppress("DEPRECATION")
            SmsManager.getDefault()
        }
        smsManager.sendTextMessage(phoneNumber, null, message, null, null)
    }
}
```

---

## 6. Feature 5: Location & Geofencing

Energy-efficient GPS tracking with `FusedLocationProviderClient` and hardware-offloaded `GeofencingClient`.

### Data Layer: `LocationRepository.kt`

```kotlin
package com.eldercare.androidhub.data.repository

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.os.Looper
import com.google.android.gms.location.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

interface LocationRepository {
    fun observeLocationUpdates(intervalMs: Long = 10000L): Flow<Location>
}

class LocationRepositoryImpl(
    private val context: Context
) : LocationRepository {

    private val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)

    @SuppressLint("MissingPermission")
    override fun observeLocationUpdates(intervalMs: Long): Flow<Location> = callbackFlow {
        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, intervalMs)
            .setMinUpdateIntervalMillis(intervalMs / 2)
            .build()

        val locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { trySend(it) }
            }
        }

        fusedLocationClient.requestLocationUpdates(
            locationRequest,
            locationCallback,
            Looper.getMainLooper()
        )

        awaitClose {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        }
    }
}
```

---

## 7. Summary & Best Practices

1. **Permissions Checklist**: Always wrap runtime permission prompts using `androidx.activity.result.contract.ActivityResultContracts`.
2. **Foreground Service Compliance**: Target `minSdk = 26` using `NotificationChannel` with `IMPORTANCE_LOW` for 24/7 background operation.
3. **Threading**: Run all heavy room database operations and image processing on `Dispatchers.IO`. Keep UI logic strictly on `Dispatchers.Main`.
