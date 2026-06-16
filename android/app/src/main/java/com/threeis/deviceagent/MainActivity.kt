package com.threeis.deviceagent

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.service.DeviceAgentService

class MainActivity : AppCompatActivity() {

    private lateinit var config: Config

    private val requestNotificationPermission = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestPermission()
    ) { granted ->
        android.widget.Toast.makeText(
            this,
            if (granted) getString(R.string.notification_permission_granted) else getString(R.string.notification_permission_denied),
            android.widget.Toast.LENGTH_SHORT
        ).show()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        config = Config.get(this)

        val etHost = findViewById<EditText>(R.id.etWorkerHost)
        val etPort = findViewById<EditText>(R.id.etWorkerPort)
        val etUrl  = findViewById<EditText>(R.id.etBackendUrl)
        val etId   = findViewById<EditText>(R.id.etDeviceId)

        etHost.setText(config.workerHost)
        etPort.setText(config.workerPort.toString())
        etUrl.setText(config.backendUrl)
        etId.setText(config.deviceId)

        findViewById<Button>(R.id.btnGrant).setOnClickListener { openManageStorageSettings() }
        findViewById<Button>(R.id.btnSave).setOnClickListener {
            val port = etPort.text.toString().toIntOrNull() ?: config.workerPort
            config.update(
                workerHost = etHost.text.toString().ifBlank { null },
                workerPort = port,
                backendUrl = etUrl.text.toString().ifBlank { null },
                deviceId = etId.text.toString().ifBlank { null },
            )
            restartService()
            Toast.makeText(this, getString(R.string.saved), Toast.LENGTH_SHORT).show()
        }
        findViewById<Button>(R.id.btnStopService).setOnClickListener {
            val i = Intent(this, DeviceAgentService::class.java).apply {
                action = DeviceAgentService.ACTION_STOP
            }
            startService(i)
        }

        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestNotificationPermission.launch(android.Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // No-op; permission status is checked at click time of btnGrant
    }

    private fun openManageStorageSettings() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                startActivity(Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                    data = Uri.parse("package:" + packageName)
                })
            } else {
                Toast.makeText(this, "Already granted", Toast.LENGTH_SHORT).show()
            }
        } else {
            Toast.makeText(this, "Pre-R devices: permission granted at install time", Toast.LENGTH_SHORT).show()
        }
    }

    private fun restartService() {
        stopService(Intent(this, DeviceAgentService::class.java))
        val i = Intent(this, DeviceAgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(i) else startService(i)
    }
}
