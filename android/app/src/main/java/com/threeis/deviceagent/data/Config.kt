package com.threeis.deviceagent.data

import android.content.Context
import android.content.SharedPreferences
import com.threeis.deviceagent.BuildConfig

class Config private constructor(private val prefs: SharedPreferences) {

    val workerHost: String =
        prefs.getString(KEY_WORKER_HOST, null) ?: BuildConfig.WORKER_HOST

    val workerPort: Int =
        prefs.getInt(KEY_WORKER_PORT, -1).takeIf { it > 0 } ?: BuildConfig.WORKER_PORT

    val backendUrl: String =
        prefs.getString(KEY_BACKEND_URL, null) ?: BuildConfig.BACKEND_URL

    val deviceId: String =
        prefs.getString(KEY_DEVICE_ID, null) ?: defaultDeviceId().also {
            prefs.edit().putString(KEY_DEVICE_ID, it).apply()
        }

    fun update(workerHost: String?, workerPort: Int?, backendUrl: String?, deviceId: String?) {
        val ed = prefs.edit()
        if (workerHost != null) ed.putString(KEY_WORKER_HOST, workerHost)
        if (workerPort != null) ed.putInt(KEY_WORKER_PORT, workerPort)
        if (backendUrl != null) ed.putString(KEY_BACKEND_URL, backendUrl)
        if (deviceId != null) ed.putString(KEY_DEVICE_ID, deviceId)
        ed.apply()
        instance = null
    }

    private fun defaultDeviceId(): String =
        "device-" + (1..3).map { ('a'..'z').random() }.joinToString("") +
        "-" + (1000..9999).random()

    companion object {
        private const val PREFS = "3is_device_agent"
        private const val KEY_WORKER_HOST = "worker_host"
        private const val KEY_WORKER_PORT = "worker_port"
        private const val KEY_BACKEND_URL = "backend_url"
        private const val KEY_DEVICE_ID = "device_id"

        @Volatile private var instance: Config? = null

        fun get(context: Context): Config =
            instance ?: synchronized(this) {
                instance ?: Config(
                    context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                ).also { instance = it }
            }
    }
}
