package com.threeis.deviceagent

import android.app.Application
import android.content.Intent
import android.os.Build
import com.threeis.deviceagent.service.DeviceAgentService

class DeviceAgentApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        val i = Intent(this, DeviceAgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i) else startService(i)
    }
}
