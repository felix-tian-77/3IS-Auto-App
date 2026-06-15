package com.threeis.deviceagent.net

import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadResult
import com.threeis.deviceagent.util.Logger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class BackendApi(private val config: Config) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun reportReady(): Boolean = withContext(Dispatchers.IO) {
        val body = JSONObject().put("status", "READY").toString()
        post("/devices/${config.deviceId}/ready", body)
    }

    suspend fun reportDownloadAck(
        transactionId: String,
        files: List<DownloadResult>,
        allSuccess: Boolean,
        sandboxClearFailed: Boolean,
    ): Boolean = withContext(Dispatchers.IO) {
        val arr = JSONArray()
        for (f in files) {
            val o = JSONObject()
                .put("attachment_id", f.attachmentId)
                .put("local_path", f.localPath)
                .put("success", f.success)
            if (f.errorReason != null) o.put("error_reason", f.errorReason)
            arr.put(o)
        }
        val body = JSONObject()
            .put("transaction_id", transactionId)
            .put("files", arr)
            .put("all_success", allSuccess)
            .put("sandbox_clear_failed", sandboxClearFailed)
            .put("completed_at", System.currentTimeMillis())
            .toString()
        post("/devices/${config.deviceId}/download-ack", body)
    }

    private fun post(path: String, jsonBody: String): Boolean {
        val url = config.backendUrl.trimEnd('/') + path
        val req = Request.Builder()
            .url(url)
            .post(jsonBody.toRequestBody(JSON))
            .build()
        return try {
            http.newCall(req).execute().use { resp ->
                if (resp.isSuccessful) true
                else {
                    Logger.w("Backend $path → ${resp.code}")
                    false
                }
            }
        } catch (e: Exception) {
            Logger.e("Backend $path failed: ${e.message}", e)
            false
        }
    }

    companion object {
        private val JSON = "application/json; charset=utf-8".toMediaType()
    }
}
