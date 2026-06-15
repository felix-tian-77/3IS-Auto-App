package com.threeis.deviceagent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.threeis.deviceagent.MainActivity
import com.threeis.deviceagent.R
import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.download.Downloader
import com.threeis.deviceagent.download.SandboxManager
import com.threeis.deviceagent.net.BackendApi
import com.threeis.deviceagent.net.SocketClient
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicReference

class DeviceAgentService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val state = AtomicReference(STATE_INITIALIZING)

    private lateinit var config: Config
    private lateinit var sandbox: SandboxManager
    private lateinit var downloader: Downloader
    private lateinit var backend: BackendApi
    private var socket: SocketClient? = null

    override fun onCreate() {
        super.onCreate()
        config = Config.get(this)
        sandbox = SandboxManager()
        downloader = Downloader(sandbox)
        backend = BackendApi(config)
        try {
            sandbox.clear()
        } catch (se: SecurityException) {
            Logger.w("onCreate: clear() failed; will retry on next download")
        }
        startInForeground(buildNotification("INITIALIZING", getString(R.string.notification_initializing)))
        socket = SocketClient(
            config = config,
            onInstruction = { instr -> handleInstruction(instr) },
            onConnected = { setState(STATE_IDLE, getString(R.string.notification_idle)) },
            onDisconnected = { _ -> setState(STATE_INITIALIZING, getString(R.string.notification_initializing)) },
        ).also { it.start() }
        scope.launch { retryReportReady() }
    }

    private suspend fun retryReportReady() {
        val backoff = intArrayOf(1, 2, 4)
        for (delay in backoff) {
            if (backend.reportReady()) return
            kotlinx.coroutines.delay(delay * 1000L)
        }
        Logger.w("reportReady failed after retries; continuing")
    }

    private fun handleInstruction(instr: com.threeis.deviceagent.data.DownloadInstruction) {
        scope.launch {
            setState(STATE_DOWNLOADING, getString(R.string.notification_downloading_fmt, instr.urls.firstOrNull()?.attachmentId ?: "?", 1, instr.urls.size))
            var clearFailed = false
            try {
                sandbox.clear()
            } catch (se: SecurityException) {
                clearFailed = true
            }
            val results: List<DownloadResult> = downloader.downloadAll(instr)
            val allOk = results.isNotEmpty() && results.all { it.success }
            backend.reportDownloadAck(
                transactionId = instr.transactionId,
                files = results,
                allSuccess = allOk,
                sandboxClearFailed = clearFailed,
            )
            setState(STATE_IDLE, getString(R.string.notification_idle))
        }
    }

    private fun setState(newState: String, text: String) {
        state.set(newState)
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIF_ID, buildNotification(newState, text))
    }

    private fun buildNotification(stateName: String, text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(pi)
            .setOngoing(true)
            .build()
    }

    private fun startInForeground(notification: Notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java)
            if (nm.getNotificationChannel(CHANNEL_ID) == null) {
                nm.createNotificationChannel(
                    NotificationChannel(
                        CHANNEL_ID,
                        getString(R.string.channel_name),
                        NotificationManager.IMPORTANCE_LOW,
                    ).apply { description = getString(R.string.channel_description) }
                )
            }
        }
        startForeground(NOTIF_ID, notification)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        socket?.stop()
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val NOTIF_ID = 1
        private const val CHANNEL_ID = "3is_device_agent"
        const val ACTION_STOP = "com.threeis.deviceagent.action.STOP"
        const val STATE_INITIALIZING = "INITIALIZING"
        const val STATE_IDLE = "IDLE"
        const val STATE_DOWNLOADING = "DOWNLOADING"
    }
}
