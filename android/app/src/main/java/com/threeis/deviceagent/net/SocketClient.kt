package com.threeis.deviceagent.net

import com.threeis.deviceagent.data.Config
import com.threeis.deviceagent.data.DownloadInstruction
import com.threeis.deviceagent.data.UrlInfo
import com.threeis.deviceagent.util.Logger
import org.json.JSONObject
import java.io.BufferedReader
import java.io.BufferedWriter
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.Socket
import java.util.concurrent.atomic.AtomicBoolean

class SocketClient(
    private val config: Config,
    private val onInstruction: (DownloadInstruction) -> Unit,
    private val onConnected: () -> Unit = {},
    private val onDisconnected: (String) -> Unit = {},
) {
    private val running = AtomicBoolean(false)
    private var thread: Thread? = null

    @Volatile private var currentWriter: BufferedWriter? = null
    private val writeLock = Any()

    fun start() {
        if (!running.compareAndSet(false, true)) return
        thread = Thread({ runLoop() }, "3is-socket-client").also { it.start() }
    }

    fun stop() {
        running.set(false)
        thread?.interrupt()
        thread = null
    }

    fun sendAck(payload: Map<String, Any?>) {
        val line = JSONObject(payload).toString() + "\n"
        synchronized(writeLock) {
            val w = currentWriter ?: run {
                Logger.w("sendAck called but no active connection")
                return
            }
            try {
                w.write(line)
                w.flush()
            } catch (e: Exception) {
                Logger.e("sendAck failed: ${e.message}", e)
            }
        }
    }

    private fun runLoop() {
        val backoff = longArrayOf(1_000, 2_000, 4_000, 8_000, 16_000, 30_000)
        var idx = 0
        while (running.get()) {
            try {
                Logger.i("connecting to ${config.workerHost}:${config.workerPort}")
                Socket(config.workerHost, config.workerPort).use { sock ->
                    sock.soTimeout = 0
                    val writer = BufferedWriter(OutputStreamWriter(sock.getOutputStream(), Charsets.UTF_8))
                    synchronized(writeLock) {
                        currentWriter = writer
                    }
                    try {
                        onConnected()
                        idx = 0
                        val reader = BufferedReader(InputStreamReader(sock.getInputStream()))
                        var line: String?
                        while (running.get() && reader.readLine().also { line = it } != null) {
                            val text = line ?: continue
                            val msg = tryParse(text) ?: continue
                            handleMessage(msg)
                        }
                    } finally {
                        synchronized(writeLock) {
                            currentWriter = null
                        }
                    }
                }
            } catch (e: Exception) {
                if (!running.get()) return
                Logger.w("socket error: ${e.message}")
                onDisconnected(e.message ?: "unknown")
            }
            if (!running.get()) return
            val delay = backoff[idx.coerceAtMost(backoff.lastIndex)]
            try { Thread.sleep(delay) } catch (_: InterruptedException) { return }
            idx++
        }
    }

    private fun tryParse(line: String): JSONObject? = try {
        JSONObject(line)
    } catch (e: Exception) {
        Logger.w("non-JSON line: $line")
        null
    }

    private fun handleMessage(json: JSONObject) {
        val cmd = json.optString("cmd")
        if (cmd != "DOWNLOAD_FILES") {
            Logger.w("unknown cmd=$cmd (ignored)")
            return
        }
        val p = json.optJSONObject("params") ?: return
        val txnId = p.optString("transaction_id")
        val urlsArr = p.optJSONArray("download_urls") ?: return
        val urls = (0 until urlsArr.length()).map { i ->
            val u = urlsArr.getJSONObject(i)
            UrlInfo(
                attachmentId = u.getString("attachment_id"),
                url = u.getString("url"),
                md5 = u.getString("md5"),
                ext = u.optString("ext", "bin"),
            )
        }
        onInstruction(DownloadInstruction(txnId, urls))
    }
}
